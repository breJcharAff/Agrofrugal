"""AgroFrugal - Diagnostic des maladies des cultures via SMS.

Endpoint /diagnose : NER (intent + entités) + recherche FAQ + cache Redis.
Cible: edge 4G, <200ms, <5W, image <150MB.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

import redis.asyncio as redis
import torch
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForTokenClassification

from shared.codecarbon_middleware import CodeCarbonMiddleware

INTENTS = ["maladie", "irrigation", "recolte"]
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
FAQ_PATH = os.getenv("FAQ_PATH", "./data/faq_agriculture_300.json")
MODEL_PATH = os.getenv("MODEL_PATH", "./models/distilbert-int8")

INFERENCE_SECONDS = Histogram("model_inference_seconds", "Latence NER DistilBERT INT8")
CACHE_HITS = Counter("cache_hits_total", "Hits cache FAQ Redis")
CACHE_MISSES = Counter("cache_misses_total", "Misses cache -> inférence + recherche FAQ")
REQUEST_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Latence requête HTTP",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0),
)
REQUESTS_TOTAL = Counter("http_requests_total", "Requêtes HTTP", labelnames=("endpoint", "status"))


class DiagnoseRequest(BaseModel):
    message: str = Field(..., min_length=3, max_length=320, description="SMS reçu (160 chars x 2)")
    phone_hash: str | None = Field(None, max_length=64)


class DiagnoseResponse(BaseModel):
    intent: str
    entities: dict[str, str]
    answer: str
    confidence: float
    cached: bool
    latency_ms: float


app = FastAPI(title="AgroFrugal", version="0.1.0")
app.add_middleware(CodeCarbonMiddleware, project_name="agrofrugal")
app.mount("/metrics", make_asgi_app())

_redis: redis.Redis | None = None
_faq: list[dict] = []
_model = None
_tokenizer = None


@app.on_event("startup")
async def _startup() -> None:
    global _redis, _faq, _model, _tokenizer
    _redis = redis.from_url(REDIS_URL, decode_responses=True)
    _faq = json.loads(open(FAQ_PATH, encoding="utf-8").read())
    
    # Phase 1: charger DistilBERT INT8 pour NER
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    
    # Chargement dynamique du modèle quantifié
    # On crée d'abord le modèle FP32 avec la structure correcte
    model_fp32 = AutoModelForTokenClassification.from_pretrained(MODEL_PATH, num_labels=len(INTENTS))
    
    # On applique la même quantification dynamique que lors de la Phase 1
    _model = torch.quantization.quantize_dynamic(model_fp32, {torch.nn.Linear}, dtype=torch.qint8)
    
    # On charge les poids quantifiés
    state_dict = torch.load(os.path.join(MODEL_PATH, "pytorch_model.bin"), map_location="cpu", weights_only=True)
    _model.load_state_dict(state_dict)
    _model.eval()


@app.on_event("shutdown")
async def _shutdown() -> None:
    if _redis is not None:
        await _redis.aclose()


def _cache_key(msg: str) -> str:
    return "diag:" + hashlib.sha1(msg.strip().lower().encode()).hexdigest()[:16]


async def _extract(message: str) -> tuple[str, dict[str, str], float]:
    """Phase 1: implémenter NER DistilBERT INT8.
    Retourne (intent, entities, confidence).
    """
    with INFERENCE_SECONDS.time():
        inputs = _tokenizer(message, return_tensors="pt", truncation=True, max_length=64)
        with torch.no_grad():
            outputs = _model(**inputs)
        
        # Intent: argmax sur le premier token (CLS)
        logits = outputs.logits
        probs = torch.softmax(logits[0, 0, :], dim=0)
        intent_idx = torch.argmax(probs).item()
        confidence = probs[intent_idx].item()
        
        intent = INTENTS[intent_idx] if intent_idx < len(INTENTS) else "maladie"
        
        # Extraction entités (Frugale via keywords pour culture)
        crops = ["tomate", "vigne", "blé", "maïs", "pomme", "courgette", "salade", "carotte"]
        culture = next((c for c in crops if c in message.lower()), "non_specifie")
        
        return intent, {"culture": culture}, round(confidence, 3)


def _find_faq(intent: str, entities: dict[str, str]) -> tuple[str, float]:
    culture = entities.get("culture", "")
    matches = [f for f in _faq if f["intent"] == intent and culture in f["entities"]["culture"]]
    if not matches:
        matches = [f for f in _faq if f["intent"] == intent]
    if not matches:
        return ("Aucune FAQ trouvée. Contactez votre conseiller agricole.", 0.1)
    # TODO Phase 2: ranker par similarité d'embedding plutôt que premier match
    return (matches[0]["answer"], 0.8)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "faq_loaded": str(len(_faq))}


@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(req: DiagnoseRequest) -> DiagnoseResponse:
    start = time.perf_counter()
    key = _cache_key(req.message)

    cached = await _redis.get(key) if _redis else None
    if cached:
        CACHE_HITS.inc()
        data = json.loads(cached)
        latency = (time.perf_counter() - start) * 1000
        REQUEST_SECONDS.observe(latency / 1000)
        REQUESTS_TOTAL.labels("/diagnose", "200").inc()
        return DiagnoseResponse(**data, cached=True, latency_ms=latency)

    CACHE_MISSES.inc()
    try:
        intent, entities, conf_intent = await _extract(req.message)
        answer, conf_faq = _find_faq(intent, entities)
    except Exception as exc:
        REQUESTS_TOTAL.labels("/diagnose", "500").inc()
        raise HTTPException(status_code=500, detail=f"inference error: {exc}") from exc

    payload = {
        "intent": intent,
        "entities": entities,
        "answer": answer,
        "confidence": round(conf_intent * conf_faq, 3),
    }
    if _redis:
        await _redis.setex(key, 86400, json.dumps(payload))

    latency = (time.perf_counter() - start) * 1000
    REQUEST_SECONDS.observe(latency / 1000)
    REQUESTS_TOTAL.labels("/diagnose", "200").inc()
    return DiagnoseResponse(**payload, cached=False, latency_ms=latency)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, workers=1)
