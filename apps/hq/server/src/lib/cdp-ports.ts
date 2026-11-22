import net from 'node:net';

export const DEFAULT_CDP_BASE = 9300;
const BLOCK_SIZE = 1024;

function bind(port: number): Promise<net.Server | null> {
  return new Promise((resolve, reject) => {
    const server = net.createServer((socket) => socket.destroy());
    server.once('error', (error: NodeJS.ErrnoException) => {
      if (error.code === 'EADDRINUSE' || error.code === 'EACCES') resolve(null);
      else reject(error);
    });
    server.listen({ port, host: '127.0.0.1', exclusive: true }, () => resolve(server));
  });
}

/** The unused base port coordinates HQ workspaces. Probes never attach to another listener. */
export async function reserveCdpBase(offsets: readonly number[], servicePorts: readonly number[]) {
  if (offsets.some((offset) => !Number.isInteger(offset) || offset < 1 || offset >= BLOCK_SIZE)) {
    throw new Error('Bot browser ports are outside the auto-selection range. Set CDP_PORT_BASE explicitly.');
  }
  const needed = new Set(offsets);
  for (let base = DEFAULT_CDP_BASE; base + BLOCK_SIZE - 1 <= 65535; base += BLOCK_SIZE) {
    if (servicePorts.some((port) => port >= base && port < base + BLOCK_SIZE)) continue;
    const reservation = await bind(base);
    if (!reservation) continue;
    let accepted = false;
    try {
      let available = 0;
      for (const offset of needed) {
        const probe = await bind(base + offset);
        if (!probe) break;
        await new Promise<void>((resolve) => probe.close(() => resolve()));
        available++;
      }
      if (available === needed.size) {
        accepted = true;
        reservation.unref();
        return { base, reservation };
      }
    } finally {
      if (!accepted) reservation.close();
    }
  }
  throw new Error('No free HQ browser port block. Set CDP_PORT_BASE to a free range.');
}
