import { Link, useLocation } from 'react-router-dom';
import { useIncidentSocket } from '../hooks/useIncidentSocket.js';
import { useState, useCallback, useEffect } from 'react';

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

const THEME_STORAGE_KEY = 'incident-ops-theme';

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
  const [theme, setTheme] = useState('light');

  const handleWsEvent = useCallback(() => {}, []);

  const { connected } = useIncidentSocket(handleWsEvent);
  if (connected !== wsConnected) setWsConnected(connected);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === 'light' || stored === 'dark') {
        setTheme(stored);
        return;
      }
    } catch (error) {
      // ignore
    }
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setTheme(prefersDark ? 'dark' : 'light');
  }, []);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch (error) {
      // best effort
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  }, []);

  const currentPage = pageNames[location.pathname] || 'Incident Response';

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <svg width="22" height="22" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="100" height="100" rx="20" fill="currentColor" style={{ color: 'var(--accent)' }}/>
            <path d="M20 55 H35 L45 25 L55 85 L65 55 H80" stroke="var(--bg-body)" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="sidebar-logo-text">ExpertMind</span>
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
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          >
            <span aria-hidden="true">{theme === 'light' ? '🌙' : '☀️'}</span>
          </button>
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
