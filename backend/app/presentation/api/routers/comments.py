"""
Comments router – handles POST /tickets/{id}/comments and GET /tickets/{id}/comments.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.infrastructure.database.connection import get_db
from app.domain.entities.ticket import Ticket
from app.domain.entities.comment import Comment
from app.presentation.api.schemas.comment_schema import CommentInput, CommentOut, CommentsResponse

router = APIRouter()

@router.post("/tickets/{ticket_id}/comments", response_model=CommentOut, status_code=201)
def create_comment(ticket_id: int, payload: CommentInput, db: Session = Depends(get_db)):
    """Add a new comment and optional star rating to a specific ticket."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} no encontrado.")
    
    comment = Comment(
        ticket_id=ticket_id,
        autor=payload.autor or "Usuario",
        texto=payload.texto,
        valoracion=payload.valoracion
    )
    
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment

@router.get("/tickets/{ticket_id}/comments", response_model=CommentsResponse)
def list_comments(ticket_id: int, db: Session = Depends(get_db)):
    """Return all comments for a ticket along with the average star rating."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} no encontrado.")
    
    comments = db.query(Comment).filter(Comment.ticket_id == ticket_id).order_by(Comment.creado_en.desc()).all()
    
    # Calculate average rating
    ratings = [c.valoracion for c in comments if c.valoracion is not None]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    
    return CommentsResponse(
        comentarios=comments,
        valoracion_promedio=avg_rating,
        total_valoraciones=len(ratings)
    )
