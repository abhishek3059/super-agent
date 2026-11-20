# Jarvis HQ independent security review brief

Scope: [PR #56](https://github.com/abhishek3059/super-agent/pull/56),
macOS with the sandbox on, a fresh HQ directory, and synthetic data only.
Record the exact revision, macOS and browser versions, and results.
[R-H.4](../../roadmap.md#parallel-track-h-jarvis-hq-local-team-dec-23) remains open.

| Surface | What to verify |
| --- | --- |
| Loopback and sign-in | Try a forged Host, foreign Origin, unauthenticated API call and spoofed loopback server. Check that the launcher sends a client proof only after verifying the server proof. Replay the client proof and the sign-in link. |
| [Sandbox profile](../../apps/hq/server/src/sandbox.ts) | Try reading a sibling bot folder, the operator's synthetic canary, and the HQ session file. Try binding another bot's port or reaching a forbidden local service. Check child processes, alternate paths, IPv4 and IPv6, and system services such as Keychain and Apple events. |
| [Server file access](../../apps/hq/server/src/lib/own.ts) | Plant symbolic links and race directory replacements during read, write, download and delete. Check the canary files from outside the sandbox. Test a locked bot directory and confirm the server can still answer other requests while removal is pending. |
| [Screen relay](../../apps/hq/server/src/screen.ts) | Check session, bot ownership, Origin and Host. Try mouse or key input in watch mode and arbitrary DevTools messages in control mode. Check browser identity after restart, including a process impersonating the DevTools endpoint. |
| [Bot credentials](../../apps/hq/server/src/engine.ts) | Inventory which values can be copied from model settings, `auth.json` and `.env` using dummy values. Check that bots cannot see the HQ voice key or another bot's credentials. Verify that copied credentials have the minimum scopes. |
| Internet and bot handoff | Serve synthetic content with an embedded instruction to disclose a canary or contact a second endpoint. Check the external receiver and the other bot's chat. Document what the sandbox and the model each allow. |

The current profile permits internet access. A bot can spend or export copied
credentials and disclose its own data. Web pages, files and bot messages can
steer it. Its shell and browser can act without prompting the operator.
System files outside the closed paths remain readable. Chromium lock folders
can be shared with other instances of the same browser. A detached process
can outlive its gateway. The Chromium inner sandbox is disabled, and macOS
`sandbox-exec` is deprecated. Test these boundaries on the demo host and use
dedicated, revocable credentials for the test.
[Containment limits](../../apps/hq/README.md#security-boundary)

The [local run record](../implementation/jarvis-hq-local-run.md) and
[self-checks](../../apps/hq/server/test/hq.test.ts) give starting cases. An
independent reviewer should reproduce claims before signing off. Findings
that expose a vulnerability belong in the maintainer's private channel.
