# -*- coding: utf-8 -*-
"""Check framework: report object, scoring, and the optional extras (credentials, secret leaks, external traces, system protection)."""
import datetime
import glob
import json
import os
import re
import time

from i18n import T

SECRET_PATTERNS = [
    (T("Alibaba Cloud AccessKey"), rb"LTAI[0-9A-Za-z]{12,24}"),
    ("AWS AccessKey", rb"AKIA[0-9A-Z]{16}"),
    (T("Anthropic API key"), rb"sk-ant-[A-Za-z0-9_\-]{20,}"),
    (T("sk- API key (OpenAI / DeepSeek etc.)"), rb"sk-(?:proj-)?[A-Za-z0-9]{32,}"),
    (T("GitHub token"), rb"gh[pousr]_[A-Za-z0-9]{36}"),
    (T("GitLab token"), rb"glpat-[A-Za-z0-9_\-]{20}"),
    (T("Slack token"), rb"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    (T("Google API key"), rb"AIza[0-9A-Za-z_\-]{35}"),
    (T("Private key"), rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"),
    ("JWT", rb"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
]
COMBINED = re.compile(b"|".join(b"(%s)" % p for _, p in SECRET_PATTERNS))

TELEMETRY_ENV = [
    ("DISABLE_TELEMETRY", "disable Statsig / event telemetry"),
    ("DISABLE_ERROR_REPORTING", "disable Sentry error reporting"),
    ("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "disable all non-essential traffic (GrowthBook, update checks)"),
    ("DISABLE_AUTOUPDATER", "disable auto-update"),
    ("DISABLE_BUG_COMMAND", "disable /bug session uploads"),
    ("CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY", "disable feedback surveys"),
]
DENY_HINTS = [(".ssh", "~/.ssh"), (".aws", "~/.aws"), (".env", T(".env files")), ("gh", "~/.config/gh")]

W = {1: 6, 2: 3, 3: 1}
LEVEL_WORD = {1: T("HIGH"), 2: T("MED"), 3: T("LOW")}


class Report:
    def __init__(self, cc, quiet=False):
        self.cc = cc
        self.quiet = quiet
        self.findings = []
        self.sections = []

    def out(self, text):
        if not self.quiet:
            print(text)

    def section(self, title):
        self.sections.append((title, []))
        if self.quiet:
            return
        cc = self.cc
        m = re.match(r"(.+?)(?:[:：]\s*|\s*[(（])(.*?)[)）]?$", title)
        head, sub = (m.group(1), m.group(2)) if m else (title, "")
        print("\n" + cc.BOLD(cc.CYAN("▍" + head)))
        if sub:
            cc.emit(sub, 2, color=cc.DIM)
        print(cc.DIM("  " + "─" * (cc.term_width() - 2)))

    def info(self, text):
        self.sections[-1][1].append(("info", None, text, "", []))
        if self.quiet:
            return
        body = text.lstrip(" ")
        indent = 9 if len(text) - len(body) >= 4 else 2
        if body[:2] in ("● ", "○ "):
            mark = self.cc.RED("● ") if body[0] == "●" else self.cc.DIM("○ ")
            self.cc.emit(body[2:], indent + 2, first=" " * indent + mark)
        else:
            self.cc.emit(body, indent, color=self.cc.DIM)

    def ok(self, text):
        self.sections[-1][1].append(("ok", None, text, "", []))
        if not self.quiet:
            self.cc.emit(text, 4, first="  " + self.cc.GREEN("✓ "))

    def risk(self, level, text, advice="", items=()):
        f = ("risk", level, text, advice, list(items))
        self.sections[-1][1].append(f)
        self.findings.append(f)
        if self.quiet:
            return
        cc = self.cc
        main, _, rest = text.partition("\n")
        print()
        m = re.match(r"(.*?[:：])\s*(~/.*)$", main)
        paths = re.split(r",\s*(?=~/)", m.group(2)) if m else []
        if len(paths) > 1 or (paths and cc.text_width(main) > cc.term_width() - 9):
            cc.emit(m.group(1), 9, first="  " + cc.badge(level) + " ")
            for p in paths:
                cc.emit(p, 11, first=" " * 9 + cc.DIM("· "), hard=True)
        else:
            cc.emit(main, 9, first="  " + cc.badge(level) + " ")
        if rest:
            cc.emit(rest, 9, color=cc.DIM)
        if advice:
            cc.emit(T("Advice: ") + advice, 11, first=" " * 9 + cc.GREEN("→ "), color=cc.GREEN)

    def counts(self):
        return [sum(1 for f in self.findings if f[1] == l) for l in (1, 2, 3)]

    def to_dict(self, mode):
        lv = {1: "high", 2: "medium", 3: "low"}
        return {
            "time": datetime.datetime.now().isoformat(timespec="seconds"),
            "mode": mode,
            "score": self.score(),
            "counts": dict(zip(("high", "medium", "low"), self.counts())),
            "sections": [{"title": t, "rows": [
                {"kind": k, "level": lv.get(l), "text": re.sub(r"\s*\n\s*", " ", x), "advice": a}
                for k, l, x, a, i in rows]} for t, rows in self.sections],
        }

    def score(self):
        n = self.counts()
        return max(0, 100 - min(60, n[0] * W[1]) - min(30, n[1] * W[2]) - min(10, n[2] * W[3]))

    def markdown(self, mode):
        lines = [T("# Claude local fingerprint report"), "",
                 T("- Time: %s") % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 T("- Mode: %s") % mode,
                 T("- Score: **%d / 100** (high %d, medium %d, low %d)") % ((self.score(),) + tuple(self.counts())),
                 ""]
        for title, rows in self.sections:
            lines += ["## " + title, ""]
            for kind, level, text, advice, items in rows:
                if kind == "info":
                    lines.append("- " + text)
                elif kind == "ok":
                    lines.append(T("- OK: ") + text)
                else:
                    lines.append("- **%s** %s" % (LEVEL_WORD[level], text))
                    if advice:
                        lines.append(T("  - Advice: %s") % advice)
            lines.append("")
        return "\n".join(re.sub(r"\033\[[0-9;]*m", "", l) for l in lines)


def mask(b):
    s = b.decode("utf-8", "replace") if isinstance(b, bytes) else b
    if s.startswith("-----BEGIN"):
        return s
    return s[:6] + "..." + "*" * 6 + T(" (length %d)") % len(s)


def tilde(p):
    return p.replace(os.path.expanduser("~"), "~")


def load_json(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

# ───────────────────────── extras ─────────────────────────
def check_credentials(r, cc):
    r.section(T("Extra · Credentials & tokens"))
    H = os.path.expanduser("~")
    cred = os.path.join(H, ".claude/.credentials.json")
    if os.path.exists(cred):
        mode = os.stat(cred).st_mode & 0o777
        r.risk(1, T("~/.claude/.credentials.json stores OAuth access / refresh tokens in plaintext (mode %o%s)") % (
            mode, T(", readable by other users") if mode & 0o044 else ""), T("sign out and delete"), ["A3"])
    found = cc.keychain_present(cc.ITEM_BY_ID["A6"])
    if found:
        r.risk(2, T("%d keychain entries: %s") % (len(found), ", ".join(v for _, v in found)), T("delete the entries"), ["A6"])
    else:
        r.ok(T("No Claude keychain entries"))

    cfgs = glob.glob(H + "/.claude/.mcp.json*") + glob.glob(H + "/Library/Application Support/Claude/claude_desktop_config.json*") + [H + "/.claude.json"]
    tokens = {}
    for p in cfgs:
        d = load_json(p)
        if not d:
            continue
        servers = dict(d.get("mcpServers") or {})
        for proj in (d.get("projects") or {}).values():
            if isinstance(proj, dict):
                servers.update(proj.get("mcpServers") or {})
        for name, s in servers.items():
            if not isinstance(s, dict):
                continue
            env = dict(s.get("env") or {})
            env.update(s.get("headers") or {})
            for k, v in env.items():
                if isinstance(v, str) and re.search(r"key|token|secret|password|auth|cookie", k, re.I) and len(v) >= 8:
                    tokens.setdefault((name, k), set()).add(tilde(p))
            args = " ".join(str(a) for a in (s.get("args") or []))
            if re.search(r"(?:key|token|secret)[=:]\S{8,}", args, re.I):
                tokens.setdefault((name, "args"), set()).add(tilde(p))
    if tokens:
        lines = [T("%s.%s (in %d files)") % (n, k, len(fs)) for (n, k), fs in sorted(tokens.items())]
        r.risk(1, T("%d likely secret fields in MCP configs: %s") % (len(tokens), "; ".join(lines[:12])),
               T("delete the configs and their .bak copies, and rotate these third-party tokens"), ["F1"])
    else:
        r.ok(T("No plaintext secret fields in MCP configs"))


def scan_secrets(r, cc, deep):
    r.section(T("Extra · Secret leaks in sessions & caches (%s)") % (T("deep: includes the Cowork data disk") if deep else T("quick")))
    H = os.path.expanduser("~")
    AS = H + "/Library/Application Support/Claude"
    roots = [H + "/.claude/projects", H + "/.claude/history.jsonl", H + "/.claude/paste-cache",
             H + "/.claude/file-history", H + "/.claude/shell-snapshots", H + "/.claude/session-env",
             H + "/.claude/transcripts", H + "/.claude/sessions", AS + "/local-agent-mode-sessions",
             AS + "/claude-code-sessions", H + "/Library/Logs/Claude"]
    if deep:
        roots.append(AS + "/vm_bundles/claudevm.bundle/sessiondata.img")
    limit = None if deep else 30 * 1024 * 1024
    files = []
    for root in roots:
        if os.path.isfile(root):
            files.append(root)
        elif os.path.isdir(root):
            for cur, _, fs in os.walk(root):
                files += [os.path.join(cur, f) for f in fs]
    hits = {}
    t0 = time.time()
    scanned = 0
    bar = cc.Progress(T("Scanning for secrets"), len(files))
    for i, f in enumerate(files):
        bar.update(i, cc.human(scanned))
        try:
            size = os.path.getsize(f)
        except OSError:
            continue
        if limit and size > limit:
            continue
        try:
            with open(f, "rb") as fp:
                prev = b""
                while True:
                    chunk = fp.read(16 * 1024 * 1024)
                    if not chunk:
                        break
                    buf = prev + chunk
                    for m in COMBINED.finditer(buf):
                        idx = m.lastindex - 1
                        hits.setdefault(idx, {}).setdefault(m.group(0), set()).add(f)
                    prev = buf[-200:]
                    scanned += len(chunk)
        except OSError:
            pass
    bar.done()
    r.info(T("Scanned %d files, %s, in %.0f s%s") % (len(files), cc.human(scanned), time.time() - t0,
                                                 "" if deep else T(" (files over 30 MB skipped; deep mode scans everything incl. the Cowork disk)")))
    if not hits:
        r.ok(T("No secrets in common formats"))
        return
    for idx in sorted(hits):
        name = SECRET_PATTERNS[idx][0]
        vals = hits[idx]
        fs = set().union(*vals.values())
        lvl = 2 if name == "JWT" else 1
        sample = "; ".join("%s @ %s" % (mask(v), tilde(sorted(f)[0])[-60:]) for v, f in list(vals.items())[:3])
        r.risk(lvl, T("%s: %d distinct values in %d files. Examples: %s") % (name, len(vals), len(fs), sample),
               T("these were already sent in conversations; deleting local files is not enough, rotate them at the provider"),
               ["B2", "B3", "B4", "D1"])


def check_telemetry(r, cc, section=True):
    if section:
        r.section(T("Telemetry & reporting settings"))
    H = os.path.expanduser("~")
    st = load_json(H + "/.claude/settings.json") or {}
    env = dict(st.get("env") or {})
    rc_text = ""
    for p in ("~/.zshrc", "~/.zprofile", "~/.zshenv", "~/.bashrc", "~/.profile"):
        try:
            rc_text += open(os.path.expanduser(p), errors="replace").read()
        except OSError:
            pass
    missing = []
    for k, desc in TELEMETRY_ENV:
        src = "settings.json" if k in env else (T("environment") if os.environ.get(k) else (T("shell rc") if re.search(r"\b%s=" % k, rc_text) else ""))
        if src:
            r.ok(T("%s is set (%s)") % (k, src))
        else:
            missing.append(k)
    if missing:
        r.risk(2, T("Not set: %s") % ", ".join(missing),
               T("add them to the env field of ~/.claude/settings.json (template in the README); re-apply after wiping ~/.claude"))
    tel = glob.glob(H + "/.claude/telemetry/*")
    if tel:
        n = 0
        for p in tel:
            try:
                n += open(p, "rb").read().count(b'"event_name"')
            except OSError:
                pass
        r.risk(2, T("%d failed-telemetry files (about %d events) may be re-sent on next launch") % (len(tel), n), T("delete"), ["C1"])
    perms = (st.get("permissions") or {}).get("deny") or []
    joined = " ".join(perms)
    lack = [label for key, label in DENY_HINTS if key not in joined]
    if lack:
        r.risk(2, T("permissions.deny does not block: %s; Claude can read them and send the content as context") % ", ".join(lack),
               T("add rules such as Read(~/.ssh/**) to permissions.deny in settings.json"))
    else:
        r.ok(T("permissions.deny blocks the common sensitive paths"))
    if st.get("cleanupPeriodDays") is None:
        r.risk(3, T("cleanupPeriodDays is not set; transcripts are kept long-term by default"), T("set a short retention, e.g. 7"))


def check_exposure(r, cc):
    r.section(T("Extra · Traces outside the Claude directories"))
    for iid, lvl, tmpl, adv in [
        ("I1", 2, T("Shell history: %s"), T("filter out the matching commands")),
        ("J1", 2, T("Browser: %s"), T("delete the related cookies / history; remove the extension inside the browser")),
        ("H4", 3, T("Browser native messaging hosts: %s"), T("delete")),
        ("K2", 3, T("Other tools' configs referencing Anthropic: %s"), T("edit manually")),
        ("L1", 3, T("Claude files in project repositories: %s"), T("confirm and delete one by one")),
    ]:
        targets, size, desc = cc.resolve(cc.ITEM_BY_ID[iid])
        if targets or desc:
            what = "; ".join(desc[:3]) if desc else T("%d paths, %s") % (len(targets), cc.human(size))
            if iid in ("H4", "L1"):
                what = T("%d paths, %s") % (len(targets), cc.human(size))
            r.risk(lvl, tmpl % what, adv, [iid])
        else:
            r.ok(tmpl % T("not found"))
    bk = cc.BACKUP_ROOT
    if os.path.isdir(bk) and os.listdir(bk):
        plain = [d for d in os.listdir(bk) if os.path.isdir(os.path.join(bk, d))]
        if plain:
            r.risk(1, T("This tool has %d unencrypted backups (%s)") % (len(plain), tilde(bk)), T("convert to an encrypted DMG or delete"))


def check_system(r, cc):
    r.section(T("Extra · System protection"))
    rc, out = cc.run(["fdesetup", "status"])
    if "On" in out:
        r.ok(T("FileVault is on (deleted data is hard to recover from the SSD)"))
    else:
        r.risk(2, T("FileVault is off: %s") % out.strip(), T("turn on FileVault, otherwise deleted files may be recoverable"))
    H = os.path.expanduser("~")
    rc, out = cc.run(["tmutil", "destinationinfo"])
    if "No destinations" in out or not out.strip():
        r.ok(T("No Time Machine destination configured"))
    else:
        rc2, ex = cc.run(["tmutil", "isexcluded", H + "/.claude"])
        if "[Excluded]" in ex:
            r.ok(T("~/.claude is excluded from Time Machine"))
        else:
            r.risk(2, T("Time Machine is configured and ~/.claude is not excluded; old snapshots keep all the data"),
                   T("delete the related backups in Time Machine and run `tmutil addexclusion ~/.claude`"))
    rc, out = cc.run(["tmutil", "listlocalsnapshots", "/"])
    snaps = [l for l in out.splitlines() if "com.apple" in l]
    if snaps:
        r.risk(3, T("%d APFS local snapshots exist; cleaned files can still be recovered from them") % len(snaps),
               T("tmutil deletelocalsnapshots <date>"))
    cloud = H + "/Library/Mobile Documents/com~apple~CloudDocs"
    desk = H + "/Desktop"
    synced = os.path.realpath(desk).startswith(os.path.realpath(cloud))
    if not synced and os.path.isdir(cloud + "/Desktop"):
        try:
            local = set(os.listdir(desk))
            remote = set(os.listdir(cloud + "/Desktop"))
            synced = len(local & remote) >= max(3, len(local) // 2)
        except OSError:
            pass
    tool = os.path.realpath(cc.TOOL_DIR)
    in_cloud = any(k in tool for k in ("CloudDocs", "CloudStorage", "Dropbox"))
    in_synced_desktop = synced and any(tool.startswith(os.path.realpath(H + d) + "/") for d in ("/Desktop", "/Documents"))
    if in_cloud or in_synced_desktop:
        r.risk(1, T("This tool's folder is cloud-synced: its backups, reports and logs are uploaded too (%s)") % tilde(tool),
               T("move this tool folder somewhere unsynced, or turn off Desktop & Documents sync"))
    else:
        r.ok(T("This tool's folder is not in a cloud-synced location"))
    for p in ("~/.claude", "~/Library/Application Support/Claude"):
        real = os.path.realpath(os.path.expanduser(p))
        if "CloudDocs" in real or "Dropbox" in real or "CloudStorage" in real:
            r.risk(1, T("%s lives in a cloud-synced folder (%s)") % (p, real), T("move it out of the synced folder"))


MODES = {
    "fp": T("Fingerprint check"),
    "fp+extra": T("Fingerprint check + extras (credentials, quick secret scan, external traces, system protection)"),
    "fp+extra_deep": T("Fingerprint check + extras (secret scan incl. the Cowork data disk)"),
}


def run(cc, mode="fp", save=True, quiet=False):
    import fingerprint_check
    r = Report(cc, quiet=quiet)
    if not quiet:
        print()
        cc.box([cc.BOLD(T("Claude Fingerprint Detect")) + cc.DIM("  v" + cc.__version__),
                cc.DIM(MODES[mode] + " · " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))])
    fingerprint_check.run_fingerprint(r, cc, check_telemetry)
    if mode != "fp":
        check_credentials(r, cc)
        scan_secrets(r, cc, deep=(mode == "fp+extra_deep"))
        check_exposure(r, cc)
        check_system(r, cc)

    s = r.score()
    if not quiet:
        color = cc.GREEN if s >= 80 else (cc.YELLOW if s >= 50 else cc.RED)
        filled = int(round(s / 5.0))
        meter = color("█" * filled) + cc.DIM("░" * (20 - filled))
        hi, mid, lo = r.counts()
        print()
        cc.box([cc.BOLD(T("Fingerprint exposure score")),
                "",
                "  " + cc.BOLD(color("%3d" % s)) + cc.DIM(" / 100   ") + meter + cc.DIM("   " + T("higher is cleaner")),
                "",
                "  " + cc.badge(1) + " %-4d" % hi + cc.badge(2) + " %-4d" % mid + cc.badge(3) + " %d" % lo])

    if save:
        os.makedirs(cc.REPORT_ROOT, exist_ok=True)
        path = os.path.join(cc.REPORT_ROOT, datetime.datetime.now().strftime("fingerprint_report_%Y%m%d_%H%M%S.md"))
        with open(path, "w", encoding="utf-8") as f:
            f.write(r.markdown(MODES[mode]))
        os.chmod(path, 0o600)
        cc.sys.stderr.write(T("Report saved: %s\n") % tilde(path))

    ids = []
    for f in r.findings:
        for i in f[4]:
            if i not in ids and i in cc.ITEM_BY_ID:
                ids.append(i)
    return ids, r
