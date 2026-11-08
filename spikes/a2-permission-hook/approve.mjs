// Approver CLI: node approve.mjs list | allow <id> | deny <id> [reason]
import { readFileSync } from "node:fs";
import { PORT, TOKEN_FILE } from "./config.mjs";

const [cmd, id, ...reason] = process.argv.slice(2);
const headers = { authorization: `Bearer ${readFileSync(TOKEN_FILE, "utf8").trim()}`, "content-type": "application/json" };
const base = `http://127.0.0.1:${PORT}`;

if (cmd === "list") {
  const items = await (await fetch(`${base}/requests`, { headers })).json();
  if (!items.length) console.log("no pending requests");
  for (const r of items) console.log(`${r.id}  ${r.tool_name}  ${JSON.stringify(r.tool_input).slice(0, 120)}  (${Math.round(r.ageMs / 1000)}s)`);
} else if ((cmd === "allow" || cmd === "deny") && id) {
  const res = await fetch(`${base}/requests/${id}/decision`, { method: "POST", headers, body: JSON.stringify({ decision: cmd, reason: reason.join(" ") }) });
  console.log(res.status, await res.text());
} else {
  console.log("usage: node approve.mjs list | allow <id> | deny <id> [reason]");
  process.exitCode = 1;
}
