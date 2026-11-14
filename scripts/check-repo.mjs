#!/usr/bin/env node
/**
 * Repository guard used by pre-commit and pre-push.
 *
 * Checks:
 *  - forbidden credential files (.env, private keys)
 *  - high-confidence secret patterns
 *  - unresolved merge-conflict markers
 *  - files larger than 2 MiB
 *  - local Markdown file links and heading fragments
 *  - roadmap.md structure, evidence, and phase order (see check-roadmap.mjs)
 *
 * Exit code 1 on any error. External URLs are not fetched.
 */
import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve, sep } from "node:path";
import { checkRoadmap } from "./check-roadmap.mjs";

const root = resolve(
  execFileSync("git", ["rev-parse", "--show-toplevel"], {
    encoding: "utf8",
  }).trim(),
);

const SKIP_DIRS = new Set([".git", "node_modules"]);
const MAX_FILE_BYTES = 2 * 1024 * 1024;
const FORBIDDEN_EXTENSIONS = new Set([".pem", ".key", ".p12", ".pfx"]);

const SECRET_PATTERNS = [
  {
    name: "private key block",
    pattern: /-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/,
  },
  { name: "AWS access key", pattern: /\bAKIA[0-9A-Z]{16}\b/ },
  { name: "GitHub token", pattern: /\bgh[pousr]_[A-Za-z0-9]{36,}\b/ },
  { name: "GitHub fine-grained token", pattern: /\bgithub_pat_[A-Za-z0-9_]{22,}\b/ },
  { name: "OpenAI-style key", pattern: /\bsk-[A-Za-z0-9]{20,}\b/ },
  { name: "Slack token", pattern: /\bxox[baprs]-[A-Za-z0-9-]{10,}\b/ },
  { name: "Google API key", pattern: /\bAIza[0-9A-Za-z_-]{35}\b/ },
  { name: "GitLab token", pattern: /\bglpat-[A-Za-z0-9_-]{20,}\b/ },
];

const errors = [];
const files = [];

function walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue;
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full);
    } else if (entry.isFile()) {
      files.push(full);
    }
  }
}

function isForbiddenName(fileName) {
  return (
    fileName === ".env" ||
    fileName.startsWith(".env.") ||
    FORBIDDEN_EXTENSIONS.has(
      fileName.slice(fileName.lastIndexOf(".")).toLowerCase(),
    )
  );
}

function slugify(heading) {
  return heading
    .replace(/<[^>]+>/g, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}_\-\s]/gu, "")
    .trim()
    .replace(/\s+/g, "-");
}

