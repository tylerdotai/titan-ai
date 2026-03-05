# Titan AI

Local AI code generation platform - powered by qwen3.5 running on your own hardware.

## Features

- **Ask Titan** - Chat with local AI to generate code in real-time
- **Task Manager** - Full CRUD task management with authentication
- **Streaming Responses** - Watch code appear as it's generated
- **Privacy First** - All data stays on your network

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JS + Svelte
- **Database**: SQLite
- **AI**: qwen3.5-35b (local)

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn sqlalchemy python-multipart

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8766
```

## Authentication

The app requires login before access. Create users via the API:

```python
import hashlib
# Create user manually or via registration endpoint
```

Default endpoints:
- POST /register - Create new account
- POST /token - Login and get JWT token

## Access

- Local: http://localhost:8766
- Network: http://YOUR_IP:8766
- Remote: Use Cloudflare Tunnel

## Architecture

```
User → FastAPI → SQLite (tasks)
         ↓
    qwen3.5-35b (Titan)
```

## License

MIT License - See LICENSE file
