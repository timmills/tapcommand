import { useState } from 'react';

interface AmplifierInfo {
  name: string;
  protocol: string;
  port: string;
  auth: string;
  zoneSupport: string;
  setupSteps: string[];
  setupTime: string;
  notes: string[];
  icon: string;
  implementationStatus: 'implemented' | 'planned' | 'future';
}

const amplifierData: Record<string, AmplifierInfo> = {
  'bosch_aes70': {
    name: 'Bosch Praesensa',
    protocol: 'bosch_aes70 (AES70/OCA)',
    port: '65000',
    auth: 'None (open protocol)',
    zoneSupport: '✅ Auto-Discovery',
    setupTime: '2 minutes',
    icon: '🔊',
    implementationStatus: 'implemented',
    setupSteps: [
      'Ensure Praesensa is connected to network',
      'Enter IP address in discovery or Audio page',
      'System auto-discovers all zones via AES70 role map',
      'Zones appear as controllable devices instantly'
    ],
    notes: [
      '✅ Industry-standard AES70/OCA protocol',
      '✅ No authentication required',
      '✅ Auto-discovers all zones via role map',
      '✅ Real-time volume control (0-100%)',
      '✅ Mute/unmute support',
      '✅ dB range auto-detected',
      '⚠️ Zones always "on" (no power control)',
      '📖 Open standard - no licensing fees'
    ]
  },
  'bosch_plena_matrix': {
    name: 'Bosch Plena Matrix',
    protocol: 'bosch_plena_matrix (UDP)',
    port: '12128/12129',
    auth: 'None (optional PASS command)',
    zoneSupport: '✅ Manual (4 zones)',
    setupTime: '2 minutes',
    icon: '📡',
    implementationStatus: 'implemented',
    setupSteps: [
      'Ensure PLM-4P220/120 is connected to network',
      'Select "Bosch Plena Matrix" protocol on Audio page',
      'Enter IP address and number of zones (default 4)',
      'Zones are created based on amplifier channels'
    ],
    notes: [
      '✅ Proprietary UDP API (well-documented)',
      '✅ No authentication required by default',
      '✅ Real-time volume control (0-100%, -80 to +10 dB)',
      '✅ Mute/unmute support',
      '✅ Supports PLM-4P220, PLM-4P120 series',
      '✅ 4 zones (standard) or 2 zones (bridged mode)',
      '⚠️ Manual zone configuration (no auto-discovery)',
      '📖 Commercial audio amplifier for PA systems'
    ]
  },
  'bosch_omneo': {
    name: 'Bosch OMNEO Network',
    protocol: 'bosch_omneo',
    port: '65000',
    auth: 'None',
    zoneSupport: '✅ Multi-zone',
    setupTime: '3 minutes',
    icon: '🔊',
    implementationStatus: 'planned',
    setupSteps: [
      'Same as AES70 (OMNEO is built on AES70)',
      'May include additional OMNEO-specific discovery',
      'Auto-detects all zones and devices',
      'Compatible with other OMNEO devices'
    ],
    notes: [
      '🚧 Planned - same as AES70',
      '✅ OMNEO = AES70 + AES67 audio transport',
      '✅ Compatible with Praesensa',
      '⚠️ Use AES70 protocol for now'
    ]
  },
  'qsc_qsys': {
    name: 'QSC Q-SYS',
    protocol: 'qsc_qsys',
    port: '1710 (QRC) or 1702 (Core)',
    auth: 'Optional PIN',
    zoneSupport: '✅ Named Controls',
    setupTime: '5 minutes',
    icon: '🔊',
    implementationStatus: 'planned',
    setupSteps: [
      'Enable External Control in Q-SYS Designer',
      'Create Named Controls for each zone',
      'Note control names (e.g., "Lobby.Volume")',
      'Optional: Set PIN for security'
    ],
    notes: [
      '🚧 Planned for Phase 2',
      '✅ QRC protocol (JSON over TCP)',
      '✅ Very flexible - control any Core parameter',
      '⚠️ Requires Named Controls setup in Designer',
      '⚠️ PIN authentication if enabled'
    ]
  },
  'biamp_tesira': {
    name: 'Biamp Tesira',
    protocol: 'biamp_tesira',
    port: '23 (Telnet)',
    auth: 'Username/Password',
    zoneSupport: '✅ Instance Tags',
    setupTime: '6 minutes',
    icon: '🔊',
    implementationStatus: 'planned',
    setupSteps: [
      'Enable Telnet control in Tesira software',
      'Note instance tags for zones (e.g., "LevelControl1")',
      'Configure username/password if required',
      'Map instance tags to friendly zone names'
    ],
    notes: [
      '🚧 Planned for Phase 2',
      '✅ Telnet-based TTP protocol',
      '✅ Very mature and stable',
      '⚠️ Requires instance tag mapping',
      '⚠️ Authentication usually required',
      '⚠️ Text-based protocol (more verbose)'
    ]
  },
  'extron': {
    name: 'Extron (Pro Series DSPs)',
    protocol: 'extron_sis',
    port: '23 (Telnet)',
    auth: 'Optional password',
    zoneSupport: '⚠️ Manual mapping',
    setupTime: '7 minutes',
    icon: '🔊',
    implementationStatus: 'future',
    setupSteps: [
      'Enable SIS (Simple Instruction Set) control',
      'Map output channels to zones manually',
      'Configure volume group numbers',
      'Optional: Set connection password'
    ],
    notes: [
      '🔮 Future consideration',
      '✅ SIS protocol well-documented',
      '⚠️ No auto-discovery',
      '⚠️ Manual channel/zone mapping required',
      '⚠️ Different models have different command sets'
    ]
  },
  'dante': {
    name: 'Dante-Enabled Devices',
    protocol: 'dante_avio',
    port: 'Various',
    auth: 'Device-specific',
    zoneSupport: '⚠️ Device-dependent',
    setupTime: 'Varies',
    icon: '🔊',
    implementationStatus: 'future',
    setupSteps: [
      'Dante is audio transport, not control protocol',
      'Would require device-specific control protocol',
      'May support AES70 if device implements it',
      'Check manufacturer documentation'
    ],
    notes: [
      '🔮 Future - device-dependent',
      'ℹ️ Dante = audio routing, not control',
      'ℹ️ Use device\'s control protocol (may be AES70)',
      '⚠️ No universal Dante control API'
    ]
  }
};

