import { useState, useRef } from 'react';
import { useBackups, useBackupStatus, useCreateBackup, useDownloadBackup, useDeleteBackup, useUploadBackup, useRestoreBackup, useCurrentDatabaseReport } from '../hooks/use-backups';
import type { BackupInfo } from '../api/backups-api';

// Format date to show relative time and absolute date
const formatBackupDate = (dateString: string): { relative: string; absolute: string } => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffMinutes = Math.floor(diffMs / (1000 * 60));

  let relative = '';
  if (diffMinutes < 1) {
    relative = 'Just now';
  } else if (diffMinutes < 60) {
    relative = `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
  } else if (diffHours < 24) {
    relative = `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  } else if (diffDays === 1) {
    relative = 'Yesterday';
  } else if (diffDays < 7) {
    relative = `${diffDays} days ago`;
  } else if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    relative = `${weeks} week${weeks === 1 ? '' : 's'} ago`;
  } else if (diffDays < 365) {
    const months = Math.floor(diffDays / 30);
    relative = `${months} month${months === 1 ? '' : 's'} ago`;
  } else {
    const years = Math.floor(diffDays / 365);
    relative = `${years} year${years === 1 ? '' : 's'} ago`;
  }

  // Format absolute date: "Jan 15, 2025 at 2:30 PM"
  const absolute = date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }) + ' at ' + date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });

  return { relative, absolute };
};

export const BackupsPage = () => {
  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-900">Database Backup & Recovery</h2>
        <p className="text-sm text-slate-500">
          Manage database backups and monitor system storage.
        </p>
      </header>

      <DiskStatusPanel />
      <BackupControlPanel />
      <UploadBackupPanel />
      <BackupsListPanel />
    </section>
  );
};

