import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { backupsApi } from '../api/backups-api';
import type { CreateBackupRequest } from '../api/backups-api';

export const BACKUPS_QUERY_KEY = 'backups';
export const BACKUP_STATUS_QUERY_KEY = 'backup-status';
export const CURRENT_DATABASE_REPORT_QUERY_KEY = 'current-database-report';

// Get list of backups
export const useBackups = () => {
  return useQuery({
    queryKey: [BACKUPS_QUERY_KEY],
    queryFn: backupsApi.getBackups,
    refetchInterval: 30000, // Refresh every 30 seconds
  });
};

// Get backup system status
export const useBackupStatus = () => {
  return useQuery({
    queryKey: [BACKUP_STATUS_QUERY_KEY],
    queryFn: backupsApi.getStatus,
    refetchInterval: 30000, // Refresh every 30 seconds
  });
};

// Get current database report
export const useCurrentDatabaseReport = () => {
  return useQuery({
    queryKey: [CURRENT_DATABASE_REPORT_QUERY_KEY],
    queryFn: backupsApi.getCurrentDatabaseReport,
    refetchInterval: 60000, // Refresh every 60 seconds
  });
};

// Create backup mutation
export const useCreateBackup = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateBackupRequest) => backupsApi.createBackup(request),
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: [BACKUPS_QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: [BACKUP_STATUS_QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: [CURRENT_DATABASE_REPORT_QUERY_KEY] });
    },
  });
};

// Download backup mutation
export const useDownloadBackup = () => {
  return useMutation({
    mutationFn: (filename: string) => backupsApi.downloadBackup(filename),
  });
};

// Delete backup mutation
export const useDeleteBackup = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (filename: string) => backupsApi.deleteBackup(filename),
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: [BACKUPS_QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: [BACKUP_STATUS_QUERY_KEY] });
    },
  });
};

// Upload backup mutation
export const useUploadBackup = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => backupsApi.uploadBackup(file),
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: [BACKUPS_QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: [BACKUP_STATUS_QUERY_KEY] });
    },
  });
};

// Restore backup mutation
export const useRestoreBackup = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (filename: string) => backupsApi.restoreBackup(filename),
    onSuccess: () => {
      // Invalidate all queries after restore since data may have changed
      queryClient.invalidateQueries();
    },
  });
};
