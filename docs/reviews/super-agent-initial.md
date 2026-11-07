FAIL

# Super-agent — independent documentation review

| Field | Assessed scope / evidence |
| --- | --- |
| Date | 2026-11-07 |
| Scope | **documentation/design-stage only; no runtime implementation certified** |
| Reviewer | Code Review Board; configured profile **`agentrouter/gpt-6-astra`**, supplied by this assignment. This is not a runtime voice-model selection; no global configuration was inspected. |
| Contract | [Signed design](../design/super-agent.md), revision 1, all 488 lines read |
| Assessed delivery | Current revision-1 documentation pack, its two delivery sources, and the implementation/delivery status records; no Git baseline available |
| Design SHA-256 | `A895DB99B560A835F664872501F9304C39CC503930352C1355A7F8D842BF91A5` |

**Disposition:** changes required to the documentation. The mandatory decision register is not expanded as contracted, and the phase plan makes several phases depend on their own completion gates. These are documentation completeness/correctness failures, not objections to the intentionally absent application, dependencies, or runtime tests. The unavailable later security disposition is not itself a finding or a fabricated failure.

## Findings — severity ranked

### R-01 — MAJOR — Required decision records are assertions rather than the contracted register

- **Location:** `descisions.md:29-103`, especially `descisions.md:43-45` and `descisions.md:95-103`.
- **Trigger:** a maintainer opens DEC-04 after discovering that the selected tasks are instantaneous/disposable and require no recovery, and needs to determine whether the ledger decision should be reopened.
- **What breaks:** DEC-04 contains only the ledger choice. Its conditional status, rationale, alternative, evidence, and reopen condition are absent. This is representative of the register: declaring at line 97 that each entry carries seven fields does not supply those fields. The other entries likewise do not provide the required per-decision alternatives/trade-offs, evidence, and reopen criteria. The global status and the DEC-06 follow-up caveat do not replace individual decision records.
- **Contract:** `docs/design/super-agent.md:67`, `:118-137`, and `:426` explicitly require the expanded register. In particular, `:125` makes DEC-04 conditional and supplies this exact counterfactual.
- **Required correction:** expand DEC-01–DEC-16 with their actual status, rationale, alternatives/trade-offs, implications, source evidence, and reopen conditions. Preserve conditional, provisional, and deferred distinctions; do not invent approvals or new council votes.

### R-02 — MAJOR — Phase entry prerequisites are circular

- **Location:** `phases.md:39-61`, especially `phases.md:49`; compare `prd.md:129-143` and `tasks/002-local-scaffold-and-boundary.md:21-23`.
- **Trigger:** RT-001 and RT-G00 are completed under a later authorized implementation request, but no scaffold or native connection exists yet. The implementer attempts to begin PH-01.
- **What breaks:** PH-01 calls RT-G01 its **prerequisite**, although RT-G01 requires the reviewed scaffold and measured native connection produced by PH-01's own RT-002/RT-003 tasks. Following the phase entry condition therefore prevents starting the work that could satisfy it. PH-00, PH-02, and PH-03 repeat this confusion with their own completion gates; the individual task dependencies do not agree with that reading of the phase plan.
- **Contract:** `docs/design/super-agent.md:331-362`, `:432`, and `:459-466` distinguish ordered work from evidence required to close runtime gates.
- **Required correction:** state entry prerequisites and exit/acceptance gates separately for each phase, consistently with task dependencies. Keep all present future-phase statuses `not started`; fixing the plan must not assert any gate has passed.

### R-03 — MINOR — PRD requirement-to-evidence/acceptance traceability was dropped

