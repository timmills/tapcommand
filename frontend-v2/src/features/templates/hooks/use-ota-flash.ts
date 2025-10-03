import { useCallback, useRef, useState } from 'react';
import { API_BASE_URL } from '@/lib/env';

export type OTAStatus = 'idle' | 'running' | 'success' | 'error' | 'cancelled';

export interface OTAResult {
  hostname: string;
  success: boolean;
  previousFirmware?: string | null;
  newFirmware?: string | null;
  resolvedIp?: string | null;
  capabilities?: Record<string, unknown> | null;
  metadataAvailable?: boolean;
  error?: string | null;
}

export interface OTAStartOptions {
  binaryPath: string;
  hostnames: string[];
  otaPort?: number;
  rebootWaitSeconds?: number;
}

export const useOtaFlash = () => {
  const [status, setStatus] = useState<OTAStatus>('idle');
  const [logLines, setLogLines] = useState<string[]>([]);
  const [progressByHost, setProgressByHost] = useState<Record<string, number>>({});
  const [results, setResults] = useState<Record<string, OTAResult>>({});
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const resultsRef = useRef<Record<string, OTAResult>>({});

  const reset = useCallback(() => {
    if (controllerRef.current) {
      controllerRef.current.abort();
      controllerRef.current = null;
    }
    setStatus('idle');
    setLogLines([]);
    setProgressByHost({});
    setResults({});
    resultsRef.current = {};
    setError(null);
  }, []);

  const appendLog = useCallback((hostname: string | undefined, message: string) => {
    if (!message) return;
    const prefix = hostname ? `[${hostname}] ` : '';
    setLogLines((prev) => [...prev, `${prefix}${message}`]);
  }, []);

  const startOTA = useCallback(async ({
    binaryPath,
    hostnames,
    otaPort,
    rebootWaitSeconds,
  }: OTAStartOptions) => {
    if (!binaryPath || hostnames.length === 0) return;

    if (controllerRef.current) {
      controllerRef.current.abort();
    }

    setStatus('running');
    setLogLines([]);
    setProgressByHost({});
    setResults({});
    resultsRef.current = {};
    setError(null);

    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/templates/ota-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          binary_path: binaryPath,
          hostnames,
          ota_port: otaPort,
          reboot_wait_seconds: rebootWaitSeconds,
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`OTA request failed (${response.status})`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      const completedHosts = new Set<string>();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let eventBoundary = buffer.indexOf('\n\n');
        while (eventBoundary !== -1) {
          const rawEvent = buffer.slice(0, eventBoundary).trim();
          buffer = buffer.slice(eventBoundary + 2);
          eventBoundary = buffer.indexOf('\n\n');

          if (!rawEvent.startsWith('data:')) {
            continue;
          }

          const payloadText = rawEvent.replace(/^data:\s*/, '');
          if (!payloadText) continue;

          try {
            const payload = JSON.parse(payloadText);
            switch (payload.type) {
              case 'device_start':
                appendLog(payload.hostname, `Starting OTA for ${payload.binary}`);
                setProgressByHost((prev) => ({ ...prev, [payload.hostname]: 0 }));
                break;
              case 'device_info':
                appendLog(
                  payload.hostname,
                  payload.stage === 'before'
                    ? `Current firmware: ${payload.firmware ?? 'unknown'}`
                    : `New firmware detected: ${payload.firmware ?? 'unknown'}`,
                );
                break;
              case 'log':
                appendLog(payload.hostname, payload.message ?? '');
                break;
              case 'progress':
                setProgressByHost((prev) => ({ ...prev, [payload.hostname]: Number(payload.value ?? 0) }));
                break;
              case 'keepalive':
                break;
              case 'device_complete': {
                completedHosts.add(payload.hostname);
                const result: OTAResult = {
                  hostname: payload.hostname,
                  success: Boolean(payload.success),
                  previousFirmware: payload.previous_firmware ?? null,
                  newFirmware: payload.new_firmware ?? null,
                  resolvedIp: payload.resolved_ip ?? null,
                  capabilities: payload.capabilities ?? null,
                  metadataAvailable: payload.metadata_available,
                  error: payload.error ?? null,
                };
                setResults((prev) => {
                  const next = { ...prev, [payload.hostname]: result };
                  resultsRef.current = next;
                  return next;
                });
                appendLog(
                  payload.hostname,
                  payload.success
                    ? 'OTA completed successfully.'
                    : payload.error ?? 'OTA failed.',
                );
                break;
              }
              default:
                break;
            }
          } catch (err) {
            console.error('Failed to parse OTA event', err, payloadText);
          }
        }
      }

      if (controller.signal.aborted) {
        setStatus('cancelled');
        appendLog(undefined, 'OTA cancelled.');
      } else if (hostnames.every((hostname) => completedHosts.has(hostname))) {
        const snapshot = resultsRef.current;
        const anyFailures = hostnames.some((hostname) => !snapshot[hostname]?.success);
        setStatus(anyFailures ? 'error' : 'success');
        if (!anyFailures) {
          appendLog(undefined, 'OTA completed for all devices.');
        }
      } else {
        setStatus('error');
        appendLog(undefined, 'OTA stream ended unexpectedly.');
      }
    } catch (err) {
      if (controller.signal.aborted) {
        setStatus('cancelled');
        appendLog(undefined, 'OTA cancelled.');
      } else {
        const message = err instanceof Error ? err.message : 'OTA failed';
        setStatus('error');
        setError(message);
        appendLog(undefined, message);
      }
    } finally {
      controllerRef.current = null;
    }
  }, [appendLog]);

  const cancelOTA = useCallback(() => {
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
  }, []);

  return {
    status,
    logLines,
    progressByHost,
    results,
    error,
    startOTA,
    cancelOTA,
    reset,
  };
};
