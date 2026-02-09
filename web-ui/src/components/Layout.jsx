import { Link, useLocation } from 'react-router-dom';
import { useState, useCallback, useEffect } from 'react';
import { useIncidentSocket } from '@/hooks/useIncidentSocket';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  BarChart3,
  Users,
  Activity,
  Moon,
  Sun,
  Wifi,
  WifiOff,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/metrics', icon: BarChart3, label: 'SRE Metrics' },
  { to: '/oncall', icon: Users, label: 'On-Call' },
];

const pageNames = {
  '/': 'Dashboard',
  '/metrics': 'SRE Metrics',
  '/oncall': 'On-Call',
};

const THEME_KEY = 'incident-ops-theme';

function SidebarLink({ to, icon: Icon, label }) {
  const { pathname } = useLocation();
  const isActive = pathname === to || (to !== '/' && pathname.startsWith(to));

  return (
    <Link
      to={to}
      className={cn(
        'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
        isActive
          ? 'bg-sidebar-accent text-sidebar-accent-foreground'
          : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
      )}
    >
      <Icon className="h-4 w-4" />
      {label}
    </Link>
  );
}

export default function Layout({ children }) {
  const { pathname } = useLocation();
  const [theme, setTheme] = useState('light');

  const handleWsEvent = useCallback(() => {}, []);
  const { connected } = useIncidentSocket(handleWsEvent);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(THEME_KEY);
      if (stored === 'light' || stored === 'dark') {
        setTheme(stored);
        return;
      }
    } catch {}
    setTheme(window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    try { localStorage.setItem(THEME_KEY, theme); } catch {}
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  }, []);

  const currentPage = pageNames[pathname] || 'Incident Response';

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="flex w-56 flex-col border-r border-sidebar-border bg-sidebar-background">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <Activity className="h-6 w-6 text-foreground" />
          <span className="text-base font-bold tracking-tight">ExpertMind</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3">
          {navItems.map((item) => (
            <SidebarLink key={item.to} {...item} />
          ))}
        </nav>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 items-center justify-between border-b border-border bg-card px-6">
          <h1 className="text-sm font-semibold">{currentPage}</h1>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
              {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            </Button>
            <div className={cn(
              'flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
              connected
                ? 'bg-status-resolved/15 text-status-resolved'
                : 'bg-muted text-muted-foreground'
            )}>
              {connected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
              {connected ? 'Live' : 'Offline'}
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
