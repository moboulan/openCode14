import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Incidents from './pages/Incidents';
import IncidentDetail from './pages/IncidentDetail';
import Analytics from './pages/Analytics';
import OnCall from './pages/OnCall';
import SystemHealth from './pages/SystemHealth';
import NotFound from './pages/NotFound';

export default function App() {
	return (
		<div className="flex min-h-screen">
			<Sidebar />
			<main className="ml-[220px] flex-1 min-h-screen transition-[margin] duration-150">
				<div className="mx-auto max-w-[1280px] px-8 py-7">
					<Routes>
						<Route path="/" element={<Dashboard />} />
						<Route path="/incidents" element={<Incidents />} />
						<Route path="/incidents/:incidentId" element={<IncidentDetail />} />
						<Route path="/analytics" element={<Analytics />} />
						<Route path="/oncall" element={<OnCall />} />
						<Route path="/health" element={<SystemHealth />} />
						<Route path="*" element={<NotFound />} />
					</Routes>
				</div>
			</main>
		</div>
	);
}
