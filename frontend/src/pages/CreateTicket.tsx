import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
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

interface AgentResult {
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
  escalado_a_humano?: boolean;
  es_recurrente?: boolean;
  causa_raiz?: string | null;
  accion_preventiva?: string | null;
  creado_en: string;
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
      borderRadius: theme.borderRadius.full, padding: '4px 14px', fontWeight: 800,
      fontSize: '0.88rem', letterSpacing: '0.04em',
    }}>
      {c.label}
    </span>
  );
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function CreateTicket() {
  const [titulo, setTitulo] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const navigate = useNavigate();

  const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!titulo.trim() || !descripcion.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await axios.post<AgentResult>(`${API_URL}/api/v1/tickets`, { titulo, descripcion });
      setResult(res.data);
    } catch (err: unknown) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.detail ?? err.message
        : 'Error desconocido';
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  };

  const handleEscalated = () => {
    if (result) {
      setResult({ ...result, escalado_a_humano: true });
    }
  };

  return (
    <div style={{ maxWidth: 780, margin: '2.5rem auto', padding: '0 1.5rem' }}>
      {/* ── Page title ── */}
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.85rem', fontWeight: 800, color: theme.colors.textMain }}>
          🤖 Nuevo Ticket con IA
        </h1>
        <p style={{ margin: '0.3rem 0 0', color: theme.colors.textMuted, fontSize: '0.95rem' }}>
          Ingresa el título y la descripción. Los 5 agentes de IA harán el resto.
        </p>
      </div>

      {/* ── Form ── */}
      <form
        id="form-create-ticket"
        onSubmit={handleSubmit}
        style={{
          background: theme.colors.bgCard,
          borderRadius: theme.borderRadius.lg,
          boxShadow: theme.boxShadow.lg,
          padding: '2rem',
          marginBottom: '1.5rem',
          border: `1px solid ${theme.colors.border}`,
        }}
      >
        <div style={{ marginBottom: '1.25rem' }}>
          <label htmlFor="input-titulo" style={{ display: 'block', fontWeight: 600, color: theme.colors.textMain, marginBottom: '0.4rem', fontSize: '0.95rem' }}>
            Título del ticket
          </label>
          <input
            id="input-titulo"
            type="text"
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            placeholder="Ej: VPN no funciona desde esta mañana"
            required
            disabled={loading}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              borderRadius: theme.borderRadius.md,
              border: `1.5px solid ${theme.colors.border}`,
              fontSize: '0.95rem',
              outline: 'none',
              boxSizing: 'border-box',
              transition: theme.transitions.default,
              color: theme.colors.textMain,
            }}
            onFocus={(e) => (e.target.style.borderColor = theme.colors.primary)}
            onBlur={(e) => (e.target.style.borderColor = theme.colors.border)}
          />
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label htmlFor="input-descripcion" style={{ display: 'block', fontWeight: 600, color: theme.colors.textMain, marginBottom: '0.4rem', fontSize: '0.95rem' }}>
            Descripción detallada
          </label>
          <textarea
            id="input-descripcion"
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            placeholder="Describe el problema con el mayor detalle posible: qué ocurrió, cuándo, qué impacto tiene…"
            required
            disabled={loading}
            rows={5}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              borderRadius: theme.borderRadius.md,
              border: `1.5px solid ${theme.colors.border}`,
              fontSize: '0.95rem',
              resize: 'vertical',
              fontFamily: 'inherit',
              outline: 'none',
              boxSizing: 'border-box',
              transition: theme.transitions.default,
              color: theme.colors.textMain,
            }}
            onFocus={(e) => (e.target.style.borderColor = theme.colors.primary)}
            onBlur={(e) => (e.target.style.borderColor = theme.colors.border)}
          />
        </div>

        <button
          id="btn-submit-ticket"
          type="submit"
          disabled={loading || !titulo.trim() || !descripcion.trim()}
          style={{
            width: '100%',
            padding: '0.85rem',
            background: loading ? '#93c5fd' : `linear-gradient(135deg, ${theme.colors.primary}, ${theme.colors.secondary})`,
            color: '#fff',
            border: 'none',
            borderRadius: theme.borderRadius.md,
            fontWeight: 700,
            fontSize: '1rem',
            cursor: loading ? 'not-allowed' : 'pointer',
            boxShadow: loading ? 'none' : theme.boxShadow.md,
            transition: theme.transitions.default,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
          }}
        >
          {loading ? (
            <>
              <span style={{
                width: 18, height: 18, border: '3px solid #fff', borderTop: '3px solid transparent',
                borderRadius: '50%', display: 'inline-block',
                animation: 'spin 0.8s linear infinite',
              }} />
              Analizando con IA…
            </>
          ) : (
            '✨ Analizar con IA'
          )}
        </button>

        {/* Spinner keyframe */}
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </form>

      {/* ── Error ── */}
      {error && (
        <div style={{
          background: theme.colors.dangerBg, border: `1px solid ${theme.colors.danger}`, borderRadius: theme.borderRadius.md,
          padding: '1rem 1.25rem', color: theme.colors.danger, marginBottom: '1.5rem', fontWeight: 500,
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* ── Results panel ── */}
      {result && (
        <div style={{
          background: theme.colors.bgCard,
          borderRadius: theme.borderRadius.lg,
          boxShadow: theme.boxShadow.lg,
          padding: '2rem',
          border: `1px solid ${theme.colors.border}`,
          animation: 'fadeIn 0.4s ease',
        }}>
          <style>{`@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }`}</style>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.3rem', fontWeight: 800, color: theme.colors.textMain }}>
              📊 Resultados del Análisis IA
            </h2>
            {result.escalado_a_humano && (
              <span style={{
                backgroundColor: theme.colors.dangerBg,
                color: theme.colors.danger,
                border: `1px solid ${theme.colors.danger}`,
                padding: '4px 10px',
                borderRadius: theme.borderRadius.full,
                fontSize: '0.75rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>
                🚨 Escalado a soporte humano
              </span>
            )}
          </div>

          {/* ── Classification row ── */}
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
            <InfoCard label="Tipo" value={result.tipo} icon="🏷️" />
            <InfoCard label="Categoría" value={`${result.categoria}${result.subcategoria ? ` / ${result.subcategoria}` : ''}`} icon="📂" />
            <div style={cardStyle}>
              <span style={{ fontSize: '0.72rem', color: theme.colors.textMuted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Prioridad
              </span>
              <div style={{ marginTop: 6 }}>
                <PriorityBadge priority={result.prioridad} />
              </div>
            </div>
          </div>

          {/* ── Reasoning ── */}
          {result.razon_clasificacion && (
            <ReasonBlock icon="🧠" title="Razón de clasificación" text={result.razon_clasificacion} bg={theme.colors.bgBlueLight} border={theme.colors.secondaryLight} />
          )}
          {result.razon_prioridad && (
            <ReasonBlock icon="⚖️" title="Razón de prioridad" text={result.razon_prioridad} bg="#fef8e7" border="#ffe5a3" />
          )}

          {/* ── Structured User response (stepper/timeline style) ── */}
          {result.respuesta_estructurada ? (
            <div style={{
              background: '#f0fdf4',
              border: '1.5px solid #bbf7d0',
              borderRadius: theme.borderRadius.md,
              padding: '1.5rem',
              marginBottom: '1.25rem',
            }}>
              <p style={{ margin: '0 0 0.75rem', fontWeight: 800, color: theme.colors.success, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                💬 Respuesta de Solución Sugerida
              </p>
              
              {/* Greeting */}
              <p style={{ margin: '0 0 1.25rem 0', color: theme.colors.textMain, fontWeight: 500, lineHeight: 1.5 }}>
                {result.respuesta_estructurada.saludo}
              </p>

              {/* Stepper */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginBottom: '1.25rem', position: 'relative' }}>
                {result.respuesta_estructurada.pasos_solucion.map((paso, idx) => (
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
                      boxShadow: '0 2px 4px rgba(16, 185, 129, 0.2)',
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
              {result.respuesta_estructurada.tiempo_estimado && (
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
                  ⏱️ Tiempo estimado: {result.respuesta_estructurada.tiempo_estimado}
                </div>
              )}

              {/* Closing */}
              <p style={{ margin: 0, color: theme.colors.textMuted, fontSize: '0.9rem', lineHeight: 1.5, borderTop: '1px solid #dcfce7', paddingTop: '0.75rem' }}>
                {result.respuesta_estructurada.cierre}
              </p>
            </div>
          ) : (
            // Plain text fallback
            result.respuesta_usuario && (
              <div style={{
                background: 'linear-gradient(135deg, #ecfdf5, #f0fdf4)',
                border: '1.5px solid #6ee7b7',
                borderRadius: theme.borderRadius.md,
                padding: '1.25rem',
                marginBottom: '1rem',
              }}>
                <p style={{ margin: '0 0 0.5rem', fontWeight: 700, color: '#065f46', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  💬 Respuesta sugerida al usuario
                </p>
                <p style={{ margin: 0, color: theme.colors.textMain, lineHeight: 1.65, whiteSpace: 'pre-line' }}>
                  {result.respuesta_usuario}
                </p>
              </div>
            )
          )}

          {/* ── Analytics ── */}
          {(result.causa_raiz || result.accion_preventiva) && (
            <div style={{
              background: theme.colors.warningBg,
              border: `1.5px solid ${theme.colors.warning}`,
              borderRadius: theme.borderRadius.md,
              padding: '1.25rem',
              marginBottom: '1.25rem',
            }}>
              <p style={{ margin: '0 0 0.75rem', fontWeight: 700, color: '#92400e', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                🔍 Análisis de recurrencia
                {result.es_recurrente && (
                  <span style={{ marginLeft: '0.5rem', background: '#fde68a', padding: '2px 8px', borderRadius: theme.borderRadius.full, fontSize: '0.75rem' }}>
                    Incidente recurrente
                  </span>
                )}
              </p>
              {result.causa_raiz && (
                <p style={{ margin: '0 0 0.5rem', color: theme.colors.textMain, fontSize: '0.9rem' }}>
                  <strong>Causa raíz:</strong> {result.causa_raiz}
                </p>
              )}
              {result.accion_preventiva && (
                <p style={{ margin: 0, color: theme.colors.textMain, fontSize: '0.9rem' }}>
                  <strong>Acción preventiva:</strong> {result.accion_preventiva}
                </p>
              )}
            </div>
          )}

          {/* ── Human escalation section ── */}
          {!result.escalado_a_humano && (
            <div style={{
              padding: '1.25rem',
              border: `1px dashed ${theme.colors.primary}`,
              backgroundColor: theme.colors.bgBlueLight,
              borderRadius: theme.borderRadius.md,
              marginBottom: '1.5rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '1rem',
              flexWrap: 'wrap',
            }}>
              <div>
                <h4 style={{ margin: '0 0 0.25rem 0', color: theme.colors.textMain, fontSize: '0.95rem', fontWeight: 700 }}>
                  ¿No se resolvió tu problema?
                </h4>
                <p style={{ margin: 0, color: theme.colors.textMuted, fontSize: '0.85rem' }}>
                  Puedes chatear, llamar o escalar el caso directamente con un especialista humano.
                </p>
              </div>
              <button
                onClick={() => setIsModalOpen(true)}
                style={{
                  padding: '0.55rem 1.2rem',
                  backgroundColor: theme.colors.primary,
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: theme.borderRadius.md,
                  fontWeight: 700,
                  fontSize: '0.88rem',
                  cursor: 'pointer',
                  boxShadow: theme.boxShadow.sm,
                  transition: theme.transitions.default,
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = theme.colors.primaryHover)}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = theme.colors.primary)}
              >
                🙋‍♂️ Hablar con un agente
              </button>
            </div>
          )}

          {/* ── Navigation buttons ── */}
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              id="btn-view-all-tickets"
              onClick={() => navigate('/')}
              style={{
                background: 'transparent',
                border: `2.5px solid ${theme.colors.primary}`,
                color: theme.colors.primary,
                borderRadius: theme.borderRadius.md,
                padding: '0.65rem 1.4rem',
                fontWeight: 700,
                fontSize: '0.95rem',
                cursor: 'pointer',
                transition: theme.transitions.default,
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = theme.colors.primary;
                (e.currentTarget as HTMLButtonElement).style.color = '#fff';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                (e.currentTarget as HTMLButtonElement).style.color = theme.colors.primary;
              }}
            >
              📋 Ver todos los tickets
            </button>
          </div>
        </div>
      )}

      {/* ── Support modal ── */}
      {result && (
        <HumanSupportModal
          ticketId={result.id}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onEscalated={handleEscalated}
        />
      )}
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

const cardStyle: React.CSSProperties = {
  flex: '1 1 160px',
  background: '#f8fafc',
  border: `1px solid ${theme.colors.border}`,
  borderRadius: '12px',
  padding: '0.85rem 1rem',
};

function InfoCard({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div style={cardStyle}>
      <span style={{ fontSize: '0.72rem', color: theme.colors.textMuted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {icon} {label}
      </span>
      <p style={{ margin: '0.35rem 0 0', fontWeight: 700, color: theme.colors.textMain, fontSize: '0.95rem', textTransform: 'capitalize' }}>
        {value}
      </p>
    </div>
  );
}

function ReasonBlock({ icon, title, text, bg, border }: { icon: string; title: string; text: string; bg: string; border: string }) {
  return (
    <div style={{ background: bg, border: `1.5px solid ${border}`, borderRadius: '12px', padding: '1rem 1.25rem', marginBottom: '1rem' }}>
      <p style={{ margin: '0 0 0.4rem', fontWeight: 700, color: theme.colors.textMain, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {icon} {title}
      </p>
      <p style={{ margin: 0, color: theme.colors.textMuted, lineHeight: 1.6, fontSize: '0.9rem' }}>{text}</p>
    </div>
  );
}
