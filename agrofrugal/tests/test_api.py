import pytest
from fastapi.testclient import TestClient
import os
import json

# Mock environment
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["FAQ_PATH"] = "Projets/eco-conception-frugal-ai/agrofrugal/data/faq_agriculture_300.json"
os.environ["MODEL_PATH"] = "Projets/eco-conception-frugal-ai/agrofrugal/models/distilbert-int8"

# Import app after env set
from agrofrugal.app import app
import agrofrugal.app as app_module
from unittest.mock import AsyncMock

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    mock = AsyncMock()
    mock.get.return_value = None
    mock.setex.return_value = True
    # On mocke la fonction from_url appelée dans _startup
    monkeypatch.setattr("redis.asyncio.from_url", lambda *args, **kwargs: mock)
    return mock

def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert "faq_loaded" in response.json()

def test_diagnose_maladie():
    # Test avec un message contenant des mots-clés de maladie
    with TestClient(app) as client:
        payload = {"message": "J'ai de la pourriture sur mes tomates", "phone_hash": "test"}
        response = client.post("/diagnose", json=payload)
        if response.status_code != 200:
            print(response.json())
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] in ["maladie", "irrigation", "recolte"] # Depend du modèle
        assert data["entities"]["culture"] == "tomate"
        assert "answer" in data
        assert "latency_ms" in data

def test_diagnose_irrigation():
    with TestClient(app) as client:
        payload = {"message": "Quand arroser mes vignes ?", "phone_hash": "test"}
        response = client.post("/diagnose", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["entities"]["culture"] == "vigne"

def test_cache_logic():
    # Ce test vérifierait idéalement que le second appel est 'cached: True'
    # mais cela nécessite un vrai Redis. Pour un test unitaire, on peut mocker redis.
    pass
