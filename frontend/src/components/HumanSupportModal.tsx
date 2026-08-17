import React, { useState } from 'react';
import axios from 'axios';
import { theme } from '../theme';

interface HumanSupportModalProps {
  ticketId: number;
  isOpen: boolean;
  onClose: () => void;
  onEscalated?: () => void;
}

export default function HumanSupportModal({ ticketId, isOpen, onClose, onEscalated }: HumanSupportModalProps) {
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justification, setJustification] = useState('');

  if (!isOpen) return null;

  const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

  const handleEscalate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await axios.post(`${API_URL}/api/v1/tickets/${ticketId}/escalate`);
      setSuccess(true);
      if (onEscalated) {
        onEscalated();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Error al escalar el ticket');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(30, 58, 95, 0.6)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 2000,
      padding: '1rem',
    }}>
      <div style={{
        background: '#ffffff',
        borderRadius: theme.borderRadius.lg,
        boxShadow: theme.boxShadow.lg,
        maxWidth: 500,
        width: '100%',
        padding: '2rem',
        position: 'relative',
        animation: 'fadeIn 0.3s ease',
      }}>
        {/* Close button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '1rem',
            right: '1rem',
            background: 'none',
            border: 'none',
            fontSize: '1.25rem',
            cursor: 'pointer',
            color: theme.colors.textMuted,
          }}
        >
          ✕
        </button>

        {!success ? (
          <>
            <h3 style={{ margin: '0 0 0.5rem 0', color: theme.colors.textMain, fontSize: '1.4rem', fontWeight: 800 }}>
              🆘 Contactar Soporte Humano
            </h3>
            <p style={{ margin: '0 0 1.5rem 0', color: theme.colors.textMuted, fontSize: '0.9rem', lineHeight: 1.5 }}>
              ¿Las soluciones de la inteligencia artificial no resolvieron tu problema? Elige uno de nuestros canales humanos de atención.
            </p>

            {/* Quick contact methods */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
              <a
                href="#chat"
                onClick={(e) => {
                  e.preventDefault();
                  alert('Iniciando chat de soporte en vivo (Demo)...');
                }}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  padding: '1rem',
                  borderRadius: theme.borderRadius.md,
                  border: `1px solid ${theme.colors.border}`,
                  textDecoration: 'none',
                  color: theme.colors.textMain,
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  textAlign: 'center',
                  backgroundColor: theme.colors.bgMain,
                  transition: theme.transitions.default,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = theme.colors.primary;
                  e.currentTarget.style.backgroundColor = theme.colors.bgBlueLight;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = theme.colors.border;
                  e.currentTarget.style.backgroundColor = theme.colors.bgMain;
                }}
              >
                <span style={{ fontSize: '1.5rem', marginBottom: '0.4rem' }}>💬</span>
                Chat en Vivo
                <span style={{ fontSize: '0.75rem', fontWeight: 400, color: theme.colors.textMuted, marginTop: '0.2rem' }}>
                  Espera: &lt; 2 min
                </span>
              </a>

              <a
                href="tel:+56912345678"
                onClick={(e) => {
                  e.preventDefault();
                  alert('Llamando a soporte al +56 9 1234 5678 (Demo)...');
                }}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  padding: '1rem',
                  borderRadius: theme.borderRadius.md,
                  border: `1px solid ${theme.colors.border}`,
                  textDecoration: 'none',
                  color: theme.colors.textMain,
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  textAlign: 'center',
                  backgroundColor: theme.colors.bgMain,
                  transition: theme.transitions.default,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = theme.colors.primary;
                  e.currentTarget.style.backgroundColor = theme.colors.bgBlueLight;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = theme.colors.border;
                  e.currentTarget.style.backgroundColor = theme.colors.bgMain;
                }}
              >
                <span style={{ fontSize: '1.5rem', marginBottom: '0.4rem' }}>📞</span>
                Llamar a Soporte
                <span style={{ fontSize: '0.75rem', fontWeight: 400, color: theme.colors.textMuted, marginTop: '0.2rem' }}>
                  +56 9 1234 5678
                </span>
              </a>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', margin: '1rem 0', gap: '0.5rem' }}>
              <hr style={{ flex: 1, border: 'none', borderTop: `1px solid ${theme.colors.border}` }} />
              <span style={{ fontSize: '0.8rem', color: theme.colors.textMuted, fontWeight: 600 }}>O BIEN</span>
              <hr style={{ flex: 1, border: 'none', borderTop: `1px solid ${theme.colors.border}` }} />
            </div>

            {/* Escalate form */}
            <form onSubmit={handleEscalate}>
              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontWeight: 600, color: theme.colors.textMain, fontSize: '0.85rem', marginBottom: '0.4rem' }}>
                  Motivo de escalamiento (opcional)
                </label>
                <textarea
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  placeholder="Ej: He seguido los pasos indicados por la IA pero sigo sin acceso al sistema..."
                  rows={3}
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.85rem',
                    borderRadius: theme.borderRadius.md,
                    border: `1.5px solid ${theme.colors.border}`,
                    fontSize: '0.9rem',
                    resize: 'none',
                    outline: 'none',
                  }}
                />
              </div>

              {error && (
                <div style={{
                  backgroundColor: theme.colors.dangerBg,
                  border: `1px solid ${theme.colors.danger}`,
                  borderRadius: theme.borderRadius.md,
                  padding: '0.75rem',
                  color: theme.colors.danger,
                  fontSize: '0.85rem',
                  marginBottom: '1rem',
                }}>
                  ⚠️ {error}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                style={{
                  width: '100%',
                  padding: '0.8rem',
                  backgroundColor: theme.colors.primary,
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: theme.borderRadius.md,
                  fontWeight: 700,
                  fontSize: '0.95rem',
                  cursor: submitting ? 'not-allowed' : 'pointer',
                  boxShadow: theme.boxShadow.md,
                  transition: theme.transitions.default,
                }}
              >
                {submitting ? 'Escalando ticket...' : '🙋‍♂️ Escalar a Soporte Humano'}
              </button>
            </form>
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '1rem 0' }}>
            <span style={{ fontSize: '3rem' }}>🚀</span>
            <h3 style={{ margin: '1rem 0 0.5rem 0', color: theme.colors.success, fontSize: '1.3rem', fontWeight: 800 }}>
              ¡Ticket Escalado Exitosamente!
            </h3>
            <p style={{ margin: '0 0 1.5rem 0', color: theme.colors.textMuted, fontSize: '0.9rem', lineHeight: 1.5 }}>
              Tu ticket ha sido marcado para revisión prioritaria por un agente técnico humano. Nos pondremos en contacto contigo pronto.
            </p>
            <button
              onClick={onClose}
              style={{
                padding: '0.6rem 1.5rem',
                backgroundColor: theme.colors.primary,
                color: '#ffffff',
                border: 'none',
                borderRadius: theme.borderRadius.md,
                fontWeight: 600,
                fontSize: '0.9rem',
                cursor: 'pointer',
                transition: theme.transitions.default,
              }}
            >
              Cerrar Ventana
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
