"""SQLAlchemy ORM model for Ticket entity"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from datetime import datetime
from app.infrastructure.database.connection import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=False)
    tipo = Column(String, nullable=False)  # incidente|requerimiento|problema
    categoria = Column(String, nullable=False)
    subcategoria = Column(String, nullable=True)
    prioridad = Column(String, nullable=False)  # P1|P2|P3|P4
    estado = Column(String, default="nuevo")
    area_responsable = Column(String, nullable=True)
    impacto = Column(String, nullable=True)
    urgencia = Column(String, nullable=True)
    razon_clasificacion = Column(Text, nullable=True)
    razon_prioridad = Column(Text, nullable=True)
    confianza_clasificacion = Column(Float, nullable=True)
    respuesta_estructurada = Column(Text, nullable=True)  # JSON string representation of the solution
    escalado_a_humano = Column(Boolean, default=False)
    es_recurrente = Column(Boolean, default=False)
    causa_raiz = Column(Text, nullable=True)
    accion_preventiva = Column(Text, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

