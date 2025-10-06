const ensureEnv = (key: string, fallback?: string): string => {
  const value = import.meta.env[key as keyof ImportMetaEnv];
  if (typeof value === 'string' && value.length > 0) {
    return value;
  }
  if (fallback !== undefined) {
    return fallback;
  }
  console.warn(`Environment variable ${key} is not set; falling back to empty string.`);
  return '';
};

/**
 * Automatically detect the best API URL based on the current hostname
 * - If accessing via Tailscale (100.x), use Tailscale backend
 * - If accessing via local network (192.168.x), use local backend
 * - Otherwise use window.location to match frontend host
 */
const getApiBaseUrl = (): string => {
  // Check if explicitly set in env
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && envUrl !== 'auto') {
    return envUrl;
  }

  // Auto-detect based on current hostname
  const hostname = window.location.hostname;

  // Tailscale network (100.x.x.x)
  if (hostname.startsWith('100.')) {
    return 'http://100.93.158.19:8000';
  }

  // Local network (192.168.x.x)
  if (hostname.startsWith('192.168.')) {
    return 'http://192.168.101.153:8000';
  }

  // Localhost
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }

  // Default: use same host as frontend with port 8000
  const protocol = window.location.protocol;
  return `${protocol}//${hostname}:8000`;
};

export const API_BASE_URL = getApiBaseUrl();
export const WS_BASE_URL = ensureEnv('VITE_WS_BASE_URL', API_BASE_URL.replace('http', 'ws'));

// Log the detected URLs for debugging
console.log('[SmartVenue] API Configuration:', {
  hostname: window.location.hostname,
  API_BASE_URL,
  WS_BASE_URL,
  mode: import.meta.env.VITE_API_BASE_URL === 'auto' ? 'auto-detect' : 'manual'
});
