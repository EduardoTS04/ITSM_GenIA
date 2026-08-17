import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { theme } from '../theme';

// ── Types ──────────────────────────────────────────────────────────────────────

interface Ticket {
  id: number;
  titulo: string;
  tipo: string;
  categoria: string;
  prioridad: string;
  estado: string;
  escalado_a_humano: boolean;
  creado_en: string;
}

// ── Priority badge styling ─────────────────────────────────────────────────────

const PRIORITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  P1: { bg: theme.colors.p1.bg, text: theme.colors.p1.text, border: theme.colors.p1.border },
  P2: { bg: theme.colors.p2.bg, text: theme.colors.p2.text, border: theme.colors.p2.border },
  P3: { bg: theme.colors.p3.bg, text: theme.colors.p3.text, border: theme.colors.p3.border },
  P4: { bg: theme.colors.p4.bg, text: theme.colors.p4.text, border: theme.colors.p4.border },
};

function PriorityBadge({ priority }: { priority: string }) {
  const c = PRIORITY_COLORS[priority] ?? { bg: '#f3f4f6', text: '#374151', border: '#d1d5db' };
  return (
    <span style={{
      background: c.bg,
      color: c.text,
      border: `1.5px solid ${c.border}`,
      display: 'inline-block',
      padding: '2px 10px',
      borderRadius: theme.borderRadius.full,
      fontWeight: 700,
      fontSize: '0.78rem',
      letterSpacing: '0.05em',
    }}>
      {priority}
    </span>
  );
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function IncidentList() {
  const [allTickets, setAllTickets] = useState<Ticket[]>([]); // complete list to extract categories
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters State
  const [showFilters, setShowFilters] = useState(false);
  const [q, setQ] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [urgencia, setUrgencia] = useState('');
  const [tipo, setTipo] = useState('');
  const [categoria, setCategoria] = useState('');
  const [prioridad, setPrioridad] = useState('');
  const [areaResponsable, setAreaResponsable] = useState('');
  
  // Available unique categories extracted dynamically
  const [categories, setCategories] = useState<string[]>([]);

  const navigate = useNavigate();
  const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

  // Debounce free-text search
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQ(q);
    }, 400);
    return () => clearTimeout(handler);
  }, [q]);

  // Fetch unique categories once from all tickets
  useEffect(() => {
    axios
      .get<Ticket[]>(`${API_URL}/api/v1/tickets`)
      .then((res) => {
        setAllTickets(res.data);
        const uniqueCats = Array.from(new Set(res.data.map((t) => t.categoria).filter(Boolean)));
        setCategories(uniqueCats);
      })
      .catch((err) => console.error('Error fetching categories:', err));
  }, [API_URL]);

  // Fetch filtered tickets
  useEffect(() => {
    setLoading(true);
    setError(null);

    const params: Record<string, string> = {};
    if (debouncedQ) params.q = debouncedQ;
    if (fechaDesde) params.fecha_desde = fechaDesde;
    if (fechaHasta) params.fecha_hasta = fechaHasta;
    if (urgencia) params.urgencia = urgencia;
    if (tipo) params.tipo = tipo;
    if (categoria) params.categoria = categoria;
    if (prioridad) params.prioridad = prioridad;
    if (areaResponsable) params.area_responsable = areaResponsable;

    axios
      .get<Ticket[]>(`${API_URL}/api/v1/tickets`, { params })
      .then((res) => setTickets(res.data))
      .catch((err) => setError(err.message ?? 'Error al cargar tickets'))
      .finally(() => setLoading(false));
  }, [API_URL, debouncedQ, fechaDesde, fechaHasta, urgencia, tipo, categoria, prioridad, areaResponsable]);

  const handleClearFilters = () => {
    setQ('');
    setFechaDesde('');
    setFechaHasta('');
    setUrgencia('');
    setTipo('');
    setCategoria('');
    setPrioridad('');
    setAreaResponsable('');
  };

  return (
    <div style={{ maxWidth: 1100, margin: '2.5rem auto', padding: '0 1.5rem' }}>
      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.85rem', fontWeight: 800, color: theme.colors.textMain }}>
            🎫 Gestión de Incidentes
          </h1>
          <p style={{ margin: '0.25rem 0 0', color: theme.colors.textMuted, fontSize: '0.95rem' }}>
            Todos los tickets procesados por el sistema ITSM GenIA
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            onClick={() => setShowFilters(!showFilters)}
            style={{
              background: '#ffffff',
              border: `1.5px solid ${theme.colors.border}`,
              color: theme.colors.textMain,
              borderRadius: theme.borderRadius.md,
              padding: '0.65rem 1.2rem',
              fontWeight: 600,
              fontSize: '0.95rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              transition: theme.transitions.default,
              boxShadow: theme.boxShadow.sm,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = theme.colors.primary;
              e.currentTarget.style.backgroundColor = theme.colors.bgBlueLight;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = theme.colors.border;
              e.currentTarget.style.backgroundColor = '#ffffff';
            }}
          >
            🔍 {showFilters ? 'Ocultar Filtros' : 'Filtros Avanzados'}
          </button>
          
          <button
            id="btn-new-ticket"
            onClick={() => navigate('/create')}
            style={{
              background: `linear-gradient(135deg, ${theme.colors.primary}, ${theme.colors.secondary})`,
              color: '#fff',
              border: 'none',
              borderRadius: theme.borderRadius.md,
              padding: '0.65rem 1.4rem',
              fontWeight: 700,
              fontSize: '0.95rem',
              cursor: 'pointer',
              boxShadow: theme.boxShadow.md,
              transition: theme.transitions.default,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-1px)';
              e.currentTarget.style.boxShadow = '0 6px 20px rgba(37,99,235,0.25)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = theme.boxShadow.md;
            }}
          >
            + Nuevo ticket
          </button>
        </div>
      </div>

      {/* ── Filters Bar (Expandable) ── */}
      {showFilters && (
        <div style={{
          background: theme.colors.bgCard,
          border: `1px solid ${theme.colors.border}`,
          borderRadius: theme.borderRadius.lg,
          padding: '1.5rem',
          marginBottom: '1.5rem',
          boxShadow: theme.boxShadow.sm,
          animation: 'slideDown 0.2s ease',
        }}>
          <style>{`@keyframes slideDown { from { opacity: 0; transform: translateY(-5px); } to { opacity: 1; transform: translateY(0); } }`}</style>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
            {/* Free text query */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <label style={labelStyle}>Búsqueda libre</label>
              <input
                type="text"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Título o descripción..."
                style={inputStyle}
              />
            </div>

            {/* Fecha Desde */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <label style={labelStyle}>Fecha Desde</label>
              <input
                type="date"
                value={fechaDesde}
                onChange={(e) => setFechaDesde(e.target.value)}
                style={inputStyle}
              />
            </div>

            {/* Fecha Hasta */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <label style={labelStyle}>Fecha Hasta</label>
              <input
                type="date"
                value={fechaHasta}
                onChange={(e) => setFechaHasta(e.target.value)}
                style={inputStyle}
              />
            </div>

            {/* Tipo */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <label style={labelStyle}>Tipo</label>
              <select value={tipo} onChange={(e) => setTipo(e.target.value)} style={inputStyle}>
                <option value="">Todos</option>
                <option value="incidente">Incidente</option>
                <option value="requerimiento">Requerimiento</option>
                <option value="problema">Problema</option>
              </select>
            </div>

            {/* Categoría */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <label style={labelStyle}>Categoría</label>
              <select value={categoria} onChange={(e) => setCategoria(e.target.value)} style={inputStyle}>
                <option value="">Todas</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            {/* Prioridad */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <label style={labelStyle}>Prioridad</label>
              <select value={prioridad} onChange={(e) => setPrioridad(e.target.value)} style={inputStyle}>
                <option value="">Todas</option>
                <option value="P1">P1 - Crítico</option>
                <option value="P2">P2 - Alto</option>
                <option value="P3">P3 - Medio</option>
                <option value="P4">P4 - Bajo</option>
              </select>
            </div>

            {/* Urgencia */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <label style={labelStyle}>Urgencia</label>
              <select value={urgencia} onChange={(e) => setUrgencia(e.target.value)} style={inputStyle}>
                <option value="">Todas</option>
                <option value="alta">Alta</option>
                <option value="media">Media</option>
                <option value="baja">Baja</option>
              </select>
            </div>

            {/* Area Responsable */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <label style={labelStyle}>Área Responsable</label>
              <select value={areaResponsable} onChange={(e) => setAreaResponsable(e.target.value)} style={inputStyle}>
                <option value="">Todas</option>
                <option value="Infraestructura">Infraestructura</option>
                <option value="Helpdesk">Helpdesk</option>
                <option value="Seguridad">Seguridad</option>
                <option value="Sistemas">Sistemas</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button
              onClick={handleClearFilters}
              style={{
                background: 'none',
                border: 'none',
                color: theme.colors.danger,
                fontSize: '0.88rem',
                fontWeight: 600,
                cursor: 'pointer',
                padding: '0.5rem 1rem',
                borderRadius: theme.borderRadius.sm,
                transition: theme.transitions.default,
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = theme.colors.dangerBg}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              🧹 Limpiar filtros
            </button>
          </div>
        </div>
      )}

      {/* ── Status Info (Results count) ── */}
      {!loading && !error && (
        <div style={{ marginBottom: '1rem', color: theme.colors.textMuted, fontSize: '0.9rem', fontWeight: 500 }}>
          {tickets.length === 1
            ? 'Mostrando 1 ticket encontrado'
            : `Mostrando ${tickets.length} de ${allTickets.length} tickets`}
        </div>
      )}

      {/* ── States ── */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '4rem', color: theme.colors.textMuted, fontSize: '1.05rem' }}>
          ⏳ Cargando incidentes filtrados...
        </div>
      )}

      {error && (
        <div style={{
          background: theme.colors.dangerBg, border: `1px solid ${theme.colors.danger}`, borderRadius: theme.borderRadius.md,
          padding: '1rem 1.5rem', color: theme.colors.danger, marginBottom: '1rem', fontWeight: 500,
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Empty State for no tickets total */}
      {!loading && !error && allTickets.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '4rem 2rem', color: theme.colors.textMuted,
          background: theme.colors.bgCard, borderRadius: theme.borderRadius.lg, border: `2px dashed ${theme.colors.border}`,
        }}>
          <p style={{ fontSize: '3rem', margin: 0 }}>📭</p>
          <h3 style={{ margin: '1rem 0 0.5rem 0', color: theme.colors.textMain, fontWeight: 700 }}>No hay tickets aún</h3>
          <p style={{ margin: 0, fontSize: '0.9rem' }}>
            Comienza creando el primer ticket haciendo clic en el botón "+ Nuevo ticket".
          </p>
        </div>
      )}

      {/* Empty State for filters with no results */}
      {!loading && !error && allTickets.length > 0 && tickets.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '4rem 2rem', color: theme.colors.textMuted,
          background: theme.colors.bgCard, borderRadius: theme.borderRadius.lg, border: `1px solid ${theme.colors.border}`,
        }}>
          <p style={{ fontSize: '3rem', margin: 0 }}>🔍</p>
          <h3 style={{ margin: '1rem 0 0.5rem 0', color: theme.colors.textMain, fontWeight: 700 }}>Sin resultados</h3>
          <p style={{ margin: '0 0 1.5rem 0', fontSize: '0.9rem' }}>
            No se encontraron tickets con los filtros aplicados.
          </p>
          <button
            onClick={handleClearFilters}
            style={{
              padding: '0.55rem 1.2rem',
              backgroundColor: theme.colors.primary,
              color: '#ffffff',
              border: 'none',
              borderRadius: theme.borderRadius.md,
              fontWeight: 600,
              fontSize: '0.88rem',
              cursor: 'pointer',
              transition: theme.transitions.default,
            }}
          >
            Limpiar Filtros
          </button>
        </div>
      )}

      {/* ── Table ── */}
      {!loading && !error && tickets.length > 0 && (
        <div style={{
          background: theme.colors.bgCard,
          borderRadius: theme.borderRadius.lg,
          border: `1px solid ${theme.colors.border}`,
          boxShadow: theme.boxShadow.sm,
          overflow: 'hidden'
        }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ background: theme.colors.bgBlueLight, borderBottom: `1.5px solid ${theme.colors.border}`, color: theme.colors.textMain }}>
                  {['ID', 'Título', 'Tipo', 'Categoría', 'Prioridad', 'Estado', 'Soporte', 'Creado'].map((col) => (
                    <th key={col} style={{ padding: '1rem 1.25rem', fontWeight: 700, letterSpacing: '0.03em', fontSize: '0.8rem', textTransform: 'uppercase' }}>
                      {col}
                    </th>
                  ))}
                  <th style={{ padding: '1rem 1.25rem', fontWeight: 700, letterSpacing: '0.03em', fontSize: '0.8rem', textTransform: 'uppercase', textAlign: 'center' }}>
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t, idx) => (
                  <tr
                    key={t.id}
                    style={{
                      borderBottom: `1px solid ${theme.colors.border}`,
                      background: idx % 2 === 0 ? '#ffffff' : '#fcfdfe',
                      transition: theme.transitions.default,
                    }}
                    onMouseEnter={(e) => ((e.currentTarget as HTMLTableRowElement).style.background = '#f1f5f9')}
                    onMouseLeave={(e) => ((e.currentTarget as HTMLTableRowElement).style.background = idx % 2 === 0 ? '#ffffff' : '#fcfdfe')}
                  >
                    {/* ID */}
                    <td style={{ padding: '0.9rem 1.25rem', color: theme.colors.primary, fontWeight: 700 }}>
                      #{t.id}
                    </td>
                    
                    {/* Título */}
                    <td style={{ padding: '0.9rem 1.25rem', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600 }}>
                      {t.titulo}
                    </td>
                    
                    {/* Tipo */}
                    <td style={{ padding: '0.9rem 1.25rem', textTransform: 'capitalize', color: theme.colors.textMuted }}>
                      {t.tipo}
                    </td>
                    
                    {/* Categoría */}
                    <td style={{ padding: '0.9rem 1.25rem', color: theme.colors.textMuted }}>
                      {t.categoria}
                    </td>
                    
                    {/* Prioridad */}
                    <td style={{ padding: '0.9rem 1.25rem' }}>
                      <PriorityBadge priority={t.prioridad} />
                    </td>
                    
                    {/* Estado */}
                    <td style={{ padding: '0.9rem 1.25rem' }}>
                      <span style={{
                        background: '#e0f2fe', color: '#0369a1', borderRadius: theme.borderRadius.full,
                        padding: '2px 10px', fontSize: '0.75rem', fontWeight: 700, textTransform: 'capitalize',
                      }}>
                        {t.estado}
                      </span>
                    </td>
                    
                    {/* Soporte Badge */}
                    <td style={{ padding: '0.9rem 1.25rem' }}>
                      {t.escalado_a_humano ? (
                        <span style={{
                          background: theme.colors.dangerBg, color: theme.colors.danger, border: `1px solid ${theme.colors.danger}`,
                          borderRadius: theme.borderRadius.full, padding: '2px 8px', fontSize: '0.72rem', fontWeight: 700,
                          textTransform: 'uppercase', letterSpacing: '0.02em',
                        }}>
                          👨‍💼 Humano
                        </span>
                      ) : (
                        <span style={{
                          background: theme.colors.successBg, color: theme.colors.success, border: `1px solid ${theme.colors.success}`,
                          borderRadius: theme.borderRadius.full, padding: '2px 8px', fontSize: '0.72rem', fontWeight: 700,
                          textTransform: 'uppercase', letterSpacing: '0.02em',
                        }}>
                          🤖 GenIA
                        </span>
                      )}
                    </td>
                    
                    {/* Fecha de creación */}
                    <td style={{ padding: '0.9rem 1.25rem', color: theme.colors.textMuted, fontSize: '0.8rem' }}>
                      {new Date(t.creado_en).toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' })}
                    </td>
                    
                    {/* Acciones */}
                    <td style={{ padding: '0.9rem 1.25rem', textAlign: 'center' }}>
                      <button
                        onClick={() => navigate(`/tickets/${t.id}`)}
                        style={{
                          background: theme.colors.bgBlueLight,
                          border: `1px solid ${theme.colors.secondaryLight}`,
                          color: theme.colors.primary,
                          borderRadius: theme.borderRadius.sm,
                          padding: '0.4rem 0.8rem',
                          fontSize: '0.85rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.3rem',
                          transition: theme.transitions.default,
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = theme.colors.primary;
                          e.currentTarget.style.color = '#ffffff';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = theme.colors.bgBlueLight;
                          e.currentTarget.style.color = theme.colors.primary;
                        }}
                      >
                        👁️ Ver detalle
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const labelStyle: React.CSSProperties = {
  fontSize: '0.8rem',
  fontWeight: 700,
  color: theme.colors.textMain,
  marginBottom: '0.3rem',
  textTransform: 'uppercase',
  letterSpacing: '0.03em',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.55rem 0.75rem',
  borderRadius: theme.borderRadius.sm,
  border: `1.5px solid ${theme.colors.border}`,
  fontSize: '0.88rem',
  color: theme.colors.textMain,
  outline: 'none',
  backgroundColor: '#ffffff',
  transition: theme.transitions.default,
};
