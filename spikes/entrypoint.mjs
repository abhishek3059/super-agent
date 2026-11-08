// Shared direct-execution guard for the A2/A3 spikes (design:
// docs/design/windows-spike-compatibility.md, "Portable entrypoints").
// Compares the importing module's URL against a canonicalized entry path so
// guards work for absolute, relative (to cwd), and URL-encoded argv paths.
// Standard-library only; safe to import from any module.
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

/**
 * @param {string} moduleUrl - the module's `import.meta.url`.
 * @param {string | URL | undefined} [argvPath=process.argv[1]]
 *   the reported entry path (URL or path). A missing entry means the module
 *   was imported (worker, `node -e`, child utils), never direct execution.
 * @returns {boolean}
 */
export function isDirectRun(moduleUrl, argvPath = process.argv[1]) {
  if (typeof moduleUrl !== "string" || moduleUrl === "") return false;
  let entry = argvPath ?? undefined;
  if (typeof entry === "string" && entry === "") entry = undefined;
  let entryHref;
  try {
    entryHref = entry instanceof URL ? entry.href : pathToFileURL(resolve(entry)).href;
  } catch {
    return false;
  }
  return moduleUrl === entryHref;
}
