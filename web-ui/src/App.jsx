import { Routes, Route } from 'react-router-dom';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import IncidentDetail from '@/pages/IncidentDetail';
import OnCall from '@/pages/OnCall';
import Metrics from '@/pages/Metrics';
import NotFound from '@/pages/NotFound';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
        <Route path="/oncall" element={<OnCall />} />
        <Route path="/metrics" element={<Metrics />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Layout>
  );
}

export default App;
