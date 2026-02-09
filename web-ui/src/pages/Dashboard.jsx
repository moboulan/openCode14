import { useEffect, useCallback, useState } from 'react';
import IncidentList from '../components/IncidentList.jsx';
import IncidentAnalytics from '../components/IncidentAnalytics.jsx';
import { useIncidentSocket } from '../hooks/useIncidentSocket.js';
import { getIncidentAnalytics, listIncidents } from '../services/api.js';

function Dashboard() {
  const [incidents, setIncidents] = useState([]);
  const [total, setTotal] = useState(0);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadIncidents = useCallback(async () => {
    try {
      const data = await listIncidents({ limit: 50 });
      setIncidents(data.incidents ?? []);
      setTotal(data.total ?? data.incidents?.length ?? 0);
      setError(null);
    } catch {
      setError('Failed to load incidents');
    }
  }, []);

  const loadAnalytics = useCallback(async () => {
    try {
      const data = await getIncidentAnalytics();
      setAnalytics(data);
    } catch {
      setError('Failed to load analytics');
    }
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([loadIncidents(), loadAnalytics()]);
    setLoading(false);
  }, [loadIncidents, loadAnalytics]);

  useEffect(() => {
    loadAll();
    const id = window.setInterval(loadAll, 30000);
    return () => window.clearInterval(id);
  }, [loadAll]);

  useIncidentSocket(loadAll);

  return (
    <div className="page">
      {error && <div className="error-banner">{error}</div>}

      {/* Incidents first */}
      <IncidentList incidents={incidents} total={total} />

      {/* Analytics below */}
      {analytics && (
        <IncidentAnalytics summary={analytics.summary} byService={analytics.by_service} />
      )}

      {loading && <span className="loading-text">Refreshing…</span>}
    </div>
  );
}

export default Dashboard;
