# Governance gate, slice 1

| Field | Value |
| --- | --- |
| Date | 2026-11-18 |
| Design | [governance gate](../design/governance.md) section 3 and section 5 "Slice 1" |
| Authority | Maintainer `abhishek3059`, in chat, 2026-11-18: accepted `policy.py` as the gate (OD-G1) and asked for slice 1 |
| Approval record | [governance gate exception](../approvals/governance-gate-exception.md) |
| Roadmap | Off-path. No roadmap item exists yet (design section 6.2). `roadmap.md` is not edited here. |
| Behaviour change | None |

## What was built

- `policy.py`: frozen `Turn` and `Decision`, and the pure function
  `decide(tool, turn)`. The `_ASKED` patterns moved here unchanged as `ASKED`.
  Codes `untrusted_read_in_turn` and `not_asked` joined `REASONS`.
- `local_adapter.py`: `call_tool` builds a `Turn` from `_HEARD` and
  `_READ_UNTRUSTED`, calls `decide`, and maps each deny code to the same string
  as before (`DELEGATE_AFTER_READ`, `memory.AFTER_READ`, `NOT_ASKED`).
  `_ASKED` is gone from this file. The "no such tool" switch checks stay (slice 2).

Rules in `decide`:

1. Not a `str` tool, not a `Turn`, a non-bool fact, or a non-`str` transcript:
   `deny` with `input_invalid`. It never raises.
2. `delegate_task` or a memory write, with `read_untrusted`: `deny`,
   `untrusted_read_in_turn`.
3. A tool with an `ASKED` pattern, a transcript, and no match: `deny`, `not_asked`.
4. Everything else, including names it does not govern: `allow`. `confirm` is never returned.

## Verification

```text
pytest apps/api -q -p no:cacheprovider
1 failed, 1117 passed, 109 skipped, 1 warning in 66.36s (0:01:06)
FAILED test_memory.py::test_files_are_private_even_when_they_already_existed  (fails on unchanged develop too)
```

The four named behaviour tests in `test_local_adapter.py` and `test_delegation.py`
pass unedited. No existing test was edited. `npm run check`: 0 errors at e75997a.

## Known limits

- `policy.py` imports `memory.WRITES`; `memory.py` imports nothing from the package, so there is no cycle.
- `Turn` has no switch fields yet; slice 2 adds them when it moves the switch checks. The adapter reads each switch only inside its own branch, as before,
  so a bad `SUPER_AGENT_DELEGATE` still breaks only `delegate_task`.
- `complete_reminder` and `undo_forget` have no `ASKED` pattern, so, as before, only the untrusted-read rule governs them.

## Review fix: unexpected denies fail closed

`call_tool` first mapped only `untrusted_read_in_turn` and `not_asked`, so any
other deny code (such as `input_invalid`) would have let the tool run. It now
returns the fixed `DENIED` text for every other deny, for memory tools and for
`delegate_task`. Test: `test_an_unexpected_gate_deny_fails_closed` in
`tests/test_local_adapter.py`.
