export function inputRms(samples: Float32Array): number {
  if (!samples.length) return 0;
  let energy = 0;
  for (const sample of samples) energy += sample * sample;
  return Math.sqrt(energy / samples.length);
}

export function pcmIsAudible(samples: Int16Array): boolean {
  if (!samples.length) return false;
  let energy = 0;
  for (const sample of samples) energy += (sample / 0x8000) ** 2;
  // A level floor prevents silent echo frames from becoming "speaking". This
  // is not speech recognition or a provider's voice-activity detector.
  return Math.sqrt(energy / samples.length) > 0.002;
}