function anchorsFor(filePath) {
  const anchors = new Set();
  const counts = new Map();
  let fenced = false;

  for (const line of readFileSync(filePath, "utf8").split(/\r?\n/)) {
    if (/^\s*(`{3,}|~{3,})/.test(line)) {
      fenced = !fenced;
      continue;
    }
    if (fenced) continue;

    const heading = line.match(/^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$/);
    if (heading) {
      let slug = slugify(heading[1]);
      const seen = counts.get(slug) ?? 0;
      counts.set(slug, seen + 1);
      if (seen > 0) slug = `${slug}-${seen}`;
      anchors.add(slug);
    }

    for (const match of line.matchAll(
      /<a\s+[^>]*(?:id|name)\s*=\s*["']([^"']+)["']/gi,
    )) {
      anchors.add(match[1]);
    }
  }

  return anchors;
}

function checkMarkdown(filePath) {
  const text = readFileSync(filePath, "utf8");
  const lines = text.split(/\r?\n/);
  let fenced = false;
  let localLinks = 0;
  let fragmentLinks = 0;

  for (let index = 0; index < lines.length; index += 1) {
    const lineNumber = index + 1;
    const rawLine = lines[index];

    if (/^\s*(`{3,}|~{3,})/.test(rawLine)) {
      fenced = !fenced;
      continue;
    }
    if (fenced) continue;

    // Ignore inline code spans so examples are not treated as live links.
    const line = rawLine.replace(/`[^`]*`/g, "");
    const linkMatches = line.matchAll(/!?\[[^\]]*\]\(([^)]+)\)/g);

    for (const match of linkMatches) {
      let href = match[1].trim().replace(/^<|>$/g, "");

      // Drop an optional Markdown title: (path "title").
      const whitespace = href.search(/\s/);
      if (whitespace !== -1) href = href.slice(0, whitespace);

      if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(href)) continue;

      const [rawPath, rawFragment = ""] = href.split("#", 2);
      let pathPart;
      let fragment;
      try {
        pathPart = decodeURIComponent(rawPath);
        fragment = decodeURIComponent(rawFragment);
      } catch {
        errors.push({
          file: relative(root, filePath),
          line: lineNumber,
          target: href,
          reason: "invalid percent-encoding",
        });
        continue;
      }

      const target =
        pathPart.length === 0
          ? filePath
          : resolve(filePath, "..", pathPart);
      localLinks += 1;

      if (
        target !== root &&
        !target.startsWith(root + sep)
      ) {
        errors.push({
          file: relative(root, filePath),
          line: lineNumber,
          target: href,
          reason: "outside repository",
        });
        continue;
      }

      let targetStat;
      try {
        targetStat = statSync(target);
      } catch {
        errors.push({
          file: relative(root, filePath),
          line: lineNumber,
          target: href,
          reason: "missing file",
        });
        continue;
      }

      if (!targetStat.isFile()) {
        errors.push({
          file: relative(root, filePath),
          line: lineNumber,
          target: href,
          reason: "not a file",
        });
        continue;
      }

      if (fragment.length > 0) {
        fragmentLinks += 1;
        const anchors = anchorsFor(target);
        if (!anchors.has(fragment)) {
          errors.push({
            file: relative(root, filePath),
            line: lineNumber,
            target: href,
            reason: "missing heading fragment",
          });
        }
      }
    }
  }

  return { localLinks, fragmentLinks };
}

walk(root);

let markdownFiles = 0;
let localLinks = 0;
let fragmentLinks = 0;

for (const filePath of files) {
  const fileName = filePath.split(sep).pop() ?? "";

  if (isForbiddenName(fileName)) {
    errors.push({
      file: relative(root, filePath),
      line: 0,
      target: fileName,
      reason: "forbidden credential file",
    });
  }

  const size = statSync(filePath).size;
  if (size > MAX_FILE_BYTES) {
    errors.push({
      file: relative(root, filePath),
      line: 0,
      target: `${(size / 1024 / 1024).toFixed(2)} MiB`,
      reason: "file exceeds 2 MiB",
    });
  }

  const text = readFileSync(filePath, "utf8");
  const lines = text.split(/\r?\n/);

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    for (const { name, pattern } of SECRET_PATTERNS) {
      if (pattern.test(line)) {
        errors.push({
          file: relative(root, filePath),
          line: index + 1,
          target: name,
          reason: "possible secret",
        });
      }
    }
  }

  if (/^<<<<<<< /m.test(text) && /^>>>>>>> /m.test(text)) {
    errors.push({
      file: relative(root, filePath),
      line: 0,
      target: "merge conflict markers",
      reason: "unresolved conflict",
    });
  }

  if (filePath.toLowerCase().endsWith(".md")) {
    markdownFiles += 1;
    const counts = checkMarkdown(filePath);
    localLinks += counts.localLinks;
    fragmentLinks += counts.fragmentLinks;
  }
}

errors.push(
  ...checkRoadmap(
    readFileSync(join(root, "roadmap.md"), "utf8"),
    readFileSync(join(root, "phases.md"), "utf8"),
    readFileSync(join(root, "scripts", "roadmap-ids.txt"), "utf8"),
  ),
);

const summary = {
  markdown_files: markdownFiles,
  files_scanned: files.length,
  local_links_checked: localLinks,
  fragment_links_checked: fragmentLinks,
  errors: errors.length,
};

console.log(JSON.stringify(summary, null, 2));

if (errors.length > 0) {
  console.error("\nRepository check failed:");
  for (const error of errors) {
    const location = error.line > 0 ? `${error.file}:${error.line}` : error.file;
    console.error(`- ${location} -> ${error.target} (${error.reason})`);
  }
  process.exit(1);
}
