"""
main.py
-------
FastAPI server for the Repo Analyzer.
Loads .env automatically and serves the analysis API.
"""

import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

# ── Load environment variables ─────────────────────────────────────────
# Priority: .env (user-specific, gitignored) > .env.example (template)
env_path = Path(__file__).parent / ".env"
env_example_path = Path(__file__).parent / ".env.example"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    loaded_from = ".env"
elif env_example_path.exists():
    # Auto-copy .env.example to .env so the user doesn't have to
    shutil.copy2(str(env_example_path), str(env_path))
    load_dotenv(dotenv_path=env_path)
    loaded_from = ".env.example (auto-copied to .env)"
else:
    loaded_from = "environment variables only (no .env or .env.example found)"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from analyzer import analyze_repo
from ai_summary import get_summary
from pydantic import BaseModel

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# ── Validate LLM configuration ────────────────────────────────────────
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
LLM_KEYS = {
    "gemini": bool(os.environ.get("GEMINI_API_KEY")),
    "openai": bool(os.environ.get("OPENAI_API_KEY")),
    "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
}
LLM_CONFIGURED = LLM_KEYS.get(LLM_PROVIDER, False)

if not LLM_CONFIGURED:
    print(f"⚠️  WARNING: LLM provider is '{LLM_PROVIDER}' but no API key is set.", file=sys.stderr)
    print(f"   Set {LLM_PROVIDER.upper()}_API_KEY in backend/.env", file=sys.stderr)
    print(f"   AI file summaries will fail until this is configured.", file=sys.stderr)
else:
    print(f"✓  LLM configured: {LLM_PROVIDER}")

app = FastAPI(
    title="Repo Analyzer API",
    description="Visualize and understand any local Git repository",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.get("/analyze")
def analyze(path: str):
    """
    Walk a local repository and return nodes + edges.
    ?path=/absolute/path/to/your/project
    """
    if not path or not path.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'path' is required")
    try:
        return analyze_repo(path.strip())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied: {path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SummaryRequest(BaseModel):
    file_path: str  # absolute path to the file
    rel_path: str   # relative path (used as cache key)


@app.post("/summarize")
def summarize(req: SummaryRequest):
    """
    Return an AI-generated plain-English summary for a single file.
    Results are cached by (rel_path, content_hash) so re-requests are free.
    """
    if not req.file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    if not req.rel_path:
        raise HTTPException(status_code=400, detail="rel_path is required")

    # Check if LLM is configured before attempting
    if not LLM_CONFIGURED:
        raise HTTPException(
            status_code=503,
            detail=(
                f"LLM provider '{LLM_PROVIDER}' is not configured. "
                f"Set {LLM_PROVIDER.upper()}_API_KEY in backend/.env "
                f"(or backend/.env.example) and restart the server."
            ),
        )

    try:
        result = get_summary(req.file_path, req.rel_path)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")
    except KeyError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Missing API key environment variable: {e}. Check backend/.env",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "provider": LLM_PROVIDER,
        "llm_configured": LLM_CONFIGURED,
        "env_loaded_from": loaded_from,
        "keys_available": {
            "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
            "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
            "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        },
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print(f"Server starting on http://{HOST}:{PORT}")
    print(f"  LLM Provider: {LLM_PROVIDER}")
    print(f"  LLM Key set:  {LLM_CONFIGURED}")
    print(f"  Env loaded:   {loaded_from}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)