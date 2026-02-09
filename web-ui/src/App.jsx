import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import Dashboard from './pages/Dashboard.jsx';
import IncidentDetail from './pages/IncidentDetail.jsx';
import OnCall from './pages/OnCall.jsx';
import Metrics from './pages/Metrics.jsx';
import NotFound from './pages/NotFound.jsx';

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
