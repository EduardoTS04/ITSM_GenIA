import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { theme } from '../theme';

export default function Navbar() {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/' && location.pathname === '/') return true;
    if (path !== '/' && location.pathname.startsWith(path)) return true;
    return false;
  };

  const linkStyle = (path: string): React.CSSProperties => {
    const active = isActive(path);
    return {
      marginLeft: '1.5rem',
      color: active ? '#ffffff' : 'rgba(255, 255, 255, 0.75)',
      textDecoration: 'none',
      fontWeight: active ? 600 : 500,
      fontSize: '0.95rem',
      padding: '0.5rem 0.9rem',
      borderRadius: theme.borderRadius.md,
      backgroundColor: active ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
      transition: theme.transitions.default,
    };
  };

  return (
    <nav style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.85rem 2rem',
      background: `linear-gradient(135deg, ${theme.colors.primary}, #1e40af)`,
      boxShadow: theme.boxShadow.md,
      position: 'sticky',
      top: 0,
      zIndex: 1000,
    }}>
      {/* Brand / Logo */}
      <Link to="/" style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.6rem',
        textDecoration: 'none',
        color: '#ffffff',
      }}>
        <span style={{ fontSize: '1.5rem' }}>🤖</span>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontWeight: 800, fontSize: '1.2rem', letterSpacing: '0.02em', lineHeight: 1.1 }}>
            ITSM GenIA
          </span>
          <span style={{ fontSize: '0.7rem', color: theme.colors.secondaryLight, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            NTT DATA HACKATHON
          </span>
        </div>
      </Link>

      {/* Nav Links */}
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <Link to="/incidents" style={linkStyle('/incidents')} onMouseEnter={(e) => {
          if (!isActive('/incidents')) e.currentTarget.style.color = '#ffffff';
        }} onMouseLeave={(e) => {
          if (!isActive('/incidents')) e.currentTarget.style.color = 'rgba(255, 255, 255, 0.75)';
        }}>
          🎫 Incidentes
        </Link>
        <Link to="/create" style={linkStyle('/create')} onMouseEnter={(e) => {
          if (!isActive('/create')) e.currentTarget.style.color = '#ffffff';
        }} onMouseLeave={(e) => {
          if (!isActive('/create')) e.currentTarget.style.color = 'rgba(255, 255, 255, 0.75)';
        }}>
          ✨ Crear Incidente
        </Link>
      </div>
    </nav>
  );
}

