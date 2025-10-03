import React from 'react';
import type { TemplateSummary } from '../types';
import { copyTextToClipboard } from '../utils';

interface YamlTemplatesTabProps {
  templateListLoading: boolean;
  templateSummaries: TemplateSummary[];
  settingsTemplateError: string | null;
  settingsTemplateId: number | null;
  settingsTemplateLoading: boolean;
  settingsTemplateSaving: boolean;
  wifiEditable: boolean;
  wifiSsid: string;
  wifiPassword: string;
  wifiHidden: boolean;
  otaPassword: string;
  settingsTemplateYaml: string;
  loadTemplateYaml: (id: number) => Promise<void>;
  setWifiEditable: (editable: boolean) => void;
  setWifiSsid: (ssid: string) => void;
  setWifiPassword: (password: string) => void;
  setWifiHidden: (hidden: boolean) => void;
  setOtaPassword: (password: string) => void;
  setSettingsTemplateYaml: (yaml: string) => void;
  handleSaveTemplate: (e: React.FormEvent) => Promise<void>;
}

const YamlTemplatesTab: React.FC<YamlTemplatesTabProps> = ({
  templateListLoading,
  templateSummaries,
  settingsTemplateError,
  settingsTemplateId,
  settingsTemplateLoading,
  settingsTemplateSaving,
  wifiEditable,
  wifiSsid,
  wifiPassword,
  wifiHidden,
  otaPassword,
  settingsTemplateYaml,
  loadTemplateYaml,
  setWifiEditable,
  setWifiSsid,
  setWifiPassword,
  setWifiHidden,
  setOtaPassword,
  setSettingsTemplateYaml,
  handleSaveTemplate
}) => {
  return (
    <div className="card">
      <div className="card-header">
        <h3>📄 ESPHome Templates</h3>
        <p>Select templates stored in the builder and edit their YAML in place.</p>
      </div>

      {templateListLoading && templateSummaries.length === 0 ? (
        <div className="loading">Loading templates...</div>
      ) : templateSummaries.length === 0 ? (
        settingsTemplateError ? (
          <div className="builder-error">⚠️ {settingsTemplateError}</div>
        ) : (
          <div className="empty-state">
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📄</div>
            <h3>No Templates Found</h3>
            <p>Seed a template through the YAML builder to edit it here.</p>
          </div>
        )
      ) : (
        <>
          <div className="form-group">
            <label>Select Template:</label>
            <select
              value={settingsTemplateId ?? ''}
              onChange={async (event) => {
                const nextId = Number(event.target.value);
                if (!nextId || nextId === settingsTemplateId) {
                  return;
                }
                await loadTemplateYaml(nextId);
              }}
            >
              <option value="" disabled>
                Select a template...
              </option>
              {templateSummaries.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name} v{template.version} (r{template.revision})
                  {template.description ? ` — ${template.description}` : ''}
                </option>
              ))}
            </select>
          </div>

          {settingsTemplateError && (
            <div className="builder-error">⚠️ {settingsTemplateError}</div>
          )}

          <div className="template-credentials-grid">
            <div className="form-group">
              <label className="credential-label">
                Wi-Fi SSID
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => setWifiEditable(!wifiEditable)}
                  title={wifiEditable ? 'Lock SSID field' : 'Edit SSID'}
                  disabled={settingsTemplateLoading || settingsTemplateSaving}
                >
                  <span role="img" aria-label={wifiEditable ? 'Lock SSID field' : 'Edit SSID'}>
                    {wifiEditable ? '🔒' : '✏️'}
                  </span>
                </button>
              </label>
              <input
                value={wifiSsid}
                onChange={(event) => {
                  if (!wifiEditable) {
                    return;
                  }
                  setWifiSsid(event.target.value);
                }}
                placeholder="Network name"
                disabled={!wifiEditable || settingsTemplateLoading || settingsTemplateSaving}
              />
            </div>
            <div className="form-group">
              <label>Wi-Fi Password</label>
              <input
                type="password"
                value={wifiPassword}
                onChange={(event) => setWifiPassword(event.target.value)}
                placeholder="Network password"
                disabled={settingsTemplateLoading || settingsTemplateSaving}
              />
            </div>
            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={wifiHidden}
                  onChange={(event) => setWifiHidden(event.target.checked)}
                  disabled={settingsTemplateLoading || settingsTemplateSaving}
                />
                Hidden Network
              </label>
            </div>
            <div className="form-group">
              <label>OTA Password</label>
              <input
                type="password"
                value={otaPassword}
                onChange={(event) => setOtaPassword(event.target.value)}
                placeholder="Over-the-air update password"
                disabled={settingsTemplateLoading || settingsTemplateSaving}
              />
            </div>
          </div>

          {settingsTemplateLoading ? (
            <div className="loading">Loading YAML template...</div>
          ) : settingsTemplateId ? (
            <div className="card preview-card">
              <div className="preview-header">
                <div className="char-count">Character Count: {settingsTemplateYaml.length}</div>
                <button
                  className="button secondary"
                  style={{ marginLeft: 'auto' }}
                  onClick={async () => {
                    const text = (settingsTemplateYaml || '').trim();
                    if (!text) {
                      return;
                    }
                    const success = await copyTextToClipboard(text);
                    if (!success) {
                      console.error('Failed to copy YAML to clipboard.');
                    }
                  }}
                >
                  📋 Copy YAML
                </button>
                <button
                  className="button"
                  style={{ marginLeft: '8px' }}
                  onClick={handleSaveTemplate}
                  disabled={settingsTemplateSaving}
                >
                  {settingsTemplateSaving ? 'Saving...' : '💾 Save Template'}
                </button>
              </div>
              {settingsTemplateLoading && <div className="preview-loading">Loading template...</div>}
              <pre
                className="yaml-preview"
                contentEditable={!settingsTemplateSaving}
                onInput={(e) => {
                  const target = e.target as HTMLPreElement;
                  setSettingsTemplateYaml(target.textContent || '');
                }}
                suppressContentEditableWarning={true}
                style={{
                  minHeight: '400px',
                  whiteSpace: 'pre-wrap',
                  wordWrap: 'break-word'
                }}
              >
                {settingsTemplateYaml || '# Template loading...'}
              </pre>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
};

export default YamlTemplatesTab;