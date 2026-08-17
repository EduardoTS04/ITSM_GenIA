"""SQLAlchemy implementation of the TicketRepository port."""

from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.domain.entities.ticket import Ticket
from app.domain.ports import TicketFilters, TicketRepository


class SqlAlchemyTicketRepository(TicketRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, ticket: Ticket) -> Ticket:
        self._db.add(ticket)
        self._db.commit()
        self._db.refresh(ticket)
        return ticket

    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        return self._db.query(Ticket).filter(Ticket.id == ticket_id).first()

    def list(self, filters: TicketFilters) -> list[Ticket]:
        query = self._db.query(Ticket)

        # Text search
        if filters.q:
            search_filter = f"%{filters.q}%"
            query = query.filter(or_(Ticket.titulo.like(search_filter), Ticket.descripcion.like(search_filter)))

        # Dates filtering
        if filters.fecha_desde:
            try:
                dt_desde = datetime.strptime(filters.fecha_desde, "%Y-%m-%d")
                query = query.filter(Ticket.creado_en >= dt_desde)
            except ValueError:
                pass

        if filters.fecha_hasta:
            try:
                # Add 23:59:59 to make the day inclusive
                dt_hasta = datetime.strptime(f"{filters.fecha_hasta} 23:59:59", "%Y-%m-%d %H:%M:%S")
                query = query.filter(Ticket.creado_en <= dt_hasta)
            except ValueError:
                pass

        # Exact match filters
        if filters.urgencia:
            query = query.filter(Ticket.urgencia == filters.urgencia)
        if filters.tipo:
            query = query.filter(Ticket.tipo == filters.tipo)
        if filters.categoria:
            query = query.filter(Ticket.categoria == filters.categoria)
        if filters.prioridad:
            query = query.filter(Ticket.prioridad == filters.prioridad)
        if filters.area_responsable:
            query = query.filter(Ticket.area_responsable == filters.area_responsable)

        return query.order_by(Ticket.creado_en.desc()).all()

    def update(self, ticket: Ticket) -> Ticket:
        self._db.commit()
        self._db.refresh(ticket)
        return ticket
