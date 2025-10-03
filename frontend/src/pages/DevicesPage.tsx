import React from 'react';
import type { ConnectedDevice, DeviceTag } from '../types';

interface DevicesPageProps {
  connectedDevices: ConnectedDevice[];
  filters: {
    name?: string;
    type?: string;
    location?: string;
    status?: string;
    tag?: string;
  };
  deviceTags: DeviceTag[];
  selectedDevices: Set<string>;
  expandedDevice: string | null;
  setCurrentPage: (page: 'devices' | 'ir-senders' | 'yaml-builder' | 'settings') => void;
  handleFilter: (key: string, value: string) => void;
  setSelectedDevices: (devices: Set<string>) => void;
  setExpandedDevice: (deviceId: string | null) => void;
}

const DevicesPage: React.FC<DevicesPageProps> = ({
  connectedDevices,
  filters,
  deviceTags,
  selectedDevices,
  expandedDevice,
  setCurrentPage,
  handleFilter,
  setSelectedDevices,
  setExpandedDevice
}) => {
  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedDevices(new Set(connectedDevices.map(d => d.id)));
    } else {
      setSelectedDevices(new Set());
    }
  };

  const handleDeviceSelect = (deviceId: string, checked: boolean) => {
    const newSelected = new Set(selectedDevices);
    if (checked) {
      newSelected.add(deviceId);
    } else {
      newSelected.delete(deviceId);
    }
    setSelectedDevices(newSelected);
  };

  const getStatusIcon = (status: 'online' | 'offline' | 'unknown') => {
    switch (status) {
      case 'online': return '🟢';
      case 'offline': return '🔴';
      default: return '⚪';
    }
  };

  return (
    <div className="modern-device-page">
      <div className="page-header">
        <h2>📺 Connected Devices</h2>
        <p>Manage and control all devices connected through IR senders</p>
      </div>

      {connectedDevices.length === 0 ? (
        <div className="empty-state">
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📱</div>
          <h3>No Connected Devices</h3>
          <p>Configure IR senders first, then add devices to their ports.</p>
          <button
            className="button"
            onClick={() => setCurrentPage('ir-senders')}
          >
            🔧 Setup IR Senders
          </button>
        </div>
      ) : (
        <>
          {/* Filters */}
          <div className="filter-bar">
            <input
              type="text"
              placeholder="🔍 Filter by name..."
              value={filters.name || ''}
              onChange={(e) => handleFilter('name', e.target.value)}
            />
            <select
              value={filters.type || ''}
              onChange={(e) => handleFilter('type', e.target.value)}
            >
              <option value="">All Types</option>
              {Array.from(new Set(connectedDevices.map(d => d.type))).map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
            <select
              value={filters.location || ''}
              onChange={(e) => handleFilter('location', e.target.value)}
            >
              <option value="">All Locations</option>
              {Array.from(new Set(connectedDevices.map(d => d.location))).map(location => (
                <option key={location} value={location}>{location}</option>
              ))}
            </select>
            <select
              value={filters.status || ''}
              onChange={(e) => handleFilter('status', e.target.value)}
            >
              <option value="">All Status</option>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
            </select>
            {deviceTags.length > 0 && (
              <select
                value={filters.tag || ''}
                onChange={(e) => handleFilter('tag', e.target.value)}
              >
                <option value="">All Tags</option>
                {deviceTags.map(tag => (
                  <option key={tag.id} value={tag.name}>{tag.name}</option>
                ))}
              </select>
            )}
          </div>

          {/* Bulk Actions */}
          {selectedDevices.size > 0 && (
            <div className="bulk-selection-bar">
              <div className="bulk-actions">
                <button className="button" disabled>
                  🎮 Send Command (Coming Soon)
                </button>
                <button className="button secondary" disabled>
                  ⚡ Power All
                </button>
                <button className="button secondary" disabled>
                  🔇 Mute All
                </button>
              </div>
            </div>
          )}

          {/* Device Table */}
          <div className="device-table-container">
            <table className="device-table">
              <thead>
                <tr>
                  <th style={{ width: '50px' }}>
                    <input
                      type="checkbox"
                      checked={selectedDevices.size === connectedDevices.length && connectedDevices.length > 0}
                      onChange={handleSelectAll}
                    />
                  </th>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Brand</th>
                  <th>Model</th>
                  <th>Location</th>
                  <th>IR Sender</th>
                  <th>Port</th>
                  <th>Status</th>
                  <th>Last Used</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {connectedDevices.map(device => (
                  <React.Fragment key={device.id}>
                    <tr className={`device-row ${expandedDevice === device.id ? 'expanded' : ''}`}>
                      <td>
                        <input
                          type="checkbox"
                          checked={selectedDevices.has(device.id)}
                          onChange={(e) => handleDeviceSelect(device.id, e.target.checked)}
                        />
                      </td>
                      <td>
                        <div className="device-name-cell">
                          <strong>{device.name}</strong>
                          {device.tags && device.tags.length > 0 && (
                            <div className="device-tags">
                              {device.tags.map(tag => (
                                <span
                                  key={tag.id}
                                  className="tag"
                                  style={{ backgroundColor: tag.color || '#3498db' }}
                                >
                                  {tag.name}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>
                      <td>{device.type}</td>
                      <td>{device.brand || '-'}</td>
                      <td>{device.model || '-'}</td>
                      <td>{device.location}</td>
                      <td>{device.ir_sender}</td>
                      <td>{device.port}</td>
                      <td>
                        <span className={`status ${device.status}`}>
                          {getStatusIcon(device.status)} {device.status}
                        </span>
                      </td>
                      <td>{device.last_used || 'Never'}</td>
                      <td>
                        <button
                          className="expand-button"
                          onClick={() => setExpandedDevice(expandedDevice === device.id ? null : device.id)}
                        >
                          {expandedDevice === device.id ? '▼' : '▶'}
                        </button>
                      </td>
                    </tr>
                    {expandedDevice === device.id && (
                      <tr className="device-details">
                        <td colSpan={11}>
                          <div className="device-details-content">
                            <h4>📋 Device Actions</h4>
                            <div className="action-grid">
                              <button className="action-button power" disabled={device.status !== 'online'}>
                                ⚡ Power On/Off
                              </button>
                              <button className="action-button volume" disabled={device.status !== 'online'}>
                                🔊 Volume
                              </button>
                              <button className="action-button channel" disabled={device.status !== 'online'}>
                                📺 Channels
                              </button>
                              <button className="action-button input" disabled={device.status !== 'online'}>
                                🔄 Input Source
                              </button>
                            </div>
                            {device.channels && device.channels.length > 0 && (
                              <div className="channel-info">
                                <h5>📡 Available Channels:</h5>
                                <div className="channel-list">
                                  {device.channels.map(channel => (
                                    <span key={channel} className="channel-tag">{channel}</span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};

export default DevicesPage;