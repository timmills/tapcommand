import React, { useState } from 'react';
import type { IRPort, IRPortConfigUpdate, DeviceTag } from '../types';

interface IRPortConfigProps {
  portNumber: number;
  port?: IRPort;
  onDataChange?: (portNumber: number, data: IRPortConfigUpdate) => void;
  availableTags?: DeviceTag[];
}

const IRPortConfig: React.FC<IRPortConfigProps> = ({
  portNumber,
  port,
  onDataChange,
  availableTags
}) => {
  const [deviceName, setDeviceName] = useState<string>(port?.connected_device_name || '');
  const [isActive, setIsActive] = useState<boolean>(port?.is_active ?? true);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>(port?.tag_ids || []);
  const [defaultChannel, setDefaultChannel] = useState<string>(port?.default_channel || '');

  const deviceInputId = `port-${portNumber}-device`;
  const channelInputId = `port-${portNumber}-channel`;
  const activeToggleId = `port-${portNumber}-active`;

  // Notify parent of data changes
  React.useEffect(() => {
    if (onDataChange) {
      onDataChange(portNumber, {
        port_number: portNumber,
        connected_device_name: deviceName || null,
        is_active: isActive,
        cable_length: port?.cable_length ?? null,
        installation_notes: port?.installation_notes ?? null,
        tag_ids: selectedTagIds.length > 0 ? selectedTagIds : null,
        default_channel: defaultChannel || null,
        device_number: port?.device_number ?? null
      });
    }
  }, [deviceName, isActive, selectedTagIds, defaultChannel, portNumber, onDataChange, port]);

  return (
    <div className={`ir-config-port ${isActive ? 'is-active' : 'is-inactive'}`}>
      <div className="ir-port-header">
        <div className="ir-port-heading">
          <span className="ir-port-number">Port {portNumber}</span>
          {port?.port_id ? <span className="ir-port-id">{port.port_id}</span> : null}
        </div>
        <label className="checkbox-label inline" htmlFor={activeToggleId}>
          <input
            id={activeToggleId}
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          <span className={`status-pill ${isActive ? 'active' : 'inactive'}`}>
            {isActive ? 'Active' : 'Disabled'}
          </span>
        </label>
      </div>

      <div className="form-group">
        <label htmlFor={deviceInputId}>Connected Device</label>
        <input
          id={deviceInputId}
          value={deviceName}
          onChange={(e) => setDeviceName(e.target.value)}
          placeholder="e.g., Main TV, Set-top Box 1"
        />
      </div>

      <div className="form-group">
        <label htmlFor={channelInputId}>Default Channel</label>
        <input
          id={channelInputId}
          value={defaultChannel}
          onChange={(e) => setDefaultChannel(e.target.value)}
          placeholder="e.g., 501, BBC1, Sky Sports"
        />
      </div>

      {/* Tag Selection */}
      {availableTags && availableTags.length > 0 && (
        <div className="form-group">
          <label>Tags:</label>
          <div className="tags-selection">
            {selectedTagIds.length > 0 && (
              <div className="selected-tags">
                {selectedTagIds.map(tagId => {
                  const tag = availableTags.find(t => t.id === tagId);
                  return tag ? (
                    <span
                      key={tagId}
                      className="tag-chip"
                      style={{ backgroundColor: tag.color || '#6b7280' }}
                      onClick={() => setSelectedTagIds(prev => prev.filter(id => id !== tagId))}
                    >
                      {tag.name} ✕
                    </span>
                  ) : null;
                })}
              </div>
            )}
            <select
              value=""
              onChange={(e) => {
                const tagId = parseInt(e.target.value);
                if (tagId && !selectedTagIds.includes(tagId)) {
                  setSelectedTagIds(prev => [...prev, tagId]);
                }
              }}
            >
              <option value="">Add tag...</option>
              {availableTags
                .filter(tag => !selectedTagIds.includes(tag.id))
                .map(tag => (
                  <option key={tag.id} value={tag.id}>
                    {tag.name}
                  </option>
                ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
};

export default IRPortConfig;