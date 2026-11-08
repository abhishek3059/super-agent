// Claude Code PermissionRequest hook: forwards the pending request to the
// loopback approval server and prints the human's decision.
// Any failure prints nothing and exits 0, so Claude Code keeps its normal
// permission flow. This hook never allows on error.
import { readFileSync } from "node:fs";
import { isDirectRun } from "../entrypoint.mjs";
import { PORT, TOKEN_FILE } from "./config.mjs";

// Below the documented 120-second hook window; leaves margin for the final
// output while outliving the server's own 110 s decision timeout.
const FETCH_DEADLINE_MS = 115_000;

export function toHookOutput({ decision, reason }) {
  if (decision === "allow") return { hookSpecificOutput: { hookEventName: "PermissionRequest", decision: { behavior: "allow" } } };
  if (decision === "deny") return { hookSpecificOutput: { hookEventName: "PermissionRequest", decision: { behavior: "deny", message: reason || "Denied by approver" } } };
  return null; // "ask" or anything unknown: no decision
}

// Fixed safe diagnostic categories: raw error text can embed paths, tokens,
// or provider output and is never forwarded.
export function describeHookError(err) {
  const error = err?.cause ?? err; // undici fetch failures wrap the real cause
  if (error?.name === "TimeoutError" || error?.name === "AbortError" || err?.name === "TimeoutError" || err?.name === "AbortError") return "server-decision-window-expired";
  if (error instanceof SyntaxError || err instanceof SyntaxError) return "invalid-hook-input";
  if (["ECONNREFUSED", "ECONNRESET", "EPIPE"].includes(error?.code)) return "server-unreachable";
  if (typeof error?.code === "string") return "token-or-server-unavailable";
  return "hook-request-unfinished";
}

async function main() {
  const input = JSON.parse(readFileSync(0, "utf8"));
  const res = await fetch(`http://127.0.0.1:${PORT}/requests`, {
    method: "POST",
    headers: { authorization: `Bearer ${readFileSync(TOKEN_FILE, "utf8").trim()}`, "content-type": "application/json" },
    body: JSON.stringify({ tool_name: input.tool_name, tool_input: input.tool_input, session_id: input.session_id, cwd: input.cwd }),
    signal: AbortSignal.timeout(FETCH_DEADLINE_MS),
  });
  if (!res.ok) return;
  const out = toHookOutput(await res.json());
  if (out) process.stdout.write(JSON.stringify(out));
}

if (isDirectRun(import.meta.url)) {
  await main().catch((err) => process.stderr.write(`super-agent hook: ${describeHookError(err)}\n`));
}
