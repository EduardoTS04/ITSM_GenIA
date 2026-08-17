import json
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.application.use_cases.create_ticket import CreateTicketUseCase
from app.domain.entities.ticket import Ticket
from app.domain.ports import AgentTraceRepository, TicketFilters, TicketRepository
from app.presentation.api.deps import (
    get_agent_trace_repository,
    get_create_ticket_use_case,
    get_ticket_repository,
)
from app.presentation.api.schemas.agent_trace_schema import AgentTraceOut
from app.presentation.api.schemas.ticket_schema import TicketInput, TicketOut

router = APIRouter()


# ── Helper for parsing and serializing ─────────────────────────────────────────

def to_ticket_out_dict(ticket: Ticket) -> dict:
    """Helper to convert Ticket ORM to dict matching TicketOut schema."""
    resp_est = None
    if ticket.respuesta_estructurada:
        try:
            resp_est = json.loads(ticket.respuesta_estructurada)
        except Exception:
            pass

    # plaintext fallback
    resp_user = None
    if resp_est:
        resp_user = (
            f"{resp_est.get('saludo', '')}\n\n" +
            "\n".join(f"{p.get('numero', i+1)}. {p.get('titulo', '')}: {p.get('descripcion', '')}" for i, p in enumerate(resp_est.get('pasos_solucion', []))) +
            f"\n\n{resp_est.get('cierre', '')}"
        )
    else:
        resp_user = "No hay respuesta de soporte disponible."

    return {
        "id": ticket.id,
        "titulo": ticket.titulo,
        "descripcion": ticket.descripcion,
        "tipo": ticket.tipo,
        "categoria": ticket.categoria,
        "subcategoria": ticket.subcategoria,
        "prioridad": ticket.prioridad,
        "estado": ticket.estado,
        "area_responsable": ticket.area_responsable,
        "impacto": ticket.impacto,
        "urgencia": ticket.urgencia,
        "razon_clasificacion": ticket.razon_clasificacion,
        "razon_prioridad": ticket.razon_prioridad,
        "confianza_clasificacion": ticket.confianza_clasificacion,
        "respuesta_estructurada": resp_est,
        "respuesta_usuario": resp_user,
        "escalado_a_humano": bool(ticket.escalado_a_humano),
        "es_recurrente": bool(ticket.es_recurrente),
        "causa_raiz": ticket.causa_raiz,
        "accion_preventiva": ticket.accion_preventiva,
        "creado_en": ticket.creado_en,
        "actualizado_en": ticket.actualizado_en,
    }


# ── POST /tickets ──────────────────────────────────────────────────────────────

@router.post("/tickets", status_code=201)
async def create_ticket(
    payload: TicketInput,
    use_case: CreateTicketUseCase = Depends(get_create_ticket_use_case),
):
    """
    Receive a ticket with only titulo and descripcion.
    The orchestrator fills in all remaining fields via the 4 AI agents.
    """
    ticket = await use_case.execute(titulo=payload.titulo, descripcion=payload.descripcion)

    response_dict = to_ticket_out_dict(ticket)

    # Serialize datetime fields manually for custom JSONResponse
    for key, val in response_dict.items():
        if isinstance(val, datetime):
            response_dict[key] = val.isoformat()

    return JSONResponse(content=response_dict, status_code=201)


# ── GET /tickets ───────────────────────────────────────────────────────────────

@router.get("/tickets", response_model=list[TicketOut])
def list_tickets(
    q: Optional[str] = Query(None, description="Búsqueda de texto libre"),
    fecha_desde: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha fin YYYY-MM-DD"),
    urgencia: Optional[str] = Query(None, description="Urgencia (alta, media, baja)"),
    tipo: Optional[str] = Query(None, description="Tipo de ticket"),
    categoria: Optional[str] = Query(None, description="Categoría"),
    prioridad: Optional[str] = Query(None, description="Prioridad P1-P4"),
    area_responsable: Optional[str] = Query(None, description="Área responsable"),
    tickets: TicketRepository = Depends(get_ticket_repository)
):
    """Return filtered tickets ordered by creation date descending."""
    filters = TicketFilters(
        q=q,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        urgencia=urgencia,
        tipo=tipo,
        categoria=categoria,
        prioridad=prioridad,
        area_responsable=area_responsable,
    )
    return [to_ticket_out_dict(t) for t in tickets.list(filters)]


# ── GET /tickets/{id} ──────────────────────────────────────────────────────────

@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, tickets: TicketRepository = Depends(get_ticket_repository)):
    """Return a single ticket by ID or 404."""
    ticket = tickets.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} no encontrado.")
    return to_ticket_out_dict(ticket)


# ── GET /tickets/{id}/trace ────────────────────────────────────────────────────

@router.get("/tickets/{ticket_id}/trace", response_model=list[AgentTraceOut])
def get_ticket_trace(
    ticket_id: int,
    tickets: TicketRepository = Depends(get_ticket_repository),
    traces: AgentTraceRepository = Depends(get_agent_trace_repository),
):
    """Return the execution trace of the agent pipeline that created the ticket."""
    if not tickets.get_by_id(ticket_id):
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} no encontrado.")
    return traces.get_traces_by_ticket_id(ticket_id)


# ── POST /tickets/{id}/escalate ────────────────────────────────────────────────

@router.post("/tickets/{ticket_id}/escalate", response_model=TicketOut)
def escalate_ticket(ticket_id: int, tickets: TicketRepository = Depends(get_ticket_repository)):
    """Mark a ticket as escalated to human support."""
    ticket = tickets.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} no encontrado.")
    
    ticket.escalado_a_humano = True
    ticket = tickets.update(ticket)
    return to_ticket_out_dict(ticket)

