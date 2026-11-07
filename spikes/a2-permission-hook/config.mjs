import { homedir } from "node:os";
import { join } from "node:path";

export const PORT = Number(process.env.SUPER_AGENT_PORT ?? 7717);
export const TOKEN_FILE = process.env.SUPER_AGENT_TOKEN_FILE ?? join(homedir(), ".super-agent", "spike-token");
// Must stay below the hook timeout in settings so the server answers first.
export const PENDING_TIMEOUT_MS = Number(process.env.SUPER_AGENT_PENDING_MS ?? 110_000);
