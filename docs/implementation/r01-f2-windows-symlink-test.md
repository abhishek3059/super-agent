# R-01.F2: portable token-symlink security test

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Trigger | Fresh locked backend run on Windows at `develop` `651e33c` |
| Failure | `test_token_file_symlink_is_refused` failed during fixture setup with `WinError 1314`; 193 other tests passed |
| Scope | Test portability only; no runtime token handling changed |

The token reader's symlink, file-type, mode, and owner checks are deliberately
POSIX-only in `config.py`. The test created a real symlink before its existing
`os.name == "posix"` assertion guard. An unprivileged Windows account can be
unable to create that fixture, and the test made no assertion on Windows even
when creation succeeded.

The test is now explicitly skipped outside POSIX and keeps the real filesystem
assertion unchanged on POSIX. This avoids weakening the security check or
requiring Windows administrator/developer-mode privileges. Windows owner-only
ACL enforcement remains the separate open review item N2; this fix does not
claim to implement or test it.

## Verification

On 2026-11-12, the full locked backend suite ran on Windows with Python 3.14.4:
193 passed and this one POSIX-only test skipped in 11.94 seconds. The frontend
voice and epoch self-tests remained at 39 and 8 passing cases, the production
build remained 116.00 kB, `npm audit` found 0 vulnerabilities, and
`npm run check` reported 0 errors. macOS CI must continue to execute the POSIX
assertion.
