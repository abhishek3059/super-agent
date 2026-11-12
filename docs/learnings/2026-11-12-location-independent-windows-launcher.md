# Launch scripts should locate their own checkout

Date: 2026-11-12

Relative setup commands fail when copied into a shell whose working directory
is the user profile. A checked-in launcher can avoid that class of failure by
deriving the repository root from its own file path rather than requiring a
particular current directory.

The launcher should also own the process it starts: wait for backend readiness
before opening the frontend, and stop the backend when the foreground frontend
exits.

Evidence: [R-01.F4 implementation record](../implementation/r01-f4-windows-launcher.md).
