/**
 * Roadmap guard: keeps roadmap.md the single path (AGENTS.md section 11).
 * It checks FORM, not truth: it cannot prove the evidence is honest. The real
 * control is human review (.github/CODEOWNERS for roadmap.md and phases.md).
 *
 * Rules:
 *  - phase IDs and order match phases.md exactly
 *  - every checkbox line is strictly '- [ ] R-x.n ...' or '- [x] R-x.n ...' (no '*', no indent, no 'X')
 *  - item IDs are unique and every item lives in a phase or a track section
 *  - a line ends with 'Evidence: none yet' (unticked) or 'Evidence: [label](target), ...' (ticked)
 *  - evidence targets are repo records (docs/, spikes/, tasks/, apps/, scripts/, .github/, a few root files)
 *    or a GitHub pull, commit, or actions run URL of this repository; never README.md, roadmap.md, or '#'
 *  - an [exception: [label](target)] must point into docs/approvals/
 *  - a ticked [human] item must cite a record under docs/approvals/ (a PR link alone is not enough)
 *  - the item IDs and [human] flags equal scripts/roadmap-ids.txt (no silent deletes or re-flagging)
 *  - a done phase has every item ticked; a 'not started' phase has no ticks except exceptions
 *  - no tick in a phase after the Current phase except exceptions; phases before it are done
 */
const ITEM = /^- \[( |x)\] (R-[A-Za-z0-9]+\.[A-Za-z]?\d+)\b(.*)$/;
const ANY_BOX = /^\s*[-*+]\s*\[[^\]]?\]/;
const STATUSES = new Set(["not started", "in progress", "done"]);
const LINK = String.raw`\[[^\]]+\]\(([^)\s]+)\)`;
const EVIDENCE_END = new RegExp(String.raw`Evidence: (${LINK}(?:, ${LINK})*)$`);
const EXCEPTION = new RegExp(String.raw`\[exception: \[[^\]]+\]\(([^)\s]+)\)\]`);
const EVIDENCE_DIRS = ["docs/", "spikes/", "tasks/", "apps/", "scripts/", ".github/"];
const EVIDENCE_ROOT_FILES = new Set(["AGENTS.md", "CONTRIBUTING.md", "LICENSE", "SECURITY.md", "phases.md"]);
const GITHUB_EVIDENCE = /^https:\/\/github\.com\/abhishek3059\/super-agent\/(pull|commit|actions\/runs)\/[A-Za-z0-9]+$/;

export function validEvidence(target) {
  if (GITHUB_EVIDENCE.test(target)) return true;
  if (/^[a-z]+:/i.test(target) || target.startsWith("#") || target.includes("..")) return false;
  const path = target.split("#")[0];
  return EVIDENCE_ROOT_FILES.has(path) || EVIDENCE_DIRS.some((d) => path.startsWith(d) && path.length > d.length);
}

