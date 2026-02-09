import { Link, useLocation } from 'react-router-dom';
import { useIncidentSocket } from '../hooks/useIncidentSocket.js';
import { useState, useCallback } from 'react';

/* ── SVG Icons (inline, no deps) ──────────────────── */
const icons = {
  dashboard: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="9" />
      <rect x="14" y="3" width="7" height="5" />
      <rect x="14" y="12" width="7" height="9" />
      <rect x="3" y="16" width="7" height="5" />
    </svg>
  ),
  metrics: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="M7 16l4-8 4 4 5-9" />
    </svg>
  ),
  oncall: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
};

const pageNames = {
  '/': 'Dashboard',
  '/metrics': 'SRE Metrics',
  '/oncall': 'On-Call',
};

function SidebarLink({ to, icon, label }) {
  const location = useLocation();
  const isActive = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
  const cls = `sidebar-link${isActive ? ' active' : ''}`;

  return (
    <Link to={to} className={cls}>
      {icon}
      <span>{label}</span>
    </Link>
  );
}

function Layout({ children }) {
  const [wsConnected, setWsConnected] = useState(false);
  const location = useLocation();

  const handleWsEvent = useCallback(() => {}, []);

  const { connected } = useIncidentSocket(handleWsEvent);
  if (connected !== wsConnected) setWsConnected(connected);

  const currentPage = pageNames[location.pathname] || 'Incident Response';

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <svg width="28" height="28" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="100" height="100" rx="20" fill="#111827"/>
            <path d="M20 55 H35 L45 25 L55 85 L65 55 H80" stroke="#ffffff" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="sidebar-logo-text">Incident Ops</span>
        </div>
        <nav className="sidebar-nav">
          <SidebarLink to="/" icon={icons.dashboard} label="Dashboard" />
          <SidebarLink to="/metrics" icon={icons.metrics} label="SRE Metrics" />
          <SidebarLink to="/oncall" icon={icons.oncall} label="On-Call" />
        </nav>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <span className="topbar-title">{currentPage}</span>
          <div className="topbar-spacer" />
          <span className="topbar-badge">
            <span className={`dot${wsConnected ? '' : ' off'}`} />
            {wsConnected ? 'Live' : 'Offline'}
          </span>
        </header>
        <div className="content">
          {children}
        </div>
      </div>
    </div>
  );
}

export default Layout;
