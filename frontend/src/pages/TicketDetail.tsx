import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { theme } from '../theme';
import HumanSupportModal from '../components/HumanSupportModal';

// ── Types ──────────────────────────────────────────────────────────────────────

interface PasoSolucion {
  numero: number;
  titulo: string;
  descripcion: string;
}

interface RespuestaEstructurada {
  saludo: string;
  pasos_solucion: PasoSolucion[];
  tiempo_estimado: string;
  cierre: string;
}

interface TicketDetailData {
  id: number;
  titulo: string;
  descripcion: string;
  tipo: string;
  categoria: string;
  subcategoria?: string | null;
  prioridad: string;
  estado: string;
  area_responsable?: string | null;
  impacto?: string | null;
  urgencia?: string | null;
  razon_clasificacion?: string | null;
  razon_prioridad?: string | null;
  confianza_clasificacion?: number | null;
  respuesta_estructurada?: RespuestaEstructurada | null;
  respuesta_usuario?: string | null;
  escalado_a_humano: boolean;
  es_recurrente?: boolean;
  causa_raiz?: string | null;
  accion_preventiva?: string | null;
  creado_en: string;
  actualizado_en: string;
}

interface Comment {
  id: number;
  autor: string;
  texto: string;
  valoracion?: number | null;
  creado_en: string;
}

interface CommentsResponse {
  comentarios: Comment[];
  valoracion_promedio?: number | null;
  total_valoraciones: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const PRIORITY_COLORS: Record<string, { bg: string; text: string; border: string; label: string }> = {
  P1: { bg: theme.colors.p1.bg, text: theme.colors.p1.text, border: theme.colors.p1.border, label: 'P1 – Crítico' },
  P2: { bg: theme.colors.p2.bg, text: theme.colors.p2.text, border: theme.colors.p2.border, label: 'P2 – Alto' },
  P3: { bg: theme.colors.p3.bg, text: theme.colors.p3.text, border: theme.colors.p3.border, label: 'P3 – Medio' },
  P4: { bg: theme.colors.p4.bg, text: theme.colors.p4.text, border: theme.colors.p4.border, label: 'P4 – Bajo' },
};

function PriorityBadge({ priority }: { priority: string }) {
  const c = PRIORITY_COLORS[priority] ?? { bg: '#f3f4f6', text: '#374151', border: '#d1d5db', label: priority };
  return (
    <span style={{
      background: c.bg, color: c.text, border: `1.5px solid ${c.border}`,
      borderRadius: theme.borderRadius.full, padding: '3px 12px', fontWeight: 800,
      fontSize: '0.82rem', letterSpacing: '0.04em',
    }}>
      {c.label}
    </span>
  );
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function TicketDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

  const [ticket, setTicket] = useState<TicketDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Comments State
  const [commentsData, setCommentsData] = useState<CommentsResponse>({ comentarios: [], total_valoraciones: 0 });
  const [commentText, setCommentText] = useState('');
  const [commentAuthor, setCommentAuthor] = useState('Usuario');
  const [rating, setRating] = useState<number | null>(null);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const [submittingComment, setSubmittingComment] = useState(false);

  // Escalate modal
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch ticket details
  const fetchTicketDetails = () => {
    setLoading(true);
    axios
      .get<TicketDetailData>(`${API_URL}/api/v1/tickets/${id}`)
      .then((res) => setTicket(res.data))
      .catch((err) => setError(err.response?.data?.detail ?? 'Error al cargar detalles del ticket'))
      .finally(() => setLoading(false));
  };

  // Fetch comments
  const fetchComments = () => {
    axios
      .get<CommentsResponse>(`${API_URL}/api/v1/tickets/${id}/comments`)
      .then((res) => setCommentsData(res.data))
      .catch((err) => console.error('Error al cargar comentarios:', err));
  };

  useEffect(() => {
    if (id) {
      fetchTicketDetails();
      fetchComments();
    }
  }, [id, API_URL]);

  const handleEscalated = () => {
    if (ticket) {
      setTicket({ ...ticket, escalado_a_humano: true });
    }
  };

  const handleSendComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;

    setSubmittingComment(true);
    try {
      await axios.post(`${API_URL}/api/v1/tickets/${id}/comments`, {
        autor: commentAuthor.trim() || 'Usuario',
        texto: commentText,
        valoracion: rating,
      });
      setCommentText('');
      setRating(null);
      fetchComments();
    } catch (err: any) {
      alert(err.response?.data?.detail ?? 'Error al enviar comentario');
    } finally {
      setSubmittingComment(false);
    }
  };

