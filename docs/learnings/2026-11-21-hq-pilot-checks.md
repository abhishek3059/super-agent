# Integrated HQ pilot checks

| Field | Value |
| --- | --- |
| Date | 2026-11-21 |
| Evidence | [Maintainer pilot](../implementation/jarvis-hq-maintainer-pilot.md) and [PR #77](https://github.com/abhishek3059/super-agent/pull/77) |

## What happened

The Windows privacy test failed when its elapsed-time field equalled the
synthetic answer under test. The assertion now checks the timing field as a
number and scans the remaining response for leaked text.

## What we learned

A successful Linux test job can mask an unavailable containment runtime when
the tests are skippable. The dedicated job now requires bubblewrap to start.
A passing run covers the Linux test environment. It does not replace the
acceptance run on a maintainer's Windows machine.
