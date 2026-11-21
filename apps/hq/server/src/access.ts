import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { env } from './env.js';

/**
 * What a bot may read beyond its own folders: folders the operator lists (HQ_READ_DIRS) and skill
 * folders (HQ_SKILL_DIRS), read-only. Never anything that holds secrets or HQ's own state, even if
 * listed: a folder inside one of those, or one that contains one (the home folder), is dropped.
 */

const home = os.homedir();
const real = (p: string) => { try { return fs.realpathSync(p); } catch { return null; } };
const inside = (child: string, parent: string) => child === parent || child.startsWith(parent + path.sep);

export function secretPlaces(): string[] {
  return [
    ...['.ssh', '.gnupg', '.aws', '.azure', '.kube', '.docker', '.config', '.netrc', '.npmrc', '.codex', '.claude', '.claude.json', 'Library', '.super-agent']
      .map((d) => path.join(home, d)),
    env.dataDir, env.hermesHome, path.join(home, '.hermes'),
  ].map((p) => real(p) ?? path.resolve(p));
}

/** Real paths of the listed folders that are safe to open read-only. `skills` lets the skills subfolders of ~/.hermes and ~/.claude through. */
export function safeDirs(list: string[], opts: { skills?: boolean } = {}): string[] {
  const secrets = secretPlaces();
  // The only ways into a closed folder: its skills subfolder, for skill folders.
  const skillRoots = ['.hermes', '.claude'].map((d) => real(path.join(home, d, 'skills'))).filter((d): d is string => !!d);
  const out = new Set<string>();
  for (const raw of list) {
    const p = raw.trim().replace(/^~(?=$|\/)/, home);
    if (!p || !path.isAbsolute(p)) continue;
    const r = real(p);
    if (!r || !fs.statSync(r).isDirectory() || r === '/' || r === home || r === '/Users') continue;
    const skillOk = opts.skills && skillRoots.some((root) => inside(r, root));
    if (secrets.some((s) => inside(s, r))) continue; // it would open a secret folder
    if (!skillOk && secrets.some((s) => inside(r, s))) continue;
    out.add(r);
  }
  return [...out];
}

/** Skill folders, plus where their linked skills really live (skill folders are often links). */
export function skillReadDirs(dirs: string[]): string[] {
  const links: string[] = [];
  // An unreadable folder is skipped: it must not stop the bot from starting.
  const list = (d: string) => { try { return fs.readdirSync(d, { withFileTypes: true }); } catch { return []; } };
  for (const d of dirs) {
    for (const a of list(d).slice(0, 1000)) {
      const p = path.join(d, a.name);
      if (a.isSymbolicLink()) links.push(p);
      else if (a.isDirectory()) for (const b of list(p).slice(0, 200)) if (b.isSymbolicLink()) links.push(path.join(p, b.name));
    }
  }
  return safeDirs([...dirs, ...links.map((l) => real(l) ?? '').filter(Boolean)], { skills: true });
}

const split = (v: string | undefined, fallback: string) => (v ?? fallback).split(path.delimiter).filter(Boolean);

// Optional Linux bind mounts could expose host IPC endpoints even when mounted read-only.
export const readDirs = () => process.platform === 'darwin' ? safeDirs(split(process.env.HQ_READ_DIRS, '')) : [];
export const skillDirs = () => process.platform === 'darwin' ? safeDirs(split(process.env.HQ_SKILL_DIRS, ''), { skills: true }) : [];
export const systemInfoOn = () => process.env.HQ_SYSTEM_INFO === '1';
/** Skills any bot creates to share; every bot reads and writes it. */
export const sharedSkillsDir = () => path.join(env.dataDir, 'shared-skills');
