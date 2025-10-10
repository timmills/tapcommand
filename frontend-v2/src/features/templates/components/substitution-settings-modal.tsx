import { useState, useEffect } from 'react';
import { useUpdateApplicationSetting } from '@/features/settings/hooks/use-update-application-setting';
import type { ApplicationSettingsMap } from '@/features/settings/api/application-settings-api';
import clsx from 'clsx';

interface SubstitutionSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentSettings: ApplicationSettingsMap | undefined;
}

interface FormState {
  wifi_ssid: string;
  wifi_password: string;
  wifi_hidden: boolean;
  esphome_api_key: string;
  ota_password: string;
}

export const SubstitutionSettingsModal = ({
  isOpen,
  onClose,
  currentSettings,
}: SubstitutionSettingsModalProps) => {
  const { mutate: updateSetting, isPending } = useUpdateApplicationSetting();
  const [formState, setFormState] = useState<FormState>({
    wifi_ssid: '',
    wifi_password: '',
    wifi_hidden: true,
    esphome_api_key: '',
    ota_password: '',
  });
  const [showPasswords, setShowPasswords] = useState(false);

  useEffect(() => {
    if (currentSettings) {
      setFormState({
        wifi_ssid: (currentSettings['wifi_ssid']?.value as string) || '',
        wifi_password: (currentSettings['wifi_password']?.value as string) || '',
        wifi_hidden: (currentSettings['wifi_hidden']?.value as boolean) ?? true,
        esphome_api_key: (currentSettings['esphome_api_key']?.value as string) || '',
        ota_password: (currentSettings['ota_password']?.value as string) || '',
      });
    }
  }, [currentSettings]);

  const handleSave = () => {
    const updates = [
      { key: 'wifi_ssid', value: formState.wifi_ssid, setting_type: 'string', is_public: false },
      { key: 'wifi_password', value: formState.wifi_password, setting_type: 'string', is_public: false },
      { key: 'wifi_hidden', value: formState.wifi_hidden, setting_type: 'boolean', is_public: false },
      { key: 'esphome_api_key', value: formState.esphome_api_key, setting_type: 'string', is_public: false },
      { key: 'ota_password', value: formState.ota_password, setting_type: 'string', is_public: false },
    ];

    // Save all settings sequentially
    let completed = 0;
    updates.forEach((update) => {
      updateSetting(update, {
        onSuccess: () => {
          completed++;
          if (completed === updates.length) {
            onClose();
          }
        },
      });
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="w-full max-w-2xl rounded-lg border border-slate-200 bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 p-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Firmware Substitution Settings</h3>
            <p className="text-sm text-slate-500">
              Configure default values for ESPHome firmware compilation
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4 p-4">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            <div className="flex items-start gap-2">
              <svg className="h-5 w-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              <div>
                <div className="font-semibold">Security Notice</div>
                <div className="mt-1">
                  These values are embedded in compiled firmware. WiFi credentials and passwords should be
                  venue-specific and secure. Changes affect all future firmware builds.
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-700">WiFi SSID</label>
              <input
                type="text"
                value={formState.wifi_ssid}
                onChange={(e) => setFormState({ ...formState, wifi_ssid: e.target.value })}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
                placeholder="TV"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">WiFi Password</label>
              <div className="relative mt-1">
                <input
                  type={showPasswords ? 'text' : 'password'}
                  value={formState.wifi_password}
                  onChange={(e) => setFormState({ ...formState, wifi_password: e.target.value })}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 pr-10 text-sm text-slate-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
                  placeholder="changeme"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="wifi-hidden"
                checked={formState.wifi_hidden}
                onChange={(e) => setFormState({ ...formState, wifi_hidden: e.target.checked })}
                className="h-4 w-4 rounded border-slate-300 text-brand-500 focus:ring-brand-500"
              />
              <label htmlFor="wifi-hidden" className="text-sm font-medium text-slate-700">
                WiFi network is hidden (SSID broadcast disabled)
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">ESPHome API Key</label>
              <div className="relative mt-1">
                <input
                  type={showPasswords ? 'text' : 'password'}
                  value={formState.esphome_api_key}
                  onChange={(e) => setFormState({ ...formState, esphome_api_key: e.target.value })}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 pr-10 text-sm font-mono text-slate-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
                  placeholder="(optional)"
                />
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Encryption key for ESPHome native API (base64-encoded, 32 bytes)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">OTA Password</label>
              <div className="relative mt-1">
                <input
                  type={showPasswords ? 'text' : 'password'}
                  value={formState.ota_password}
                  onChange={(e) => setFormState({ ...formState, ota_password: e.target.value })}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 pr-10 text-sm text-slate-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
                  placeholder="(optional)"
                />
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Password required for over-the-air firmware updates
              </p>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="show-passwords"
                checked={showPasswords}
                onChange={(e) => setShowPasswords(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-brand-500 focus:ring-brand-500"
              />
              <label htmlFor="show-passwords" className="text-sm font-medium text-slate-700">
                Show passwords and keys
              </label>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-slate-200 p-4">
          <button
            onClick={onClose}
            disabled={isPending}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isPending}
            className={clsx(
              'rounded-md px-4 py-2 text-sm font-semibold text-white shadow-sm transition',
              isPending
                ? 'cursor-not-allowed bg-brand-300'
                : 'bg-brand-500 hover:bg-brand-600'
            )}
          >
            {isPending ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};
