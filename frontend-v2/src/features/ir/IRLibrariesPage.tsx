import { useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '../../lib/axios';
import type {
  IRLibraryListResponse,
  IRLibrarySummary,
  IRLibraryFiltersResponse,
  IRCommandListResponse,
} from '../../types/api';

const PAGE_SIZE_OPTIONS = [25, 50, 100, 500] as const;
const COMMAND_PAGE_SIZE = 50;

interface LibraryFilters {
  searchInput: string;
  brand: string;
  category: string;
  protocol: string;
  espNative: 'all' | 'native' | 'imported';
}

interface CommandFilters {
  searchInput: string;
  protocol: string;
}

const useDebouncedValue = <T,>(value: T, delay: number): T => {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(handle);
  }, [value, delay]);
  return debounced;
};

export const IRLibrariesPage = () => {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<LibraryFilters>({
    searchInput: '',
    brand: 'all',
    category: 'all',
    protocol: 'all',
    espNative: 'all',
  });

  const [selectedLibrary, setSelectedLibrary] = useState<IRLibrarySummary | null>(null);
  const [commandPage, setCommandPage] = useState(1);
  const [commandFilters, setCommandFilters] = useState<CommandFilters>({ searchInput: '', protocol: 'all' });

  const debouncedLibrarySearch = useDebouncedValue(filters.searchInput, 300);
  const debouncedCommandSearch = useDebouncedValue(commandFilters.searchInput, 300);

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

  const [pageSize, setPageSize] = useState<number>(PAGE_SIZE_OPTIONS[0]);

  const { data: librariesData, isLoading: loadingLibraries } = useQuery({
    queryKey: ['ir-libraries', page, pageSize, filters.brand, filters.category, filters.protocol, filters.espNative, debouncedLibrarySearch],
    queryFn: async () => {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
        include_hidden: true,
      };
      if (debouncedLibrarySearch) params.search = debouncedLibrarySearch;
      if (filters.brand !== 'all') params.brand = filters.brand;
      if (filters.category !== 'all') params.device_category = filters.category;
      if (filters.protocol !== 'all') params.protocol = filters.protocol;
      if (filters.espNative !== 'all') params.esp_native = filters.espNative === 'native';
      const response = await apiClient.get<IRLibraryListResponse>('/api/v1/ir-libraries', { params });
      return response.data;
    },
  });

  const libraries = librariesData?.items ?? [];
  const totalLibraries = librariesData?.total ?? 0;
  const totalLibraryPages = Math.max(1, Math.ceil(totalLibraries / pageSize));

  const { data: commandsData, isLoading: loadingCommands } = useQuery({
    queryKey: ['ir-library-commands', selectedLibrary?.id, commandPage, commandFilters.protocol, debouncedCommandSearch],
    queryFn: async () => {
      if (!selectedLibrary) return undefined;
      const params: Record<string, unknown> = {
        page: commandPage,
        page_size: COMMAND_PAGE_SIZE,
      };
      if (commandFilters.protocol !== 'all') params.protocol = commandFilters.protocol;
      if (debouncedCommandSearch) params.search = debouncedCommandSearch;
      const response = await apiClient.get<IRCommandListResponse>(
        `/api/v1/ir-libraries/${selectedLibrary.id}/commands`,
        { params },
      );
      return response.data;
    },
    enabled: Boolean(selectedLibrary),
  });

  const commands = commandsData?.items ?? [];
  const totalCommands = commandsData?.total ?? 0;
  const totalCommandPages = Math.max(1, Math.ceil(totalCommands / COMMAND_PAGE_SIZE));
  const [selectedLibraryIds, setSelectedLibraryIds] = useState<Set<number>>(new Set());

  const toggleVisibility = useMutation({
    mutationFn: async ({ library, hidden }: { library: IRLibrarySummary; hidden: boolean }) => {
      await apiClient.patch(`/api/v1/ir-libraries/${library.id}/visibility`, { hidden });
      return { library, hidden };
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['ir-libraries'] });
      queryClient.invalidateQueries({ queryKey: ['ir-library-commands'] });
      queryClient.invalidateQueries({ queryKey: ['ir-library-filters'] });
      if (selectedLibrary && variables.library.id === selectedLibrary.id) {
        setSelectedLibrary({ ...selectedLibrary, hidden: variables.hidden });
      }
    },
  });

  const bulkVisibility = useMutation({
    mutationFn: async ({ ids, hidden }: { ids: number[]; hidden: boolean }) => {
      await Promise.all(
        ids.map((id) => apiClient.patch(`/api/v1/ir-libraries/${id}/visibility`, { hidden })),
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ir-libraries'] });
      queryClient.invalidateQueries({ queryKey: ['ir-library-commands'] });
      queryClient.invalidateQueries({ queryKey: ['ir-library-filters'] });
      setSelectedLibraryIds(new Set());
    },
  });

  const toggleSelection = (libraryId: number) => {
    setSelectedLibraryIds((prev) => {
      const next = new Set(prev);
      if (next.has(libraryId)) {
        next.delete(libraryId);
      } else {
        next.add(libraryId);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    setSelectedLibraryIds((prev) => {
      if (prev.size === libraries.length) {
        return new Set();
      }
      return new Set(libraries.map((library) => library.id));
    });
  };

  const allSelectedHidden = libraries
    .filter((library) => selectedLibraryIds.has(library.id))
    .every((library) => library.hidden);

  const handleBulkVisibility = (hidden: boolean) => {
    if (selectedLibraryIds.size === 0) return;
    bulkVisibility.mutate({ ids: Array.from(selectedLibraryIds), hidden });
    if (selectedLibrary && selectedLibraryIds.has(selectedLibrary.id)) {
      setSelectedLibrary({ ...selectedLibrary, hidden });
    }
  };

  useEffect(() => {
    setPage(1);
  }, [filters.brand, filters.category, filters.protocol, filters.espNative, debouncedLibrarySearch, pageSize]);

  useEffect(() => {
    setCommandPage(1);
  }, [selectedLibrary, commandFilters.protocol, debouncedCommandSearch]);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-4">
          <h2 className="text-lg font-semibold text-slate-900">IR Library Catalogue</h2>
          <p className="text-sm text-slate-500">
            Search, filter, and inspect every IR library imported into the system.
          </p>
        </div>

        <div className="grid gap-4 border-b border-slate-100 p-4 md:grid-cols-5">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-slate-500">Search</label>
            <input
              type="search"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
              placeholder="Search brand, model, or category"
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
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, espNative: event.target.value as LibraryFilters['espNative'] }))
              }
            >
              <option value="all">All libraries</option>
              <option value="native">ESPHome native</option>
              <option value="imported">Imported</option>
            </select>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-2 border-b border-slate-200 px-4 py-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-col gap-1">
              <span className="font-medium text-slate-900">Libraries</span>
              <span>
                Page {page} of {totalLibraryPages} • {totalLibraries.toLocaleString()} total
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={pageSize}
                onChange={(event) => setPageSize(Number(event.target.value) || PAGE_SIZE_OPTIONS[0])}
                className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
              >
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    {size} per page
                  </option>
                ))}
              </select>
              <span className="text-xs text-slate-500">
                {selectedLibraryIds.size} selected
              </span>
              <button
                type="button"
                onClick={() => handleBulkVisibility(true)}
                disabled={selectedLibraryIds.size === 0 || bulkVisibility.isPending || allSelectedHidden}
                className={clsx(
                  'rounded-md border px-3 py-1 text-xs font-semibold transition',
                  selectedLibraryIds.size === 0 || bulkVisibility.isPending || allSelectedHidden
                    ? 'border-slate-200 bg-slate-100 text-slate-400 cursor-not-allowed'
                    : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400',
                )}
              >
                Hide selected
              </button>
              <button
                type="button"
                onClick={() => handleBulkVisibility(false)}
                disabled={selectedLibraryIds.size === 0 || bulkVisibility.isPending || !allSelectedHidden}
                className={clsx(
                  'rounded-md border px-3 py-1 text-xs font-semibold transition',
                  selectedLibraryIds.size === 0 || bulkVisibility.isPending || !allSelectedHidden
                    ? 'border-slate-200 bg-slate-100 text-slate-400 cursor-not-allowed'
                    : 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:border-emerald-300',
                )}
              >
                Show selected
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2 text-left font-semibold text-slate-600">
                    <input
                      type="checkbox"
                      className="h-3.5 w-3.5 rounded border-slate-300 text-brand-500 focus:ring-brand-500"
                      checked={selectedLibraryIds.size === libraries.length && libraries.length > 0}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th className="px-4 py-2 text-left font-semibold text-slate-600">Brand</th>
                  <th className="px-4 py-2 text-left font-semibold text-slate-600">Model</th>
                  <th className="px-4 py-2 text-left font-semibold text-slate-600">Category</th>
                  <th className="px-4 py-2 text-left font-semibold text-slate-600">Commands</th>
                  <th className="px-4 py-2 text-left font-semibold text-slate-600">Protocols</th>
                  <th className="px-4 py-2 text-left font-semibold text-slate-600">Hidden</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {loadingLibraries ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                      Loading libraries…
                    </td>
                  </tr>
                ) : libraries.length > 0 ? (
                  libraries.map((library) => {
                    const isSelected = selectedLibrary?.id === library.id;
                    return (
                      <tr
                        key={library.id}
                        onClick={() => {
                          setSelectedLibrary(library);
                          setCommandPage(1);
                          setCommandFilters({ searchInput: '', protocol: 'all' });
                        }}
                        className={`cursor-pointer ${isSelected ? 'bg-brand-50' : 'hover:bg-slate-50'}`}
                      >
                        <td className="px-4 py-2" onClick={(event) => event.stopPropagation()}>
                          <input
                            type="checkbox"
                            className="h-3.5 w-3.5 rounded border-slate-300 text-brand-500 focus:ring-brand-500"
                            checked={selectedLibraryIds.has(library.id)}
                            onChange={() => toggleSelection(library.id)}
                          />
                        </td>
                        <td className="px-4 py-2">
                          <div className="font-medium text-slate-900">{library.brand}</div>
                          <div className="text-xs text-slate-500">{library.name}</div>
                        </td>
                        <td className="px-4 py-2 text-slate-700">{library.model || '—'}</td>
                        <td className="px-4 py-2 text-slate-700">{library.device_category}</td>
                        <td className="px-4 py-2 text-slate-700">{library.command_count}</td>
                        <td className="px-4 py-2 text-slate-700">
                          {library.protocols.length ? library.protocols.join(', ') : '—'}
                        </td>
                        <td className="px-4 py-2" onClick={(event) => event.stopPropagation()}>
                          <label className="inline-flex items-center gap-2 text-xs text-slate-600">
                            <input
                              type="checkbox"
                              checked={library.hidden}
                              onChange={(event) =>
                                toggleVisibility.mutate({ library, hidden: event.target.checked })
                              }
                              disabled={toggleVisibility.isPending}
                            />
                            <span>{library.hidden ? 'Hidden' : 'Visible'}</span>
                          </label>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                      No libraries matched the current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-xs text-slate-600">
            <span>
              Showing {libraries.length ? (page - 1) * pageSize + 1 : 0}–
              {libraries.length ? Math.min(page * pageSize, totalLibraries) : 0} of {totalLibraries.toLocaleString()}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                disabled={page <= 1}
                className="rounded border border-slate-300 px-2 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
              >
                ‹
              </button>
              <button
                onClick={() => setPage((prev) => Math.min(totalLibraryPages, prev + 1))}
                disabled={page >= totalLibraryPages}
                className="rounded border border-slate-300 px-2 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
              >
                ›
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-4 py-3">
            <h3 className="text-sm font-medium text-slate-900">Commands</h3>
            {selectedLibrary ? (
              <p className="mt-1 text-xs text-slate-500">
                Viewing {totalCommands.toLocaleString()} commands for{' '}
                <span className="font-semibold text-slate-700">{selectedLibrary.name}</span>
              </p>
            ) : (
              <p className="mt-1 text-xs text-slate-500">Select a library to inspect its commands.</p>
            )}
          </div>

          {selectedLibrary && (
            <div className="grid gap-3 border-b border-slate-100 p-4 md:grid-cols-3">
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-500">Command search</label>
                <input
                  type="search"
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
                  placeholder="Search command name"
                  value={commandFilters.searchInput}
                  onChange={(event) => setCommandFilters((prev) => ({ ...prev, searchInput: event.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500">Protocol</label>
                <select
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
                  value={commandFilters.protocol}
                  onChange={(event) => setCommandFilters((prev) => ({ ...prev, protocol: event.target.value }))}
                >
                  <option value="all">All protocols</option>
                  {selectedLibrary.protocols.map((proto) => (
                    <option key={proto} value={proto}>
                      {proto}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2 text-left font-semibold text-slate-600">Command</th>
                  <th className="px-4 py-2 text-left font-semibold text-slate-600">Protocol</th>
                  <th className="px-4 py-2 text-left font-semibold text-slate-600">Category</th>
                  <th className="px-4 py-2 text-left font-semibold text-slate-600">Signal data</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {!selectedLibrary ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                      Select a library to inspect its commands.
                    </td>
                  </tr>
                ) : loadingCommands ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                      Loading commands…
                    </td>
                  </tr>
                ) : commands.length > 0 ? (
                  commands.map((command) => (
                    <tr key={command.id}>
                      <td className="px-4 py-2 text-slate-900">
                        <div className="font-semibold">{command.name}</div>
                        <div className="text-xs text-slate-500">{command.category || '—'}</div>
                      </td>
                      <td className="px-4 py-2 text-slate-700">{command.protocol || '—'}</td>
                      <td className="px-4 py-2 text-slate-700">{command.category || '—'}</td>
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

          {selectedLibrary && (
            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-xs text-slate-600">
              <span>
                Showing {commands.length ? (commandPage - 1) * COMMAND_PAGE_SIZE + 1 : 0}–
                {commands.length ? Math.min(commandPage * COMMAND_PAGE_SIZE, totalCommands) : 0} of {totalCommands.toLocaleString()}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCommandPage((prev) => Math.max(1, prev - 1))}
                  disabled={commandPage <= 1}
                  className="rounded border border-slate-300 px-2 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                >
                  ‹
                </button>
                <button
                  onClick={() => setCommandPage((prev) => Math.min(totalCommandPages, prev + 1))}
                  disabled={commandPage >= totalCommandPages}
                  className="rounded border border-slate-300 px-2 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                >
                  ›
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
