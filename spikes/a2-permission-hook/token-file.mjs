// Internal A2 helper: staged, verified, private creation of the approval
// server token file (design: docs/design/windows-spike-compatibility.md,
// "Token file lifecycle"). Shared by the CLI startup in server.mjs and the
// selftest only. Fails closed: any protection uncertainty aborts the startup,
// keeps the listener closed, and removes only files this startup created.
//
// Windows ACL work uses fixed native tools resolved from the system directory
// with argument arrays and shell:false. Tokens never enter arguments or logs.
// Every native call is bounded (5 s / 64 KiB) and verified from `icacls /save`
// SDDL output (observed UTF-16LE without BOM), never localized display text.
import { execFile } from "node:child_process";
import {
  chmodSync,
  closeSync,
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  openSync,
  readFileSync,
  realpathSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";

const NATIVE_TIMEOUT_MS = 5_000; // bounding value from the design
const MAX_NATIVE_OUTPUT = 64 * 1024;
const STAGING_PREFIX = "spike-token-";

// Write-capable rights that others must NOT hold on the token's parent.
const GENERIC_RIGHTS = 0x10000000 | 0x40000000;
const WRITE_BITS = (0x10000 | 0x40000 | 0x80000 | 0x100 | 0x40 | 0x2 | 0x4) | GENERIC_RIGHTS; // Includes directory delete-child, not just deletion of the directory itself.
const READONLY_RIGHTS = /^(R|RX|X|FR|FX|GR)$/i;
const TRUSTED_OWNER_SIDS = ["S-1-5-18", "S-1-5-32-544"]; // SYSTEM, BUILTIN\Administrators
const TRUSTED_ALIASES = new Set(["SY", "BA", "LA"]); // SYSTEM, Administrators, and the local Administrator account

/** Error carrying a fixed safe diagnostic category; messages never embed tokens. */
const category = (c, message) => Object.assign(new Error(message), { category: c });

// Fixed system directory, never PATH or a caller-selected executable.
const sysTool = (name) => {
  const root = process.env.SystemRoot ?? process.env.windir ?? "C:\\Windows";
  return join(root, "System32", name);
};

/**
 * Run a native (Windows) tool with bounds. `run` is injectable for selftest
 * failure injection; the default resolves with `{ stdout: Buffer }`.
 */
function runNative(argv, { timeoutMs = NATIVE_TIMEOUT_MS } = {}) {
  return new Promise((done, fail) => {
    execFile(argv[0], argv.slice(1), { timeout: timeoutMs, maxBuffer: MAX_NATIVE_OUTPUT, shell: false, windowsHide: true }, (err, stdout) => {
      if (!err) return done({ stdout: typeof stdout === "string" ? Buffer.from(stdout) : stdout });
      fail(
        err.killed
          ? category("native-timeout", "native tool timed out")
          : err.code === "ENOENT"
            ? category("native-tool-missing", "native tool not found in system directory")
            : category("native-exit", `native tool exited with ${Number.isFinite(err.code) ? err.code : "unknown status"}`),
      );
    });
  });
}

// Normalize uncategorized injected-run failures into the same fixed categories
// so selftest injections behave like real process failures.
const wrapRun = (run) => async (argv, opts) => {
  try {
    return await run(argv, opts);
  } catch (err) {
    if (err?.category) throw err;
    if (err?.killed) throw category("native-timeout", "native tool timed out");
    if (err?.code === "ENOENT") throw category("native-tool-missing", "native tool not found in system directory");
    throw category("native-exit", `native tool exited with ${Number.isFinite(err?.code) ? err.code : "unknown status"}`);
  }
};

/** Decode `icacls /save` output: UTF-16LE without BOM (observed) or UTF-8. */
function decodeDump(buf) {
  if (buf.length > 1 && buf[0] === 0xff && buf[1] === 0xfe) return buf.subarray(2).toString("utf16le");
  if (buf.length > 1 && buf[1] === 0) return buf.toString("utf16le");
  return buf.toString("utf8");
}

/**
 * Parse exactly one `D:` SDDL line from bounded /save output. Returns
 * `{ flags, aces }`. Structural anomalies throw with safe categories so the
 * caller fails closed (NULL/empty DACLs, unknown shapes, unexpected SACL).
 * Trailing junk outside complete ACE groups is rejected; every ACE must be a
 * full (reconstructed) 6-field body.
 */
export function parseDaclDump(text) {
  const lines = text.split(/\r?\n/).filter((l) => l.trim() !== "");
  const daclLines = lines.filter((l) => /^D:[A-Z(]/.test(l)); // path lines start "D\"; ignore them
  if (lines.some((l) => /^S:[A-Z(]/.test(l))) throw category("acl-format", "unexpected SACL in dump");
  if (daclLines.length !== 1) throw category("acl-format", "expected a single DACL line");
  const m = /^D:([A-Z]*)(.*)$/.exec(daclLines[0]);
  if (!m) throw category("acl-format", "unrecognized DACL descriptor");
  const rest = m[2];
  const aceBodies = [...rest.matchAll(/\(([^()]*)\)/g)].map((x) => x[1]);
  if (aceBodies.length === 0) throw category("acl-format", "empty DACL");
  const remainder = rest.replace(/\([^()]*\)/g, "").trim();
  const reconstructed = aceBodies.map((b) => `(${b})`).join("");
  if (remainder !== "" || reconstructed !== rest) throw category("acl-format", "stray characters in DACL");
  const aces = aceBodies.map((body) => {
    const parts = body.split(";");
    if (parts.length !== 6) throw category("acl-format", "malformed ACE");
    const [type, aceFlags, rights, obj, objInherit, trustee] = parts;
    if (!/^[A-Z]*$/.test(aceFlags) || !/^[A-Z0-9;x]*$/i.test(rights)) throw category("acl-format", "unrecognized ACE fields");
    return { type, flags: aceFlags, rights, obj, objInherit, trustee };
  });
  return { flags: m[1], aces };
}

// Protected from inheritance (P), optionally marked auto-inherited (observed
// "PAI" form). Rejects "D:AI(...)" DACLs with enabled inheritance.
const DACL_FLAG_OK = /^P(AI)?$/;

/** True only when the DACL is a protected, owner-only allow grant for `sid`. */
function verifyOwnerOnly({ flags, aces }, sid, { requireInheritable = false } = {}) {
  if (!DACL_FLAG_OK.test(flags)) throw category("acl-verify", "dacl is not protected from inheritance");
  if (aces.length !== 1) throw category("acl-verify", "unexpected principals in DACL");
  const { type, flags: aceFlags, rights, obj, objInherit, trustee } = aces[0];
  if (!/^[A-Z]*$/.test(aceFlags) || !/^[A-Z0-9;x]*$/i.test(rights)) throw category("acl-format", "unrecognized ACE fields");
  if (type !== "A") throw category("acl-verify", "non-allow ACE in DACL");
  if (aceFlags !== (requireInheritable ? "OICI" : "")) throw category("acl-verify", "unexpected ACE inheritance flags");
  if (rights !== "FA") throw category("acl-verify", "unexpected rights");
  if (obj !== "" || objInherit !== "") throw category("acl-verify", "(guid) object ACE not expected");
  const normalizedTrustee = trustee.toUpperCase();
  const normalizedSid = sid.toUpperCase();
  const isLocalAdministratorAlias = normalizedTrustee === "LA" && normalizedSid.endsWith("-500");
  if (normalizedTrustee !== normalizedSid && !isLocalAdministratorAlias) throw category("acl-verify", "unexpected principal");
}

/**
 * Parent must not be shared-writable: only the current SID, SYSTEM, and
 * BUILTIN\Administrators may hold write rights; every other principal must be
 * explicitly read-only (observed sibling entries carry numeric 0x1200a9
 * read+execute). Any non-allow ACE, malformed trustee, or unknown shape
 * fails closed.
 */
function verifyParentAcl(dumpText, sid) {
  const { aces } = parseDaclDump(dumpText);
  for (const { type, trustee, rights } of aces) {
    if (type !== "A") throw category("parent-untrusted", "unexpected ACE type on parent");
    const t = trustee.toUpperCase();
    const numeric = /^S-1-(0|[1-9]\d*)(-\d+)+$/.test(trustee) && trustee.length <= 68;
    const symbolic = /^[A-Z0-9]{2}$/.test(t); // Standard SDDL aliases are locale-independent two-character codes.
    const trusted = TRUSTED_ALIASES.has(t) || (numeric && (t === sid.toUpperCase() || TRUSTED_OWNER_SIDS.includes(t)));
    if (!trusted && !numeric && !symbolic) throw category("parent-untrusted", "unrecognized trustee on parent");
    if (trusted) continue;
    const upper = rights.toUpperCase();
    const numericRights = upper.startsWith("0X") ? Number.parseInt(upper, 16) : Number.NaN;
    if (Number.isFinite(numericRights)) {
      if ((numericRights & WRITE_BITS) !== 0) throw category("parent-untrusted", "unprivileged write grant on parent");
    } else if (!READONLY_RIGHTS.test(upper)) {
      throw category("parent-untrusted", "unprivileged write grant on parent");
    }
  }
}

// POSIX equivalent: the parent must be user-owned and not group/other-write.
function verifyParentPosix(path) {
  const st = statSync(path);
  const uid = process.getuid?.();
  if (uid === undefined || st.uid !== uid || (st.mode & 0o022) !== 0) throw category("parent-untrusted", "target parent is not user-owned private");
}

/** Rejects anything but a real, non-reparse directory at `path`. */
function assertRealDirectory(path) {
  let st;
  try { st = lstatSync(path); } catch { throw category("parent-directory", "target parent is not a directory"); }
  if (!st.isDirectory() || st.isSymbolicLink()) throw category("parent-directory", "target parent is not a plain directory");
  if (process.platform !== "win32") return;
  let real;
  try { real = realpathSync(path); } catch { throw category("parent-directory", "cannot resolve target parent"); }
  if (real.toLowerCase() !== resolve(path).toLowerCase()) throw category("parent-reparse", "target parent is a reparse point");
}

/** Rejects symlinks and unexpected existing target types. */
function assertPublishableTarget(target) {
  if (!existsSync(target)) return;
  const st = lstatSync(target);
  if (st.isSymbolicLink() || !st.isFile()) throw category("target-type", "unexpected existing target type");
}

async function saveDacl(targetPath, dumpPath, { run, timeoutMs }) {
  await run([sysTool("icacls.exe"), targetPath, "/save", dumpPath], { timeoutMs });
  let buf;
  try { buf = readFileSync(dumpPath); } catch { throw category("acl-verify", "acl dump unreadable"); }
  rmSync(dumpPath, { force: true }); // dumps live only inside the private staging dir
  return buf;
}

async function verifyDacl(targetPath, sid, stagingDir, { run, timeoutMs, slug, requireInheritable = false }) {
  const buf = await saveDacl(targetPath, join(stagingDir, `acl-${slug}.tmp`), { run, timeoutMs });
  verifyOwnerOnly(parseDaclDump(decodeDump(buf)), sid, { requireInheritable });
}

function assertMode(path, wanted) {
  const st = statSync(path);
  if ((st.mode & 0o777) !== wanted) throw category("mode-verify", `unexpected file mode (wanted ${wanted.toString(8)})`);
}

/**
 * Create, protect, verify, and atomically publish the token at `target`.
 * Order: staging dir + exclusively created file -> parent trust check ->
 * protect -> verify -> write token -> publish (rename on the same volume) ->
 * reverify published object. On any failure: throw with `.category`; cleanup
 * removes only files this startup created (staging dir, dump files, its own
 * published token, or the pre-existing token restored from the same-volume
 * snapshot taken before the publish replaced it).
 */
export async function writeTokenFile({ target, token, run: injectedRun = runNative, timeoutMs = NATIVE_TIMEOUT_MS } = {}) {
  if (typeof target !== "string" || target === "") throw category("argument", "missing target");
  if (typeof token !== "string" || token === "") throw category("argument", "missing token");
  const run = wrapRun(injectedRun);
  const parent = dirname(target);
  let stagingDir = null;
  let published = false;
  let hadTarget = false;
  let backup = null;
  try {
    try {
      mkdirSync(parent, { recursive: true, mode: 0o700 });
    } catch (err) {
      if (err?.category) throw err;
      throw category("parent-create", "cannot create target parent directory");
    }
    assertRealDirectory(parent);
    assertPublishableTarget(target);
    hadTarget = existsSync(target);
    stagingDir = mkdtempSync(join(parent, STAGING_PREFIX), { mode: 0o700 });
    const stagingFile = join(stagingDir, "token");
    closeSync(openSync(stagingFile, "wx", 0o600)); // exclusive; a symlink/junction at the name fails here
    const ic = [sysTool("icacls.exe")];
    if (process.platform === "win32") {
      assertRealDirectory(stagingDir);
      const sid = await windowsCurrentSid({ run, timeoutMs });
      // The parent must not be shared-writable; verified before any token
      // materializes anywhere outside the private staging dir.
      const parentDump = await saveDacl(parent, join(stagingDir, "acl-parent.tmp"), { run, timeoutMs });
      verifyParentAcl(decodeDump(parentDump), sid);
      // Fresh objects start from an empty DACL once inherited grants are
      // removed (and writes fail on an empty DACL: probe evidence), so grant
      // first, strip inheritance, and set the owner last.
      await run([...ic, stagingDir, "/grant", `*${sid}:(OI)(CI)F`], { timeoutMs }); // inheritable into staging files
      await run([...ic, stagingDir, "/inheritance:r"], { timeoutMs });
      await run([...ic, stagingDir, "/setowner", `*${sid}`], { timeoutMs });
      await verifyDacl(stagingDir, sid, stagingDir, { run, timeoutMs, slug: "dir", requireInheritable: true });
      await run([...ic, stagingFile, "/grant", `*${sid}:F`], { timeoutMs });
      await run([...ic, stagingFile, "/inheritance:r"], { timeoutMs });
      await run([...ic, stagingFile, "/setowner", `*${sid}`], { timeoutMs });
      await verifyDacl(stagingFile, sid, stagingDir, { run, timeoutMs, slug: "staging" });
      // Only after protection is established and verified, write the token.
      writeFileSync(stagingFile, token);
    } else {
      verifyParentPosix(parent);
      assertMode(stagingDir, 0o700);
      assertMode(stagingFile, 0o600); // verified before writing
      writeFileSync(stagingFile, token);
    }
    if (existsSync(target)) {
      backup = join(stagingDir, "previous");
      writeFileSync(backup, readFileSync(target), { mode: 0o600 }); // restore-on-failure snapshot, itself private
    }
    renameSync(stagingFile, target); // atomic publish on the same volume
    published = true;
    if (process.platform === "win32") {
      const sid = await windowsCurrentSid({ run, timeoutMs });
      await verifyDacl(target, sid, stagingDir, { run, timeoutMs, slug: "published" });
    } else {
      chmodSync(target, 0o600); // replacement must not preserve a less-restricted old mode
      assertMode(target, 0o600);
    }
  } catch (err) {
    if (published) {
      if (hadTarget && backup) {
        try { renameSync(backup, target); } catch {} // restore the pre-existing token, published now from this startup's protected staging copy
      } else {
        rmSync(target, { force: true }); // our unprotected published token: remove it
      }
    }
    throw err;
  } finally {
    if (stagingDir) rmSync(stagingDir, { recursive: true, force: true }); // removes staging file, dumps, backup
  }
}

/** Current process SID via fixed `whoami`; validated, never resolved via PATH. */
export async function windowsCurrentSid({ run = runNative, timeoutMs = NATIVE_TIMEOUT_MS } = {}) {
  const { stdout } = await run([sysTool("whoami.exe"), "/user", "/fo", "csv", "/nh"], { timeoutMs });
  const line = stdout.toString("utf8").trim();
  if (line.split(/\r?\n/).length !== 1) throw category("sid-format", "unexpected whoami output");
  const sid = /^"[^"]*"\s*,\s*"([^"]+)"$/.exec(line)?.[1];
  if (!sid || !/^S-1-\d{1,10}(-\d{1,10}){1,14}$/.test(sid) || sid.length > 68) throw category("sid-format", "malformed SID");
  return sid;
}
