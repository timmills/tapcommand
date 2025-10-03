// Core types for the SmartVenue IR Control System

export interface IRPort {
  id: number;
  port_number: number;
  port_id: string;
  gpio_pin: string;
  connected_device_name: string | null;
  is_active: boolean;
  cable_length: string | null;
  installation_notes: string | null;
  tag_ids: number[] | null;
  default_channel: string | null;
  device_number: number;
}

export interface Device {
  id: number;
  hostname: string;
  mac_address: string;
  current_ip_address: string;
  device_name: string;
  api_key: string;
  venue_name: string;
  location: string;
  total_ir_ports: number;
  firmware_version: string;
  device_type: string;
  is_online: boolean;
  last_seen: string;
  last_ip_address: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
  ir_ports: IRPort[];
}

export interface DiscoveredDevice {
  id: number;
  hostname: string;
  mac_address: string;
  ip_address: string;
  friendly_name: string;
  device_type: string;
  firmware_version: string;
  discovery_properties: Record<string, any>;
  is_managed: boolean;
  first_discovered: string;
  last_seen: string;
}

export interface ManagedDevice extends Device {}

export interface ConnectedDevice {
  id: string;
  name: string;
  status: 'online' | 'offline';
}

export interface DeviceTag {
  id: number;
  name: string;
  color: string;
  description?: string;
  usage_count?: number;
  created_at: string;
  updated_at: string;
}

export interface IRPortConfigUpdate {
  connected_device_name?: string;
  is_active?: boolean;
  cable_length?: string;
  installation_notes?: string;
  tag_ids?: number[];
  default_channel?: string;
  device_number?: number;
}

export interface Channel {
  id: number;
  channel_name: string;
  channel_number: string;
  lcn?: string;
  foxtel_number?: string;
  broadcaster_network?: string;
  logo_url?: string;
  local_logo_path?: string;
  platform: 'free-to-air' | 'foxtel';
  disabled: boolean;
  availability?: string[];
  description?: string;
}

export interface ChannelStats {
  total_channels: number;
  enabled_channels: number;
  free_to_air_channels: number;
  foxtel_channels: number;
}

export interface AreaInfo {
  area_name: string;
  total_channels: number;
  enabled_channels: number;
}

export interface InHouseChannelCreate {
  channel_name: string;
  channel_number: string;
  description?: string;
  logo_url?: string;
  disabled?: boolean;
}

export interface InHouseChannelUpdate extends Partial<InHouseChannelCreate> {
  id?: number;
}

export interface TemplateLibraryItem {
  id: string;
  name: string;
  manufacturer: string;
  model: string;
  category: string;
  description?: string;
  ir_codes: Record<string, string>;
}

export interface RawTemplateCategory {
  [key: string]: TemplateLibraryItem[];
}

export interface TemplateCategory {
  category: string;
  items: TemplateLibraryItem[];
}

export interface SelectedLibrary {
  port_number: number;
  library_id: string;
  device_name?: string;
}

export interface ManagedDeviceUpdateRequest {
  device_name?: string;
  api_key?: string;
  venue_name?: string;
  location?: string;
  notes?: string;
}

export interface TemplateSummary {
  id: number;
  name: string;
  board: string;
  description?: string;
  version: string;
  revision: number;
  created_at: string;
  updated_at: string;
}

export interface ESPTemplateResponse {
  yaml_content: string;
  substitutions: Record<string, any>;
  project_name: string;
  friendly_name: string;
}

// UI State types
export type Page = 'devices' | 'ir-senders' | 'yaml-builder' | 'settings';
export type SettingsTab = 'channels' | 'templates' | 'tags';
export type ChannelTab = 'area-selection' | 'channel-list' | 'inhouse-channels';