import { useEffect, useCallback, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar,
} from 'recharts';
import { getIncidentAnalytics, getMetricsTrends } from '@/services/api';
import { formatDuration } from '@/utils/formatters';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  AlertTriangle, Clock, CheckCircle2, Timer, TrendingUp, BarChart3,
} from 'lucide-react';

function ChartTooltip({ active, payload, label, valueFormatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border bg-popover p-2 shadow-md">
      <p className="text-xs font-medium text-popover-foreground mb-1">{label}</p>
      {payload.map((entry, idx) => (
        <div key={idx} className="flex items-center gap-2 text-xs">
          <span className="h-2 w-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-mono font-medium">{valueFormatter ? valueFormatter(entry.value) : entry.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function Metrics() {
  const [data, setData] = useState(null);
  const [trends, setTrends] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [analytics, trendData] = await Promise.all([
        getIncidentAnalytics(),
        getMetricsTrends(),
      ]);
      setData(analytics);
      setTrends(trendData);
      setError(null);
    } catch {
      setError('Failed to load metrics');
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, Number(import.meta.env.VITE_METRICS_POLL_INTERVAL || 15000));
    return () => clearInterval(interval);
  }, [load]);

  if (error) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
        {error}
      </div>
    );
  }
  if (!data) return <p className="text-sm text-muted-foreground animate-pulse">Loading metrics…</p>;

  const summary = data.summary;
  const byService = data.by_service ?? [];

  const stats = [
    { label: 'Total', value: summary.total ?? 0, icon: AlertTriangle, color: 'text-foreground' },
    { label: 'Open', value: summary.open_count ?? 0, icon: AlertTriangle, color: 'text-status-open' },
    { label: 'Acknowledged', value: summary.ack_count ?? 0, icon: Clock, color: 'text-status-acknowledged' },
    { label: 'Resolved', value: summary.resolved_count ?? 0, icon: CheckCircle2, color: 'text-status-resolved' },
    { label: 'Avg MTTA', value: formatDuration(summary.avg_mtta), icon: Timer, color: 'text-cyan-500' },
    { label: 'Avg MTTR', value: formatDuration(summary.avg_mttr), icon: TrendingUp, color: 'text-yellow-500' },
  ];

  const mttaData = trends?.trends?.map(d => ({ date: d.date, 'MTTA (min)': Math.round(d.mtta / 60 * 10) / 10 })) ?? [];
  const mttrData = trends?.trends?.map(d => ({ date: d.date, 'MTTR (min)': Math.round(d.mttr / 60 * 10) / 10 })) ?? [];
  const incidentVolume = trends?.trends?.map(d => ({ date: d.date, Incidents: d.incidents })) ?? [];

  const combinedData = mttaData.map((d, i) => ({
    date: d.date,
    'MTTA (min)': d['MTTA (min)'],
    'MTTR (min)': mttrData[i]?.['MTTR (min)'] ?? 0,
  }));

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardContent className="flex items-center justify-between p-4">
              <div>
                <p className="text-xs text-muted-foreground">{s.label}</p>
                <p className={`text-xl font-bold font-mono ${s.color}`}>{s.value}</p>
              </div>
              <s.icon className={`h-4 w-4 ${s.color}`} />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4" />
              MTTA / MTTR Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={combinedData} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} axisLine={false} unit=" min" />
                <Tooltip content={<ChartTooltip valueFormatter={(v) => `${v} min`} />} />
                <Line type="monotone" dataKey="MTTA (min)" stroke="#06b6d4" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="MTTR (min)" stroke="#eab308" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <BarChart3 className="h-4 w-4" />
              Daily Incident Volume
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={incidentVolume} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="Incidents" fill="hsl(240, 5.9%, 10%)" radius={[3, 3, 0, 0]} barSize={20} className="fill-foreground" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Service breakdown */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Service Breakdown</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Service</TableHead>
                <TableHead>Incidents</TableHead>
                <TableHead>Avg MTTA</TableHead>
                <TableHead>Avg MTTR</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {byService.map((item) => (
                <TableRow key={item.service}>
                  <TableCell className="font-semibold">{item.service}</TableCell>
                  <TableCell><code className="text-xs">{item.count}</code></TableCell>
                  <TableCell><code className="text-xs">{formatDuration(item.avg_mtta)}</code></TableCell>
                  <TableCell><code className="text-xs">{formatDuration(item.avg_mttr)}</code></TableCell>
                </TableRow>
              ))}
              {byService.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                    No data available
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
