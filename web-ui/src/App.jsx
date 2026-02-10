import { Routes, Route, Navigate } from 'react-router-dom';
import { TooltipProvider } from '@radix-ui/react-tooltip';
import { useAuth } from '@/hooks/useAuth';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Incidents from './pages/Incidents';
import IncidentDetail from './pages/IncidentDetail';
import Alerts from './pages/Alerts';
import Analytics from './pages/Analytics';
import OnCall from './pages/OnCall';
import Notifications from './pages/Notifications';
import SystemHealth from './pages/SystemHealth';
import NotFound from './pages/NotFound';

function ProtectedRoute({ children }) {
	const { isAuthenticated } = useAuth();
	if (!isAuthenticated) return <Navigate to="/login" replace />;
	return children;
}

export default function App() {
	const { isAuthenticated } = useAuth();

	if (!isAuthenticated) {
		return (
			<Routes>
				<Route path="/login" element={<Login />} />
				<Route path="*" element={<Navigate to="/login" replace />} />
			</Routes>
		);
	}

	return (
		<TooltipProvider delayDuration={200}>
			<div className="flex min-h-screen">
				<Sidebar />
				<main className="ml-[240px] flex-1 min-h-screen transition-[margin] duration-150">
					<div className="mx-auto max-w-[1400px] px-8 py-6">
						<Routes>
							<Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
							<Route path="/incidents" element={<ProtectedRoute><Incidents /></ProtectedRoute>} />
							<Route path="/incidents/:incidentId" element={<ProtectedRoute><IncidentDetail /></ProtectedRoute>} />
							<Route path="/alerts" element={<ProtectedRoute><Alerts /></ProtectedRoute>} />
							<Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
							<Route path="/oncall" element={<ProtectedRoute><OnCall /></ProtectedRoute>} />
							<Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
							<Route path="/health" element={<ProtectedRoute><SystemHealth /></ProtectedRoute>} />
							<Route path="/login" element={<Navigate to="/" replace />} />
							<Route path="*" element={<NotFound />} />
						</Routes>
					</div>
				</main>
			</div>
		</TooltipProvider>
	);
}
