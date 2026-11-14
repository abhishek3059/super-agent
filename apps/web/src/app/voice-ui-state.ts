const STATUS_LABELS: Record<string, string> = {
  stopped: 'Disconnected',
  connecting: 'Connecting',
  listening: 'Listening',
  thinking: 'Thinking',
  speaking: 'Local echo',
  muted: 'Muted',
  error: 'Needs attention',
};

const PIPELINE_SUMMARIES: Record<string, string> = {
  stopped: 'Ready for a local session',
  connecting: 'Authenticating on loopback',
  listening: 'Microphone streaming locally',
  thinking: 'Working on a reply locally',
  speaking: 'Playing the local echo',
  muted: 'Microphone transmission paused',
  error: 'Open connection settings',
};

export interface ProviderCopy {
  badge: string;
  tag: string;
  micStep: string;
  replyStep: string;
  replyNote: string;
  privacy: string;
  settingsTitle: string;
  settingsNote: string;
}

const PROVIDER_COPY: Record<string, ProviderCopy> = {
  fake: {
    badge: 'Fake echo adapter', tag: 'Local only',
    micStep: 'Personal audio stays on this device',
    replyStep: 'Local echo playback', replyNote: 'No Gemini session or cloud microphone upload',
    privacy: 'Fake adapter active. Microphone audio stays local.',
    settingsTitle: 'Local fake adapter', settingsNote: 'No Gemini connection and no cloud microphone upload.',
  },
  local: {
    badge: 'Local private model', tag: 'Local only',
    micStep: 'Personal audio stays on this device',
    replyStep: 'Local model reply', replyNote: 'No Gemini session or cloud microphone upload',
    privacy: 'Local model active. Microphone audio stays local.',
    settingsTitle: 'Local private model', settingsNote: 'No Gemini connection and no cloud microphone upload.',
  },
  'gemini-live': {
    badge: 'Gemini Live (cloud)', tag: 'Cloud',
    micStep: 'Microphone audio is sent to Google Gemini',
    replyStep: 'Gemini Live reply', replyNote: "Testing only. Google's free tier may use inputs for training.",
    privacy: 'Gemini Live active. Microphone audio goes to Google. Speak nothing personal.',
    settingsTitle: 'Gemini Live (cloud)', settingsNote: 'Microphone audio goes to Google. Speak nothing personal.',
  },
};

// Never default to a local or fake claim: before connecting, or for an unknown provider, say nothing about where audio goes.
const NEUTRAL_COPY = (badge: string): ProviderCopy => ({
  badge, tag: 'Unverified',
  micStep: 'Where audio goes is shown after connecting',
  replyStep: 'Reply', replyNote: 'Adapter shown after connecting',
  privacy: 'Adapter shown after connecting.',
  settingsTitle: badge, settingsNote: 'Adapter shown after connecting.',
});

export function providerCopy(provider: string): ProviderCopy {
  return PROVIDER_COPY[provider] ?? NEUTRAL_COPY(provider === '' ? 'Not connected' : 'Unknown provider');
}

// The echo wording is only true for the fake adapter; the local model speaks its own reply.
export function statusLabel(status: string, provider = ''): string {
  if (status === 'speaking' && (provider === 'local' || provider === 'gemini-live')) return 'Speaking';
  return STATUS_LABELS[status] ?? 'Unavailable';
}

export function pipelineSummary(status: string, provider = ''): string {
  if (status === 'speaking' && provider === 'local') return 'Playing the local reply';
  if (status === 'speaking' && provider === 'gemini-live') return 'Playing the Gemini reply';
  return PIPELINE_SUMMARIES[status] ?? 'Local voice path';
}

export function isSessionActive(status: string): boolean {
  return !['stopped', 'error'].includes(status);
}

export function isSessionReady(status: string): boolean {
  return ['listening', 'thinking', 'speaking', 'muted'].includes(status);
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
  if (status === 'thinking') return 12 + strength * 20;
  if (status === 'speaking') return 28 + strength * 58;
  return 8 + Math.min(1, inputLevel * 12) * strength * 84;
}
