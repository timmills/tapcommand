import { useState } from 'react';

interface BrandInfo {
  name: string;
  protocol: string;
  port: string;
  auth: string;
  powerOn: string;
  setupSteps: string[];
  setupTime: string;
  notes: string[];
  icon: string;
}

const brandData: Record<string, BrandInfo> = {
  'samsung_websocket': {
    name: 'Samsung Modern (2016+)',
    protocol: 'samsung_websocket',
    port: '8001/8002',
    auth: 'Auth token (auto)',
    powerOn: '✅ WOL (10-20s)',
    setupTime: '2 minutes',
    icon: '📺',
    setupSteps: [
      'Click "Adopt" in TapCommand',
      'WATCH THE TV SCREEN - permission dialog appears',
      'Press "Allow" within 30 seconds',
      'Token saved automatically - no more prompts!'
    ],
    notes: [
      '✅ One-time permission during adoption',
      '✅ Token saved permanently',
      '✅ Fast response, full control',
      '⚠️ Must accept within 30 seconds',
      '⚠️ If denied, must reset TV device list'
    ]
  },
  'samsung_legacy': {
    name: 'Samsung Legacy (2011-2015)',
    protocol: 'samsung_legacy',
    port: '55000',
    auth: 'None',
    powerOn: '✗ IR Only',
    setupTime: '2 minutes',
    icon: '📺',
    setupSteps: [
      'Press MENU on TV remote',
      'Navigate to Network → AllShare Settings',
      'Enable AllShare or External Device Control',
      'No pairing required - works immediately'
    ],
    notes: [
      '✅ No authentication required',
      '✅ Fast response (< 500ms)',
      '⚠️ Cannot power on when TV is OFF',
      '⚠️ No status feedback'
    ]
  },
  'hisense_vidaa': {
    name: 'Hisense (VIDAA OS)',
    protocol: 'hisense_vidaa',
    port: '36669',
    auth: 'Default credentials',
    powerOn: '⚠️ WOL (Unreliable)',
    setupTime: '3 minutes',
    icon: '📺',
    setupSteps: [
      'Network control usually enabled by default',
      'Some models show authorization prompt on TV screen',
      'Accept connection when prompted',
      'May require SSL (auto-detected)'
    ],
    notes: [
      '✅ Can query TV state (volume, sources)',
      '✅ MQTT protocol',
      '⚠️ WOL unreliable - use WOL + IR fallback',
      '⚠️ Deep sleep mode stops network'
    ]
  },
  'lg_webos': {
    name: 'LG webOS (2014+)',
    protocol: 'lg_webos',
    port: '3000/3001',
    auth: 'Pairing key',
    powerOn: '⚠️ WOL (Usually works)',
    setupTime: '5 minutes',
    icon: '📺',
    setupSteps: [
      'Connect from TapCommand',
      'TV displays 6-digit pairing code on screen',
      'Accept pairing within 30 seconds',
      'Enable "Mobile TV On" for WOL support'
    ],
    notes: [
      '✅ Rich API with status feedback',
      '✅ WOL usually works well',
      '⚠️ Cannot power ON via protocol (only OFF)',
      '⚠️ One-time pairing required'
    ]
  },
  'sony_bravia': {
    name: 'Sony Bravia (2013+)',
    protocol: 'sony_bravia',
    port: '80 (or 50001)',
    auth: 'PSK or PIN',
    powerOn: '⚠️ WOL (Varies)',
    setupTime: '4 minutes',
    icon: '📺',
    setupSteps: [
      'Settings → Network → IP Control',
      'Enable Authentication',
      'Set Pre-Shared Key (PSK) - e.g., "0000"',
      'Store PSK in TapCommand credentials'
    ],
    notes: [
      '✅ IRCC (IR over IP) - very reliable',
      '✅ No pairing prompt (PSK pre-configured)',
      '⚠️ PSK required',
      '⚠️ WOL varies by model'
    ]
  },
  'roku': {
    name: 'Roku (All Models)',
    protocol: 'roku',
    port: '8060',
    auth: 'None',
    powerOn: '✅ Network PowerOn',
    setupTime: '1 minute',
    icon: '📺',
    setupSteps: [
      'Already enabled by default on all Roku devices',
      'No setup required!',
      'Works immediately out of the box'
    ],
    notes: [
      '✅ Best network TV for simplicity',
      '✅ No authentication required',
      '✅ Can power ON via network (discrete PowerOn)',
      '✅ Fast and reliable'
    ]
  },
  'vizio_smartcast': {
    name: 'Vizio SmartCast (2016+)',
    protocol: 'vizio_smartcast',
    port: '7345 or 9000',
    auth: 'Auth token',
    powerOn: '⚠️ Sometimes',
    setupTime: '6 minutes',
    icon: '📺',
    setupSteps: [
      'Install pyvizio: pip install pyvizio',
      'Run pairing: pyvizio --ip=TV_IP pair',
      'TV displays 4-digit PIN code on screen',
      'Enter PIN and save auth token'
    ],
    notes: [
      '⚠️ Pairing required before control works',
      '⚠️ Token invalidated by factory reset',
      '⚠️ HTTPS with self-signed cert',
      '⚠️ Power-on reliability varies'
    ]
  },
  'philips_jointspace': {
    name: 'Philips Android TV (2015+)',
    protocol: 'philips_jointspace',
    port: '1926 (or 1925)',
    auth: 'Optional digest auth',
    powerOn: '⚠️ Varies',
    setupTime: '3-5 minutes',
    icon: '📺',
    setupSteps: [
      'Usually enabled by default on Android TVs',
      'Some models require username/password (digest auth)',
      'Port 1926 for Android TVs (HTTPS)',
      'Port 1925 for older models (HTTP)'
    ],
    notes: [
      '✅ JointSpace API v6',
      '✅ Auto-detects port 1925 vs 1926',
      '⚠️ Port and authentication vary by model',
      '⚠️ Power-on varies by model'
    ]
  }
};

