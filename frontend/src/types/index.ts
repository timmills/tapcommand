// Navigation types
export type Page = 'devices' | 'ir-senders' | 'yaml-builder' | 'settings';
export type SettingsTab = 'yaml-templates' | 'tag-management' | 'channels';
export type ChannelTab = 'area-selection' | 'channel-list' | 'inhouse-channels';

// Discovery and Capability types
export interface DiscoveryCapabilities {
  device_id?: string;
  project?: string;
  firmware_version?: string;
  brands?: string[];
  commands?: string[];
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface DiscoveryProperties extends Record<string, unknown> {
  capabilities?: DiscoveryCapabilities;
}

export interface DiscoveredDevice {
  id: number;
  hostname: string;
  mac_address: string;
  ip_address: string;
  friendly_name?: string;
  device_type?: string;
  firmware_version?: string;
  discovery_properties?: DiscoveryProperties;
  is_managed: boolean;
  first_discovered: string;
  last_seen: string;
}

// Device Management types
export interface DeviceTag {
  id: number;
  name: string;
  color?: string;
  description?: string;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface IRPort {
  id?: number;
  port_number: number;
  port_id?: string;
  gpio_pin?: string;
  connected_device_name?: string;
  is_active: boolean;
  cable_length?: string;
  installation_notes?: string;
  tag_ids?: number[];
  default_channel?: string;
  device_number?: number;
}

export interface IRPortConfigUpdate {
  port_number: number;
  connected_device_name: string | null;
  is_active: boolean;
  cable_length: string | null;
  installation_notes: string | null;
  tag_ids: number[] | null;
  default_channel: string | null;
  device_number: number | null;
}

export interface ManagedDevice {
  id: number;
  hostname: string;
  mac_address: string;
  current_ip_address: string;
  device_name?: string;
  venue_name?: string;
  location?: string;
  device_type: string;
  is_online: boolean;
  last_seen: string;
  total_ir_ports: number;
  ir_ports: IRPort[];
}

export interface ManagedDeviceUpdateRequest {
  device_name?: string | null;
  api_key?: string | null;
  venue_name?: string | null;
  location?: string | null;
  notes?: string | null;
  ir_ports?: IRPortConfigUpdate[];
}

// Connected device interface for the new homepage
export interface ConnectedDevice {
  id: string;
  name: string;
  type: string;
  brand?: string;
  model?: string;
  location: string;
  ir_sender: string;
  port: string;
  status: 'online' | 'offline' | 'unknown';
  last_used?: string;
  channels?: string[];
  tags?: DeviceTag[];
}

// Channel Management types
export interface Channel {
  id: number;
  platform: string;
  broadcaster_network: string;
  channel_name: string;
  lcn?: string;
  foxtel_number?: string;
  broadcast_hours?: string;
  format?: string;
  programming_content?: string;
  availability?: string;
  logo_url?: string;
  notes?: string;
  internal: boolean;
  disabled: boolean;
  local_logo_path?: string;
}

export interface ChannelStats {
  total_channels: number;
  enabled_channels: number;
  disabled_channels: number;
  platforms: string[];
  broadcasters: string[];
}

export interface AreaInfo {
  name: string;
  full_name: string;
  type: string;
  state?: string;
  cities: string[];
  channel_count: number;
}

export interface AreasResponse {
  areas: AreaInfo[];
}

export interface InHouseChannelCreate {
  channel_name: string;
  channel_number: string;
  description?: string;
  logo_url?: string;
  disabled?: boolean;
}

export interface InHouseChannelUpdate {
  channel_name?: string;
  channel_number?: string;
  description?: string;
  logo_url?: string;
  disabled?: boolean;
}

// Template types
export interface TemplateLibraryItem {
  id: number;
  name: string;
  device_category: string;
  brand: string;
  model?: string;
  source_path: string;
  espNative: boolean;
}

export interface RawTemplateLibrary {
  id: number;
  name: string;
  device_category: string;
  brand: string;
  model?: string | null;
  source_path: string;
  esp_native?: boolean;
}

export interface RawTemplateBrand {
  name: string;
  libraries: RawTemplateLibrary[];
}

export interface RawTemplateCategory {
  name: string;
  brands: RawTemplateBrand[];
}

export interface TemplateBrand {
  name: string;
  libraries: TemplateLibraryItem[];
}

export interface TemplateCategory {
  name: string;
  brands: TemplateBrand[];
}

export interface SelectedLibrary {
  id: number;
  name: string;
  device_category: string;
  brand: string;
  model?: string;
  source_path: string;
  espNative: boolean;
}

export interface TemplateSummary {
  id: number;
  name: string;
  board: string;
  description?: string | null;
  version: string;
  revision: number;
}

export interface ESPTemplateResponse extends TemplateSummary {
  template_yaml: string;
}