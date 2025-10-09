import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/axios';
import type {
  IRCommandCatalogueResponse,
  IRCommandWithLibrarySummary,
  IRLibraryFiltersResponse,
} from '../../types/api';

const PAGE_SIZE = 50;

interface FilterState {
  searchInput: string;
  brand: string;
  category: string;
  protocol: string;
  espNative: 'all' | 'native' | 'imported';
}

const useDebouncedValue = <T,>(value: T, delay: number): T => {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(handle);
  }, [value, delay]);

  return debounced;
};

export const IRCommandsPage = () => {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<FilterState>({
    searchInput: '',
    brand: 'all',
    category: 'all',
    protocol: 'all',
    espNative: 'all',
  });

  const debouncedSearch = useDebouncedValue(filters.searchInput, 300);

  const { data: filterOptions } = useQuery({
    queryKey: ['ir-library-filters'],
    queryFn: async () => {
      const response = await apiClient.get<IRLibraryFiltersResponse>('/api/v1/ir-libraries/filters');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  const brandOptions = useMemo(
    () => Array.from(new Set(filterOptions?.brands ?? [])),
    [filterOptions],
  );
  const categoryOptions = useMemo(
    () => Array.from(new Set(filterOptions?.device_categories ?? [])),
    [filterOptions],
  );
  const protocolOptions = useMemo(
    () => Array.from(new Set(filterOptions?.protocols ?? [])),
    [filterOptions],
  );

  const { data: commandData, isLoading } = useQuery({
    queryKey: ['ir-commands', page, filters.brand, filters.category, filters.protocol, filters.espNative, debouncedSearch],
    queryFn: async () => {
      const params: Record<string, unknown> = {
        page,
        page_size: PAGE_SIZE,
      };
      if (debouncedSearch) params.search = debouncedSearch;
      if (filters.brand !== 'all') params.brand = filters.brand;
      if (filters.category !== 'all') params.device_category = filters.category;
      if (filters.protocol !== 'all') params.protocol = filters.protocol;
      if (filters.espNative !== 'all') params.esp_native = filters.espNative === 'native';
      const response = await apiClient.get<IRCommandCatalogueResponse>('/api/v1/ir-libraries/commands', { params });
      return response.data;
    },
  });

  useEffect(() => {
    setPage(1);
  }, [filters.brand, filters.category, filters.protocol, filters.espNative, debouncedSearch]);

  const totalPages = useMemo(() => {
    if (!commandData) return 1;
    return Math.max(1, Math.ceil(commandData.total / PAGE_SIZE));
  }, [commandData]);

  const commands: IRCommandWithLibrarySummary[] = commandData?.items ?? [];
  const totalCommands = commandData?.total ?? 0;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-4">
          <h2 className="text-lg font-semibold text-slate-900">IR Command Explorer</h2>
          <p className="text-sm text-slate-500">
            Browse every imported IR command across brands, categories, and protocols.
          </p>
        </div>

        <div className="grid gap-4 border-b border-slate-100 p-4 md:grid-cols-5">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-slate-500">Command search</label>
            <input
              type="search"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
              placeholder="Search command name"
              value={filters.searchInput}
              onChange={(event) => setFilters((prev) => ({ ...prev, searchInput: event.target.value }))}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500">Brand</label>
            <select
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
              value={filters.brand}
              onChange={(event) => setFilters((prev) => ({ ...prev, brand: event.target.value }))}
            >
              <option value="all">All brands</option>
              {brandOptions.map((brand) => (
                <option key={brand} value={brand}>
                  {brand}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500">Category</label>
            <select
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
              value={filters.category}
              onChange={(event) => setFilters((prev) => ({ ...prev, category: event.target.value }))}
            >
              <option value="all">All categories</option>
              {categoryOptions.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500">Protocol</label>
            <select
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
              value={filters.protocol}
              onChange={(event) => setFilters((prev) => ({ ...prev, protocol: event.target.value }))}
            >
              <option value="all">All protocols</option>
              {protocolOptions.map((proto) => (
                <option key={proto} value={proto}>
                  {proto}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500">Library type</label>
            <select
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
              value={filters.espNative}
              onChange={(event) => setFilters((prev) => ({ ...prev, espNative: event.target.value as FilterState['espNative'] }))}
            >
              <option value="all">All libraries</option>
              <option value="native">ESPHome native</option>
              <option value="imported">Imported</option>
            </select>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 text-sm text-slate-600">
          <span className="font-medium text-slate-900">Commands</span>
          <span>
            Page {page} of {totalPages} • {totalCommands.toLocaleString()} total
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Command</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Protocol</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Library</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Signal data</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {isLoading ? (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                    Loading commands…
                  </td>
                </tr>
              ) : commands.length > 0 ? (
                commands.map((command) => (
                  <tr key={`${command.id}-${command.library.id}`}>
                    <td className="px-4 py-2 text-slate-900">
                      <div className="font-semibold">{command.name}</div>
                      <div className="text-xs text-slate-500">{command.category || '—'}</div>
                    </td>
                    <td className="px-4 py-2 text-slate-700">{command.protocol || '—'}</td>
                    <td className="px-4 py-2 text-slate-700">
                      <div className="font-medium text-slate-900">{command.library.brand}</div>
                      <div className="text-xs text-slate-500">{command.library.name}</div>
                      <div className="text-xs text-slate-500">
                        {command.library.device_category} • {command.library.esp_native ? 'ESPHome native' : 'Imported'}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-xs text-slate-600">
                      <pre className="whitespace-pre-wrap break-words">
                        {JSON.stringify(command.signal_data, null, 2)}
                      </pre>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                    No commands matched the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-xs text-slate-600">
          <span>
            Showing {commands.length ? (page - 1) * PAGE_SIZE + 1 : 0}–
            {commands.length ? Math.min(page * PAGE_SIZE, totalCommands) : 0} of {totalCommands}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={page <= 1}
              className="flex items-center justify-center rounded border border-slate-300 px-2 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
            >
              ‹
            </button>
            <button
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={page >= totalPages}
              className="flex items-center justify-center rounded border border-slate-300 px-2 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
            >
              ›
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
