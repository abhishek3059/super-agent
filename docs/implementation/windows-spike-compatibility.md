# Windows spike compatibility: implementation record

| Field | Value |
| --- | --- |
| Date | 2026-11-08 |
| Branch | `fix/windows-spike-compatibility` |
| Stacked base | PR #10, `fix/restore-reverted-pr-8`, commit `b9c12be` |
| Delivery target | Existing PR #10; operator requested integrating the Windows changes into its branch, not opening another PR |
| Design | [Signed Windows compatibility design](../design/windows-spike-compatibility.md) |
| Operator | `abhishek3059` |
| Status | Local implementation and offline checks complete, prepared for PR #10. Reviewed baseline passed; small subsequent corrections self-checked. A2 independent security audit skipped by the operator. No runtime acceptance claimed. |

## Delivery adjustment

The signed design originally proposed a separate stacked Windows PR.
The operator subsequently requested adding the fixes to the already-open
PR #10. This changes only the delivery branch: the dedicated Windows status,
unchanged Ubuntu workflow, offline scope, and code-review checks are retained.
Commit and push of the verified Windows increment to the existing PR branch
are authorized by that request. Merging into `develop` and settings changes
are not authorized.

The operator also requested skipping the remaining `security-auditor` run.
No A2/helper independent security audit was performed or claimed. The
completed A3/workflow partial audit remains recorded. This is a disclosed
deviation from the signed proposal's full independent-audit condition, not
a waiver of repository security invariants or human merge approval.

The operator requested reserving repeat agent reviews for substantial code
increments. The initial A2 review passed; the small subsequent corrections
were self-checked and tested, without another reviewer run. This record does
not extend that independent PASS to changes the reviewer did not inspect.

## Scope

Portable Node entrypoints, private Windows token storage, offline A2/A3
tests, and an independent Windows workflow. The changes are a compatibility
increment on the restored throwaway spikes, not product runtime approval.

The existing Ubuntu workflow, package pins, macOS defaults, historical
measurements, product voice policy, contributor policy, and GitHub settings
must remain unchanged.

## Verification

The table is updated only after each command is actually executed against
the completed implementation. Baseline checks are not implementation proof.

| Check | Result |
| --- | --- |
| Root `npm ci` | PASS, exit 0, coordinator run; hooks installed normally |
| Root `npm audit` | PASS, 0 vulnerabilities reported, coordinator run |
| A3 `npm ci --ignore-scripts` | PASS, exit 0, implementation-agent run; existing SDK pin unchanged |
| A3 `npm audit` | PASS, 0 vulnerabilities reported, implementation-agent run |
| `npm run check` | PASS, exit 0, coordinator run, 0 errors; final file/link counts are reported by the pre-commit check |
| A2 offline self-test | PASS on local Windows Node 26.1.0: `selftest: all checks passed`, exit 0, coordinator rerun after ACL corrections |
| A3 offline self-test | PASS on local Windows Node 26.1.0: all 19 tests passed, exit 0, coordinator rerun |
| Ubuntu workflow unchanged | PASS: git diff against base b9c12be, exit 0; manifests and lockfiles also unchanged |
| Independent implementation review | A3/workflow PASS; [A2 baseline review](../reviews/windows-spike-compatibility-a2.md) PASS, average 8.9. Small subsequent A2 corrections self-checked and tested; no repeat review at the operator's request |
| Independent security assessment | [A3/workflow audit](../security/windows-spike-compatibility-a3.md) PASS, partial scope; A2/helper audit not run, skipped at the operator's request |
| macOS execution | Not run |
| GitHub Windows Node 22 workflow | Not run |
| Gemini or Claude Code runtime | Not run; no key access or cloud-model calls authorized |

### A2 evidence

The first coordinator run failed with `Cannot read properties of undefined
(reading 'length')` in ACL dump decoding, exit 1. The helper expected a
different return shape from its native-command adapter. The implementation
agent corrected that error and related parser and cleanup defects.

The coordinator then ran both suites and the repository check together:

```powershell
$env:SUPER_AGENT_TEST_TMP = "C:\Users\user\AppData\Local\Temp\opencode"
node spikes/a2-permission-hook/selftest.mjs
node spikes/a3-gemini-live/selftest.mjs
npm run check
git diff --check
```

Each command exited 0. Actual A2 output: `selftest: all checks passed`.
Tests use synthetic tokens, loopback requests, and unique temporary files.
The [A2 implementation record](windows-spike-compatibility-a2.md) describes
the checks and platform-specific caveats. macOS and hosted Windows Node 22
execution have not run, so the design's cross-platform execution conditions
are not yet fully verified.

The final A2 corrections cover the review's parent-rights mask finding,
missing native-tool errors, absent argv, and malformed/extra-principal or
inherited DACL rejection. Token comparison assertions no longer print
synthetic token values on failure. A2 again reported `selftest: all checks
passed`, A3 `all 19 passed`, and the repository check 0 errors, all exit 0.

Coordinator self-assessment for the complete Windows increment: correctness
9, security 8.5, honesty 10, scope 9, clarity 9, average 9.1. This is not a
substitute claim of an independent full-change security audit.

### A3 evidence

The A3 implementation agent reported GLM-5.3-Flash Free (OpenCode provider,
fallback developer). The coordinator added and verified key-free
CLI validation/zero-success tests, synchronous connection-error cleanup,
and prompt-send failure coverage. The final coordinator command was:

```powershell
$env:SUPER_AGENT_TEST_TMP = "C:\Users\user\AppData\Local\Temp\opencode"
node spikes/a3-gemini-live/selftest.mjs
```

The independent initial review caught a missing turn-completion timestamp
that nulled the total-duration result despite a vacuous test assertion.
The timestamp was restored and the test now requires a finite numeric
duration. Positive CLI, malformed-message, and reply-write-failure tests
were added. Actual latest output: `all 19 passed`, exit 0. Tests inject fake clients;
no real Gemini client, provider connection, or credential read is needed.

## Constraints and residual decisions

- The Windows status is separate and is not configured as required here.
- Registry installation traffic is distinct from the offline test execution.
- Local Windows test storage is under the approved OpenCode temporary root;
  hosted CI uses an explicitly selected runner temporary directory.
- File permissions do not isolate an administrator or a same-user process.
- Remaining product-direction and measurement findings from PR #10 are not
  resolved by this Windows change.
- Every push requires operator approval. No merge or settings change is
  authorized by this record.

## Rollback

Revert only the Windows compatibility commit on PR #10. That keeps the
restoration itself and the earlier folder rename, rulebook, and license.