  const renderAvgStars = (val: number) => {
    return [1, 2, 3, 4, 5].map((star) => {
      const isFilled = val >= star - 0.3;
      return (
        <span key={star} style={{ color: isFilled ? '#eab308' : '#cbd5e1', fontSize: '1.25rem', marginRight: '0.1rem' }}>
          ★
        </span>
      );
    });
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '5rem', color: theme.colors.textMuted }}>
        ⏳ Cargando detalles del ticket #{id}...
      </div>
    );
  }

  if (error || !ticket) {
    return (
      <div style={{ maxWidth: 800, margin: '3rem auto', padding: '0 1.5rem' }}>
        <div style={{
          background: theme.colors.dangerBg, border: `1px solid ${theme.colors.danger}`, borderRadius: theme.borderRadius.md,
          padding: '1.5rem', color: theme.colors.danger, textAlign: 'center', marginBottom: '1.5rem',
        }}>
          <h3>⚠️ Error</h3>
          <p>{error ?? 'No se pudo encontrar el ticket solicitado.'}</p>
        </div>
        <button onClick={() => navigate('/incidents')} style={backButtonStyle}>
          ← Volver a la lista
        </button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 960, margin: '2.5rem auto', padding: '0 1.5rem' }}>
      
      {/* ── Header Actions ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <button onClick={() => navigate('/incidents')} style={backButtonStyle}>
          ← Volver a la lista
        </button>
        
        {ticket.escalado_a_humano && (
          <span style={{
            backgroundColor: theme.colors.dangerBg,
            color: theme.colors.danger,
            border: `1.5px solid ${theme.colors.danger}`,
            padding: '6px 14px',
            borderRadius: theme.borderRadius.full,
            fontSize: '0.8rem',
            fontWeight: 800,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            boxShadow: theme.boxShadow.sm,
          }}>
            🚨 Escalado a soporte humano
          </span>
        )}
      </div>

      {/* ── Title & Meta ── */}
      <div style={{
        background: theme.colors.bgCard,
        border: `1px solid ${theme.colors.border}`,
        borderRadius: theme.borderRadius.lg,
        padding: '2rem',
        marginBottom: '1.5rem',
        boxShadow: theme.boxShadow.sm,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <span style={{ color: theme.colors.primary, fontWeight: 800, fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Ticket #{ticket.id}
            </span>
            <h1 style={{ margin: '0.2rem 0 0.5rem 0', fontSize: '1.65rem', fontWeight: 800, color: theme.colors.textMain }}>
              {ticket.titulo}
            </h1>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <span style={badgeStyle}>{ticket.tipo}</span>
              <span style={badgeStyle}>{ticket.categoria}</span>
              {ticket.subcategoria && <span style={badgeStyle}>{ticket.subcategoria}</span>}
              <PriorityBadge priority={ticket.prioridad} />
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{
              background: '#e0f2fe', color: '#0369a1', borderRadius: theme.borderRadius.full,
              padding: '4px 14px', fontSize: '0.85rem', fontWeight: 700, textTransform: 'capitalize',
              display: 'inline-block',
            }}>
              Estado: {ticket.estado}
            </span>
            <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.78rem', color: theme.colors.textMuted }}>
              Creado: {new Date(ticket.creado_en).toLocaleString('es-ES')}
            </p>
          </div>
        </div>

        <hr style={{ border: 'none', borderTop: `1px solid ${theme.colors.border}`, margin: '1.5rem 0' }} />

        {/* Description */}
        <h3 style={{ fontSize: '1rem', color: theme.colors.textMain, fontWeight: 700, marginBottom: '0.5rem' }}>
          Descripción del problema
        </h3>
        <p style={{ margin: 0, color: theme.colors.textMuted, fontSize: '0.95rem', lineHeight: 1.6, whiteSpace: 'pre-line' }}>
          {ticket.descripcion}
        </p>
      </div>

      {/* ── Two Column Layout (AI Info + Solution) ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        
        {/* Solution Step-by-Step Card */}
        <div style={{
          background: theme.colors.bgCard,
          border: `1px solid ${theme.colors.border}`,
          borderRadius: theme.borderRadius.lg,
          padding: '2rem',
          boxShadow: theme.boxShadow.sm,
        }}>
          <h2 style={{ margin: '0 0 1.25rem 0', fontSize: '1.2rem', fontWeight: 800, color: theme.colors.textMain }}>
            💡 Solución Propuesta por GenIA
          </h2>

          {ticket.respuesta_estructurada ? (
            <div style={{
              background: '#f0fdf4',
              border: '1.5px solid #bbf7d0',
              borderRadius: theme.borderRadius.md,
              padding: '1.5rem',
            }}>
              <p style={{ margin: '0 0 1.25rem 0', color: theme.colors.textMain, fontWeight: 500, lineHeight: 1.5 }}>
                {ticket.respuesta_estructurada.saludo}
              </p>

              {/* Stepper */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginBottom: '1.25rem' }}>
                {ticket.respuesta_estructurada.pasos_solucion.map((paso, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                    <div style={{
                      backgroundColor: theme.colors.success,
                      color: '#ffffff',
                      borderRadius: '50%',
                      width: '28px',
                      height: '28px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                      fontSize: '0.85rem',
                      flexShrink: 0,
                    }}>
                      {paso.numero}
                    </div>
                    <div>
                      <h4 style={{ margin: '0 0 0.25rem 0', color: theme.colors.textMain, fontSize: '0.95rem', fontWeight: 700 }}>
                        {paso.titulo}
                      </h4>
                      <p style={{ margin: 0, color: theme.colors.textMuted, fontSize: '0.88rem', lineHeight: 1.5 }}>
                        {paso.descripcion}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Estimated Time */}
              {ticket.respuesta_estructurada.tiempo_estimado && (
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  backgroundColor: '#dcfce7',
                  color: '#15803d',
                  padding: '4px 12px',
                  borderRadius: theme.borderRadius.sm,
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  marginBottom: '1rem',
                }}>
                  ⏱️ Tiempo estimado: {ticket.respuesta_estructurada.tiempo_estimado}
                </div>
              )}

              {/* Closing */}
              <p style={{ margin: 0, color: theme.colors.textMuted, fontSize: '0.9rem', lineHeight: 1.5, borderTop: '1px solid #dcfce7', paddingTop: '0.75rem' }}>
                {ticket.respuesta_estructurada.cierre}
              </p>
            </div>
          ) : (
            ticket.respuesta_usuario && (
              <div style={{
                background: 'linear-gradient(135deg, #ecfdf5, #f0fdf4)',
                border: '1.5px solid #6ee7b7',
                borderRadius: theme.borderRadius.md,
                padding: '1.25rem',
              }}>
                <p style={{ margin: 0, color: theme.colors.textMain, lineHeight: 1.65, whiteSpace: 'pre-line' }}>
                  {ticket.respuesta_usuario}
                </p>
              </div>
            )
          )}
        </div>

        {/* Diagnostic Metadata & Recurrence Card */}
        <div style={{
          background: theme.colors.bgCard,
          border: `1px solid ${theme.colors.border}`,
          borderRadius: theme.borderRadius.lg,
          padding: '2rem',
          boxShadow: theme.boxShadow.sm,
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '1.5rem',
        }}>
          <div style={{ gridColumn: 'span 2' }}>
            <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800, color: theme.colors.textMain }}>
              ⚙️ Diagnóstico del Sistema ITSM
            </h2>
          </div>

          <InfoField label="Área Responsable asignada" value={ticket.area_responsable ?? 'Por determinar'} />
          <InfoField label="Nivel de Confianza (IA)" value={ticket.confianza_clasificacion ? `${(ticket.confianza_clasificacion * 100).toFixed(1)}%` : 'No disponible'} />
          <InfoField label="Impacto estimado" value={ticket.impacto ?? 'Por determinar'} />
          <InfoField label="Urgencia estimada" value={ticket.urgencia ?? 'Por determinar'} />
          
          <div style={{ gridColumn: 'span 2' }}>
            <ReasonBlock icon="🧠" title="Razón de Clasificación" text={ticket.razon_clasificacion ?? 'Sin explicación.'} bg={theme.colors.bgBlueLight} border={theme.colors.secondaryLight} />
            <ReasonBlock icon="⚖️" title="Razón de Prioridad" text={ticket.razon_prioridad ?? 'Sin explicación.'} bg="#faf5ff" border="#e9d5ff" />
          </div>

          {/* Recurrence analytics */}
          {(ticket.causa_raiz || ticket.accion_preventiva) && (
            <div style={{
              gridColumn: 'span 2',
              background: theme.colors.warningBg,
              border: `1.5px solid ${theme.colors.warning}`,
              borderRadius: theme.borderRadius.md,
              padding: '1.25rem',
            }}>
              <h4 style={{ margin: '0 0 0.75rem 0', fontWeight: 700, color: '#92400e', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                🔍 Análisis de Recurrencia
                {ticket.es_recurrente && (
                  <span style={{ marginLeft: '0.5rem', background: '#fde68a', padding: '2px 8px', borderRadius: theme.borderRadius.full, fontSize: '0.72rem' }}>
                    Recurrente
                  </span>
                )}
              </h4>
              {ticket.causa_raiz && (
                <p style={{ margin: '0 0 0.5rem 0', color: theme.colors.textMain, fontSize: '0.88rem' }}>
                  <strong>Causa raíz:</strong> {ticket.causa_raiz}
                </p>
              )}
              {ticket.accion_preventiva && (
                <p style={{ margin: 0, color: theme.colors.textMain, fontSize: '0.88rem' }}>
                  <strong>Acción preventiva:</strong> {ticket.accion_preventiva}
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Human Escalation Section ── */}
      {!ticket.escalado_a_humano && (
        <div style={{
          padding: '1.5rem',
          border: `1px dashed ${theme.colors.primary}`,
          backgroundColor: theme.colors.bgBlueLight,
          borderRadius: theme.borderRadius.lg,
          marginBottom: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '1.5rem',
          flexWrap: 'wrap',
        }}>
          <div>
            <h4 style={{ margin: '0 0 0.25rem 0', color: theme.colors.textMain, fontSize: '1rem', fontWeight: 800 }}>
              ¿No se solucionó tu problema con estos pasos?
            </h4>
            <p style={{ margin: 0, color: theme.colors.textMuted, fontSize: '0.88rem' }}>
              Puedes chatear, llamar o escalar este ticket con un técnico humano en cualquier momento.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            style={{
              padding: '0.65rem 1.4rem',
              backgroundColor: theme.colors.primary,
              color: '#ffffff',
              border: 'none',
              borderRadius: theme.borderRadius.md,
              fontWeight: 700,
              fontSize: '0.9rem',
              cursor: 'pointer',
              boxShadow: theme.boxShadow.sm,
              transition: theme.transitions.default,
            }}
          >
            🙋‍♂️ Contactar un agente
          </button>
        </div>
      )}

      {/* ── Comments & Star Rating Section ── */}
      <div style={{
        background: theme.colors.bgCard,
        border: `1px solid ${theme.colors.border}`,
        borderRadius: theme.borderRadius.lg,
        padding: '2rem',
        boxShadow: theme.boxShadow.sm,
        marginBottom: '3rem',
      }}>
        <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem', fontWeight: 800, color: theme.colors.textMain, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          💬 Comentarios y Valoración
        </h2>

        {/* Rating summary */}
        {commentsData.valoracion_promedio ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem', padding: '0.75rem 1rem', backgroundColor: theme.colors.bgMain, borderRadius: theme.borderRadius.md }}>
            <span style={{ fontSize: '1.25rem', fontWeight: 800, color: theme.colors.textMain }}>
              {commentsData.valoracion_promedio.toFixed(1)}
            </span>
            <div style={{ display: 'flex' }}>
              {renderAvgStars(commentsData.valoracion_promedio)}
            </div>
            <span style={{ fontSize: '0.85rem', color: theme.colors.textMuted, marginLeft: '0.5rem' }}>
              ({commentsData.total_valoraciones} {commentsData.total_valoraciones === 1 ? 'valoración' : 'valoraciones'})
            </span>
          </div>
        ) : (
          <p style={{ margin: '0 0 1.5rem 0', fontSize: '0.85rem', color: theme.colors.textMuted }}>
            Este ticket no tiene valoraciones de estrellas todavía.
          </p>
        )}

        {/* Send Comment Form */}
        <form onSubmit={handleSendComment} style={{ marginBottom: '2rem', borderBottom: `1px solid ${theme.colors.border}`, paddingBottom: '2rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={formLabelStyle}>Tu Nombre</label>
              <input
                type="text"
                value={commentAuthor}
                onChange={(e) => setCommentAuthor(e.target.value)}
                placeholder="Nombre o cargo..."
                style={formInputStyle}
              />
            </div>
            
            {/* Interactive Stars Selector */}
            <div>
              <label style={formLabelStyle}>¿Cómo valoras la solución sugerida por la IA?</label>
              <div style={{ display: 'flex', alignItems: 'center', marginTop: '0.2rem' }}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <span
                    key={star}
                    style={{
                      cursor: 'pointer',
                      fontSize: '1.75rem',
                      color: star <= (hoverRating ?? rating ?? 0) ? '#eab308' : '#cbd5e1',
                      transition: 'color 0.1s',
                      marginRight: '0.3rem',
                    }}
                    onClick={() => setRating(star)}
                    onMouseEnter={() => setHoverRating(star)}
                    onMouseLeave={() => setHoverRating(null)}
                  >
                    ★
                  </span>
                ))}
                {rating && (
                  <span style={{ fontSize: '0.8rem', color: theme.colors.textMuted, marginLeft: '0.5rem', fontWeight: 600 }}>
                    {rating} de 5 estrellas
                  </span>
                )}
              </div>
            </div>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={formLabelStyle}>Comentario / Observaciones</label>
            <textarea
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Escribe tu comentario aquí..."
              required
              rows={3}
              style={{
                width: '100%',
                padding: '0.65rem 0.85rem',
                borderRadius: theme.borderRadius.md,
                border: `1.5px solid ${theme.colors.border}`,
                fontSize: '0.9rem',
                color: theme.colors.textMain,
                outline: 'none',
                resize: 'none',
              }}
            />
          </div>

          <button
            type="submit"
            disabled={submittingComment || !commentText.trim()}
            style={{
              padding: '0.65rem 1.5rem',
              backgroundColor: theme.colors.primary,
              color: '#ffffff',
              border: 'none',
              borderRadius: theme.borderRadius.md,
              fontWeight: 700,
              fontSize: '0.9rem',
              cursor: (submittingComment || !commentText.trim()) ? 'not-allowed' : 'pointer',
              transition: theme.transitions.default,
              boxShadow: theme.boxShadow.sm,
            }}
          >
            {submittingComment ? 'Enviando...' : 'Enviar valoración'}
          </button>
        </form>

        {/* Comments List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ fontSize: '1rem', color: theme.colors.textMain, fontWeight: 700, marginBottom: '0.5rem' }}>
            Comentarios existentes ({commentsData.comentarios.length})
          </h3>
          
          {commentsData.comentarios.length === 0 ? (
            <p style={{ margin: 0, color: theme.colors.textMuted, fontSize: '0.9rem', fontStyle: 'italic' }}>
              No hay comentarios escritos. ¡Escribe el primero arriba!
            </p>
          ) : (
            commentsData.comentarios.map((c) => (
              <div key={c.id} style={{
                padding: '1rem',
                border: `1px solid ${theme.colors.border}`,
                borderRadius: theme.borderRadius.md,
                backgroundColor: '#fcfdfe',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 700, color: theme.colors.textMain, fontSize: '0.9rem' }}>
                    👤 {c.autor}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {c.valoracion && (
                      <div style={{ display: 'flex' }}>
                        {renderAvgStars(c.valoracion)}
                      </div>
                    )}
                    <span style={{ fontSize: '0.78rem', color: theme.colors.textMuted }}>
                      {new Date(c.creado_en).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })}
                    </span>
                  </div>
                </div>
                <p style={{ margin: 0, color: theme.colors.textMuted, fontSize: '0.88rem', lineHeight: 1.5 }}>
                  {c.texto}
                </p>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ── Human Escalation Modal ── */}
      <HumanSupportModal
        ticketId={ticket.id}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onEscalated={handleEscalated}
      />
    </div>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const backButtonStyle: React.CSSProperties = {
  background: '#ffffff',
  border: `1.5px solid ${theme.colors.border}`,
  color: theme.colors.textMain,
  borderRadius: theme.borderRadius.md,
  padding: '0.55rem 1.1rem',
  fontWeight: 600,
  fontSize: '0.9rem',
  cursor: 'pointer',
  transition: theme.transitions.default,
  boxShadow: theme.boxShadow.sm,
};

const badgeStyle: React.CSSProperties = {
  background: theme.colors.bgBlueLight,
  color: theme.colors.primary,
  border: `1px solid ${theme.colors.secondaryLight}`,
  borderRadius: theme.borderRadius.sm,
  padding: '2px 8px',
  fontSize: '0.75rem',
  fontWeight: 700,
  textTransform: 'capitalize',
};

const formLabelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '0.8rem',
  fontWeight: 700,
  color: theme.colors.textMain,
  marginBottom: '0.3rem',
  textTransform: 'uppercase',
  letterSpacing: '0.03em',
};

const formInputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.6rem 0.8rem',
  borderRadius: theme.borderRadius.md,
  border: `1.5px solid ${theme.colors.border}`,
  fontSize: '0.9rem',
  color: theme.colors.textMain,
  outline: 'none',
};

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <span style={{ fontSize: '0.72rem', color: theme.colors.textMuted, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.2rem' }}>
        {label}
      </span>
      <span style={{ fontSize: '0.92rem', color: theme.colors.textMain, fontWeight: 600 }}>
        {value}
      </span>
    </div>
  );
}

function ReasonBlock({ icon, title, text, bg, border }: { icon: string; title: string; text: string; bg: string; border: string }) {
  return (
    <div style={{ background: bg, border: `1.5px solid ${border}`, borderRadius: '10px', padding: '0.85rem 1rem', marginBottom: '0.85rem' }}>
      <p style={{ margin: '0 0 0.3rem', fontWeight: 700, color: theme.colors.textMain, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {icon} {title}
      </p>
      <p style={{ margin: 0, color: theme.colors.textMuted, lineHeight: 1.5, fontSize: '0.85rem' }}>{text}</p>
    </div>
  );
}
