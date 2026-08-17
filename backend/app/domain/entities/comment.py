"""SQLAlchemy ORM model for Comment entity"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.infrastructure.database.connection import Base

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    autor = Column(String, default="Usuario", nullable=False)
    texto = Column(Text, nullable=False)
    valoracion = Column(Integer, nullable=True)  # rating 1-5
    creado_en = Column(DateTime, default=datetime.utcnow)
