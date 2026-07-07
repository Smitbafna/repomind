"""Interactive chatbot for RepoMind AI features."""

import requests

BASE_URL = "http://localhost:8000"
REPO_ID = "01981d63-7bd7-459e-af26-d8a80617d499"

print("=" * 70)
print("RepoMind AI Chatbot")
print("=" * 70)
print("\nCommands:")
print("  /ask <question>      - Ask a question (RAG)")
print("  /vector <query>      - Semantic search")
print("  /keyword <query>     - Keyword search")
print("  /hybrid <query>      - Hybrid search")
print("  /graph <query>       - GraphRAG query")
print("  /crag <query>        - CRAG query")
print("  /quit                - Exit")
print("=" * 70)

while True:
    user_input = input("\nYou: ").strip()
    
    if not user_input:
        continue
    
    if user_input == "/quit":
        print("Goodbye!")
        break
    
    parts = user_input.split(" ", 1)
    command = parts[0]
    query = parts[1] if len(parts) > 1 else ""
    
    if not query:
        print("Please provide a query")
        continue
    
    try:
        if command == "/ask":
            r = requests.post(
                f"{BASE_URL}/repositories/{REPO_ID}/ask",
                json={"question": query}
            )
            if r.status_code == 200:
                data = r.json()
                print(f"\nAI: {data['answer']}")
                print(f"\nSources: {len(data['sources'])} documents")
            else:
                print(f"Error: {r.status_code} - {r.text[:100]}")
        
        elif command == "/vector":
            r = requests.post(
                f"{BASE_URL}/repositories/{REPO_ID}/query",
                json={"query": query, "retriever": "vector", "top_k": 5}
            )
            if r.status_code == 200:
                data = r.json()
                print(f"\nFound {data['total']} results:")
                for i, result in enumerate(data['results'], 1):
                    print(f"{i}. {result['file']} - {result['symbol']} ({result['score']:.3f})")
        
        elif command == "/keyword":
            r = requests.post(
                f"{BASE_URL}/repositories/{REPO_ID}/query",
                json={"query": query, "retriever": "keyword", "top_k": 5}
            )
            if r.status_code == 200:
                data = r.json()
                print(f"\nFound {data['total']} results:")
                for i, result in enumerate(data['results'], 1):
                    print(f"{i}. {result['file']} - {result['symbol']}")
        
        elif command == "/hybrid":
            r = requests.post(
                f"{BASE_URL}/repositories/{REPO_ID}/query",
                json={"query": query, "retriever": "hybrid", "top_k": 5}
            )
            if r.status_code == 200:
                data = r.json()
                print(f"\nFound {data['total']} results:")
                for i, result in enumerate(data['results'], 1):
                    print(f"{i}. {result['file']} - {result['symbol']} ({result['score']:.3f})")
        
        elif command == "/graph":
            r = requests.post(
                f"{BASE_URL}/repositories/{REPO_ID}/graph/query",
                json={"question": query}
            )
            if r.status_code == 200:
                data = r.json()
                print(f"\nGraphRAG Results:")
                print(f"Nodes: {data['total_nodes']}, Edges: {data['total_edges']}")
                print(f"Answer: {data['answer']}")
        
        elif command == "/crag":
            r = requests.post(
                f"{BASE_URL}/repositories/{REPO_ID}/crag/ask",
                json={"question": query}
            )
            if r.status_code == 200:
                data = r.json()
                print(f"\nCRAG Answer:")
                print(f"Answer: {data['answer']}")
                print(f"Confidence: {data['confidence']:.2f}")
                print(f"Valid: {data['answer_valid']}")
        
        else:
            print(f"Unknown command: {command}")
            print("Commands: /ask, /vector, /keyword, /hybrid, /graph, /crag, /quit")
    
    except Exception as e:
        print(f"Error: {e}")