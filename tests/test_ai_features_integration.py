"""Integration tests for AI features (indexing, query, ask)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.api.main import app
from backend.config.settings import get_settings

# Test repository ID (AssignMentor)
TEST_REPO_ID = "01981d63-7bd7-459e-af26-d8a80617d499"


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def settings():
    """Get settings."""
    return get_settings()


class TestAIServices:
    """Test AI features require Qdrant and Ollama."""

    def test_configuration_loaded(self, settings):
        """Test that configuration is loaded correctly."""
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.qdrant_url == "http://localhost:6333"
        assert settings.ollama_embedding_model == "nomic-embed-text"
        assert settings.ollama_chat_model == "llama3.2"

    def test_index_repository(self, client):
        """Test indexing a repository."""
        response = client.post(f"/repositories/{TEST_REPO_ID}/index")
        
        # Print detailed error info
        if response.status_code != 200:
            print(f"\n=== INDEX ERROR ===")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            print(f"Headers: {dict(response.headers)}")
        
        # Should return 200 with documents_indexed
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "documents_indexed" in data
        assert data["documents_indexed"] > 0

    def test_vector_search(self, client):
        """Test vector search."""
        response = client.post(
            f"/repositories/{TEST_REPO_ID}/query",
            json={"query": "authentication", "retriever": "vector", "top_k": 3}
        )
        
        # Print detailed error info
        if response.status_code != 200:
            print(f"\n=== VECTOR SEARCH ERROR ===")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data

    def test_keyword_search(self, client):
        """Test keyword search."""
        response = client.post(
            f"/repositories/{TEST_REPO_ID}/query",
            json={"query": "class", "retriever": "keyword", "top_k": 3}
        )
        
        if response.status_code != 200:
            print(f"\n=== KEYWORD SEARCH ERROR ===")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_hybrid_search(self, client):
        """Test hybrid search."""
        response = client.post(
            f"/repositories/{TEST_REPO_ID}/query",
            json={"query": "assignment", "retriever": "hybrid", "top_k": 3}
        )
        
        if response.status_code != 200:
            print(f"\n=== HYBRID SEARCH ERROR ===")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_ask_question(self, client):
        """Test question answering."""
        response = client.post(
            f"/repositories/{TEST_REPO_ID}/ask",
            json={"question": "What is the main purpose of this repository?"}
        )
        
        if response.status_code != 200:
            print(f"\n=== ASK QUESTION ERROR ===")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert len(data["answer"]) > 0

    def test_graphrag_query(self, client):
        """Test GraphRAG query."""
        response = client.post(
            f"/repositories/{TEST_REPO_ID}/graph/query",
            json={"question": "What functions handle assignments?"}
        )
        
        if response.status_code != 200:
            print(f"\n=== GRAPHRAG ERROR ===")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_nodes" in data
        assert "total_edges" in data

    def test_crag_query(self, client):
        """Test CRAG query."""
        response = client.post(
            f"/repositories/{TEST_REPO_ID}/crag/ask",
            json={"question": "Explain how assignments are created"}
        )
        
        if response.status_code != 200:
            print(f"\n=== CRAG ERROR ===")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "confidence" in data
        assert "answer_valid" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])