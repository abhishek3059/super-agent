# Synthetic voice console for R-01.10

Proposal for independent review. The existing
[PH-00 authorization](../approvals/ph-00-setup-decisions.md) permits
generated audio to Gemini for the opt-in test. The browser proof needs an
authenticated control path and visible playback under that same boundary.
This proposal covers the operator's first run on macOS.

## Session

1. An operator launches the local probe explicitly with a process-scoped
   provider key. The launcher generates a fresh 256-bit probe secret,
   transfers it through the existing owner-only local secret handling
   path, and binds the service to the reviewed loopback address. Use the
   secret for this invocation only. The existing local echo token is
   invalid for the probe.
2. The probe view shows the Gemini recipient and the generated-audio
   scope before the operator presses Start. The browser opens
   `/ws/voice-check` at the fixed backend address. The server checks the
   exact Host and Origin before entering the existing bounded pre-auth
   path. The browser uses the handshake below before it enables controls.
3. The authenticated Start control starts the adapter and plays a fixed
   synthetic prompt that requests a long spoken reply. The server generates
   the two short input clips locally, validates 16 kHz mono PCM16 and a
   ten-second bound per clip, and paces them through the existing adapter.
   One activation can send the initial clip and one interruption clip.
   The WebSocket accepts a closed set of control messages. Any binary
   input, unknown action, or unexpected field closes the session. The
   browser playback path requests zero microphone permissions. Serve the
   probe page with `Permissions-Policy: microphone=()`.
4. The screen reports connection and playback state. The operator can mute
   generated input, stop playback, end the session, or send the second
   fixed utterance during a reply. The latter measures provider interruption.
   Mute cancels pending input and prevents future enqueue until unmuted.
   End cancels input before adapter teardown.
   Manual playback stop measures the browser cutoff independently. Reuse
   the existing playback epochs and teardown limits. A missing key or
   unsupported provider fails closed with a fixed error. Stop ends input
   and playback and releases the slot after confirmed closure. The browser
   stops playback immediately on Stop or disconnect. A 45-second server
   deadline bounds a session if a relay drops its Stop or close.

## Loopback authentication

The [boundary review](../reviews/r01-6-security-review.md) flagged handing
a reusable bearer token to whichever process binds the backend port.
Use HMAC-SHA256 with the fresh probe secret and Web Crypto in the browser.
The browser sends a fresh random 32-byte nonce. The backend sends its
own 32-byte nonce and a server proof. The browser verifies that proof
before sending a client proof. The backend compares the client proof in
constant time before creating the adapter or admitting Start.

The proof input is a fixed ASCII transcript containing the protocol version,
the role (`server` or `client`), the expected origin and endpoint, the
synthetic-only profile, and the two nonces in that order. Use lowercase
fixed-length hex for nonces and a newline delimiter between fields. One
challenge is valid per socket under the existing authentication deadline.
Refuse bearer authentication, retry on the same socket, and profile downgrade.
Keep proofs, secrets, audio, and provider payloads out of logs.

Mutual proofs authenticate the handshake. Authenticate the messages after
it as well. Derive separate client and server message keys from the two
nonces and distinct role labels using HMAC-SHA256. A message carries its
role-local sequence number, exact UTF-8 body, and HMAC over the sequence
number and body. Verify the MAC and next sequence before parsing or acting
on the body. Use a single signed body for each audio chunk with its PCM
encoded as base64. Validate the decoded frame size and playback epoch
before scheduling audio. Close on invalid MAC, sequence, or size.

The browser trusts the locally served frontend and the OS. A local
relay may still read synthetic traffic, delay it, or drop it. It cannot
forge authenticated Start, change an input command, or substitute
playback without the probe secret. Fixed input and a server deadline bound
the provider work even when a relay withholds a Stop.

## Acceptance checks

- Offline, check wrong Host and Origin, forged and replayed proofs,
  a role-swapped proof, bearer rejection, and failure before adapter
  construction. From a fake server, verify that the browser sends no
  client proof without a valid server proof and requests no capture.
  Verify that a relay cannot insert or replay Start or substitute
  playback, and that a dropped Stop is bounded by the server deadline.
- With a scripted SDK, check authenticated activation, zero binary input
  accepted, bounded synthetic sends, playback epochs, mute, stop and
  close, and missing-key or unsupported-model failure.
- After independent review, the operator runs the browser test against
  Gemini. Record the first PCM and playback timings, states, local stop,
  the provider event after the second utterance, and unsupported-model
  failure. Record `Interrupted` and `TurnComplete` separately. A natural
  completion cannot establish interruption. Save only timing, counts,
  status, and fixed error categories.

The [acceptance record](../implementation/r01-10-acceptance.md) tracks the
remaining evidence for RT-G01.
