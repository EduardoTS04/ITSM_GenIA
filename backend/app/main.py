# ITSM Hackathon MVP: Main FastAPI Application

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime

# Settings
from app.core.config import settings

# Database setup
from app.infrastructure.database.connection import engine, Base

# Routers
from app.presentation.api.routers.tickets import router as tickets_router
from app.presentation.api.routers.comments import router as comments_router

# Entities (imported explicitly so Base registers them)
from app.domain.entities.ticket import Ticket
from app.domain.entities.comment import Comment
from app.domain.entities.agent_trace import AgentTrace

# ── Bootstrap ──────────────────────────────────────────────────────────────────

# Ensure the data directory exists (SQLite needs it)
os.makedirs("/app/data", exist_ok=True)

# Alembic owns the schema: run `alembic upgrade head` before starting the app
# (see backend/MIGRATIONS.md). The flag below is a dev-only shortcut for throwaway
# databases and is off by default.
if settings.AUTO_CREATE_SCHEMA:
    Base.metadata.create_all(bind=engine)


# ── Application ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ITSM GenIA – NTT DATA Hackathon",
    version="1.0.0",
    description="Asistente Inteligente de Gestión de Incidentes TI con 5 agentes GenIA.",
)

# Enforce valid CORS configuration (wildcard origins with credentials is insecure and invalid)
if "*" in settings.CORS_ALLOWED_ORIGINS:
    raise ValueError(
        "Invalid CORS configuration: 'CORS_ALLOWED_ORIGINS' cannot contain '*' when 'allow_credentials' is True."
    )

# CORS – explicit allow-list for security with allow_credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────────────────

# Tickets API (all ticket operations)
app.include_router(tickets_router, prefix="/api/v1", tags=["tickets"])
app.include_router(comments_router, prefix="/api/v1", tags=["comments"])



# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return HTMLResponse(
        content=(
            f"<h1>ITSM GenIA API está operativa!</h1>"
            f"<p>Versión: 1.0.0 – Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        )
    )


# Root
@app.get("/", tags=["Root"])
def root():
    return {
        "app": "ITSM GenIA",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)