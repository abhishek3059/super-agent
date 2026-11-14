// node scripts/selftest-roadmap.mjs : proves the roadmap guard catches drift and common bypasses.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { checkRoadmap, validEvidence } from "./check-roadmap.mjs";

const phases = "### PH-A\n### PH-B\n### PH-C\n";
const OK = "Evidence: [rec](docs/implementation/x.md)";
const mk = ({ current = "PH-A", a = "in progress", b = "not started", aItems, bItems, track } = {}) => `| Current phase | ${current} |
## PH-A: one
**Status:** ${a}
${aItems ?? "- [ ] R-A.1 do. Evidence: none yet"}
## PH-B: two
**Status:** ${b}
${bItems ?? "- [ ] R-B.1 do. Evidence: none yet"}
## PH-C: three
**Status:** not started
- [ ] R-C.1 do. Evidence: none yet
## Parallel track X
${track ?? "- [ ] R-X.1 do. Evidence: none yet"}
`;
// By default the manifest is derived from the text, so only the rule under test fires.
const manifestOf = (text) => [...text.matchAll(/^- \[[ x]\] (R-[A-Za-z0-9]+\.[A-Za-z]?\d+)\b(.*)$/gm)].map((m) => m[1] + (m[2].includes("[human]") ? " human" : "")).join("\n");
const reasons = (text, ph = phases, man = manifestOf(text)) => checkRoadmap(text, ph, man).map((e) => e.reason);
const has = (text, part, ph, man) => assert.ok(reasons(text, ph, man).some((r) => r.includes(part)), `expected '${part}' in ${JSON.stringify(reasons(text, ph, man))}`);

assert.deepEqual(reasons(mk()), [], "valid roadmap passes");
assert.deepEqual(reasons(mk({ aItems: `- [x] R-A.1 do. ${OK}, [pr](https://github.com/abhishek3059/super-agent/pull/13)` })), [], "two evidence links pass");

// evidence must exist, be well formed, and be a real record
has(mk({ aItems: "- [x] R-A.1 do. Evidence: none yet" }), "ticked but the line does not end");
has(mk({ aItems: "- [ ] R-A.1 do." }), "must end with 'Evidence: none yet'");
has(mk({ aItems: `- [ ] R-A.1 do. ${OK}` }), "must end with 'Evidence: none yet'");
has(mk({ aItems: "- [x] R-A.1 do. Evidence: [x](README.md)" }), "not an accepted repo record");
has(mk({ aItems: "- [x] R-A.1 do. Evidence: [x](roadmap.md)" }), "not an accepted repo record");
has(mk({ aItems: "- [x] R-A.1 do. Evidence: [x](#)" }), "not an accepted repo record");
has(mk({ aItems: "- [x] R-A.1 do. Evidence: [x](https://example.com/pull/1)" }), "not an accepted repo record");
has(mk({ aItems: "- [x] R-A.1 do. Evidence: [x](docs/../README.md)" }), "not an accepted repo record");
has(mk({ aItems: `- [x] R-A.1 do. ${OK} trailing` }), "ticked but the line does not end");

// format tricks
has(mk({ aItems: `* [x] R-A.1 do. ${OK}` }), "must be exactly");
has(mk({ aItems: `  - [x] R-A.1 do. ${OK}` }), "must be exactly");
has(mk({ aItems: `- [X] R-A.1 do. ${OK}` }), "must be exactly");
has(mk({ aItems: "- [ ] R-A.1 a. Evidence: none yet\n- [ ] R-A.1 b. Evidence: none yet" }), "duplicate item id");
has(mk() + "\n## Notes\n- [ ] R-Z.1 stray. Evidence: none yet\n", "outside any phase or track");

// tracks are checked too
has(mk({ track: "- [x] R-X.1 do. Evidence: [x](README.md)" }), "not an accepted repo record");

// manifest: no silent deletes, extra items, or removed [human] flags
const base = mk({ aItems: "- [ ] R-A.1 [human] do. Evidence: none yet\n- [ ] R-A.2 do. Evidence: none yet" });
assert.deepEqual(reasons(base), [], "manifest derived from text matches");
has(base.replace("- [ ] R-A.2 do. Evidence: none yet\n", ""), "missing from roadmap.md (deleted?)", phases, manifestOf(base));
has(base.replace("[human] ", ""), "[human] flag differs", phases, manifestOf(base));
has(base, "not in roadmap-ids.txt", phases, manifestOf(base).replace("R-A.2", "R-A.9"));
has(base, "roadmap-ids.txt is missing or empty", phases, "");

// [human] ticks need a record under docs/approvals/; a PR link alone is not enough
has(mk({ aItems: `- [x] R-A.1 [human] do. ${OK}` }), "is [human]: evidence must include");
has(mk({ aItems: "- [x] R-A.1 [human] do. Evidence: [pr](https://github.com/abhishek3059/super-agent/pull/9)" }), "is [human]: evidence must include");
assert.deepEqual(reasons(mk({ aItems: "- [x] R-A.1 [human] do. Evidence: [rec](docs/approvals/a.md)" })), [], "approvals record passes");

// order and status
has(mk({ bItems: `- [x] R-B.1 early. ${OK}` }), "'not started' but R-B.1 is ticked");
has(mk({ b: "in progress", bItems: `- [x] R-B.1 early. ${OK}` }), "after the current phase");
assert.deepEqual(reasons(mk({ bItems: `- [x] R-B.1 early. [exception: [rec](docs/approvals/r.md)] ${OK}` })), [], "approved exception passes");
has(mk({ bItems: `- [x] R-B.1 early. [exception: [rec](README.md)] ${OK}` }), "exception must link into docs/approvals/");
has(mk({ bItems: `- [x] R-B.1 early. [exception: [rec](docs/reviews/r.md)] ${OK}` }), "exception must link into docs/approvals/");
has(mk({ a: "done" }), "is done but R-A.1 is not ticked");
has(mk({ current: "PH-B", a: "in progress", b: "in progress" }), "before the current phase but is not done");
has(mk(), "not in roadmap.md", phases + "### PH-D\n");
has(mk(), "not in phases.md", "### PH-A\n### PH-B\n");
has(mk({ a: "finished" }), "invalid status");
has(mk().replace("| Current phase | PH-A |", ""), "missing 'Current phase'");

assert.equal(validEvidence("docs/reviews/super-agent.md#x"), true);
assert.equal(validEvidence("https://github.com/abhishek3059/super-agent/pull/13"), true);
assert.equal(validEvidence("https://github.com/someone-else/repo/pull/1"), false);

// The real files must pass too.
const real = checkRoadmap(readFileSync("roadmap.md", "utf8"), readFileSync("phases.md", "utf8"), readFileSync("scripts/roadmap-ids.txt", "utf8"));
assert.deepEqual(real, [], `real roadmap has errors: ${JSON.stringify(real)}`);
console.log("roadmap self-test: all checks passed");
