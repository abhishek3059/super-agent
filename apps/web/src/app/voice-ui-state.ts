const STATUS_LABELS: Record<string, string> = {
  stopped: 'Disconnected',
  connecting: 'Connecting',
  listening: 'Listening',
  speaking: 'Local echo',
  muted: 'Muted',
  error: 'Needs attention',
};

const PIPELINE_SUMMARIES: Record<string, string> = {
  stopped: 'Ready for a local session',
  connecting: 'Authenticating on loopback',
  listening: 'Microphone streaming locally',
  speaking: 'Playing the local echo',
  muted: 'Microphone transmission paused',
  error: 'Open connection settings',
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? 'Unavailable';
}

export function pipelineSummary(status: string): string {
  return PIPELINE_SUMMARIES[status] ?? 'Local voice path';
}

export function isSessionActive(status: string): boolean {
  return !['stopped', 'error'].includes(status);
}

export function isSessionReady(status: string): boolean {
  return ['listening', 'speaking', 'muted'].includes(status);
}

export function formatElapsed(elapsed: number): string {
  const totalSeconds = Math.floor(elapsed / 1000);
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
  const seconds = (totalSeconds % 60).toString().padStart(2, '0');
  const tenths = Math.floor((elapsed % 1000) / 100);
  return `${minutes}:${seconds}.${tenths}`;
}

export function spectrumBarHeight(status: string, inputLevel: number, strength: number): number {
  if (status === 'muted' || status === 'stopped' || status === 'error') return 7 + strength * 5;
  if (status === 'connecting') return 10 + strength * 16;
  if (status === 'speaking') return 28 + strength * 58;
  return 8 + Math.min(1, inputLevel * 12) * strength * 84;
}