- **Location:** `prd.md:31-111`, for example `prd.md:49-51` (REQ-03).
- **Trigger:** a reviewer follows REQ-03 and tries to identify its source evidence, governing decisions, and designated acceptance test.
- **What breaks:** the requirement is present, but its mapping to DEC-08/DEC-09 and RT-A02, and its brief/council citations, are absent. The requirement and acceptance sections exist separately without the contracted per-requirement traceability. Readers must reconstruct it from the signed design rather than use the PRD as the canonical requirements handoff.
- **Contract:** `docs/design/super-agent.md:91-114` supplies the mappings; `:425` requires acceptance links and source citations in the PRD.
- **Required correction:** restore source, decision, and acceptance links for REQ-D01/REQ-D02 and REQ-01–REQ-18. This is a traceability defect, not a claim that the requirements themselves are missing.

### R-04 — MINOR — Meeting 2 omits the recorded provider-recommendation change

- **Location:** `council meetings/council-meeting-2.md:46-55`; related loss of eligibility context in `council meetings/council-meeting-1.md:52-56`.
- **Trigger:** a reader uses meeting 2 to establish what the anonymized cross-review changed about the initially presumed Gemini runtime.
- **What breaks:** the four disagreement summaries and counterfactual paragraph do not record the actual recommendation change: do not presume Gemini for this personal runtime; investigate an eligible direct OpenAI native alternative. The source states this explicitly at `docs/delivery/council.md:113-117`, with the Researcher's terms/eligibility rationale at `:85-87`. Meeting 3 correctly separates the later GPT-Live follow-up, but does not make meeting 2's account of the cross-review complete.
- **Contract:** `docs/design/super-agent.md:325` and `:428` require preservation of the provider change and genuine disagreements.
- **Required correction:** add a source-cited summary of that change and its eligibility rationale. Keep Gemini eligibility-gated, not categorically prohibited, and keep later GPT-Live research distinct from the original votes.

### R-05 — MINOR — RT-001 acceptance mixes today's unresolved status with future success criteria

- **Location:** `tasks/001-runtime-consent-and-feasibility.md:35-39`.
- **Trigger:** the future setup task obtains explicit approval of a monetary budget and bounded retention/retry windows, as required by RT-G00.
- **What breaks:** its first acceptance bullet says those values **remain unset and unapproved**. Read as a completion criterion, that becomes false precisely when the task successfully resolves the gate. The current unresolved status is appropriate, but is misplaced as a future acceptance condition.
- **Required correction:** keep today's unresolved values in a dated status/input note. Define acceptance in terms of a truthful dated setup decision and explicit approvals before proceeding, without pre-approving any amount or silently treating missing approval as success.

### R-06 — MINOR — Progress points to validation counts that the named report does not contain

- **Location:** `progress.md:45`; compare `docs/implementation/super-agent.md:64-68` and `docs/delivery/super-agent.md:48-65`.
- **Trigger:** a reviewer follows the progress record's instruction to find the actual evidence and counts of the most recent artifact check in the implementation report.
- **What breaks:** that report lists inspection activities but no check counts. The scoped historical counts and parser limitations are instead in the delivery record. The evidence pointer is inaccurate even though the underlying delivery record is available.
- **Required correction:** point to the actual existing evidence and preserve its stated snapshot/parser scope. Do not imply historical counts describe all subsequent edits.

## What was checked

