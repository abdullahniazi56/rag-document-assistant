from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data ["status"] == "ok"
    assert data["service"] == "ai-doc-assistant"

def test_generate():
    response = client.post(
        "/generate",
        json={
            "messages": [
                {"role": "user", "content": "What is 2 + 2?"}
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "confidence" in data


def test_generate_empty_messages():
    response = client.post(
        "/generate",
        json={"messages": []},
    )
    assert response.status_code == 422


def test_list_documents():
    response = client.get("/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)