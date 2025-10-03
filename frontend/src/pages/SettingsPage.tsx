import React from 'react';
import type { SettingsTab, TemplateSummary, DeviceTag, ChannelTab, AreaInfo, Channel, InHouseChannelCreate, InHouseChannelUpdate } from '../types';
import YamlTemplatesTab from '../components/YamlTemplatesTab';
import TagManagementTab from '../components/TagManagementTab';
import ChannelsTab from '../components/ChannelsTab';

interface SettingsPageProps {
  settingsTab: SettingsTab;
  setSettingsTab: (tab: SettingsTab) => void;

  // YAML Templates Tab Props
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

  // Tag Management Tab Props
  settingsLoading: boolean;
  deviceTags: DeviceTag[];
  editingTag: DeviceTag | null;
  setEditingTag: (tag: DeviceTag | null) => void;
  handleTagDelete: (tagId: number) => Promise<void>;
  handleTagSave: (e: React.FormEvent) => Promise<void>;

  // Channels Tab Props
  channelTab: ChannelTab;
  setChannelTab: (tab: ChannelTab) => void;
  channelsLoading: boolean;
  areas: AreaInfo[];
  selectedAreaName: string | null;
  setSelectedAreaName: (name: string | null) => void;
  channels: Channel[];
  selectedChannels: string[];
  setSelectedChannels: (channels: string[]) => void;
  handleSaveAreaChannels: () => Promise<void>;
  channelsSaving: boolean;
  inHouseChannels: Channel[];
  editingInHouseChannel: InHouseChannelCreate | InHouseChannelUpdate | null;
  setEditingInHouseChannel: (channel: InHouseChannelCreate | InHouseChannelUpdate | null) => void;
  handleDeleteInHouseChannel: (channelId: number) => Promise<void>;
  handleSaveInHouseChannel: (e: React.FormEvent) => Promise<void>;
}

const SettingsPage: React.FC<SettingsPageProps> = ({
  settingsTab,
  setSettingsTab,

  // YAML Templates Tab Props
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
  handleSaveTemplate,

  // Tag Management Tab Props
  settingsLoading,
  deviceTags,
  editingTag,
  setEditingTag,
  handleTagDelete,
  handleTagSave,

  // Channels Tab Props
  channelTab,
  setChannelTab,
  channelsLoading,
  areas,
  selectedAreaName,
  setSelectedAreaName,
  channels,
  selectedChannels,
  setSelectedChannels,
  handleSaveAreaChannels,
  channelsSaving,
  inHouseChannels,
  editingInHouseChannel,
  setEditingInHouseChannel,
  handleDeleteInHouseChannel,
  handleSaveInHouseChannel
}) => {
  return (
    <div className="settings-page">
      <div className="page-header">
        <h2>⚙️ Settings</h2>
        <p>Manage templates and system-wide configuration</p>
      </div>

      {/* Settings Tabs */}
      <div className="settings-tabs">
        <button
          className={`settings-tab ${settingsTab === 'yaml-templates' ? 'active' : ''}`}
          onClick={() => setSettingsTab('yaml-templates')}
        >
          📄 YAML Templates
        </button>
        <button
          className={`settings-tab ${settingsTab === 'tag-management' ? 'active' : ''}`}
          onClick={() => setSettingsTab('tag-management')}
        >
          🏷️ Tag Management
        </button>
        <button
          className={`settings-tab ${settingsTab === 'channels' ? 'active' : ''}`}
          onClick={() => setSettingsTab('channels')}
        >
          📺 Channels
        </button>
      </div>

      {/* YAML Templates Tab */}
      {settingsTab === 'yaml-templates' && (
        <YamlTemplatesTab
          templateListLoading={templateListLoading}
          templateSummaries={templateSummaries}
          settingsTemplateError={settingsTemplateError}
          settingsTemplateId={settingsTemplateId}
          settingsTemplateLoading={settingsTemplateLoading}
          settingsTemplateSaving={settingsTemplateSaving}
          wifiEditable={wifiEditable}
          wifiSsid={wifiSsid}
          wifiPassword={wifiPassword}
          wifiHidden={wifiHidden}
          otaPassword={otaPassword}
          settingsTemplateYaml={settingsTemplateYaml}
          loadTemplateYaml={loadTemplateYaml}
          setWifiEditable={setWifiEditable}
          setWifiSsid={setWifiSsid}
          setWifiPassword={setWifiPassword}
          setWifiHidden={setWifiHidden}
          setOtaPassword={setOtaPassword}
          setSettingsTemplateYaml={setSettingsTemplateYaml}
          handleSaveTemplate={handleSaveTemplate}
        />
      )}

      {/* Tag Management Tab */}
      {settingsTab === 'tag-management' && (
        <TagManagementTab
          settingsLoading={settingsLoading}
          deviceTags={deviceTags}
          editingTag={editingTag}
          setEditingTag={setEditingTag}
          handleTagDelete={handleTagDelete}
          handleTagSave={handleTagSave}
        />
      )}

      {/* Channels Tab */}
      {settingsTab === 'channels' && (
        <ChannelsTab
          channelTab={channelTab}
          setChannelTab={setChannelTab}
          channelsLoading={channelsLoading}
          areas={areas}
          selectedAreaName={selectedAreaName}
          setSelectedAreaName={setSelectedAreaName}
          channels={channels}
          selectedChannels={selectedChannels}
          setSelectedChannels={setSelectedChannels}
          handleSaveAreaChannels={handleSaveAreaChannels}
          channelsSaving={channelsSaving}
          inHouseChannels={inHouseChannels}
          editingInHouseChannel={editingInHouseChannel}
          setEditingInHouseChannel={setEditingInHouseChannel}
          handleDeleteInHouseChannel={handleDeleteInHouseChannel}
          handleSaveInHouseChannel={handleSaveInHouseChannel}
        />
      )}
    </div>
  );
};

export default SettingsPage;