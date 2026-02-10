import { NavLink, useLocation } from 'react-router-dom';
import {
	LayoutDashboard,
	AlertTriangle,
	CalendarClock,
	BarChart3,
	Activity,
	PanelLeftClose,
	PanelLeft,
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '../lib/utils';

const mainNav = [
	{ name: 'Overview', href: '/', icon: LayoutDashboard },
	{ name: 'Incidents', href: '/incidents', icon: AlertTriangle },
	{ name: 'On-Call', href: '/oncall', icon: CalendarClock },
];

const insightNav = [
	{ name: 'Analytics', href: '/analytics', icon: BarChart3 },
	{ name: 'Health', href: '/health', icon: Activity },
];

export default function Sidebar() {
	const [collapsed, setCollapsed] = useState(false);
	const location = useLocation();

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
					'group flex items-center gap-2.5 rounded-md px-2.5 py-[7px] text-[13px] transition-colors duration-100',
					isActive
						? 'bg-white/[0.08] text-white font-medium'
						: 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]'
				)}
				title={collapsed ? item.name : undefined}
			>
				<item.icon
					className={cn('h-4 w-4 shrink-0', isActive ? 'text-zinc-200' : 'text-zinc-500')}
					strokeWidth={isActive ? 2 : 1.5}
				/>
				{!collapsed && <span>{item.name}</span>}
			</NavLink>
		);
	};

	return (
		<aside
			className={cn(
				'fixed left-0 top-0 z-40 flex h-screen flex-col bg-zinc-900 transition-[width] duration-150',
				collapsed ? 'w-[60px]' : 'w-[220px]'
			)}
		>
			{/* Brand */}
			<div className="flex h-14 items-center gap-2 px-4 shrink-0">
				<div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-blue-600">
					<span className="text-[11px] font-bold text-white leading-none">R</span>
				</div>
				{!collapsed && (
					<span className="text-[14px] font-semibold tracking-[-0.01em] text-white">
						Resilience
					</span>
				)}
			</div>

			{/* Navigation */}
			<nav className="flex-1 overflow-y-auto px-2 pb-2">
				<div className="space-y-0.5">
					{mainNav.map(renderLink)}
				</div>

				{!collapsed && (
					<p className="mt-5 mb-1.5 px-2.5 text-[10px] font-medium uppercase tracking-widest text-zinc-600">
						Insights
					</p>
				)}
				{collapsed && <div className="mt-4 mb-1 mx-2.5 border-t border-zinc-800" />}
				<div className="space-y-0.5">
					{insightNav.map(renderLink)}
				</div>
			</nav>

			{/* Footer */}
			<div className="shrink-0 border-t border-zinc-800 p-2">
				{!collapsed && (
					<div className="mb-1.5 flex items-center gap-2 px-2.5 py-1.5">
						<div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zinc-700 text-[10px] font-semibold text-zinc-300">
							SR
						</div>
						<div className="min-w-0">
							<p className="truncate text-[12px] font-medium text-zinc-300">SRE Team</p>
							<p className="text-[10px] text-zinc-600">Platform Ops</p>
						</div>
					</div>
				)}
				<button
					onClick={() => setCollapsed((c) => !c)}
					className="flex w-full items-center justify-center rounded-md py-1 text-zinc-600 hover:text-zinc-400 hover:bg-white/[0.04] transition-colors"
					title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
				>
					{collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
				</button>
			</div>
		</aside>
	);
}
