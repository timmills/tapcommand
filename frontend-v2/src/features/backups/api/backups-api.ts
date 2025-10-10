import { apiClient } from '@/lib/axios';

export interface BackupReport {
  generated_at: string;
  database_path: string;
  tables: Record<string, number | null>;
  summary: {
    total_devices?: number;
    device_types_count?: number;
    total_users?: number;
    total_schedules?: number;
    total_channels?: number;
    total_ir_commands?: number;
    total_captured_remotes?: number;
    total_command_history?: number;
    commands_last_24h?: number;
    total_audit_entries?: number;
  };
}

export interface BackupInfo {
  type: string;
  filename: string;
  size_bytes: number;
  size_mb: number;
  created_at: string;
  is_compressed: boolean;
  has_report?: boolean;
  report_summary?: string | null;
  report?: BackupReport | null;
}

export interface BackupStatus {
  disk_usage: {
    used_gb: number;
    total_gb: number;
    usage_percent: number;
    free_gb: number;
  };
  backup_folder_size_gb: number;
  backup_folder_max_gb: number;
  last_daily_backup: string | null;
  last_weekly_backup: string | null;
  last_monthly_backup: string | null;
  total_backups: number;
  disk_alerts: Array<{
    type: string;
    message: string;
    timestamp: string;
  }>;
  warnings: string[];
}

export interface CreateBackupRequest {
  type?: string;
}

export interface CreateBackupResponse {
  success: boolean;
  filename: string | null;
  message: string | null;
}

export interface CurrentDatabaseReport {
  report: BackupReport;
  summary: string;
}

export const backupsApi = {
  // Get list of all backups
  getBackups: async (): Promise<BackupInfo[]> => {
    const response = await apiClient.get('/api/v1/backups');
    return response.data;
  },

  // Get backup system status
  getStatus: async (): Promise<BackupStatus> => {
    const response = await apiClient.get('/api/v1/backups/status');
    return response.data;
  },

  // Get current database report
  getCurrentDatabaseReport: async (): Promise<CurrentDatabaseReport> => {
    const response = await apiClient.get('/api/v1/backups/current-database-report');
    return response.data;
  },

  // Create a new backup
  createBackup: async (request: CreateBackupRequest = {}): Promise<CreateBackupResponse> => {
    const response = await apiClient.post('/api/v1/backups/create', request);
    return response.data;
  },

  // Download a backup file
  downloadBackup: async (filename: string): Promise<void> => {
    const response = await apiClient.get(`/api/v1/backups/download/${filename}`, {
      responseType: 'blob',
    });

    // Create a download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  // Delete a backup
  deleteBackup: async (filename: string): Promise<{ success: boolean; message: string | null }> => {
    const response = await apiClient.delete(`/api/v1/backups/${filename}`);
    return response.data;
  },

  // Upload a backup file
  uploadBackup: async (file: File): Promise<{ success: boolean; filename: string | null; message: string | null }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/api/v1/backups/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Restore from a backup
  restoreBackup: async (filename: string): Promise<{ success: boolean; message: string | null; emergency_backup: string | null; warning?: string }> => {
    const response = await apiClient.post(`/api/v1/backups/restore/${filename}`);
    return response.data;
  },
};