interface BrandInfoCardsProps {
  onSelectBrand?: (protocol: string) => void;
}

export const BrandInfoCards = ({ onSelectBrand }: BrandInfoCardsProps) => {
  const [expandedBrand, setExpandedBrand] = useState<string | null>(null);
  const [showComparison, setShowComparison] = useState(false);

  const toggleBrand = (protocol: string) => {
    setExpandedBrand(expandedBrand === protocol ? null : protocol);
  };

  return (
    <div className="space-y-4">
      {/* Header with comparison toggle */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-900">Supported TV Brands</h3>
        <button
          onClick={() => setShowComparison(!showComparison)}
          className="text-xs text-brand-600 hover:text-brand-700 underline"
        >
          {showComparison ? 'Hide' : 'Show'} Comparison
        </button>
      </div>

      {/* Comparison Table */}
      {showComparison && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-slate-700">Brand</th>
                <th className="px-3 py-2 text-left font-medium text-slate-700">Auth</th>
                <th className="px-3 py-2 text-left font-medium text-slate-700">Power-On</th>
                <th className="px-3 py-2 text-left font-medium text-slate-700">Setup Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {Object.values(brandData).map((brand) => (
                <tr key={brand.protocol} className="hover:bg-slate-50">
                  <td className="px-3 py-2 font-medium text-slate-900">{brand.name}</td>
                  <td className="px-3 py-2 text-slate-600">{brand.auth}</td>
                  <td className="px-3 py-2">{brand.powerOn}</td>
                  <td className="px-3 py-2 text-slate-600">{brand.setupTime}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Brand Cards Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(brandData).map(([protocol, info]) => (
          <div
            key={protocol}
            className={`rounded-lg border transition-all ${
              expandedBrand === protocol
                ? 'border-brand-300 bg-brand-50 ring-2 ring-brand-200'
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            {/* Card Header */}
            <button
              onClick={() => toggleBrand(protocol)}
              className="w-full px-4 py-3 text-left"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{info.icon}</span>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900">{info.name}</h4>
                    <p className="text-xs text-slate-500">Port {info.port}</p>
                  </div>
                </div>
                <svg
                  className={`h-5 w-5 text-slate-400 transition-transform ${
                    expandedBrand === protocol ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </button>

            {/* Expanded Details */}
            {expandedBrand === protocol && (
              <div className="border-t border-slate-200 px-4 py-3 space-y-3">
                {/* Quick Info */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-600">Auth:</span>
                    <span className="ml-1 font-medium text-slate-900">{info.auth}</span>
                  </div>
                  <div>
                    <span className="text-slate-600">Power-On:</span>
                    <span className="ml-1 font-medium">{info.powerOn}</span>
                  </div>
                </div>

                {/* Setup Steps */}
                <div>
                  <p className="text-xs font-medium text-slate-700 mb-1">Setup Steps:</p>
                  <ol className="list-decimal list-inside space-y-1 text-xs text-slate-600">
                    {info.setupSteps.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ol>
                </div>

                {/* Notes */}
                <div>
                  <p className="text-xs font-medium text-slate-700 mb-1">Notes:</p>
                  <ul className="space-y-1 text-xs">
                    {info.notes.map((note, idx) => (
                      <li key={idx} className="text-slate-600">{note}</li>
                    ))}
                  </ul>
                </div>

                {/* Setup Time */}
                <div className="pt-2 border-t border-slate-200">
                  <p className="text-xs text-slate-500">
                    <span className="font-medium">Estimated setup time:</span> {info.setupTime}
                  </p>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Help Text */}
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
        <p className="text-xs text-blue-900">
          <strong>💡 Tip:</strong> Click on any brand card above to see detailed setup instructions.
          For the easiest setup, choose <strong>Roku</strong> (no configuration needed).
        </p>
      </div>
    </div>
  );
};
