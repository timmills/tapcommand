import React from 'react';
import type { ChannelTab, AreaInfo, Channel, InHouseChannelCreate, InHouseChannelUpdate } from '../types';

interface ChannelsTabProps {
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

const ChannelsTab: React.FC<ChannelsTabProps> = ({
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
  const [platformFilter, setPlatformFilter] = React.useState<string | null>(null);

  // Filter channels based on platform
  // Ensure selectedChannels is always an array
  const safeSelectedChannels = Array.isArray(selectedChannels) ? selectedChannels : [];

  const filteredChannels = React.useMemo(() => {
    if (!platformFilter) return channels;
    return channels.filter(channel => {
      if (platformFilter === 'terrestrial') {
        return !channel.platform || channel.platform === 'terrestrial' || channel.platform.toLowerCase().includes('free');
      }
      return channel.platform?.toLowerCase() === platformFilter.toLowerCase();
    });
  }, [channels, platformFilter]);
  return (
    <div className="card">
      <div className="card-header">
        <h3>📺 Channel Management</h3>
        <p>Configure local Australian TV channels for your area</p>
      </div>

      {/* Channel Sub-Tabs */}
      <div className="channel-tabs">
        <button
          className={`channel-tab ${channelTab === 'area-selection' ? 'active' : ''}`}
          onClick={() => setChannelTab('area-selection')}
        >
          📍 Area Selection
        </button>
        <button
          className={`channel-tab ${channelTab === 'channel-list' ? 'active' : ''}`}
          onClick={() => setChannelTab('channel-list')}
        >
          📋 Channel List
        </button>
        <button
          className={`channel-tab ${channelTab === 'inhouse-channels' ? 'active' : ''}`}
          onClick={() => setChannelTab('inhouse-channels')}
        >
          🏠 InHouse Channels
        </button>
      </div>

      {/* Area Selection Tab */}
      {channelTab === 'area-selection' && (
        <div className="channels-content">
          <div className="form-group">
            <label>Select Your Area:</label>
            <select
              value={selectedAreaName ?? ''}
              onChange={(e) => setSelectedAreaName(e.target.value || null)}
              disabled={channelsLoading}
            >
              <option value="">Choose your area...</option>
              {areas.map((area) => (
                <option key={area.area_name || area.name} value={area.area_name || area.name}>
                  {area.area_name || area.name} ({area.total_channels || area.channel_count} channels)
                </option>
              ))}
            </select>
          </div>

          {selectedAreaName && (
            <div style={{ marginTop: '16px', padding: '12px', background: '#f0f9ff', border: '1px solid #0ea5e9', borderRadius: '8px' }}>
              <p><strong>Selected:</strong> {selectedAreaName}</p>
              <p>This will load the standard TV channels for your area. You can customize the channel list in the Channel List tab.</p>
            </div>
          )}
        </div>
      )}

      {/* Channel List Tab */}
      {channelTab === 'channel-list' && (
        <div className="channels-content">
          {channelsLoading ? (
            <div className="loading">Loading channels...</div>
          ) : channels.length === 0 ? (
            <div className="empty-state">
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>📺</div>
              <h3>No Channels Available</h3>
              <p>Please select an area first in the Area Selection tab to load channels.</p>
            </div>
          ) : (
            <>
              <div className="channel-selection">
                <div className="channel-selection-header">
                  <h4>Available Channels ({filteredChannels.length}{channels.length !== filteredChannels.length ? ` of ${channels.length}` : ''})</h4>
                  <div className="channel-filters">
                    <button
                      className={`filter-button ${!platformFilter ? 'active' : ''}`}
                      onClick={() => setPlatformFilter(null)}
                    >
                      📺 All Channels
                    </button>
                    <button
                      className={`filter-button ${platformFilter === 'terrestrial' ? 'active' : ''}`}
                      onClick={() => setPlatformFilter('terrestrial')}
                    >
                      📡 Free-to-Air
                    </button>
                    {channels.some(c => c.platform?.toLowerCase().includes('foxtel')) && (
                      <button
                        className={`filter-button ${platformFilter === 'foxtel' ? 'active' : ''}`}
                        onClick={() => setPlatformFilter('foxtel')}
                      >
                        📺 Foxtel
                      </button>
                    )}
                  </div>
                  <div className="channel-actions">
                    <button
                      className="button secondary"
                      onClick={() => {
                        const filteredChannelIds = filteredChannels.map(c => c.id.toString());
                        const allFilteredSelected = filteredChannelIds.every(id => safeSelectedChannels.includes(id));

                        if (allFilteredSelected) {
                          // Deselect all filtered channels
                          setSelectedChannels(safeSelectedChannels.filter(id => !filteredChannelIds.includes(id)));
                        } else {
                          // Select all filtered channels
                          const newSelection = [...new Set([...safeSelectedChannels, ...filteredChannelIds])];
                          setSelectedChannels(newSelection);
                        }
                      }}
                    >
                      {filteredChannels.length > 0 && filteredChannels.every(c => safeSelectedChannels.includes(c.id.toString()))
                        ? 'Deselect All'
                        : 'Select All'}
                    </button>
                  </div>
                </div>

                <div className="channels-grid">
                  {filteredChannels.map((channel) => (
                    <div key={channel.id} className={`channel-card ${safeSelectedChannels.includes(channel.id.toString()) ? 'selected' : ''}`}>
                      <div className="channel-card-header">
                        <div className="channel-logo-container">
                          {channel.logo_url || channel.local_logo_path ? (
                            <img
                              src={
                                channel.local_logo_path
                                  ? `http://localhost:8000/${channel.local_logo_path}`
                                  : channel.logo_url
                              }
                              alt={channel.channel_name}
                              className="channel-logo"
                              onError={(e) => {
                                // Try fallback to remote URL if local fails
                                if (channel.local_logo_path && channel.logo_url && e.currentTarget.src.includes('localhost')) {
                                  e.currentTarget.src = channel.logo_url;
                                } else {
                                  e.currentTarget.style.display = 'none';
                                }
                              }}
                            />
                          ) : (
                            <div className="channel-logo-placeholder">
                              {channel.channel_name.charAt(0).toUpperCase()}
                            </div>
                          )}
                        </div>
                        <div className="channel-number-badge">
                          {channel.lcn || channel.foxtel_number || 'N/A'}
                        </div>
                        <label className="channel-checkbox-wrapper">
                          <input
                            type="checkbox"
                            checked={safeSelectedChannels.includes(channel.id.toString())}
                            onChange={(e) => {
                              const channelId = channel.id.toString();
                              if (e.target.checked) {
                                setSelectedChannels([...safeSelectedChannels, channelId]);
                              } else {
                                setSelectedChannels(safeSelectedChannels.filter(id => id !== channelId));
                              }
                            }}
                            className="channel-checkbox-input"
                          />
                          <span className="checkmark"></span>
                        </label>
                      </div>
                      <div className="channel-card-body">
                        <div className="channel-name">{channel.channel_name}</div>
                        <div className="channel-network">{channel.broadcaster_network}</div>
                        {channel.platform && (
                          <div className="channel-platform">{channel.platform}</div>
                        )}
                        {channel.programming_content && (
                          <div className="channel-content">{channel.programming_content}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="form-actions">
                  <button
                    className="button"
                    onClick={handleSaveAreaChannels}
                    disabled={channelsSaving || safeSelectedChannels.length === 0}
                  >
                    {channelsSaving ? 'Saving...' : `Save ${safeSelectedChannels.length} Selected Channels`}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* InHouse Channels Tab */}
      {channelTab === 'inhouse-channels' && (
        <div className="channels-content">
          <div className="inhouse-channels-header">
            <h4>Custom InHouse Channels</h4>
            <button
              className="button"
              onClick={() => setEditingInHouseChannel({
                channel_number: '',
                channel_name: '',
                broadcaster_network: 'InHouse',
                platform: 'terrestrial'
              })}
            >
              ➕ Add InHouse Channel
            </button>
          </div>

          {inHouseChannels.length === 0 ? (
            <div className="empty-state">
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>🏠</div>
              <h3>No InHouse Channels</h3>
              <p>Create custom channels for internal content, streaming services, or special programming.</p>
            </div>
          ) : (
            <div className="inhouse-channels-list">
              {inHouseChannels.map((channel) => (
                <div key={channel.id} className="inhouse-channel-item">
                  <div className="channel-details">
                    <div className="channel-number">{channel.lcn || channel.foxtel_number || 'N/A'}</div>
                    <div className="channel-info">
                      <div className="channel-name">{channel.channel_name}</div>
                      <div className="channel-network">{channel.broadcaster_network}</div>
                    </div>
                  </div>
                  <div className="channel-actions">
                    <button
                      className="button secondary"
                      onClick={() => setEditingInHouseChannel({
                        id: channel.id,
                        channel_number: channel.lcn || channel.foxtel_number || '',
                        channel_name: channel.channel_name,
                        broadcaster_network: channel.broadcaster_network,
                        platform: channel.platform
                      })}
                    >
                      ✏️ Edit
                    </button>
                    <button
                      className="button danger"
                      onClick={() => handleDeleteInHouseChannel(channel.id!)}
                    >
                      🗑️ Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* InHouse Channel Edit Modal */}
          {editingInHouseChannel && (
            <div className="modal-overlay" onClick={() => setEditingInHouseChannel(null)}>
              <div className="modal-content" onClick={e => e.stopPropagation()}>
                <form onSubmit={handleSaveInHouseChannel}>
                  <div className="modal-header">
                    <h3>{editingInHouseChannel.id ? 'Edit' : 'Create'} InHouse Channel</h3>
                  </div>

                  <div className="modal-body">
                    <div className="form-group">
                      <label>Channel Number</label>
                      <input
                        type="text"
                        value={editingInHouseChannel.channel_number}
                        onChange={(e) => setEditingInHouseChannel({
                          ...editingInHouseChannel,
                          channel_number: e.target.value
                        })}
                        placeholder="e.g., 501, HDMI1, Netflix"
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label>Channel Name</label>
                      <input
                        type="text"
                        value={editingInHouseChannel.channel_name}
                        onChange={(e) => setEditingInHouseChannel({
                          ...editingInHouseChannel,
                          channel_name: e.target.value
                        })}
                        placeholder="e.g., House Content, Main Screen"
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label>Broadcaster/Network</label>
                      <input
                        type="text"
                        value={editingInHouseChannel.broadcaster_network}
                        onChange={(e) => setEditingInHouseChannel({
                          ...editingInHouseChannel,
                          broadcaster_network: e.target.value
                        })}
                        placeholder="e.g., InHouse, Custom, Streaming"
                        required
                      />
                    </div>
                  </div>

                  <div className="modal-footer">
                    <button
                      type="button"
                      className="button secondary"
                      onClick={() => setEditingInHouseChannel(null)}
                    >
                      Cancel
                    </button>
                    <button type="submit" className="button">
                      Save Changes
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ChannelsTab;