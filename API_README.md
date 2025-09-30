# Claude Agent SDK HTTP API

This HTTP API exposes the functionality of the Claude Agent SDK through REST endpoints.

## Quick Start

### Using Docker (Recommended)

1. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

2. **Build and run:**
   ```bash
   make build
   make run
   ```

3. **Access the API:**
   - API Base URL: `http://localhost:8000`
   - Interactive API Docs: `http://localhost:8000/docs`
   - Alternative Docs: `http://localhost:8000/redoc`

### Using Python Directly

```bash
# Install dependencies
pip install -e ".[api-server]"

# Set API key
export ANTHROPIC_API_KEY=your_key_here

# Run the server
python -m claude_agent_sdk.api_server --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check

```bash
GET /health
```

### Stateless Query (Simple)

```bash
POST /query
Content-Type: application/json

{
  "prompt": "What is 2 + 2?",
  "stream": false,
  "options": {
    "cwd": "/path/to/working/directory"
  }
}
```

### Session Management

#### Create Session

```bash
POST /sessions
Content-Type: application/json

{
  "options": {
    "cwd": "/path/to/project"
  }
}

# Response:
{
  "session_id": "uuid-here",
  "message": "Session created successfully"
}
```

#### List Sessions

```bash
GET /sessions
```

#### Query Within Session

```bash
POST /sessions/{session_id}/query
Content-Type: application/json

{
  "prompt": "Review the code in main.py",
  "stream": true
}
```

#### Delete Session

```bash
DELETE /sessions/{session_id}
```

## Usage Examples

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Simple query (non-streaming)
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello Claude!", "stream": false}'

# Create a session
SESSION_ID=$(curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{}' | jq -r '.session_id')

# Query in session
curl -X POST http://localhost:8000/sessions/$SESSION_ID/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is Python?", "stream": false}'

# Delete session
curl -X DELETE http://localhost:8000/sessions/$SESSION_ID
```

### Python Client Example

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000"

# Simple query
response = requests.post(
    f"{BASE_URL}/query",
    json={
        "prompt": "Write a hello world in Python",
        "stream": False
    }
)
print(response.json())

# Session-based interaction
# 1. Create session
session_resp = requests.post(f"{BASE_URL}/sessions", json={})
session_id = session_resp.json()["session_id"]

# 2. Query in session
query_resp = requests.post(
    f"{BASE_URL}/sessions/{session_id}/query",
    json={
        "prompt": "Create a factorial function",
        "stream": False
    }
)
print(query_resp.json())

# 3. Follow-up query in same session
followup_resp = requests.post(
    f"{BASE_URL}/sessions/{session_id}/query",
    json={
        "prompt": "Now add error handling to the function",
        "stream": False
    }
)
print(followup_resp.json())

# 4. Clean up
requests.delete(f"{BASE_URL}/sessions/{session_id}")
```

### JavaScript/TypeScript Example

```typescript
const BASE_URL = "http://localhost:8000";

// Simple query
async function simpleQuery() {
  const response = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: "Hello Claude!",
      stream: false
    })
  });
  const data = await response.json();
  console.log(data);
}

// Session-based interaction
async function sessionQuery() {
  // Create session
  const sessionResp = await fetch(`${BASE_URL}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  });
  const { session_id } = await sessionResp.json();

  // Query
  const queryResp = await fetch(`${BASE_URL}/sessions/${session_id}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: "Write a quicksort in JavaScript",
      stream: false
    })
  });
  const result = await queryResp.json();
  console.log(result);

  // Clean up
  await fetch(`${BASE_URL}/sessions/${session_id}`, { method: "DELETE" });
}
```

## Docker Commands

```bash
# Build the image
docker-compose build

# Start the server
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the server
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

## Environment Variables

- `ANTHROPIC_API_KEY` - Your Anthropic API key (required)
- `CLAUDE_CODE_USE_BEDROCK` - Set to `1` to use AWS Bedrock
- `CLAUDE_CODE_USE_VERTEX` - Set to `1` to use Google Vertex AI

## Port Configuration

By default, the API runs on port 8000. To change:

```bash
# In docker-compose.yml, modify:
ports:
  - "9000:8000"  # Maps host port 9000 to container port 8000
```

## Troubleshooting

### API Key Not Set

If you get authentication errors, ensure `ANTHROPIC_API_KEY` is set:

```bash
echo $ANTHROPIC_API_KEY  # Should show your key
```

### Port Already in Use

If port 8000 is busy:

```bash
# Option 1: Change port in docker-compose.yml
# Option 2: Stop other services using port 8000
lsof -ti:8000 | xargs kill
```

### Container Won't Start

Check logs:

```bash
docker-compose logs claude-agent-api
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json
