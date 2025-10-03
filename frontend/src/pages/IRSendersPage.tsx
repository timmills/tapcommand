import React from 'react';
import type { DiscoveredDevice, ManagedDevice } from '../types';

interface IRSendersPageProps {
  discoveredDevices: DiscoveredDevice[];
  managedDevices: ManagedDevice[];
  editingDevice: ManagedDevice | null;
  setEditingDevice: (device: ManagedDevice | null) => void;
  setShowIRConfig: (device: ManagedDevice | null) => void;
  addToManagement: (hostname: string) => Promise<void>;
  forgetDevice: (hostname: string) => Promise<void>;
  removeFromManagement: (deviceId: number) => Promise<void>;
  syncDeviceStatus: (deviceId: number) => Promise<void>;
}

const IRSendersPage: React.FC<IRSendersPageProps> = ({
  discoveredDevices,
  managedDevices,
  editingDevice,
  setEditingDevice,
  setShowIRConfig,
  addToManagement,
  forgetDevice,
  removeFromManagement,
  syncDeviceStatus
}) => {
  const unmanaged = discoveredDevices.filter(device => !device.is_managed);

  return (
    <div className="ir-senders-page">
      <div className="page-header">
        <h2>📡 IR Senders</h2>
        <p>Manage IR blaster devices and their connected devices</p>
      </div>

      {/* Discovered Devices */}
      {unmanaged.length > 0 && (
        <div className="discovered-section">
          <h2>📡 Discovered Devices ({unmanaged.length})</h2>
          <p style={{ color: '#92400e', marginBottom: '16px' }}>
            These devices were found on the network but haven't been added to management yet.
          </p>

          <div className="device-grid">
            {unmanaged.map((device) => (
              <div key={device.hostname} className="device-card">
                <div className="device-header">
                  <div>
                    <div className="device-title">{device.hostname}</div>
                    <div className="device-subtitle">{device.friendly_name}</div>
                  </div>
                  <span className={`device-badge ${device.device_type || 'universal'}`}>
                    {device.device_type || 'universal'}
                  </span>
                </div>

                <div className="device-info">
                  <div>💻 IP: {device.ip_address}</div>
                  <div>🔧 MAC: {device.mac_address}</div>
                  {device.firmware_version && (
                    <div>📦 Version: {device.firmware_version}</div>
                  )}
                  <div>🕒 Discovered: {new Date(device.first_discovered).toLocaleString()}</div>
                </div>

                <div className="button-group">
                  <button
                    className="button"
                    onClick={() => addToManagement(device.hostname)}
                  >
                    ➕ Add IR Sender
                  </button>
                  <button
                    className="button secondary"
                    onClick={() => forgetDevice(device.hostname)}
                  >
                    🗑️ Forget Sender
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Managed Devices */}
      <div className="card">
        <h2>📡 IR Senders ({managedDevices.length})</h2>

        {managedDevices.length === 0 ? (
          <div className="empty-state">
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📱</div>
            <h3>No IR Senders</h3>
            <p>Add IR blasters from the discovered section above to start managing connected devices.</p>
          </div>
        ) : (
          <div className="device-grid">
            {managedDevices.map((device) => {
              const discovery = discoveredDevices.find(d => d.hostname === device.hostname);
              const properties = discovery?.discovery_properties;
              const capabilities = properties?.capabilities;
              const discoveryDump = properties
                ? JSON.stringify(properties, null, 2)
                : null;

              return (
                <div key={device.id} className="device-card">
                  <div className="device-header">
                    <div>
                      <div className="device-title">
                        {device.device_name || device.hostname}
                        <button
                          className="edit-icon"
                          onClick={() => setEditingDevice(device)}
                          title="Edit device name"
                        >
                          ✏️
                        </button>
                      </div>
                      <div className="device-subtitle">{device.hostname}</div>
                    </div>
                    <span className={`device-badge ${device.device_type}`}>
                      {device.device_type}
                    </span>
                  </div>

                  {(device.venue_name || device.location) && (
                    <div style={{ margin: '8px 0', fontSize: '14px', color: '#64748b' }}>
                      📍 {device.venue_name} {device.location && `• ${device.location}`}
                    </div>
                  )}

                  <div className="status-indicator">
                    <div className={`status-dot ${device.is_online ? 'online' : 'offline'}`} />
                    <span style={{ fontSize: '14px' }}>
                      {device.is_online ? '🟢 Online' : '🔴 Offline'} - {device.current_ip_address}
                    </span>
                  </div>

                  <div className="device-info">
                    <div>🔌 IR Ports: {device.total_ir_ports}</div>
                    <div>🕒 Last seen: {new Date(device.last_seen).toLocaleString()}</div>
                  </div>

                  {/* IR Ports Configuration */}
                  <div className="ir-ports-section">
                    <div className="section-header">
                      <h4>📺 Connected Devices</h4>
                      <button
                        className="button secondary"
                        onClick={() => setShowIRConfig(device)}
                      >
                        ⚙️ Configure Ports
                      </button>
                    </div>

                    <div className="ir-ports-grid">
                      {Array.from({ length: device.total_ir_ports }, (_, i) => {
                        const port = device.ir_ports?.find(p => p.port_number === i + 1);
                        return (
                          <div key={i + 1} className={`ir-port ${port?.is_active ? 'active' : 'inactive'}`}>
                            <div className="port-number">{port?.port_id || `Port ${i + 1}`}</div>
                            <div className="port-device">
                              {port?.connected_device_name || 'Not configured'}
                            </div>
                            {port?.device_number && (
                              <div className="port-detail">Device {port.device_number}</div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="button-group">
                    <button
                      className="button secondary"
                      onClick={() => syncDeviceStatus(device.id)}
                    >
                      🔄 Sync Status
                    </button>
                    <button
                      className="button danger"
                      onClick={() => removeFromManagement(device.id)}
                    >
                      🗑️ Remove
                    </button>
                  </div>

                  {capabilities && (
                    <div style={{ marginTop: '16px', padding: '12px', background: '#f8fafc', border: '1px solid #dbeafe', borderRadius: '8px' }}>
                      <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '8px', color: '#1d4ed8' }}>
                        Supported Capabilities
                      </div>
                      {capabilities.brands && capabilities.brands.length > 0 && (
                        <div style={{ marginBottom: '8px' }}>
                          <div style={{ fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>Brands</div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {capabilities.brands.map((brand) => (
                              <span
                                key={brand}
                                style={{
                                  background: '#bfdbfe',
                                  color: '#1e3a8a',
                                  padding: '2px 8px',
                                  borderRadius: '999px',
                                  fontSize: '12px',
                                  fontWeight: 500
                                }}
                              >
                                {brand}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {capabilities.commands && capabilities.commands.length > 0 && (
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>Functions</div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {capabilities.commands.map((cmd) => (
                              <span
                                key={cmd}
                                style={{
                                  background: '#e0f2fe',
                                  color: '#0369a1',
                                  padding: '2px 8px',
                                  borderRadius: '6px',
                                  fontSize: '12px',
                                  fontWeight: 500,
                                  textTransform: 'capitalize'
                                }}
                              >
                                {cmd.replace(/_/g, ' ')}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {!capabilities && properties && (
                    <div style={{ marginTop: '16px', padding: '12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                      <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '8px', color: '#475569' }}>
                        Device Snapshot
                      </div>
                      <div style={{ display: 'grid', gap: '6px', fontSize: '13px', color: '#334155' }}>
                        {(properties as any)?.project_name && (
                          <div><strong>Project:</strong> {String((properties as any).project_name)}</div>
                        )}
                        {(properties as any)?.project_version && (
                          <div><strong>Firmware:</strong> {String((properties as any).project_version)}</div>
                        )}
                        {(properties as any)?.version && (
                          <div><strong>ESPHome:</strong> {String((properties as any).version)}</div>
                        )}
                        {(properties as any)?.friendly_name && (
                          <div><strong>Reported Name:</strong> {String((properties as any).friendly_name)}</div>
                        )}
                        {(properties as any)?.board && (
                          <div><strong>Board:</strong> {String((properties as any).board)}</div>
                        )}
                        {(properties as any)?.mac && (
                          <div><strong>MAC:</strong> {String((properties as any).mac)}</div>
                        )}
                        {!(properties as any)?.project_name && !(properties as any)?.project_version && !(properties as any)?.version && (
                          <div>No capability payload available yet.</div>
                        )}
                      </div>
                      <div style={{ marginTop: '8px', fontSize: '12px', color: '#64748b' }}>
                        Trigger "Sync Status" or re-adopt to capture supported brands/functions.
                      </div>
                    </div>
                  )}

                  {discoveryDump && (
                    <div style={{ marginTop: '12px' }}>
                      <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px', color: '#334155' }}>
                        Discovered Metadata
                      </div>
                      <pre
                        style={{
                          background: '#f1f5f9',
                          border: '1px solid #cbd5f5',
                          borderRadius: '8px',
                          padding: '12px',
                          fontSize: '12px',
                          overflowX: 'auto',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word'
                        }}
                      >{discoveryDump}</pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default IRSendersPage;