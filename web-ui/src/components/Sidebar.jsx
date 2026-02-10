import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
	LayoutDashboard,
	AlertTriangle,
	CalendarClock,
	BarChart3,
	Bell,
	Zap,
	LogOut,
	Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';

const mainNav = [
	{ name: 'Dashboard', href: '/', icon: LayoutDashboard },
	{ name: 'Incidents', href: '/incidents', icon: AlertTriangle },
	{ name: 'Alerts', href: '/alerts', icon: Zap },
	{ name: 'On-Call', href: '/oncall', icon: CalendarClock },
	{ name: 'Notifications', href: '/notifications', icon: Bell },
];

const insightNav = [
	{ name: 'Analytics', href: '/analytics', icon: BarChart3 },
];

export default function Sidebar() {
	const location = useLocation();
	const navigate = useNavigate();
	const { user, logout } = useAuth();

	const renderLink = (item) => {
		const isActive =
			item.href === '/'
				? location.pathname === '/'
				: location.pathname.startsWith(item.href);

		return (
			<NavLink
				key={item.name}
				to={item.href}
				className={cn(
					'group flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-all duration-150',
					isActive
						? 'bg-primary/10 text-primary'
						: 'text-sidebar-foreground hover:text-foreground hover:bg-white/4'
				)}
			>
				<item.icon
					className={cn('h-4 w-4 shrink-0', isActive ? 'text-primary' : 'text-zinc-500')}
					strokeWidth={isActive ? 2.2 : 1.5}
				/>
				<span>{item.name}</span>
			</NavLink>
		);
	};

	return (
		<aside className="fixed left-0 top-0 z-40 flex h-screen w-60 flex-col border-r border-border bg-sidebar">
			{/* Brand */}
			<div className="flex h-14 items-center gap-2.5 px-5 shrink-0 border-b border-border">
				<div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary">
					<Shield className="h-4 w-4 text-white" />
				</div>
				<span className="text-[15px] font-semibold tracking-tight text-foreground">
					ExpertMind
				</span>
			</div>

			{/* Navigation */}
			<nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
				<div className="space-y-1">
					<p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
						Operations
					</p>
					{mainNav.map(renderLink)}
				</div>

				<div className="space-y-1">
					<p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
						Insights
					</p>
					{insightNav.map(renderLink)}
				</div>
			</nav>

			{/* Footer */}
			<div className="shrink-0 border-t border-border p-3">
				<div className="flex items-center gap-3 rounded-lg px-3 py-2">
					<div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary text-[11px] font-bold">
						{user?.name?.split(' ').map(w => w[0]).join('') || 'A'}
					</div>
					<div className="min-w-0 flex-1">
						<p className="truncate text-[12px] font-medium text-foreground">{user?.name || 'Admin'}</p>
						<p className="text-[10px] text-zinc-500">{user?.role || 'admin'}</p>
					</div>
					<button
						onClick={() => { logout(); navigate('/login'); }}
						className="rounded-md p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
						title="Sign out"
					>
						<LogOut className="h-4 w-4" />
					</button>
				</div>
			</div>
		</aside>
	);
}
