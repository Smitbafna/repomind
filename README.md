# RepoMind

**Agentic Code Intelligence Platform** — Backend Foundation

RepoMind is an open-source platform for understanding software repositories through intelligent code analysis. This repository contains the backend foundation built with clean architecture principles, designed to eventually support LangChain, LangGraph, GraphRAG, CRAG, hybrid retrieval, and GitHub API integrations.

> **⚠️ Current Status:** MVP — Repository Ingestion only. No AI functionality has been implemented yet.

## Architecture

```
backend/
├── api/                    # FastAPI application layer
│   ├── main.py             # App factory, lifespan, CORS
│   ├── dependencies.py     # FastAPI dependency injection
│   └── routes/
│       ├── health.py       # GET / health check
│       └── repositories.py # POST /repositories/ingest, GET /repositories
│
├── core/                   # Business logic (no framework coupling)
│   └── ingestion/
│       ├── types.py        # Dataclass DTOs
│       ├── clone.py        # GitHub URL parsing & git clone
│       ├── scanner.py      # Recursive file scanning
│       ├── metadata.py     # Git metadata extraction
│       └── service.py      # Ingestion orchestrator
│
├── database/               # Persistence layer
│   ├── models.py           # SQLAlchemy ORM models
│   ├── database.py         # Engine & session factories
│   ├── session.py          # Session lifecycle manager
│   └── repositories.py     # Repository pattern DAOs
│
├── config/
│   └── settings.py         # Pydantic Settings (env-based)
│
├── schemas/                # Pydantic request/response models
│   └── ingestion.py
│
└── utils/
    └── logging.py          # Logging configuration

cli/                        # Typer CLI
└── main.py                 # repomind init-db, ingest, list-repos
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12+ |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.x (async) |
| Validation | Pydantic v2 |
| CLI | Typer |
| Git | GitPython |
| Database | SQLite (via aiosqlite) |
| Package Manager | uv |

## Quick Start

```bash
# Install dependencies
uv sync

# Start the API server
uv run uvicorn backend.api.main:app --reload

# Or use the CLI
uv run repomind init-db
uv run repomind ingest https://github.com/octocat/Hello-World
uv run repomind list-repos
```

## API Endpoints

### `GET /`
Health check.

```json
{"status": "ok"}
```

### `POST /repositories/ingest`
Ingest a GitHub repository.

**Request:**
```json
{"url": "https://github.com/owner/repo"}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "repo",
  "owner": "owner",
  "files": 42,
  "path": "/path/to/clone",
  "status": "completed"
}
```

### `GET /repositories`
List all ingested repositories.

## Design Principles

- **Layered architecture** — API layer never contains business logic
- **Dependency injection** — Services receive their dependencies explicitly
- **Repository pattern** — Database access is abstracted behind DAO classes
- **Single responsibility** — Every class has one clear purpose
- **Type hints everywhere** — Full static type coverage
- **No global mutable state** — All state is managed through dependency injection
- **Future-proof** — Core modules are isolated and ready for AI integration

## Future Roadmap

- [ ] LangChain integration
- [ ] LangGraph workflows
- [ ] GraphRAG knowledge graphs
- [ ] CRAG (Corrective RAG)
- [ ] Hybrid retrieval (BM25 + embeddings)
- [ ] GitHub API integration
- [ ] React dashboard
- [ ] VS Code extension
- [ ] Advanced CLI features