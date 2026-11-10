# Local voice streaming: uncertain findings and known limits

| Field | Value |
| --- | --- |
| Date | Created 2026-11-10; final-review observations added 2026-11-11 |
| Scope | PH-01 local fake-adapter slice in PR #24 |
| Operator direction | Continue implementation; review concrete failure paths and log skeptical cases separately |
| Purpose | Keep uncertain observations visible without treating speculation as implementation scope or acceptance evidence |
| Gate effect | None. Credential, security, hardware, and native-provider acceptance remain open |

## Review rule for this work

Finish implementation and the agreed tests, then use one consolidated review.
Block delivery for a demonstrated logical failure, broken requirement, or
concrete security issue. Batch those fixes and recheck the affected findings.
Do not start another full review for cosmetic edits. Log uncertain cases here
with their evidence and the condition that would justify action. An unresolved
actual blocker remains a blocker, even if the review budget is exhausted.
The repository quality threshold is unchanged.

## Observations

| ID | Classification | Observation and evidence | When to revisit |
| --- | --- | --- | --- |
| U-01 | Unverified production behavior | The in-process abrupt-disconnect test covers TestClient cancellation. Shutdown timing and callback delivery on a real Windows or macOS server are not established by that test alone. No production shutdown defect is claimed. | During the required on-host acceptance run, if Stop, disconnect, or shutdown fails to finish normally. |
| U-02 | Known browser limitation, not a new defect claim | A hung, throwing, or rejected `AudioContext.close()` does not prove browser resource release. The service detaches capture and finalizes UI state without waiting for successful closure. The frontend tests and [final review](voice-streaming-frontend.md) explicitly cover and disclose this. | If the hardware run shows an observable device or playback resource remaining active after Stop. |
| U-03 | Unverified future adapter assumption | Successful fake-adapter `close()` is the current closure contract. It does not establish how a future native provider confirms remote-session termination or handles cancellation. No Gemini adapter is implemented in this slice. | When the approved native adapter is designed and implemented, before live acceptance. |
| U-04 | Disclosed residual lifetime | A cancellation-resistant final wire operation may remain owned after the handler's deadline. Worker quiescence and confirmed adapter closure allow the slot to be released, but do not bound that old connection's lifetime. The [teardown design](../design/voice-streaming-teardown.md) discloses this. Actual transport behavior and accumulation under repeated stalled connections have not been measured. | If the real transport reproduces stalled final writes or persistent accumulation during the required boundary tests. |
| U-05 | Cooperative scheduling assumption | A monotonic asyncio deadline bounds asynchronous waits, not synchronous code that blocks the event loop. The current fake has no synchronous provider call. No hard real-time or force-kill guarantee is claimed. | If an approved adapter introduces blocking work on the voice event loop. |
| U-06 | Reported scheduling observation; platform cause unverified | The test developer reported that the handler can return at its deadline while cleanup still has a scheduled resumption. The supervisor owns and awaits that cleanup before reconciliation. Tests now inspect terminal flags after the owning supervisor finishes. The combined parent run passed all 66 cases on 2026-11-11; a Windows-timer cause was not established. | If a reproduction shows lost ownership, early gate release, overlapping writes, or unresolved cleanup despite releasing every test blocker. Do not add a scheduling yield solely to make intermediate flags look final. |
| U-07 | Non-blocking coverage gap | The final reviewer found no test directly asserting that the app's supervisor list becomes empty after its done callback runs (`app.py:525-529`). The callback's outcome retrieval and list removal were inspected, not separately asserted. | If completed supervisors accumulate in a reproduction, or when that ownership callback changes. |
| U-08 | Timing sensitivity, not a reproduced current failure | The hanging-close API test uses `time.sleep(0.8)` before checking retained ownership. The reviewer noted possible sensitivity under extreme event-loop starvation; the combined 66-case run passed. | If CI or an on-host run reproduces a timing failure, replace the separator with a terminal-state barrier rather than changing product behavior. |
| U-09 | Non-blocking fault-injection gap | The supervisor's generic exception fallback (`app.py:561-564`) was not exercised with an injected unexpected exception. The inspected branch retains the slot rather than recording success. | When modifying that fallback, or if an actual supervisor fault fails to retain unresolved ownership. |

These entries are not tests passed, implementation approvals, or a list of
features to build now. Record any concrete reproduction and its disposition
before upgrading an uncertain observation to a required correction. Report
security vulnerabilities through the repository's private reporting channel,
not a public issue or this general uncertainty log.
