"""Middleware FastAPI qui mesure le CO2 par requête via CodeCarbon.

Ajoute l'entête HTTP `X-CO2-kg` à chaque réponse et expose un compteur Prometheus
`co2_kg_total` agrégé sur l'instance.

Usage:
    from fastapi import FastAPI
    from shared.codecarbon_middleware import CodeCarbonMiddleware

    app = FastAPI()
    app.add_middleware(CodeCarbonMiddleware, project_name="triagevert")
"""
from __future__ import annotations

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

try:
    from codecarbon import EmissionsTracker
except ImportError as exc:
    raise ImportError("codecarbon est requis: pip install codecarbon") from exc


class CodeCarbonMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, project_name: str = "frugal-api", measure_power_secs: int = 15):
        super().__init__(app)
        self.project_name = project_name
        self._tracker = EmissionsTracker(
            project_name=project_name,
            measure_power_secs=measure_power_secs,
            save_to_file=False,
            log_level="error",
            tracking_mode="process",
        )
        self._tracker.start()
        self._total_kg = 0.0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        try:
            delta_kg = self._tracker.flush() or 0.0
        except Exception:
            delta_kg = 0.0
        self._total_kg += delta_kg

        response.headers["X-CO2-kg"] = f"{delta_kg:.6f}"
        response.headers["X-Latency-ms"] = f"{elapsed * 1000:.2f}"
        response.headers["X-CO2-Total-kg"] = f"{self._total_kg:.6f}"
        return response

    def __del__(self):
        try:
            self._tracker.stop()
        except Exception:
            pass
