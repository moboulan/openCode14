import { useEffect, useState } from 'react';
import { getCurrentOncall, listSchedules } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Users, Calendar, Shield, User } from 'lucide-react';

function initials(email) {
  if (!email) return '?';
  const name = email.split('@')[0];
  const parts = name.split(/[._-]/);
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

function UserChip({ email, role }) {
  const isPrimary = role === 'Primary';
  return (
    <div className="flex items-center gap-3 rounded-md border border-border p-2.5">
      <div className={`flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold ${
        isPrimary ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
      }`}>
        {initials(email)}
      </div>
      <div className="flex flex-col">
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">{role}</span>
        <span className="text-sm font-medium">{email}</span>
      </div>
    </div>
  );
}

export default function OnCall() {
  const [schedules, setSchedules] = useState([]);
  const [oncall, setOncall] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [schedResp, oncallResp] = await Promise.all([listSchedules(), getCurrentOncall()]);
        setSchedules(schedResp.schedules ?? []);
        setOncall(oncallResp);
      } catch {
        setError('Failed to load on-call data');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const oncallList = oncall ? (Array.isArray(oncall.oncall) ? oncall.oncall : [oncall]) : [];

  if (loading) return <p className="text-sm text-muted-foreground animate-pulse">Loading on-call data…</p>;

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Current On-Call */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <Shield className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold">Current On-Call</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {oncallList.map((item, idx) => (
            <Card key={`${item.team}-${idx}`}>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Users className="h-4 w-4" />
                  {item.team}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <UserChip email={item.primary} role="Primary" />
                {item.secondary && <UserChip email={item.secondary} role="Secondary" />}
              </CardContent>
            </Card>
          ))}
          {oncallList.length === 0 && (
            <Card>
              <CardContent className="py-8 text-center text-sm text-muted-foreground">
                No on-call teams configured.
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Schedules */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold">Schedules</h2>
        </div>
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Team</TableHead>
                  <TableHead>Rotation</TableHead>
                  <TableHead>Start</TableHead>
                  <TableHead>Engineers</TableHead>
                  <TableHead>Escalation</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {schedules.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-semibold">{item.team}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">{item.rotation_type}</Badge>
                    </TableCell>
                    <TableCell><code className="text-xs">{item.start_date}</code></TableCell>
                    <TableCell className="text-muted-foreground text-xs max-w-[200px] truncate">
                      {item.engineers.join(', ')}
                    </TableCell>
                    <TableCell><code className="text-xs">{item.escalation_minutes}m</code></TableCell>
                  </TableRow>
                ))}
                {schedules.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                      No schedules found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