- Read the complete signed design, the discovery brief (110 lines), and the council source (237 lines), rather than relying on the supplied audit summary.
- Read all **24 requested files**: seven root documents; `tasks/README.md` and RT-001–RT-012; `council meetings/README.md` and meetings 1–3. Also read `docs/implementation/super-agent.md` and `docs/delivery/super-agent.md`.
- Independently inspected the workspace, including hidden files: all literal requested paths exist; no `tasks/` or `decisions.md` substitute exists; no non-Markdown file or application scaffold was present in that inspection. This establishes observed contents, not historical proof that no external/global action ever occurred.
- Independently checked local **inline Markdown links** before adding this report: **29 Markdown files, 477 local link occurrences, 75 nonempty fragment occurrences, zero detected missing-file/outside-workspace/fragment errors**. The checker decoded percent-encoded paths, retained hyphens in heading slugs, and recognized explicit anchors. Twenty inline external-link occurrences (10 distinct URLs) were excluded. Bare external URLs in the source records were not part of those inline-link counts. These are this review's snapshot counts, not a repetition of the manager's earlier totals.
- Confirmed all twelve future task records state `not started` and execution evidence `none`, and all eight future phase headings retain their initial `not started` status. Checked task dependencies and scope against the signed task table, not just field presence.
- Compared the eight canonical job-state rows with the design and traced admission, revision, cancellation/completion races, `unknown`, restart reconciliation, and the distinct stop workflows. Checked separation of job identity/revision, voice/playback epochs, and native delegation correlation; verified the documented single backend execution owner and rejection of narration as task evidence.
- Checked the written native-audio requirement, transient native transcript disclosure, direct browser media versus backend context consent, provider mute versus local mic-stop, fail-closed setup/control obligations, and prohibition on silent fallback. These are proposed obligations, not deployed controls.
- Checked the fixed synthetic-worker versus real planner distinction, no ambient-voice elevation, deferred OS-contained OpenCode/independent child scope, Host/Origin/CORS/WS/CSRF requirements, backend-only secrets, unresolved bounded retention and spending gates, provider-retention caveats, and sleep/off execution limits. The signed design's numerical resource/latency targets remain proposals, not approved money or measurements.
- Verified meeting 2's four rating triples and all four rankings against the source; checked all five counterfactuals and meeting 3's separation of chair synthesis from later research. Official links retain the relevant `?api=live` query and the recorded check date. R-04 identifies the substantive history still missing.
- Checked build/status language: no current runnable build; future commands individually labeled non-runnable/unexecuted; recorded OpenCode v2.1.2 HTTP 404 is not presented as voice success; authored documentation is not portrayed as independent acceptance. Planned review/security paths are code references, not fake successful report links.

## What is good

- The job-state table and stop workflows retain the difficult distinctions: cancellation requested is not confirmed cancellation; a completed effect is not rolled back by interruption; an uncertain outcome is not invented success; publication is not playback.
- Runtime microphone/context consent is kept separate from development-model permission. Native transcript use and provider retention are disclosed without pretending that local storage choices make cloud inference private.
- Meeting 3 explicitly labels GPT-Live/WebRTC/client delegation as provisional post-review research, not unanimous re-voted consensus or tested account access. The exact source ratings/rankings are preserved without fabricated raw scorecards.
- Literal filenames, local references, future statuses, and non-runnable command labels are substantially sound. The pack does not manufacture a passing independent assessment or a working assistant.

## Test gaps and limitations

- The local checker is an inline-link/heading check, **not a full Markdown renderer or semantic contract validator**. Valid targets and present template headings cannot detect missing decision content, circular prerequisites, or incorrect evidence pointers; the findings above required reading the documents.
- Public provider/OpenCode pages were **not fetched in this review**. URL/date preservation and fidelity to the opened local sources/design were checked; current external availability, published API behavior/terms, and authenticated eligibility were not independently certified. Recorded discovery commands and additional parent-supplied diagnostic observations were not rerun.
- No Git commands, code/build/test commands, dependencies, credential/global-file inspection, model/cloud API calls, microphone/audio activity, or nested delegation were used. No code was changed. **Only this review report was edited.** With no Git baseline, historical preservation and authorship claims cannot be independently established from a diff.
- There is intentionally no runtime evidence for actual native media/control failure handling, browser security boundaries, race/idempotency behavior, shared-budget accounting, retention/WAL/backup purge, latency distributions, containment, or hardware/account feasibility. Future RT-A01–RT-A06 and extension gates must supply it under separate authorization. Their absence is not a documentation-only blocker.
- The independent design-stage security disposition was unavailable in the assessed incoming snapshot. This review neither supplies that assessment nor closes DOC-A06 by itself. The delivery manager must record the real review/security dispositions for the assessed revision and commission correction/re-review of blocking findings before accepting PH-DOC.
