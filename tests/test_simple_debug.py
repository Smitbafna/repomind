"""Simple debug test to see exact errors."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from backend.api.main import app

REPO_ID = "01981d63-7bd7-459e-af26-d8a80617d499"

client = TestClient(app)

print("=" * 70)
print("SIMPLE DEBUG TEST")
print("=" * 70)

# Test 1: Index
print("\n1. Testing INDEX...")
response = client.post(f"/repositories/{REPO_ID}/index")
print(f"   Status: {response.status_code}")
print(f"   Response: {response.text}")

# Test 2: Vector search
print("\n2. Testing VECTOR SEARCH...")
response = client.post(
    f"/repositories/{REPO_ID}/query",
    json={"query": "test", "retriever": "vector", "top_k": 3}
)
print(f"   Status: {response.status_code}")
print(f"   Response: {response.text}")

# Test 3: Ask
print("\n3. Testing ASK...")
response = client.post(
    f"/repositories/{REPO_ID}/ask",
    json={"question": "test"}
)
print(f"   Status: {response.status_code}")
print(f"   Response: {response.text}")

print("\n" + "=" * 70)