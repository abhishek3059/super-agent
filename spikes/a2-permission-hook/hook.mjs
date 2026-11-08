// Claude Code PermissionRequest hook: forwards the pending request to the
// loopback approval server and prints the human's decision.
// Any failure prints nothing and exits 0, so Claude Code keeps its normal
// permission flow. This hook never allows on error.
import { readFileSync } from "node:fs";
import { PORT, TOKEN_FILE } from "./config.mjs";

export function toHookOutput({ decision, reason }) {
  if (decision === "allow") return { hookSpecificOutput: { hookEventName: "PermissionRequest", decision: { behavior: "allow" } } };
  if (decision === "deny") return { hookSpecificOutput: { hookEventName: "PermissionRequest", decision: { behavior: "deny", message: reason || "Denied by approver" } } };
  return null; // "ask" or anything unknown: no decision
}

async function main() {
  const input = JSON.parse(readFileSync(0, "utf8"));
  const res = await fetch(`http://127.0.0.1:${PORT}/requests`, {
    method: "POST",
    headers: { authorization: `Bearer ${readFileSync(TOKEN_FILE, "utf8").trim()}`, "content-type": "application/json" },
    body: JSON.stringify({ tool_name: input.tool_name, tool_input: input.tool_input, session_id: input.session_id, cwd: input.cwd }),
  });
  if (!res.ok) return;
  const out = toHookOutput(await res.json());
  if (out) process.stdout.write(JSON.stringify(out));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await main().catch((err) => process.stderr.write(`super-agent hook: ${err.message}\n`));
}
