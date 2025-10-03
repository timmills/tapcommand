import { useState, useEffect, useCallback } from 'react';
import type { TemplateSummary } from '../types';

const API_BASE_URL = 'http://localhost:8000';

export const useTemplates = () => {
  const [templateSummaries, setTemplateSummaries] = useState<TemplateSummary[]>([]);
  const [settingsTemplateId, setSettingsTemplateId] = useState<number | null>(null);
  const [settingsTemplateYaml, setSettingsTemplateYaml] = useState<string>('');
  const [wifiSsid, setWifiSsid] = useState<string>('');
  const [wifiPassword, setWifiPassword] = useState<string>('');
  const [wifiHidden, setWifiHidden] = useState<boolean>(false);
  const [wifiEditable, setWifiEditable] = useState<boolean>(false);
  const [otaPassword, setOtaPassword] = useState<string>('');

  const [templateListLoading, setTemplateListLoading] = useState(true);
  const [settingsTemplateLoading, setSettingsTemplateLoading] = useState(false);
  const [settingsTemplateSaving, setSettingsTemplateSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTemplateSummaries = useCallback(async () => {
    setTemplateListLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/templates`);
      if (!response.ok) {
        throw new Error(`Failed to fetch template summaries: ${response.statusText}`);
      }
      const data = await response.json();
      setTemplateSummaries(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch template summaries';
      setError(errorMessage);
      console.error('Error fetching template summaries:', err);
    } finally {
      setTemplateListLoading(false);
    }
  }, []);

  const loadTemplateYaml = useCallback(async (templateId: number) => {
    setSettingsTemplateLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/templates/${templateId}`);
      if (!response.ok) {
        throw new Error(`Failed to load template YAML: ${response.statusText}`);
      }
      const data = await response.json();

      setSettingsTemplateId(templateId);
      setSettingsTemplateYaml(data.template_yaml);

      // Parse substitutions from YAML content
      const yamlContent = data.template_yaml;
      const wifiSsidMatch = yamlContent.match(/wifi_ssid:\s*"([^"]+)"/);
      const wifiPasswordMatch = yamlContent.match(/wifi_password:\s*"([^"]+)"/);
      const wifiHiddenMatch = yamlContent.match(/wifi_hidden:\s*"([^"]+)"/);
      const otaPasswordMatch = yamlContent.match(/ota_password:\s*"([^"]*)"/);

      setWifiSsid(wifiSsidMatch ? wifiSsidMatch[1] : '');
      setWifiPassword(wifiPasswordMatch ? wifiPasswordMatch[1] : '');
      setWifiHidden(wifiHiddenMatch ? wifiHiddenMatch[1] === 'true' : false);
      setOtaPassword(otaPasswordMatch ? otaPasswordMatch[1] : '');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load template YAML';
      setError(errorMessage);
      console.error('Error loading template YAML:', err);
    } finally {
      setSettingsTemplateLoading(false);
    }
  }, []);

  const saveTemplate = useCallback(async (templateData: {
    yaml_content: string;
    wifi_ssid: string;
    wifi_password: string;
    wifi_hidden: boolean;
    ota_password: string;
  }) => {
    if (!settingsTemplateId) return;

    setSettingsTemplateSaving(true);
    setError(null);
    try {
      // Update YAML content with the new substitutions
      let updatedYaml = templateData.yaml_content;
      updatedYaml = updatedYaml.replace(/wifi_ssid:\s*"[^"]*"/, `wifi_ssid: "${templateData.wifi_ssid}"`);
      updatedYaml = updatedYaml.replace(/wifi_password:\s*"[^"]*"/, `wifi_password: "${templateData.wifi_password}"`);
      updatedYaml = updatedYaml.replace(/wifi_hidden:\s*"[^"]*"/, `wifi_hidden: "${templateData.wifi_hidden}"`);
      updatedYaml = updatedYaml.replace(/ota_password:\s*"[^"]*"/, `ota_password: "${templateData.ota_password}"`);

      const response = await fetch(`${API_BASE_URL}/api/v1/templates/${settingsTemplateId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          template_yaml: updatedYaml,
          test_compile: false,
          version_increment: 'patch'
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to save template: ${response.statusText}`);
      }

      await fetchTemplateSummaries();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save template';
      setError(errorMessage);
      console.error('Error saving template:', err);
      throw err;
    } finally {
      setSettingsTemplateSaving(false);
    }
  }, [settingsTemplateId, fetchTemplateSummaries]);

  useEffect(() => {
    fetchTemplateSummaries();
  }, [fetchTemplateSummaries]);

  return {
    templateSummaries,
    settingsTemplateId,
    settingsTemplateYaml,
    wifiSsid,
    wifiPassword,
    wifiHidden,
    wifiEditable,
    otaPassword,
    templateListLoading,
    settingsTemplateLoading,
    settingsTemplateSaving,
    error,
    setSettingsTemplateYaml,
    setWifiSsid,
    setWifiPassword,
    setWifiHidden,
    setWifiEditable,
    setOtaPassword,
    loadTemplateYaml,
    saveTemplate,
  };
};