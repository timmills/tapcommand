-- Migration: Add Hybrid IR + Network Support to Virtual Devices
-- Date: 2025-10-07
-- Purpose: Enable virtual devices to link IR fallback for power-on and cache status

-- Add hybrid control fields
ALTER TABLE virtual_devices ADD COLUMN fallback_ir_controller TEXT;
ALTER TABLE virtual_devices ADD COLUMN fallback_ir_port INTEGER;
ALTER TABLE virtual_devices ADD COLUMN power_on_method TEXT DEFAULT 'network';
ALTER TABLE virtual_devices ADD COLUMN control_strategy TEXT DEFAULT 'network_only';

-- Add status cache fields
ALTER TABLE virtual_devices ADD COLUMN cached_power_state TEXT;
ALTER TABLE virtual_devices ADD COLUMN cached_volume_level INTEGER;
ALTER TABLE virtual_devices ADD COLUMN cached_mute_status BOOLEAN;
ALTER TABLE virtual_devices ADD COLUMN cached_current_input TEXT;
ALTER TABLE virtual_devices ADD COLUMN cached_current_app TEXT;

-- Add status metadata fields
ALTER TABLE virtual_devices ADD COLUMN last_status_poll TIMESTAMP;
ALTER TABLE virtual_devices ADD COLUMN status_poll_failures INTEGER DEFAULT 0;
ALTER TABLE virtual_devices ADD COLUMN status_available BOOLEAN DEFAULT 0;

-- Set status_available based on protocol (brands that support status queries)
UPDATE virtual_devices SET status_available = 1
WHERE protocol IN ('lg_webos', 'hisense_vidaa', 'sony_bravia', 'vizio_smartcast', 'philips_jointspace', 'roku');

-- Samsung Legacy doesn't support status
UPDATE virtual_devices SET status_available = 0
WHERE protocol = 'samsung_legacy';

-- For Samsung Legacy TVs, recommend IR power-on
UPDATE virtual_devices SET power_on_method = 'ir'
WHERE protocol = 'samsung_legacy';
