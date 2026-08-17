"""Pydantic schemas for Ticket API"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Input schema: only what the user provides ──────────────────────────────────
class TicketInput(BaseModel):
    """Schema for the POST /tickets endpoint – only titulo and descripcion required."""
    titulo: str = Field(..., example="VPN no funciona")
    descripcion: str = Field(..., example="Mi VPN dejó de funcionar y no puedo acceder al ERP.")


# ── Full base model (used internally / for TicketCreate) ───────────────────────
class TicketBase(BaseModel):
    titulo: str = Field(..., example="VPN no funciona")
    descripcion: str = Field(..., example="Mi VPN dejó de funcionar y no puedo acceder al ERP.")
    tipo: str = Field(..., example="incidente")
    categoria: str = Field(..., example="Red")
    subcategoria: Optional[str] = Field(None, example="VPN")
    prioridad: str = Field(..., example="P2")
    area_responsable: Optional[str] = None
    impacto: Optional[str] = None
    urgencia: Optional[str] = None


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    prioridad: Optional[str] = None
    estado: Optional[str] = None
    area_responsable: Optional[str] = None
    impacto: Optional[str] = None
    urgencia: Optional[str] = None
    razon_clasificacion: Optional[str] = None
    razon_prioridad: Optional[str] = None
    confianza_clasificacion: Optional[float] = None


class PasoSolucion(BaseModel):
    numero: int
    titulo: str
    descripcion: str


class RespuestaEstructurada(BaseModel):
    saludo: str
    pasos_solucion: list[PasoSolucion]
    tiempo_estimado: str
    cierre: str


class TicketOut(TicketBase):
    id: int
    estado: str
    razon_clasificacion: Optional[str] = None
    razon_prioridad: Optional[str] = None
    confianza_clasificacion: Optional[float] = None
    respuesta_estructurada: Optional[RespuestaEstructurada] = None
    respuesta_usuario: Optional[str] = None
    escalado_a_humano: bool = False
    es_recurrente: Optional[bool] = None
    causa_raiz: Optional[str] = None
    accion_preventiva: Optional[str] = None
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        from_attributes = True