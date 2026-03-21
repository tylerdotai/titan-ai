# Titan AI

Local AI code generation platform built for private, GPU-backed development on your own hardware.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?style=flat-square&logo=fastapi)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Live Demo

- Repository: `https://github.com/tylerdotai/titan-ai`
- Local app URL: `http://localhost:3000`

## About

Titan AI is a local-first coding assistant that keeps inference on your own hardware. The current repo combines a FastAPI backend, a static web interface, lightweight auth, and streaming chat endpoints that connect to a local model server for code generation and related tasks.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI |
| Database | SQLite |
| Auth | OAuth2-style token flow |
| Inference | Local model server over HTTP |
| Frontend | Static HTML in `app/static/` |

## Features

### Core Product
- Local code generation with private inference flow
- Streaming chat endpoint in `/chat/stream`
- Text-to-speech endpoint for audio output
- Lightweight auth and user/task storage

### Repo Surface
- Single FastAPI app in `app/main.py`
- Static frontend bundled in `app/static/`
- SQLite-backed local state in `tasks.db`

## Project Structure

```text
app/main.py           FastAPI app, auth, chat, and TTS endpoints
app/static/index.html Local web interface
tasks.db              SQLite data store
LICENSE               MIT license
README.md             Project overview
```

## Getting Started

### Prerequisites

- Python 3.10+
- A reachable local model server for inference
- `pip`

### Installation

```bash
git clone https://github.com/tylerdotai/titan-ai.git
cd titan-ai
pip install fastapi uvicorn sqlalchemy requests httpx python-multipart
```

## Deployment

Titan AI is currently optimized for local/self-hosted use.

- Repository: `https://github.com/tylerdotai/titan-ai`
- Local app URL: `http://localhost:3000`

## Usage

```bash
uvicorn app.main:app --reload --port 3000
```

## Current Limitations

- Local model server endpoints are hard-coded in the app
- Dependency management is implicit rather than fully packaged
- The current frontend is lightweight and not split into a separate modern web app

## Roadmap

- Externalize model server configuration cleanly
- Add a formal dependency file and reproducible setup flow
- Improve the frontend experience for multi-step coding workflows
- Expand model and deployment flexibility across local hardware setups

## License

MIT License - see `LICENSE` for details.
