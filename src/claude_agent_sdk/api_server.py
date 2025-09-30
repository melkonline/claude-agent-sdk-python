"""
HTTP API Server for Claude Agent SDK
Exposes ClaudeSDKClient functionality via REST API endpoints
"""

import asyncio
import uuid
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, create_sdk_mcp_server, tool
from claude_agent_sdk.query import query as sdk_query


# ============================================
# Pydantic Models for API Request/Response
# ============================================

class QueryRequest(BaseModel):
    """Request model for querying Claude"""
    prompt: str = Field(..., description="The prompt to send to Claude")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Claude Agent options")
    stream: bool = Field(default=True, description="Whether to stream the response")


class SessionCreateRequest(BaseModel):
    """Request model for creating a session"""
    options: Optional[Dict[str, Any]] = Field(default=None, description="Claude Agent options")


class SessionQueryRequest(BaseModel):
    """Request model for querying in a session"""
    prompt: str = Field(..., description="The prompt to send to Claude")
    stream: bool = Field(default=True, description="Whether to stream the response")


class ToolDefinition(BaseModel):
    """Tool definition for custom tools"""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    input_schema: Dict[str, Any] = Field(..., description="Tool input schema")


class SessionResponse(BaseModel):
    """Response model for session creation"""
    session_id: str
    message: str


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None


# ============================================
# Session Management
# ============================================

class SessionManager:
    """Manages active Claude SDK client sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, ClaudeSDKClient] = {}
        self.session_options: Dict[str, ClaudeAgentOptions] = {}
    
    async def create_session(self, options: Optional[ClaudeAgentOptions] = None) -> str:
        """Create a new session and return session ID"""
        session_id = str(uuid.uuid4())
        
        if options is None:
            options = ClaudeAgentOptions()
        
        client = ClaudeSDKClient(options=options)
        await client.__aenter__()
        
        self.sessions[session_id] = client
        self.session_options[session_id] = options
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ClaudeSDKClient]:
        """Get a session by ID"""
        return self.sessions.get(session_id)
    
    async def close_session(self, session_id: str) -> bool:
        """Close and remove a session"""
        if session_id in self.sessions:
            client = self.sessions[session_id]
            await client.__aexit__(None, None, None)
            del self.sessions[session_id]
            if session_id in self.session_options:
                del self.session_options[session_id]
            return True
        return False
    
    async def close_all_sessions(self):
        """Close all active sessions"""
        for session_id in list(self.sessions.keys()):
            await self.close_session(session_id)
    
    def list_sessions(self) -> List[str]:
        """List all active session IDs"""
        return list(self.sessions.keys())


# ============================================
# FastAPI Application
# ============================================

# Global session manager
session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    print(" Claude Agent SDK API Server starting up...")
    yield
    # Shutdown
    print(" Shutting down Claude Agent SDK API Server...")
    await session_manager.close_all_sessions()


app = FastAPI(
    title="Claude Agent SDK API",
    description="HTTP API for Claude Agent SDK - Exposes ClaudeSDKClient functionality",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================
# Health Check Endpoint
# ============================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "claude-agent-sdk-api",
        "active_sessions": len(session_manager.sessions)
    }


# ============================================
# Simple Query Endpoints (Stateless)
# ============================================

@app.post("/query", tags=["Query"])
async def query_claude(request: QueryRequest):
    """
    Query Claude with a prompt (stateless).
    This uses the simple query() function without maintaining session state.
    """
    try:
        # Convert options dict to ClaudeAgentOptions if provided
        options = None
        if request.options:
            options = ClaudeAgentOptions(**request.options)
        
        if request.stream:
            async def generate():
                try:
                    async for message in sdk_query(request.prompt, options=options):
                        # Format each message as JSON and yield
                        import json
                        yield f"data: {json.dumps({'type': 'message', 'content': str(message)})}\n\n"
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # Non-streaming response - collect all messages
            messages = []
            async for message in sdk_query(request.prompt, options=options):
                messages.append(str(message))
            
            return JSONResponse({
                "status": "success",
                "messages": messages
            })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Session-based Endpoints (Stateful)
# ============================================

@app.post("/sessions", response_model=SessionResponse, tags=["Sessions"])
async def create_session(request: SessionCreateRequest):
    """
    Create a new Claude SDK client session.
    Sessions maintain state and context across multiple queries.
    """
    try:
        # Convert options dict to ClaudeAgentOptions if provided
        options = None
        if request.options:
            options = ClaudeAgentOptions(**request.options)
        
        session_id = await session_manager.create_session(options)
        
        return SessionResponse(
            session_id=session_id,
            message="Session created successfully"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions", tags=["Sessions"])
async def list_sessions():
    """List all active sessions"""
    return {
        "sessions": session_manager.list_sessions(),
        "count": len(session_manager.sessions)
    }


@app.get("/sessions/{session_id}", tags=["Sessions"])
async def get_session_info(session_id: str):
    """Get information about a specific session"""
    client = session_manager.get_session(session_id)
    
    if not client:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "status": "active"
    }


@app.post("/sessions/{session_id}/query", tags=["Sessions"])
async def query_session(session_id: str, request: SessionQueryRequest):
    """
    Query Claude within an existing session.
    This maintains conversation context across multiple queries.
    """
    client = session_manager.get_session(session_id)
    
    if not client:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Send query to the session
        await client.query(request.prompt)
        
        if request.stream:
            async def generate():
                try:
                    async for message in client.receive_response():
                        import json
                        yield f"data: {json.dumps({'type': 'message', 'content': str(message)})}\n\n"
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # Non-streaming response
            messages = []
            async for message in client.receive_response():
                messages.append(str(message))
            
            return JSONResponse({
                "status": "success",
                "session_id": session_id,
                "messages": messages
            })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sessions/{session_id}", tags=["Sessions"])
async def delete_session(session_id: str):
    """Delete a session and clean up resources"""
    success = await session_manager.close_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "status": "success",
        "message": f"Session {session_id} deleted successfully"
    }


# ============================================
# Main Entry Point
# ============================================

def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Start the API server"""
    uvicorn.run(
        "claude_agent_sdk.api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Claude Agent SDK API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    start_server(host=args.host, port=args.port, reload=args.reload)
