export interface ManagedDevice {
  id: number;
  hostname: string;
  mac_address: string;
  current_ip_address: string;
  device_name: string | null;
  api_key: string | null;
  venue_name: string | null;
  location: string | null;
  total_ir_ports: number;
  firmware_version: string | null;
  device_type: string;
  is_online: boolean;
  last_seen: string;
  last_ip_address: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  ir_ports: IRPort[];
  capabilities?: Record<string, unknown> | null;
}

export interface IRPort {
  id: number;
  port_number: number;
  port_id: string | null;
  gpio_pin: string | null;
  connected_device_name: string | null;
  is_active: boolean;
  cable_length: string | null;
  installation_notes: string | null;
  tag_ids: number[] | null;
  default_channel: string | null;
  device_number: number | null;
  created_at: string;
  updated_at: string;
}

export interface DeviceTag {
  id: number;
  name: string;
  color: string | null;
  description: string | null;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChannelOption {
  id: number;
  channel_name: string;
  lcn: string | null;
  foxtel_number: string | null;
  platform: string | null;
  broadcaster_network: string | null;
}

export interface ChannelLocationSummary {
  availability: string;
  display_name: string;
  total_channels: number;
  enabled_channels: number;
}

export interface ChannelLocationListResponse {
  selected: string | null;
  locations: ChannelLocationSummary[];
}

export interface ChannelRecord {
  id: number;
  platform: string;
  broadcaster_network: string | null;
  channel_name: string;
  lcn: string | null;
  foxtel_number: string | null;
  availability: string | null;
  disabled: boolean;
  is_recommended: boolean;
}

export interface ChannelGroupsResponse {
  availability: string | null;
  recommended: ChannelRecord[];
  other_fta: ChannelRecord[];
  foxtel: ChannelRecord[];
  inhouse: ChannelRecord[];
}

export interface ChannelVisibilityUpdatePayload {
  enable_ids?: number[];
  disable_ids?: number[];
}

export interface DiscoveredDevice {
  id?: number;
  hostname: string;
  mac_address: string;
  ip_address: string;
  friendly_name: string | null;
  device_type: string | null;
  firmware_version: string | null;
  discovery_properties: Record<string, unknown> | null;
  is_managed: boolean;
  first_discovered: string;
  last_seen: string;
  created_at?: string;
  updated_at?: string;
}

export interface TemplateSummary {
  id: number;
  name: string;
  board: string;
  description: string | null;
  version: string;
  revision: number;
}

export interface TemplateDetail extends TemplateSummary {
  template_yaml: string;
}

export interface TemplateLibraryItem {
  id: number;
  name: string;
  device_category: string;
  brand: string;
  model?: string | null;
  source_path: string;
  esp_native: boolean;
}

export interface TemplateBrand {
  name: string;
  libraries: TemplateLibraryItem[];
}

export interface TemplateCategory {
  name: string;
  brands: TemplateBrand[];
}

export interface SelectedDevicePreview {
  library_id: number;
  display_name: string;
  device_category: string;
  brand: string;
  model: string | null;
  source_path: string;
}

export interface TemplatePreviewResponse {
  yaml: string;
  char_count: number;
  selected_devices: SelectedDevicePreview[];
}

export interface TemplatePreviewAssignment {
  port_number: number;
  library_id: number | null;
}

export interface TemplatePreviewRequest {
  template_id: number;
  assignments: TemplatePreviewAssignment[];
  include_comments: boolean;
}

export interface FirmwareCompileResponse {
  success: boolean;
  log: string;
  binary_path: string | null;
  binary_filename: string | null;
}

export interface IRLibraryFiltersResponse {
  brands: string[];
  device_categories: string[];
  protocols: string[];
}

export interface IRLibrarySummary {
  id: number;
  name: string;
  brand: string;
  device_category: string;
  model: string | null;
  esp_native: boolean;
  hidden: boolean;
  source: string;
  description?: string | null;
  import_status?: string | null;
  command_count: number;
  protocols: string[];
  updated_at?: string | null;
}

export interface IRLibraryListResponse {
  items: IRLibrarySummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface IRCommandSummary {
  id: number;
  name: string;
  protocol: string;
  category?: string | null;
  signal_data: Record<string, unknown>;
  created_at?: string | null;
}

export interface IRCommandListResponse {
  items: IRCommandSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface IRCommandLibrarySummary {
  id: number;
  name: string;
  brand: string;
  device_category: string;
  esp_native: boolean;
}

export interface IRCommandWithLibrarySummary {
  id: number;
  name: string;
  protocol: string;
  category?: string | null;
  signal_data: Record<string, unknown>;
  created_at?: string | null;
  library: IRCommandLibrarySummary;
}

export interface IRCommandCatalogueResponse {
  items: IRCommandWithLibrarySummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface Channel {
  id: number;
  platform: string;
  broadcaster_network: string;
  channel_name: string;
  lcn: string | null;
  foxtel_number: string | null;
  broadcast_hours: string | null;
  format: string | null;
  programming_content: string | null;
  availability: string | null;
  logo_url: string | null;
  notes: string | null;
  internal: boolean;
  disabled: boolean;
  local_logo_path: string | null;
}

export interface ApiError {
  status: number;
  message: string;
  details?: unknown;
}
