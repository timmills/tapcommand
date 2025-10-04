import { useState, useEffect } from 'react';
import axios from 'axios';

interface SamsungTV {
  ip: string;
  name: string;
  model: string;
  mac: string;
  protocol: string;
  status: 'online' | 'offline';
}

export const NetworkControllersPage = () => {
  const [tvs, setTvs] = useState<SamsungTV[]>([]);
  const [discovering, setDiscovering] = useState(false);
  const [commandInProgress, setCommandInProgress] = useState<string | null>(null);

  const handleDiscover = async () => {
    setDiscovering(true);
    try {
      const response = await axios.get('http://localhost:8000/api/network-tv/discover', {
        timeout: 5000 // 5 second timeout
      });
      setTvs(response.data);
    } catch (error) {
      console.error('Discovery failed:', error);
      // Show error but don't clear TVs
    } finally {
      setDiscovering(false);
    }
  };

  const handleCommand = async (ip: string, command: string) => {
    setCommandInProgress(`${ip}-${command}`);
    try {
      await axios.post('http://localhost:8000/api/network-tv/command', {
        ip,
        command,
      });
    } catch (error) {
      console.error('Command failed:', error);
    } finally {
      setCommandInProgress(null);
    }
  };

  // Auto-discover on mount
  useEffect(() => {
    handleDiscover();
  }, []);

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Network Controllers</h2>
          <p className="text-sm text-slate-500">
            Discover and control Samsung TVs via network. {tvs.filter(tv => tv.status === 'online').length} of {tvs.length} TVs online.
          </p>
        </div>
        <button
          type="button"
          onClick={handleDiscover}
          disabled={discovering}
          className="inline-flex items-center gap-1 rounded-md bg-brand-500 px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
        >
          {discovering ? 'Discovering...' : 'Discover TVs'}
        </button>
      </header>

      <div className="space-y-4">
        {tvs.map((tv) => (
          <div key={tv.ip} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
                  <svg className="h-6 w-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-medium text-slate-900">{tv.name}</h3>
                  <p className="text-sm text-slate-500">{tv.model} • {tv.ip}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {tv.status === 'online' ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-1 text-xs font-medium text-green-700">
                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 8 8">
                      <circle cx="4" cy="4" r="3" />
                    </svg>
                    Online
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-1 text-xs font-medium text-red-700">
                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 8 8">
                      <circle cx="4" cy="4" r="3" />
                    </svg>
                    Offline
                  </span>
                )}
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700">
                  {tv.protocol === 'samsung_legacy' ? 'Legacy' : 'Modern'}
                </span>
              </div>
            </div>

            {tv.status === 'online' && (
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => handleCommand(tv.ip, 'power')}
                  disabled={commandInProgress === `${tv.ip}-power`}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Power
                </button>
                <button
                  onClick={() => handleCommand(tv.ip, 'volume_up')}
                  disabled={commandInProgress === `${tv.ip}-volume_up`}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                  </svg>
                  Volume +
                </button>
                <button
                  onClick={() => handleCommand(tv.ip, 'volume_down')}
                  disabled={commandInProgress === `${tv.ip}-volume_down`}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                  </svg>
                  Volume -
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="font-medium text-slate-900">Setup Instructions</h3>
        <p className="mt-1 text-sm text-slate-500">
          Enable network control on your Samsung TVs
        </p>
        <div className="mt-3 space-y-2 text-sm text-slate-600">
          <p className="font-medium">On each TV (using physical remote):</p>
          <ol className="list-decimal list-inside space-y-1 pl-2">
            <li>Press <strong>Home</strong> button</li>
            <li>Navigate to <strong>Settings</strong> → <strong>General</strong> → <strong>External Device Manager</strong></li>
            <li>Enable <strong>Device Connect Manager</strong></li>
            <li>Go to <strong>General</strong> → <strong>Network</strong> → <strong>Expert Settings</strong></li>
            <li>Enable <strong>"Power On with Mobile"</strong></li>
          </ol>
          <p className="text-xs text-slate-500 pt-2">
            See <code className="rounded bg-slate-100 px-1 py-0.5">/docs/SAMSUNG_TV_SETUP_GUIDE.md</code> for detailed instructions
          </p>
        </div>
      </div>
    </section>
  );
};
