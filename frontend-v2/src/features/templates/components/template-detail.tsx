import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { duotoneSpace } from 'react-syntax-highlighter/dist/esm/styles/prism';

import { useTemplateDetail } from '../hooks/use-template-detail';
import { useApplicationSettings } from '@/features/settings/hooks/use-application-settings';
import { useTemplateHierarchy } from '../hooks/use-template-hierarchy';
import { useTemplatePreview } from '../hooks/use-template-preview';
import { useCompileTemplate } from '../hooks/use-compile-template';
import { useOtaFlash } from '../hooks/use-ota-flash';
import { getFirmwareDownloadUrl } from '../api/templates-api';
import type {
  TemplatePreviewAssignment,
  TemplateCategory,
  TemplateLibraryItem,
} from '@/types';
import { useManagedDevices } from '@/features/devices/hooks/use-managed-devices';
import type { ManagedDevice } from '@/types';
import { SubstitutionSettingsModal } from './substitution-settings-modal';

interface TemplateDetailProps {
  templateId: number;
}

export const TemplateDetail = ({ templateId }: TemplateDetailProps) => {
  const { data, isLoading, isError, error } = useTemplateDetail(templateId);
  const { data: hierarchy, isLoading: hierarchyLoading, isError: hierarchyError } = useTemplateHierarchy();
  const {
    data: appSettings,
    isLoading: settingsLoading,
    isError: settingsError,
    error: settingsErrorDetail,
  } = useApplicationSettings(true);
  const [copied, setCopied] = useState(false);
  const [includeComments, setIncludeComments] = useState(true);
  const [assignments, setAssignments] = useState<TemplatePreviewAssignment[]>(() =>
    Array.from({ length: 5 }, (_, index) => ({ port_number: index + 1, library_id: null })),
  );
  const {
    startCompilation,
    cancelCompilation,
    resetCompilation,
    status: compileStatus,
    logLines: compileLogLines,
    result: compileResult,
    error: compileError,
  } = useCompileTemplate();
  const {
    status: otaStatus,
    logLines: otaLogLines,
    progressByHost,
    results: otaResults,
    error: otaError,
    startOTA,
    cancelOTA,
    reset: resetOTA,
  } = useOtaFlash();
  const { data: managedDevices, isLoading: loadingDevices } = useManagedDevices();
  const devices = managedDevices ?? [];
  const queryClient = useQueryClient();
  const [binaryPath, setBinaryPath] = useState('');
  const [selectedHostnames, setSelectedHostnames] = useState<string[]>([]);
  const [otaPort, setOtaPort] = useState('');
  const [rebootDelay, setRebootDelay] = useState(20);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);

  useEffect(() => {
    setIncludeComments(true);
    setAssignments(Array.from({ length: 5 }, (_, index) => ({ port_number: index + 1, library_id: null })));
    resetCompilation();
    resetOTA();
    setBinaryPath('');
    setSelectedHostnames([]);
    setOtaPort('');
    setRebootDelay(20);
  }, [templateId, resetCompilation, resetOTA]);

  const previewAssignments = useMemo(
    () => assignments.map((assignment) => ({ ...assignment })),
    [assignments],
  );

  const {
    data: preview,
    isLoading: previewLoading,
    isError: previewError,
    error: previewErrorDetail,
  } = useTemplatePreview(templateId, previewAssignments, includeComments);

  const isCompiling = compileStatus === 'running';
  const compileLog = compileLogLines.join('\n');

  const substitutionValues = useMemo(() => {
    const getString = (key: string, fallback = '') => {
      const value = appSettings?.[key]?.value;
      if (value === undefined || value === null) {
        return fallback;
      }
      if (typeof value === 'boolean') {
        return value ? 'true' : 'false';
      }
      return String(value);
    };

    return {
      wifi_ssid: getString('wifi_ssid', 'TV'),
      wifi_password: getString('wifi_password', 'changeme'),
      wifi_hidden: getString('wifi_hidden', 'true'),
      api_key: getString('esphome_api_key', ''),
      ota_password: getString('ota_password', ''),
    };
  }, [appSettings]);

  const libraryOptions = useMemo(() => {
    if (!hierarchy) return [] as { value: number; label: string; category: string; brand: string; library: TemplateLibraryItem }[];

    const options: { value: number; label: string; category: string; brand: string; library: TemplateLibraryItem }[] = [];
    hierarchy.forEach((category: TemplateCategory) => {
      category.brands.forEach((brand) => {
        brand.libraries.forEach((library) => {
          options.push({
            value: library.id,
            label: `${category.name} • ${brand.name} • ${library.name}`,
            category: category.name,
            brand: brand.name,
            library,
          });
        });
      });
    });
    return options;
  }, [hierarchy]);

  const libraryMap = useMemo(() => {
    const map = new Map<number, TemplateLibraryItem>();
    libraryOptions.forEach((option) => {
      map.set(option.value, option.library);
    });
    return map;
  }, [libraryOptions]);

  const previewYamlSource = preview?.yaml ?? data?.template_yaml ?? '';

  const renderedYaml = useMemo(() => {
    if (!previewYamlSource) return '';
    const subs = substitutionValues;
    let output = previewYamlSource;
    output = output.replace(/wifi_ssid:\s*"[^"]*"/g, `wifi_ssid: "${subs.wifi_ssid}"`);
    output = output.replace(/wifi_password:\s*"[^"]*"/g, `wifi_password: "${subs.wifi_password}"`);
    output = output.replace(/wifi_hidden:\s*("?(true|false)"?)/g, `wifi_hidden: ${subs.wifi_hidden}`);
    output = output.replace(/api_key:\s*"[^"]*"/g, `api_key: "${subs.api_key}"`);
    output = output.replace(/ota_password:\s*"[^"]*"/g, `ota_password: "${subs.ota_password}"`);
    return output;
  }, [previewYamlSource, substitutionValues]);

  const substitutionCount = useMemo(() => {
    if (!renderedYaml) return 0;
    return (renderedYaml.match(/{{/g) ?? []).length;
  }, [renderedYaml]);

  const handleCopy = async () => {
    if (!renderedYaml) return;
    try {
      await navigator.clipboard.writeText(renderedYaml);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy template YAML', err);
    }
  };

  useEffect(() => {
    if (compileResult?.binary_path) {
      setBinaryPath(compileResult.binary_path);
    }
  }, [compileResult]);

  useEffect(() => {
    if (otaStatus === 'success') {
      queryClient.invalidateQueries({ queryKey: ['managed-devices'] });
    }
  }, [otaStatus, queryClient]);

  const toggleHostname = (hostname: string) => {
    setSelectedHostnames((prev) =>
      prev.includes(hostname) ? prev.filter((value) => value !== hostname) : [...prev, hostname],
    );
  };

  const formatCapabilities = (capabilities: ManagedDevice['capabilities']) => {
    if (!capabilities || typeof capabilities !== 'object') return 'Capabilities not reported';
    const record = capabilities as Record<string, unknown>;
    const brands = Array.isArray(record.brands) ? (record.brands as string[]) : [];
    const commands = Array.isArray(record.commands) ? (record.commands as string[]) : [];
    const parts: string[] = [];
    if (brands.length) {
      const visible = brands.slice(0, 3).join(', ');
      parts.push(`Brands: ${visible}${brands.length > 3 ? ', …' : ''}`);
    }
    if (commands.length) {
      parts.push(`${commands.length} commands`);
    }
    return parts.length ? parts.join(' • ') : 'Capabilities reported';
  };

  const handleStartOTA = () => {
    if (!binaryPath || selectedHostnames.length === 0) return;
    const parsedPort = parseInt(otaPort, 10);
    const portNumber = Number.isFinite(parsedPort) && parsedPort > 0 ? parsedPort : undefined;
    startOTA({
      binaryPath,
      hostnames: selectedHostnames,
      otaPort: portNumber,
      rebootWaitSeconds: rebootDelay,
    });
  };

  const isFlashing = otaStatus === 'running';

  if (isLoading || settingsLoading || hierarchyLoading) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
        Loading template…
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
        Failed to load template detail. {error instanceof Error ? error.message : 'Please retry later.'}
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-900">{data.name}</h3>
          <p className="text-xs text-slate-500">
            Board: {data.board} • Version {data.version} (rev {data.revision})
          </p>
        </div>
        <button
          type="button"
          onClick={handleCopy}
          className={clsx(
            'inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-xs font-medium transition',
            copied
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
              : 'border-slate-300 bg-white text-slate-700 hover:border-brand-200 hover:text-brand-600'
          )}
        >
          {copied ? 'Copied!' : 'Copy YAML'}
        </button>
      </header>

      {data.description && <p className="text-sm text-slate-600">{data.description}</p>}

      {settingsError && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
          Unable to load substitution settings. Using fallback values.{' '}
          {settingsErrorDetail instanceof Error ? settingsErrorDetail.message : null}
        </div>
      )}

      {hierarchyError && (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
          Failed to load library hierarchy. Port assignments may be limited.
        </div>
      )}

      <section className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-800">Port assignments</h4>
            <p className="text-xs text-slate-500">
              Select IR libraries or leave ports unassigned. Assignments feed directly into the YAML preview.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
              <input
                type="checkbox"
                className="h-3.5 w-3.5 rounded border-slate-300 text-brand-500 focus:ring-brand-500"
                checked={includeComments}
                onChange={(event) => setIncludeComments(event.target.checked)}
              />
              Include comments
            </label>
            <button
              type="button"
              onClick={() =>
                setAssignments(Array.from({ length: 5 }, (_, index) => ({ port_number: index + 1, library_id: null })))
              }
              className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600 transition hover:bg-white"
            >
              Clear all
            </button>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          {assignments.map((assignment) => {
            const selectedLibrary = assignment.library_id ? libraryMap.get(assignment.library_id) : null;
            return (
              <div key={assignment.port_number} className="rounded-md border border-slate-200 bg-white p-3 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-slate-800">Port {assignment.port_number}</div>
                    <div className="text-xs text-slate-500">
                      {selectedLibrary ? `${selectedLibrary.brand} • ${selectedLibrary.name}` : 'Unassigned'}
                    </div>
                  </div>
                  {assignment.library_id !== null && (
                    <button
                      type="button"
                      onClick={() =>
                        setAssignments((prev) =>
                          prev.map((entry) =>
                            entry.port_number === assignment.port_number
                              ? { ...entry, library_id: null }
                              : entry,
                          ),
                        )
                      }
                      className="text-xs font-medium text-brand-600 hover:underline"
                    >
                      Remove
                    </button>
                  )}
                </div>
                <select
                  value={assignment.library_id ?? ''}
                  onChange={(event) => {
                    const value = event.target.value;
                    setAssignments((prev) =>
                      prev.map((entry) =>
                        entry.port_number === assignment.port_number
                          ? { ...entry, library_id: value ? Number(value) : null }
                          : entry,
                      ),
                    );
                  }}
                  className="mt-3 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
                >
                  <option value="">Unassigned</option>
                  {libraryOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {selectedLibrary?.esp_native && (
                  <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
                    ESPHome native
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
        <span className="rounded-full bg-slate-100 px-3 py-1">
          Characters: {(preview?.char_count ?? renderedYaml.length).toLocaleString()}
        </span>
        <span className="rounded-full bg-slate-100 px-3 py-1">Placeholders: {substitutionCount}</span>
        {previewLoading && <span className="text-brand-600">Refreshing preview…</span>}
      </div>

      <section className="rounded-md border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-slate-800">Applied substitutions</h4>
          <button
            type="button"
            onClick={() => setIsSettingsModalOpen(true)}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-brand-200 hover:text-brand-600"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Edit
          </button>
        </div>
        <dl className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          {Object.entries(substitutionValues).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between gap-2 rounded bg-white px-3 py-2 shadow-sm">
              <dt className="font-medium text-slate-700">{key}</dt>
              <dd className="font-mono text-slate-600">{value || '—'}</dd>
            </div>
          ))}
        </dl>
      </section>

      {previewError && (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
          Failed to generate preview. {previewErrorDetail instanceof Error ? previewErrorDetail.message : null}
        </div>
      )}

      {preview?.selected_devices?.length ? (
        <section className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <h4 className="text-sm font-semibold text-slate-800">Selected devices</h4>
          <ul className="mt-3 space-y-1 text-xs text-slate-600">
            {preview.selected_devices.map((device) => (
              <li key={device.library_id} className="rounded bg-white px-3 py-2 shadow-sm">
                <span className="font-medium text-slate-700">{device.display_name}</span>
                <span className="ml-2 text-slate-500">
                  ({device.device_category} • {device.brand}
                  {device.model ? ` • ${device.model}` : ''})
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-800">Firmware compilation</h4>
            <p className="text-xs text-slate-500">
              Generate a flashable ESPHome binary using the current assignments and substitutions.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              className={clsx(
                'inline-flex items-center gap-1 rounded-md border px-3 py-2 text-xs font-medium transition',
                copied
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                  : 'border-slate-300 bg-white text-slate-700 hover:border-brand-200 hover:text-brand-600'
              )}
            >
              {copied ? 'Copied!' : 'Copy YAML'}
            </button>
            <button
              type="button"
              onClick={() => startCompilation(renderedYaml)}
              disabled={isCompiling || !renderedYaml.trim()}
              className="inline-flex items-center gap-2 rounded-md bg-brand-500 px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
            >
              {isCompiling ? 'Compiling…' : 'Compile firmware'}
            </button>
            {isCompiling && (
              <button
                type="button"
                onClick={() => cancelCompilation()}
                className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-white"
              >
                Cancel
              </button>
            )}
          </div>
        </div>

        {compileError && (
          <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
            Failed to compile firmware. {compileError}
          </div>
        )}

        {(compileResult || compileLogLines.length > 0) && (
          <div className="space-y-2 rounded-md border border-slate-200 bg-white p-3 shadow-sm">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <span
                className={clsx(
                  'inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold',
                  compileStatus === 'success'
                    ? 'bg-emerald-50 text-emerald-700'
                    : compileStatus === 'running'
                      ? 'bg-brand-50 text-brand-700'
                      : compileStatus === 'error'
                        ? 'bg-rose-50 text-rose-700'
                        : 'bg-slate-100 text-slate-600',
                )}
              >
                {compileStatus === 'running'
                  ? 'Compilation in progress…'
                  : compileStatus === 'success'
                    ? 'Compilation succeeded'
                    : compileStatus === 'error'
                      ? 'Compilation failed'
                      : 'Compilation log'}
              </span>
              {compileResult?.success && compileResult.binary_filename && (
                <a
                  href={getFirmwareDownloadUrl(compileResult.binary_filename)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-md border border-brand-200 px-3 py-1 text-xs font-semibold text-brand-600 transition hover:bg-brand-50"
                >
                  Download firmware ({compileResult.binary_filename})
                </a>
              )}
            </div>
            <div className="max-h-64 overflow-auto rounded border border-slate-200 bg-slate-950/95">
              <pre className="whitespace-pre-wrap break-words p-3 text-[11px] text-slate-100">
                {compileLog || 'Awaiting compiler output…'}
              </pre>
            </div>
          </div>
        )}
      </section>

      <section className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-800">OTA deployment</h4>
            <p className="text-xs text-slate-500">
              Select controllers and push the compiled firmware directly over the air.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleStartOTA}
              disabled={isFlashing || !binaryPath || selectedHostnames.length === 0}
              className={clsx(
                'inline-flex items-center gap-2 rounded-md px-3 py-2 text-xs font-semibold shadow-sm transition',
                isFlashing || !binaryPath || selectedHostnames.length === 0
                  ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                  : 'bg-emerald-500 text-white hover:bg-emerald-600',
              )}
            >
              {isFlashing ? 'Uploading…' : 'Start OTA'}
            </button>
            {isFlashing ? (
              <button
                type="button"
                onClick={cancelOTA}
                className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-white"
              >
                Cancel
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  resetOTA();
                  setSelectedHostnames([]);
                }}
                className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-500 transition hover:bg-slate-100"
              >
                Reset
              </button>
            )}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="block text-xs font-medium text-slate-600">Firmware binary path</label>
            <input
              type="text"
              value={binaryPath}
              onChange={(event) => setBinaryPath(event.target.value)}
              placeholder="/tmp/tapcommand-esphome/builds/firmware_xxx.bin"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600">OTA port (optional)</label>
              <input
                type="number"
                min={1}
                value={otaPort}
                onChange={(event) => setOtaPort(event.target.value)}
                placeholder="3232"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600">Reboot wait (seconds)</label>
              <input
                type="number"
                min={5}
                value={rebootDelay}
                onChange={(event) => setRebootDelay(Number(event.target.value) || 20)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
              />
            </div>
          </div>
        </div>

        <div>
          <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-600">Controllers</h5>
          <div className="mt-3 space-y-2 rounded-md border border-slate-200 bg-white p-3">
            {loadingDevices ? (
              <p className="text-xs text-slate-500">Loading controllers…</p>
            ) : devices.length === 0 ? (
              <p className="text-xs text-slate-500">No managed controllers found.</p>
            ) : (
              devices.map((device) => {
                const selected = selectedHostnames.includes(device.hostname);
                const progress = progressByHost[device.hostname] ?? 0;
                const result = otaResults[device.hostname];
                const statusLabel = result
                  ? result.success
                    ? 'Updated'
                    : 'Failed'
                  : isFlashing && selected
                    ? `${progress}%`
                    : device.firmware_version || 'Unknown';
                return (
                  <label
                    key={device.id}
                    className={clsx(
                      'flex flex-col gap-1 rounded-md border px-3 py-2 text-xs transition',
                      selected ? 'border-brand-400 bg-brand-50' : 'border-slate-200 bg-white hover:border-brand-200',
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          className="h-3.5 w-3.5 rounded border-slate-300 text-brand-500 focus:ring-brand-500"
                          checked={selected}
                          onChange={() => toggleHostname(device.hostname)}
                          disabled={isFlashing}
                        />
                        <div>
                          <p className="font-semibold text-slate-800">
                            {device.device_name || device.hostname}
                          </p>
                          <p className="text-slate-500">
                            {device.hostname} • {device.current_ip_address}
                          </p>
                        </div>
                      </div>
                      <span
                        className={clsx(
                          'rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                          result
                            ? result.success
                              ? 'bg-emerald-100 text-emerald-700'
                              : 'bg-rose-100 text-rose-700'
                            : 'bg-slate-100 text-slate-600',
                        )}
                      >
                        {statusLabel}
                      </span>
                    </div>
                    <p className="text-slate-600">{formatCapabilities(device.capabilities ?? null)}</p>
                    {isFlashing && selected && (
                      <div className="mt-1 h-1.5 w-full rounded-full bg-slate-200">
                        <div
                          className="h-full rounded-full bg-brand-500"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    )}
                    {result && result.error && (
                      <p className="text-rose-600">{result.error}</p>
                    )}
                  </label>
                );
              })
            )}
          </div>
        </div>

        <div className="space-y-2">
          <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-600">OTA log</h5>
          <div className="max-h-48 overflow-y-auto rounded border border-slate-200 bg-slate-950/95">
            <pre className="whitespace-pre-wrap break-words p-3 text-[11px] text-slate-100">
              {otaLogLines.length ? otaLogLines.join('\n') : 'Waiting for OTA output…'}
            </pre>
          </div>
          {otaError && <p className="text-xs text-rose-600">{otaError}</p>}
        </div>
      </section>

      <div className="max-h-[480px] overflow-auto rounded-md border border-slate-200 bg-slate-950/95">
        <SyntaxHighlighter
          language="yaml"
          style={duotoneSpace}
          wrapLines
          wrapLongLines
          customStyle={{ background: 'transparent', margin: 0, padding: '1rem', fontSize: '0.75rem' }}
        >
          {renderedYaml}
        </SyntaxHighlighter>
      </div>

      <SubstitutionSettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        currentSettings={appSettings}
      />
    </div>
  );
};
