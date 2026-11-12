# Platform-specific security fixtures

Date: 2026-11-12

A security test can be portable even when the security mechanism is not. The
token-file symlink check is POSIX-only, but its fixture was created before the
platform guard. An unprivileged Windows run therefore failed on fixture setup
without testing any application behavior.

Keep the real filesystem assertion on the platform where the control exists.
Skip the whole test elsewhere, and track the other platform's control
separately. Do not require elevated test-runner privileges merely to reach an
assertion that is disabled on that platform.

Evidence: [R-01.F2 implementation record](../implementation/r01-f2-windows-symlink-test.md).