export function checkRoadmap(roadmapText, phasesText, manifestText) {
  const errors = [];
  const err = (line, reason) => errors.push({ file: "roadmap.md", line, target: "roadmap rule", reason });

  const phaseIds = [...phasesText.matchAll(/^### (PH-[A-Z0-9]+)\b/gm)].map((m) => m[1]);
  const lines = roadmapText.split(/\r?\n/);

  const current = roadmapText.match(/^\| Current phase \| (PH-[A-Z0-9]+) \|/m)?.[1];
  if (!current) err(0, "missing 'Current phase' row in the header table");
  else if (!phaseIds.includes(current)) err(0, `Current phase ${current} is not in phases.md`);

  const phases = []; // { id, status, items: [{ticked, id, exception, line}], line }
  let section = null; // a phase object, "track", or null
  const seen = new Set();
  const found = new Map(); // id -> human flag
  lines.forEach((text, i) => {
    const n = i + 1;
    const heading = text.match(/^## (PH-[A-Z0-9]+)\b/);
    if (heading) {
      section = { id: heading[1], status: null, items: [], line: n };
      phases.push(section);
      return;
    }
    if (/^## /.test(text)) {
      section = /^## Parallel track /.test(text) ? "track" : null;
      return;
    }
    const status = text.match(/^\*\*Status:\*\* (.+)$/);
    if (status && section && section !== "track") {
      section.status = status[1].trim();
      if (!STATUSES.has(section.status)) err(n, `invalid status '${section.status}'`);
    }
    if (!ANY_BOX.test(text)) return;
    const item = text.match(ITEM);
    if (!item) return err(n, "checkbox line must be exactly '- [ ] R-x.n ...' or '- [x] R-x.n ...' at column 0");
    const [, mark, id] = item;
    const ticked = mark === "x";
    if (!section) err(n, `${id} is outside any phase or track section`);
    if (seen.has(id)) err(n, `duplicate item id ${id}`);
    seen.add(id);

    const exceptionTarget = text.match(EXCEPTION)?.[1];
    const exception = Boolean(exceptionTarget);
    if (exception && !/^docs\/approvals\/[^#]+/.test(exceptionTarget)) err(n, `${id} exception must link into docs/approvals/`);
    const human = /\[human\]/.test(text);
    found.set(id, human);

    const evidence = text.match(EVIDENCE_END);
    const none = text.endsWith("Evidence: none yet");
    if (ticked) {
      if (!evidence) err(n, `${id} is ticked but the line does not end with 'Evidence: [label](target)'`);
      else {
        const targets = [...evidence[1].matchAll(new RegExp(LINK, "g"))].map((m) => m[1]);
        for (const t of targets) if (!validEvidence(t)) err(n, `${id} evidence '${t}' is not an accepted repo record or GitHub link`);
        if (human && !targets.some((t) => t.startsWith("docs/approvals/"))) err(n, `${id} is [human]: evidence must include a record under docs/approvals/`);
      }
    } else if (!none) {
      err(n, `${id} is unticked, so the line must end with 'Evidence: none yet'`);
    }
    if (section && section !== "track") section.items.push({ ticked, id, exception, line: n });
  });

  const expected = new Map();
  for (const raw of (manifestText ?? "").split(/\r?\n/)) {
    const m = raw.match(/^(R-[A-Za-z0-9]+\.[A-Za-z]?\d+)( human)?$/);
    if (m) expected.set(m[1], Boolean(m[2]));
  }
  if (expected.size === 0) err(0, "scripts/roadmap-ids.txt is missing or empty");
  for (const [id, human] of expected) {
    if (!found.has(id)) err(0, `${id} is in roadmap-ids.txt but missing from roadmap.md (deleted?)`);
    else if (found.get(id) !== human) err(0, `${id} [human] flag differs from roadmap-ids.txt`);
  }
  for (const id of found.keys()) if (!expected.has(id)) err(0, `${id} is in roadmap.md but not in roadmap-ids.txt`);

  const roadmapIds = phases.map((p) => p.id);
  for (const id of phaseIds) if (!roadmapIds.includes(id)) err(0, `${id} is in phases.md but not in roadmap.md`);
  for (const id of roadmapIds) if (!phaseIds.includes(id)) err(0, `${id} is in roadmap.md but not in phases.md`);
  if (roadmapIds.join() !== phaseIds.filter((id) => roadmapIds.includes(id)).join()) err(0, "phase order differs from phases.md");

  const currentIdx = roadmapIds.indexOf(current);
  phases.forEach((p, idx) => {
    if (!p.status) return err(p.line, `${p.id} has no '**Status:**' line`);
    const unticked = p.items.filter((it) => !it.ticked);
    const ticks = p.items.filter((it) => it.ticked && !it.exception);
    if (p.items.length === 0) err(p.line, `${p.id} has no items`);
    if (p.status === "done" && unticked.length) err(p.line, `${p.id} is done but ${unticked[0].id} is not ticked`);
    if (p.status === "not started" && ticks.length) err(ticks[0].line, `${p.id} is 'not started' but ${ticks[0].id} is ticked`);
    if (currentIdx >= 0 && idx < currentIdx && p.status !== "done") err(p.line, `${p.id} comes before the current phase but is not done`);
    if (currentIdx >= 0 && idx > currentIdx && ticks.length) err(ticks[0].line, `${ticks[0].id} is ticked in ${p.id}, which is after the current phase (needs [exception: link])`);
  });
  return errors;
}
