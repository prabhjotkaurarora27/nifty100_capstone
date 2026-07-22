import json
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.api.routers import (
    companies,
    documents,
    health,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"

app = FastAPI(
    title="Nifty 100 Financial Analytics REST API",
    description="Production-Grade REST API for Nifty 100 Company Financials, Ratio Analytics, Screener, and Reports.",
    version="6.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware (Allow all origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    response.headers["X-Process-Time"] = f"{duration:.4f}s"
    return response


# Include Routers under /api/v1
app.include_router(health.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(screener.router, prefix="/api/v1")
app.include_router(sectors.router, prefix="/api/v1")
app.include_router(peers.router, prefix="/api/v1")
app.include_router(valuation.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "Nifty 100 Financial Analytics API v6.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


def export_openapi_spec():
    """Export OpenAPI JSON schema specification to docs/openapi.json."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    spec_path = DOCS_DIR / "openapi.json"
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"✅ Exported OpenAPI spec to {spec_path.name}")


if __name__ == "__main__":
    export_openapi_spec()
