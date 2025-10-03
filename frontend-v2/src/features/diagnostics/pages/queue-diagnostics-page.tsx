import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/axios';
import { formatRelativeTime } from '@/utils/datetime';

interface QueueCommand {
  id: string;
  source: string;
  hostname: string;
  device_name: string;
  location: string | null;
  command: string;
  port: number;
  channel: string | null;
  digit: number | null;
  command_class: string | null;
  batch_id: string | null;
  status: string;
  priority: number | null;
  scheduled_at: string | null;
  attempts: number | null;
  max_attempts: number | null;
  last_attempt_at: string | null;
  completed_at: string | null;
  success: boolean | null;
  error_message: string | null;
  execution_time_ms: number | null;
  routing_method: string | null;
  created_at: string;
  created_by: string | null;
  user_ip: string | null;
  notes: string | null;
}

interface QueueDataResponse {
  total: number;
  commands: QueueCommand[];
}

type SortColumn = 'created_at' | 'hostname' | 'status' | 'command' | 'priority';
type SortDirection = 'asc' | 'desc';

export const QueueDiagnosticsPage = () => {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [hostnameFilter, setHostnameFilter] = useState<string>('');
  const [commandFilter, setCommandFilter] = useState<string>('');
  const [commandClassFilter, setCommandClassFilter] = useState<string>('');
  const [locationFilter, setLocationFilter] = useState<string>('');
  const [sortColumn, setSortColumn] = useState<SortColumn>('created_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['queue-diagnostics'],
    queryFn: async (): Promise<QueueDataResponse> => {
      const response = await apiClient.get<QueueDataResponse>('/api/v1/commands/queue/all', {
        params: { limit: 1000 }
      });
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Get unique values for filters
  const uniqueHostnames = useMemo(() => {
    if (!data?.commands) return [];
    return Array.from(new Set(data.commands.map(c => c.hostname))).sort();
  }, [data]);

  const uniqueLocations = useMemo(() => {
    if (!data?.commands) return [];
    return Array.from(new Set(data.commands.map(c => c.location).filter(Boolean))).sort();
  }, [data]);

  const uniqueCommands = useMemo(() => {
    if (!data?.commands) return [];
    return Array.from(new Set(data.commands.map(c => c.command))).sort();
  }, [data]);

  // Filter and sort data
  const filteredAndSortedCommands = useMemo(() => {
    if (!data?.commands) return [];

    let filtered = data.commands;

    if (statusFilter) {
      filtered = filtered.filter(c => c.status === statusFilter);
    }
    if (hostnameFilter) {
      filtered = filtered.filter(c => c.hostname === hostnameFilter);
    }
    if (commandFilter) {
      filtered = filtered.filter(c => c.command === commandFilter);
    }
    if (commandClassFilter) {
      filtered = filtered.filter(c => c.command_class === commandClassFilter);
    }
    if (locationFilter) {
      filtered = filtered.filter(c => c.location === locationFilter);
    }

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      let aVal: any = a[sortColumn];
      let bVal: any = b[sortColumn];

      if (sortColumn === 'created_at') {
        aVal = new Date(aVal).getTime();
        bVal = new Date(bVal).getTime();
      }

      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    return sorted;
  }, [data, statusFilter, hostnameFilter, commandFilter, commandClassFilter, locationFilter, sortColumn, sortDirection]);

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-blue-100 text-blue-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-slate-100 text-slate-800';
    }
  };

  const getSortIcon = (column: SortColumn) => {
    if (sortColumn !== column) return '↕';
    return sortDirection === 'asc' ? '↑' : '↓';
  };

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Queue Diagnostics</h2>
          <p className="text-sm text-slate-500">
            View all command queue data with filtering and sorting capabilities
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1 rounded-md bg-brand-500 px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
        >
          {isFetching ? 'Refreshing…' : 'Refresh'}
        </button>
      </header>

      {/* Filters */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Hostname</label>
            <select
              value={hostnameFilter}
              onChange={(e) => setHostnameFilter(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              {uniqueHostnames.map((hostname) => (
                <option key={hostname} value={hostname}>
                  {hostname}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Location</label>
            <select
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              {uniqueLocations.map((location) => (
                <option key={location} value={location}>
                  {location}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Command</label>
            <select
              value={commandFilter}
              onChange={(e) => setCommandFilter(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              {uniqueCommands.map((command) => (
                <option key={command} value={command}>
                  {command}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Class</label>
            <select
              value={commandClassFilter}
              onChange={(e) => setCommandClassFilter(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              <option value="immediate">Immediate</option>
              <option value="interactive">Interactive</option>
              <option value="bulk">Bulk</option>
              <option value="system">System</option>
            </select>
          </div>
        </div>

        {(statusFilter || hostnameFilter || commandFilter || commandClassFilter || locationFilter) && (
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setStatusFilter('');
                setHostnameFilter('');
                setCommandFilter('');
                setCommandClassFilter('');
                setLocationFilter('');
              }}
              className="text-xs text-brand-600 hover:text-brand-700"
            >
              Clear all filters
            </button>
            <span className="text-xs text-slate-500">
              Showing {filteredAndSortedCommands.length} of {data?.total ?? 0} commands
            </span>
          </div>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500">
          Loading queue data…
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Failed to load queue data. {error instanceof Error ? error.message : 'Please try again.'}
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200" style={{ minWidth: '1400px' }}>
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    ID
                  </th>
                  <th
                    className="cursor-pointer px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-100"
                    onClick={() => handleSort('created_at')}
                  >
                    Created {getSortIcon('created_at')}
                  </th>
                  <th
                    className="cursor-pointer px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-100"
                    onClick={() => handleSort('hostname')}
                  >
                    Device {getSortIcon('hostname')}
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Location
                  </th>
                  <th
                    className="cursor-pointer px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-100"
                    onClick={() => handleSort('command')}
                  >
                    Command {getSortIcon('command')}
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Port
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Channel
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Class
                  </th>
                  <th
                    className="cursor-pointer px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-100"
                    onClick={() => handleSort('status')}
                  >
                    Status {getSortIcon('status')}
                  </th>
                  <th
                    className="cursor-pointer px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-100"
                    onClick={() => handleSort('priority')}
                  >
                    Priority {getSortIcon('priority')}
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Attempts
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Success
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Time (ms)
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Routing
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Error
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredAndSortedCommands.length === 0 ? (
                  <tr>
                    <td colSpan={15} className="px-3 py-8 text-center text-sm text-slate-500">
                      No commands found
                    </td>
                  </tr>
                ) : (
                  filteredAndSortedCommands.map((command) => (
                    <tr key={command.id} className="hover:bg-slate-50/70">
                      <td className="px-3 py-2 text-xs text-slate-600">{command.id}</td>
                      <td className="px-3 py-2 text-xs text-slate-600">
                        {formatRelativeTime(command.created_at)}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        <div className="font-medium text-slate-900">{command.device_name}</div>
                        <div className="text-slate-500">{command.hostname}</div>
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-600">{command.location || '—'}</td>
                      <td className="px-3 py-2 text-xs font-medium text-slate-900">{command.command}</td>
                      <td className="px-3 py-2 text-xs text-slate-600">{command.port}</td>
                      <td className="px-3 py-2 text-xs text-slate-600">{command.channel || '—'}</td>
                      <td className="px-3 py-2 text-xs text-slate-600">{command.command_class || '—'}</td>
                      <td className="px-3 py-2">
                        <span
                          className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusBadgeClass(
                            command.status
                          )}`}
                        >
                          {command.status}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-600">{command.priority ?? '—'}</td>
                      <td className="px-3 py-2 text-xs text-slate-600">
                        {command.attempts !== null && command.max_attempts !== null
                          ? `${command.attempts} / ${command.max_attempts}`
                          : '—'}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {command.success === null ? (
                          <span className="text-slate-400">—</span>
                        ) : command.success ? (
                          <span className="text-green-600">✓</span>
                        ) : (
                          <span className="text-red-600">✗</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-600">
                        {command.execution_time_ms ?? '—'}
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-600">{command.routing_method || '—'}</td>
                      <td className="px-3 py-2 text-xs text-slate-600">
                        {command.error_message ? (
                          <span className="max-w-xs truncate text-red-600" title={command.error_message}>
                            {command.error_message}
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
};