const DiskStatusPanel = () => {
  const statusQuery = useBackupStatus();

  if (statusQuery.isLoading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="text-sm text-slate-500">Loading system status...</div>
      </div>
    );
  }

  if (statusQuery.isError) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 shadow-sm">
        <div className="text-sm text-rose-700">
          Failed to load system status. {statusQuery.error instanceof Error ? statusQuery.error.message : 'Please try again.'}
        </div>
      </div>
    );
  }

  const status = statusQuery.data;
  if (!status) return null;

  const diskUsagePercent = status.disk_usage.usage_percent;
  const isCritical = diskUsagePercent >= 90;
  const isWarning = diskUsagePercent >= 80;

  return (
    <div className="space-y-4">
      {/* Warnings */}
      {status.warnings.length > 0 && (
        <div className={`rounded-lg border p-4 shadow-sm ${isCritical ? 'border-rose-200 bg-rose-50' : 'border-amber-200 bg-amber-50'}`}>
          <h4 className={`text-sm font-semibold ${isCritical ? 'text-rose-900' : 'text-amber-900'}`}>
            {isCritical ? 'Critical Alerts' : 'Warnings'}
          </h4>
          <ul className={`mt-2 space-y-1 text-sm ${isCritical ? 'text-rose-700' : 'text-amber-700'}`}>
            {status.warnings.map((warning, idx) => (
              <li key={idx}>• {warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Disk Usage */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Disk Usage</h3>
        <div className="mt-3 space-y-3">
          <div>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-slate-600">System Storage</span>
              <span className={`font-medium ${isCritical ? 'text-rose-600' : isWarning ? 'text-amber-600' : 'text-slate-900'}`}>
                {diskUsagePercent.toFixed(1)}% used
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full transition-all ${
                  isCritical ? 'bg-rose-500' : isWarning ? 'bg-amber-500' : 'bg-brand-500'
                }`}
                style={{ width: `${diskUsagePercent}%` }}
              />
            </div>
            <div className="mt-1 text-xs text-slate-500">
              {status.disk_usage.used_gb.toFixed(1)} GB used of {status.disk_usage.total_gb.toFixed(1)} GB
              ({status.disk_usage.free_gb.toFixed(1)} GB free)
            </div>
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-slate-600">Backup Folder</span>
              <span className="font-medium text-slate-900">
                {status.backup_folder_size_gb.toFixed(2)} GB
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full bg-blue-500 transition-all"
                style={{ width: `${(status.backup_folder_size_gb / status.backup_folder_max_gb) * 100}%` }}
              />
            </div>
            <div className="mt-1 text-xs text-slate-500">
              Limit: {status.backup_folder_max_gb.toFixed(1)} GB
            </div>
          </div>
        </div>
      </div>

      {/* Last Backup Times */}
      <div className="grid gap-4 sm:grid-cols-3">
        <BackupTimeCard label="Daily" timestamp={status.last_daily_backup} />
        <BackupTimeCard label="Weekly" timestamp={status.last_weekly_backup} />
        <BackupTimeCard label="Monthly" timestamp={status.last_monthly_backup} />
      </div>
    </div>
  );
};

const BackupTimeCard = ({ label, timestamp }: { label: string; timestamp: string | null }) => {
  const formattedTime = timestamp ? new Date(timestamp).toLocaleString() : 'Never';

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <div className="text-xs font-medium text-slate-600">{label} Backup</div>
      <div className="mt-1 text-sm font-semibold text-slate-900">{formattedTime}</div>
    </div>
  );
};

const BackupControlPanel = () => {
  const createBackup = useCreateBackup();
  const currentReport = useCurrentDatabaseReport();
  const [message, setMessage] = useState<string | null>(null);

  const handleCreateBackup = async () => {
    setMessage(null);
    try {
      const result = await createBackup.mutateAsync({ type: 'manual' });
      if (result.success) {
        setMessage(`✓ Backup created: ${result.filename}`);
      } else {
        setMessage(`✗ ${result.message || 'Failed to create backup'}`);
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to create backup';
      setMessage(`✗ ${msg}`);
    }
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-slate-900">Manual Backup</h3>
          <p className="text-xs text-slate-500">
            Create an immediate backup of the database. Automatic backups run daily at 2:00 AM.
          </p>
          {currentReport.data && (
            <div className="mt-2">
              <div className="text-xs text-slate-600 font-medium">Current Database:</div>
              <div className="text-xs text-slate-700 mt-1 rounded bg-blue-50 px-2 py-1 inline-block">
                📊 {currentReport.data.summary}
              </div>
            </div>
          )}
          {currentReport.isLoading && (
            <div className="mt-2 text-xs text-slate-500">Loading database info...</div>
          )}
        </div>
        <button
          type="button"
          onClick={handleCreateBackup}
          disabled={createBackup.isPending}
          className="rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
        >
          {createBackup.isPending ? 'Creating...' : 'Create Backup Now'}
        </button>
      </div>
      {message && (
        <div className={`mt-3 text-sm ${message.startsWith('✓') ? 'text-emerald-600' : 'text-rose-600'}`}>
          {message}
        </div>
      )}
    </div>
  );
};

const UploadBackupPanel = () => {
  const uploadBackup = useUploadBackup();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setMessage(null);
    try {
      const result = await uploadBackup.mutateAsync(file);
      if (result.success) {
        setMessage(`✓ Uploaded: ${result.filename}`);
        // Reset file input
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } else {
        setMessage(`✗ ${result.message || 'Failed to upload'}`);
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to upload backup';
      setMessage(`✗ ${msg}`);
    }
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Upload Backup</h3>
          <p className="text-xs text-slate-500">
            Upload a previously downloaded compressed backup file (.db.gz).
          </p>
        </div>
        <label className="cursor-pointer">
          <input
            ref={fileInputRef}
            type="file"
            accept=".db.gz,.gz"
            onChange={handleFileSelect}
            disabled={uploadBackup.isPending}
            className="hidden"
          />
          <span className="inline-block rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">
            {uploadBackup.isPending ? 'Uploading...' : 'Choose File'}
          </span>
        </label>
      </div>
      {message && (
        <div className={`mt-3 text-sm ${message.startsWith('✓') ? 'text-emerald-600' : 'text-rose-600'}`}>
          {message}
        </div>
      )}
    </div>
  );
};

const BackupsListPanel = () => {
  const backupsQuery = useBackups();
  const downloadBackup = useDownloadBackup();
  const deleteBackup = useDeleteBackup();
  const restoreBackup = useRestoreBackup();
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [restoreConfirm, setRestoreConfirm] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleDownload = async (filename: string) => {
    setMessage(null);
    try {
      await downloadBackup.mutateAsync(filename);
      setMessage(`✓ Downloading ${filename}...`);
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to download';
      setMessage(`✗ ${msg}`);
    }
  };

  const handleDelete = async (filename: string) => {
    setMessage(null);
    try {
      const result = await deleteBackup.mutateAsync(filename);
      if (result.success) {
        setMessage(`✓ Deleted ${filename}`);
        setDeleteConfirm(null);
      } else {
        setMessage(`✗ ${result.message || 'Failed to delete backup'}`);
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to delete';
      setMessage(`✗ ${msg}`);
    }
  };

  const handleRestore = async (filename: string) => {
    setMessage(null);
    try {
      const result = await restoreBackup.mutateAsync(filename);
      if (result.success) {
        setMessage(`✓ Database restored from ${filename}. Emergency backup created: ${result.emergency_backup}`);
        setRestoreConfirm(null);
      } else {
        setMessage(`✗ ${result.message || 'Failed to restore backup'}`);
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to restore';
      setMessage(`✗ ${msg}`);
    }
  };

  if (backupsQuery.isLoading) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500">
        Loading backups...
      </div>
    );
  }

  if (backupsQuery.isError) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
        Failed to load backups. {backupsQuery.error instanceof Error ? backupsQuery.error.message : 'Please try again.'}
      </div>
    );
  }

  const backups = backupsQuery.data || [];

  // Group backups by type
  const dailyBackups = backups.filter((b) => b.type === 'daily');
  const weeklyBackups = backups.filter((b) => b.type === 'weekly');
  const monthlyBackups = backups.filter((b) => b.type === 'monthly');

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Available Backups</h3>
        {message && (
          <div className={`text-sm ${message.startsWith('✓') ? 'text-emerald-600' : 'text-rose-600'}`}>
            {message}
          </div>
        )}
      </div>

      {backups.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
          No backups available. Create your first backup above.
        </div>
      ) : (
        <div className="space-y-4">
          {dailyBackups.length > 0 && (
            <BackupSection
              title="Daily Backups"
              description="Last 14 days"
              backups={dailyBackups}
              onDownload={handleDownload}
              onDelete={(filename) => setDeleteConfirm(filename)}
              onRestore={(filename) => setRestoreConfirm(filename)}
              deleteConfirm={deleteConfirm}
              restoreConfirm={restoreConfirm}
              onConfirmDelete={handleDelete}
              onConfirmRestore={handleRestore}
              onCancelDelete={() => setDeleteConfirm(null)}
              onCancelRestore={() => setRestoreConfirm(null)}
              isDeleting={deleteBackup.isPending}
              isRestoring={restoreBackup.isPending}
            />
          )}
          {weeklyBackups.length > 0 && (
            <BackupSection
              title="Weekly Backups"
              description="Last 4 weeks"
              backups={weeklyBackups}
              onDownload={handleDownload}
              onDelete={(filename) => setDeleteConfirm(filename)}
              onRestore={(filename) => setRestoreConfirm(filename)}
              deleteConfirm={deleteConfirm}
              restoreConfirm={restoreConfirm}
              onConfirmDelete={handleDelete}
              onConfirmRestore={handleRestore}
              onCancelDelete={() => setDeleteConfirm(null)}
              onCancelRestore={() => setRestoreConfirm(null)}
              isDeleting={deleteBackup.isPending}
              isRestoring={restoreBackup.isPending}
            />
          )}
          {monthlyBackups.length > 0 && (
            <BackupSection
              title="Monthly Backups"
              description="Last 6 months"
              backups={monthlyBackups}
              onDownload={handleDownload}
              onDelete={(filename) => setDeleteConfirm(filename)}
              onRestore={(filename) => setRestoreConfirm(filename)}
              deleteConfirm={deleteConfirm}
              restoreConfirm={restoreConfirm}
              onConfirmDelete={handleDelete}
              onConfirmRestore={handleRestore}
              onCancelDelete={() => setDeleteConfirm(null)}
              onCancelRestore={() => setRestoreConfirm(null)}
              isDeleting={deleteBackup.isPending}
              isRestoring={restoreBackup.isPending}
            />
          )}
        </div>
      )}
    </div>
  );
};

const BackupSection = ({
  title,
  description,
  backups,
  onDownload,
  onDelete,
  onRestore,
  deleteConfirm,
  restoreConfirm,
  onConfirmDelete,
  onConfirmRestore,
  onCancelDelete,
  onCancelRestore,
  isDeleting,
  isRestoring,
}: {
  title: string;
  description: string;
  backups: BackupInfo[];
  onDownload: (filename: string) => void;
  onDelete: (filename: string) => void;
  onRestore: (filename: string) => void;
  deleteConfirm: string | null;
  restoreConfirm: string | null;
  onConfirmDelete: (filename: string) => void;
  onConfirmRestore: (filename: string) => void;
  onCancelDelete: () => void;
  onCancelRestore: () => void;
  isDeleting: boolean;
  isRestoring: boolean;
}) => {
  const [expandedReport, setExpandedReport] = useState<string | null>(null);
  return (
    <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-4 py-3">
        <h4 className="text-sm font-semibold text-slate-900">{title}</h4>
        <p className="text-xs text-slate-500">{description}</p>
      </div>
      <div className="divide-y divide-slate-100">
        {backups.map((backup) => {
          const dateInfo = formatBackupDate(backup.created_at);
          return (
          <div key={backup.filename} className="px-4 py-3">
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1">
                <div className="text-sm font-medium text-slate-900">
                  {backup.filename}
                  {backup.is_compressed && (
                    <span className="ml-2 rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                      Compressed
                    </span>
                  )}
                </div>
                <div className="mt-1 space-y-1">
                  <div className="text-xs text-slate-500">
                    <span className="font-medium text-slate-700">{dateInfo.relative}</span>
                    <span className="mx-1">•</span>
                    {dateInfo.absolute}
                    <span className="mx-1">•</span>
                    {backup.size_mb.toFixed(2)} MB
                  </div>
                  {backup.has_report && backup.report_summary && (
                    <div className="text-xs text-slate-600">
                      <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700">
                        📊 {backup.report_summary}
                      </span>
                      {backup.report && (
                        <button
                          type="button"
                          onClick={() => setExpandedReport(expandedReport === backup.filename ? null : backup.filename)}
                          className="ml-2 text-brand-600 hover:text-brand-700 underline"
                        >
                          {expandedReport === backup.filename ? 'Hide details' : 'View details'}
                        </button>
                      )}
                    </div>
                  )}
                  {expandedReport === backup.filename && backup.report && (
                    <div className="mt-2 rounded border border-slate-200 bg-slate-50 p-3 text-xs">
                      <div className="font-semibold text-slate-700 mb-2">Database Content Details</div>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                        {backup.report.summary.total_devices !== undefined && (
                          <>
                            <div className="text-slate-600">Devices:</div>
                            <div className="font-medium text-slate-900">{backup.report.summary.total_devices}</div>
                          </>
                        )}
                        {backup.report.summary.device_types_count !== undefined && (
                          <>
                            <div className="text-slate-600">Device Types:</div>
                            <div className="font-medium text-slate-900">{backup.report.summary.device_types_count}</div>
                          </>
                        )}
                        {backup.report.summary.total_users !== undefined && (
                          <>
                            <div className="text-slate-600">Users:</div>
                            <div className="font-medium text-slate-900">{backup.report.summary.total_users}</div>
                          </>
                        )}
                        {backup.report.summary.total_schedules !== undefined && (
                          <>
                            <div className="text-slate-600">Schedules:</div>
                            <div className="font-medium text-slate-900">{backup.report.summary.total_schedules}</div>
                          </>
                        )}
                        {backup.report.summary.total_channels !== undefined && (
                          <>
                            <div className="text-slate-600">Channels:</div>
                            <div className="font-medium text-slate-900">{backup.report.summary.total_channels}</div>
                          </>
                        )}
                        {backup.report.summary.total_ir_commands !== undefined && (
                          <>
                            <div className="text-slate-600">IR Commands:</div>
                            <div className="font-medium text-slate-900">{backup.report.summary.total_ir_commands.toLocaleString()}</div>
                          </>
                        )}
                        {backup.report.summary.total_captured_remotes !== undefined && (
                          <>
                            <div className="text-slate-600">Captured Remotes:</div>
                            <div className="font-medium text-slate-900">{backup.report.summary.total_captured_remotes}</div>
                          </>
                        )}
                        {backup.report.summary.total_command_history !== undefined && (
                          <>
                            <div className="text-slate-600">Command History:</div>
                            <div className="font-medium text-slate-900">{backup.report.summary.total_command_history}</div>
                          </>
                        )}
                        {backup.report.summary.commands_last_24h !== undefined && (
                          <>
                            <div className="text-slate-600">Commands (24h):</div>
                            <div className="font-medium text-slate-900">{backup.report.summary.commands_last_24h}</div>
                          </>
                        )}
                        {backup.report.summary.total_audit_entries !== undefined && (
                          <>
                            <div className="text-slate-600">Audit Entries:</div>
                            <div className="font-medium text-slate-900">{backup.report.summary.total_audit_entries}</div>
                          </>
                        )}
                      </div>
                      <div className="mt-2 pt-2 border-t border-slate-200 text-slate-500">
                        Report generated: {new Date(backup.report.generated_at).toLocaleString()}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                {restoreConfirm === backup.filename ? (
                  <div className="flex flex-col gap-2">
                    <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                      <div className="font-semibold">Warning: This will replace the current database!</div>
                      <div className="mt-1">An emergency backup will be created first.</div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => onConfirmRestore(backup.filename)}
                        disabled={isRestoring}
                        className="rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isRestoring ? 'Restoring...' : 'Confirm Restore'}
                      </button>
                      <button
                        type="button"
                        onClick={onCancelRestore}
                        disabled={isRestoring}
                        className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : deleteConfirm === backup.filename ? (
                  <>
                    <button
                      type="button"
                      onClick={() => onConfirmDelete(backup.filename)}
                      disabled={isDeleting}
                      className="rounded-md border border-rose-300 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isDeleting ? 'Deleting...' : 'Confirm'}
                    </button>
                    <button
                      type="button"
                      onClick={onCancelDelete}
                      disabled={isDeleting}
                      className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => onDownload(backup.filename)}
                      className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                    >
                      Download
                    </button>
                    <button
                      type="button"
                      onClick={() => onRestore(backup.filename)}
                      className="rounded-md border border-brand-300 bg-brand-50 px-3 py-1.5 text-xs font-medium text-brand-700 transition hover:bg-brand-100"
                    >
                      Restore
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(backup.filename)}
                      className="rounded-md border border-rose-300 px-3 py-1.5 text-xs font-medium text-rose-600 transition hover:bg-rose-50"
                    >
                      Delete
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        );
        })}
      </div>
    </div>
  );
};
