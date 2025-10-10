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

  // When using nginx proxy, just use same origin (no port needed)
  // Nginx will proxy /api requests to backend on port 8000
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  const port = window.location.port;

  // If accessing on port 80 (default http) or 443 (https), use relative URL
  if (!port || port === '80' || port === '443') {
    return `${protocol}//${hostname}`;
  }

  // Otherwise use the same port (e.g., dev server on 5173)
  return `${protocol}//${hostname}:${port}`;
};

export const API_BASE_URL = getApiBaseUrl();
export const WS_BASE_URL = ensureEnv('VITE_WS_BASE_URL', API_BASE_URL.replace('http', 'ws'));

// Log the detected URLs for debugging
console.log('[TapCommand] API Configuration:', {
  hostname: window.location.hostname,
  API_BASE_URL,
  WS_BASE_URL,
  mode: import.meta.env.VITE_API_BASE_URL === 'auto' ? 'auto-detect' : 'manual'
});