interface AmplifierInfoCardsProps {
  onSelectAmplifier?: (protocol: string) => void;
}

export const AmplifierInfoCards = ({ onSelectAmplifier: _onSelectAmplifier }: AmplifierInfoCardsProps) => {
  const [expandedAmplifier, setExpandedAmplifier] = useState<string | null>(null);
  const [showComparison, setShowComparison] = useState(false);
  const [filterStatus, setFilterStatus] = useState<'all' | 'implemented' | 'planned' | 'future'>('all');

  const toggleAmplifier = (protocol: string) => {
    setExpandedAmplifier(expandedAmplifier === protocol ? null : protocol);
  };

  const filteredData = Object.entries(amplifierData).filter(([_, info]) => {
    if (filterStatus === 'all') return true;
    return info.implementationStatus === filterStatus;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'implemented':
        return <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">✓ Available Now</span>;
      case 'planned':
        return <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">🚧 Planned</span>;
      case 'future':
        return <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">🔮 Future</span>;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-4">
      {/* Header with comparison toggle and filters */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-900">Supported Audio Amplifiers</h3>
        <div className="flex items-center gap-3">
          {/* Filter Tabs */}
          <div className="flex gap-1 text-xs">
            <button
              onClick={() => setFilterStatus('all')}
              className={`rounded px-2 py-1 transition ${
                filterStatus === 'all' ? 'bg-brand-100 text-brand-700' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterStatus('implemented')}
              className={`rounded px-2 py-1 transition ${
                filterStatus === 'implemented' ? 'bg-green-100 text-green-700' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              Available
            </button>
            <button
              onClick={() => setFilterStatus('planned')}
              className={`rounded px-2 py-1 transition ${
                filterStatus === 'planned' ? 'bg-blue-100 text-blue-700' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              Planned
            </button>
          </div>
          <button
            onClick={() => setShowComparison(!showComparison)}
            className="text-xs text-brand-600 hover:text-brand-700 underline"
          >
            {showComparison ? 'Hide' : 'Show'} Comparison
          </button>
        </div>
      </div>

      {/* Comparison Table */}
      {showComparison && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-slate-700">Brand</th>
                <th className="px-3 py-2 text-left font-medium text-slate-700">Protocol</th>
                <th className="px-3 py-2 text-left font-medium text-slate-700">Auth</th>
                <th className="px-3 py-2 text-left font-medium text-slate-700">Zone Discovery</th>
                <th className="px-3 py-2 text-left font-medium text-slate-700">Setup Time</th>
                <th className="px-3 py-2 text-left font-medium text-slate-700">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {Object.values(amplifierData).map((amp) => (
                <tr key={amp.protocol} className="hover:bg-slate-50">
                  <td className="px-3 py-2 font-medium text-slate-900">{amp.name}</td>
                  <td className="px-3 py-2 text-slate-600 font-mono text-[10px]">{amp.protocol}</td>
                  <td className="px-3 py-2 text-slate-600">{amp.auth}</td>
                  <td className="px-3 py-2">{amp.zoneSupport}</td>
                  <td className="px-3 py-2 text-slate-600">{amp.setupTime}</td>
                  <td className="px-3 py-2">{getStatusBadge(amp.implementationStatus)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Amplifier Cards Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filteredData.map(([protocol, info]) => (
          <div
            key={protocol}
            className={`rounded-lg border transition-all ${
              expandedAmplifier === protocol
                ? 'border-brand-300 bg-brand-50 ring-2 ring-brand-200'
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            {/* Card Header */}
            <button
              onClick={() => toggleAmplifier(protocol)}
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
                <div className="flex items-center gap-2">
                  {getStatusBadge(info.implementationStatus)}
                  <svg
                    className={`h-5 w-5 text-slate-400 transition-transform ${
                      expandedAmplifier === protocol ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </button>

            {/* Expanded Details */}
            {expandedAmplifier === protocol && (
              <div className="border-t border-slate-200 px-4 py-3 space-y-3">
                {/* Quick Info */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-600">Auth:</span>
                    <span className="ml-1 font-medium text-slate-900">{info.auth}</span>
                  </div>
                  <div>
                    <span className="text-slate-600">Zones:</span>
                    <span className="ml-1 font-medium">{info.zoneSupport}</span>
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

      {filteredData.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-8 text-center">
          <p className="text-sm text-slate-600">No amplifiers match the selected filter</p>
        </div>
      )}

      {/* Help Text */}
      <div className="rounded-lg border border-green-200 bg-green-50 p-3">
        <p className="text-xs text-green-900">
          <strong>🎉 Ready to Use:</strong> <strong>Bosch Praesensa</strong> (AES70) and <strong>Bosch Plena Matrix</strong> (UDP) are fully implemented!
          Select the appropriate protocol when adding your amplifier.
        </p>
      </div>

      <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
        <p className="text-xs text-blue-900">
          <strong>💡 About AES70/OCA:</strong> AES70 (Open Control Architecture) is an industry-standard protocol
          for professional audio control. It's completely open (no licensing fees), supports auto-discovery,
          and is used by Bosch, d&b audiotechnik, and other professional audio brands.
        </p>
      </div>
    </div>
  );
};
