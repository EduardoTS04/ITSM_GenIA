"""Pydantic schemas for Comment API"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class CommentInput(BaseModel):
    autor: Optional[str] = Field("Usuario", example="Usuario")
    texto: str = Field(..., example="Excelente servicio, se solucionó rápido.")
    valoracion: Optional[int] = Field(None, example=5, description="Valoración de 1 a 5 estrellas")

    @validator("valoracion")
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError("La valoración debe ser un número entero entre 1 y 5")
        return v

class CommentOut(BaseModel):
    id: int
    ticket_id: int
    autor: str
    texto: str
    valoracion: Optional[int] = None
    creado_en: datetime

    class Config:
        from_attributes = True

class CommentsResponse(BaseModel):
    comentarios: list[CommentOut]
    valoracion_promedio: Optional[float] = None
    total_valoraciones: int
