# Loopback names are different browser Origins

Date: 2026-11-12

Binding a development server to `127.0.0.1` does not stop a browser from loading
it through the `localhost` alias. The page then sends a different Origin, which
a strict backend must reject even though both names resolve to loopback.

Keep the strict allowlist. Make launch documentation and fixed error messages
name the canonical URL so an operator does not mistake a pre-authentication
handshake rejection for a microphone failure.

Evidence: [R-01.F3 implementation record](../implementation/r01-f3-origin-diagnostic.md).
