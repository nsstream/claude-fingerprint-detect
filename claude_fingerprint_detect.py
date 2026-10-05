#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claude-fingerprint-detect: fingerprint check, scan, backup, clean and verify Claude traces on macOS.

Standard library only; works with the python3 (3.9) that ships with macOS. Makes no network requests.
Nothing is deleted without confirmation: every clean lists what will be removed and asks first.
"""
import datetime
import getpass
import glob
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import unicodedata
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i18n
from i18n import T

i18n.init(sys.argv)

__version__ = "1.1.0"
HOME = os.path.expanduser("~")
TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
PROG = (os.environ.get("CFD_PROG") or ("cfd" if shutil.which("cfd") else "")
        or "python3 " + os.path.abspath(__file__).replace(HOME, "~"))
BACKUP_ROOT = os.path.join(TOOL_DIR, "backups")
LOG_ROOT = os.path.join(TOOL_DIR, "logs")
REPORT_ROOT = os.path.join(TOOL_DIR, "reports")
TMP = os.environ.get("TMPDIR", "/tmp").rstrip("/")
AS = "~/Library/Application Support/Claude"
DOMAINS = ["claude.ai", "claude.com", "anthropic.com", "claudeusercontent.com"]
KEYWORDS = [b"claude", b"anthropic"]
BIG_ITEM = 2 * 1024 ** 3
FULLWIDTH_COMMA = "\uff0c"
REPO_ROOT_CANDIDATES = ["~/Workspace", "~/Projects", "~/Developer", "~/Code", "~/code", "~/src", "~/dev",
                        "~/repos", "~/GitHub", "~/git", "~/Documents/GitHub"]


def default_repo_roots():
    roots, seen = [], set()
    for r in REPO_ROOT_CANDIDATES:
        real = os.path.realpath(os.path.expanduser(r)).lower()
        if os.path.isdir(real) and real not in seen:
            seen.add(real)
            roots.append(r)
    return roots


SETTINGS = {
    "delete_mode": "trash",          # trash | rm
    "repo_roots": default_repo_roots(),
    "assume_yes": False,             # CLI --yes: answer "yes" to every confirmation
    "include_big": False,            # CLI --include-big: include items larger than 2 GB in backups
    "dmg": True,                     # CLI --no-dmg: skip the encrypted DMG step
}

# ───────────────────────── terminal output ─────────────────────────
def c(text, code):
    return "\033[%sm%s\033[0m" % (code, text) if sys.stdout.isatty() else text

RED = lambda t: c(t, "31")
GREEN = lambda t: c(t, "32")
YELLOW = lambda t: c(t, "33")
CYAN = lambda t: c(t, "36")
BOLD = lambda t: c(t, "1")
DIM = lambda t: c(t, "2")


_log_fp = None


def log(msg, echo=True):
    global _log_fp
    if _log_fp is None:
        os.makedirs(LOG_ROOT, exist_ok=True)
        name = datetime.datetime.now().strftime("run_%Y%m%d_%H%M%S.log")
        _log_fp = open(os.path.join(LOG_ROOT, name), "a", encoding="utf-8")
    _log_fp.write("[%s] %s\n" % (datetime.datetime.now().strftime("%H:%M:%S"), re.sub(r"\033\[[0-9;]*m", "", msg)))
    _log_fp.flush()
    if echo:
        print(msg)


_stdin_closed = False


def ask(prompt, default=""):
    global _stdin_closed
    try:
        s = input(prompt).strip()
    except EOFError:
        print()
        _stdin_closed = True
        return default
    return s or default


def confirm(prompt, default=False):
    if SETTINGS["assume_yes"]:
        print(T("%s [auto: yes]") % prompt)
        return True
    hint = "[Y/n]" if default else "[y/N]"
    body = prompt.lstrip("\n")
    s = ask(prompt[:len(prompt) - len(body)] + CYAN("? ") + body + " " + DIM(hint) + " ").lower()
    if _stdin_closed:
        return False
    if not s:
        return default
    return s in ("y", "yes")


def human(n):
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024 or unit == "T":
            return ("%.1f%s" % (n, unit)) if unit != "B" else ("%d%s" % (n, unit))
        n /= 1024.0


def run(cmd, sudo=False, capture=True):
    if sudo:
        cmd = ["sudo"] + cmd
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE if capture else None,
                           stderr=subprocess.PIPE if capture else None)
        out = (p.stdout or b"").decode("utf-8", "replace") if capture else ""
        return p.returncode, out
    except FileNotFoundError:
        return 127, ""


def text_width(s):
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s)


def clip(s, width):
    out, w = "", 0
    for ch in s:
        w += text_width(ch)
        if w > width:
            return out + "…"
        out += ch
    return s


ANSI = re.compile(r"\033\[[0-9;]*m")
_WRAP_TOKEN = re.compile(r"\033\[[0-9;]*m|[^\s\u2e80-\uffff]+\s*|\s+|.")


def visible_width(s):
    return text_width(ANSI.sub("", s))


def term_width():
    return max(40, min(shutil.get_terminal_size((100, 20)).columns - 1, 110))


def wrap(text, width, hard=False):
    """Wrap one paragraph to a display width: Latin words stay whole, CJK breaks anywhere, ANSI codes are free.
    hard=True breaks at the width regardless of spaces (for paths)."""
    if hard:
        lines = []
        while text_width(text) > width:
            head = clip(text, width - 1)[:-1]
            lines.append(head)
            text = text[len(head):]
        return lines + [text]
    lines, cur, w = [], "", 0
    for tok in _WRAP_TOKEN.findall(text):
        if tok.startswith("\033"):
            cur += tok
            continue
        tw = text_width(tok)
        if w + tw > width and w:
            lines.append(cur.rstrip())
            cur, w = "", 0
            tok = tok.lstrip()
            tw = text_width(tok)
        while tw > width:
            head = clip(tok, width - 1)[:-1]
            lines.append(head)
            tok = tok[len(head):]
            tw = text_width(tok)
        cur += tok
        w += tw
    lines.append(cur.rstrip())
    return lines


def emit(text, indent=0, first="", color=None, hard=False):
    """Print text wrapped to the terminal; `first` replaces the indent on the first line."""
    width = term_width() - indent
    pad = " " * indent
    for n, para in enumerate(text.split("\n")):
        for m, line in enumerate(wrap(para.strip(), width, hard)):
            lead = first if (n == 0 and m == 0 and first) else pad
            print(lead + (color(line) if color else line))


def box(lines, width=None):
    width = width or min(term_width(), 72)
    inner = width - 4
    print(DIM("╭" + "─" * (width - 2) + "╮"))
    for line in lines:
        print(DIM("│ ") + line + " " * max(0, inner - visible_width(line)) + DIM(" │"))
    print(DIM("╰" + "─" * (width - 2) + "╯"))


def heading(title, sub=""):
    print("\n" + BOLD(CYAN("▍" + title)))
    if sub:
        emit(sub, 2, color=DIM)
    print(DIM("  " + "─" * (term_width() - 2)))


def row(left, right="", indent=2):
    """`left ······ right`, right-aligned to the terminal width."""
    width = term_width()
    room = width - indent - visible_width(right) - 6
    if visible_width(left) > room:
        left = clip(ANSI.sub("", left), room)
    gap = width - indent - visible_width(left) - visible_width(right)
    print(" " * indent + left + (" " + DIM("·" * (gap - 2)) + " " if right else "") + right)


def menu(rows, prompt_default=""):
    """rows: (key, label, description). Returns the answer."""
    lw = max(text_width(r[1]) for r in rows)
    print()
    for key, label, desc in rows:
        print("  " + BOLD(CYAN(key)) + "  " + label + (" " * (lw - text_width(label) + 3) + DIM(desc) if desc else ""))
    return ask("\n" + CYAN("› "), prompt_default)


def badge(level):
    word = {1: T("HIGH"), 2: T("MED"), 3: T("LOW")}[level]
    word = " %s " % (word + " " * (4 - text_width(word)))
    return c(word, {1: "1;97;41", 2: "1;30;43", 3: "30;47"}[level])


class Progress:
    """Single-line progress bar on stderr; silent when stderr is not a terminal."""
    SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, label, total):
        self.label, self.total = label, max(total, 1)
        self.tty = sys.stderr.isatty()
        self.t0 = self.last = time.time()
        self.frame = 0

    def update(self, n, detail=""):
        now = time.time()
        if not self.tty or (now - self.last < 0.08 and n < self.total):
            return
        self.last = now
        self.frame += 1
        cols = shutil.get_terminal_size((80, 20)).columns
        pct = min(n / float(self.total), 1.0)
        elapsed = now - self.t0
        eta = ""
        if n and elapsed > 1 and n < self.total:
            left = int(elapsed * (self.total - n) / n)
            eta = T("%s left") % ("%d:%02d" % divmod(left, 60))
        total_s = format(self.total, ",")
        count = ("%s/%s" % (format(n, ","), total_s)).rjust(len(total_s) * 2 + 1)
        right = " %3d%%  %s  " % (pct * 100, count)
        right_w = len(right) + text_width(T("%s left") % "00:00")
        if cols < 64:
            eta, right_w = "", len(right)
        label = clip(self.label, max(6, cols - 1 - right_w - 6 - 10))
        head_w = text_width(label) + 6
        bar_w = max(10, min(36, cols - 1 - head_w - right_w))
        fill = int(round(bar_w * pct))
        spin = self.SPIN[self.frame % len(self.SPIN)]
        head = "  \033[36m%s\033[0m %s  " % (spin, label)
        bar = "\033[36m" + "━" * fill + "\033[0m\033[2m" + "─" * (bar_w - fill) + "\033[0m"
        line_w = head_w + bar_w + len(right) + text_width(eta)
        room = cols - 1 - line_w - 2
        tail = ("  \033[2m" + clip(detail, room - 1) + "\033[0m") if detail and room > 8 else ""
        sys.stderr.write("\r\033[K" + head + bar + right + "\033[2m" + eta + "\033[0m" + tail)
        sys.stderr.flush()

    def done(self):
        if self.tty:
            sys.stderr.write("\r\033[K")
            sys.stderr.flush()

# ───────────────────────── risk catalog ─────────────────────────
CATEGORIES = [
    ("A", T("Identity & credentials")),
    ("B", T("Sessions & content")),
    ("C", T("Telemetry, logs & crash reports")),
    ("D", T("Cowork virtual machine")),
    ("E", T("Desktop app embedded browser data (cookies / storage / cache)")),
    ("F", T("Config, MCP, plugins & skills")),
    ("G", T("Application files & leftover directories")),
    ("H", T("macOS system integration traces")),
    ("I", T("Shell history")),
    ("J", T("External browsers (Chromium family)")),
    ("K", T("Claude leftovers in third-party tools")),
    ("L", T("Claude files inside project repositories")),
]
CAT_NAME = dict(CATEGORIES)

NMH = "NativeMessagingHosts/com.anthropic.*"
BROWSER_ROOTS = {
    "Chrome": ("~/Library/Application Support/Google/Chrome", "Google Chrome"),
    "Chromium": ("~/Library/Application Support/Chromium", "Chromium"),
    "Edge": ("~/Library/Application Support/Microsoft Edge", "Microsoft Edge"),
    "Brave": ("~/Library/Application Support/BraveSoftware/Brave-Browser", "Brave Browser"),
    "Arc": ("~/Library/Application Support/Arc/User Data", "Arc"),
    "Vivaldi": ("~/Library/Application Support/Vivaldi", "Vivaldi"),
}


def item(id, cat, level, name, kind="path", paths=(), note="", sudo=False, **kw):
    d = dict(id=id, cat=cat, level=level, name=name, kind=kind, paths=list(paths), note=note, sudo=sudo)
    d.update(kw)
    return d


ITEMS = [
    # A identity & credentials
    item("A1", "A", 1, T("Claude Code account & device IDs (userID / machineID / oauthAccount / email) and all backups"),
         paths=["~/.claude.json", "~/.claude.json.*"],
         note=T("Deleting only the main file is not enough: .backup / .bak* hold the same userID")),
    item("A2", "A", 1, T("Claude Code config backup directory"), paths=["~/.claude/backups"]),
    item("A3", "A", 1, T("Claude Code plaintext OAuth tokens"), paths=["~/.claude/.credentials.json"]),
    item("A4", "A", 1, T("Desktop app device ID (ant-did), device registry, hardware probe"),
         paths=[AS + "/ant-did", AS + "/ant-device-registry.json", AS + "/vm-support-probe.json"]),
    item("A5", "A", 1, T("Desktop app account config, tokens and remote-session bridge state"),
         paths=[AS + "/config.json", AS + "/config.json.journal", AS + "/buddy-tokens.json",
                AS + "/bridge-state.json"]),
    item("A6", "A", 1, T("Claude / Anthropic keychain entries"), kind="keychain",
         generic_services=["Claude Code-credentials", "Claude Safe Storage", "Claude Code", "Claude"],
         generic_accounts=["Claude Key"],
         internet_servers=["claude.ai", "anthropic.com", "console.anthropic.com", "claude.com"],
         note=T("Backups record entry metadata only; secrets are not exported")),

    # B sessions & content
    item("B1", "B", 1, T("Claude Code prompt history (every prompt you typed)"), paths=["~/.claude/history.jsonl"]),
    item("B2", "B", 1, T("Claude Code full session transcripts"), paths=["~/.claude/projects", "~/.claude/sessions",
                                                                    "~/.claude/transcripts", "~/.claude/todos"]),
    item("B3", "B", 2, T("File snapshots, paste cache, shell / environment snapshots (may contain secrets)"),
         paths=["~/.claude/file-history", "~/.claude/paste-cache", "~/.claude/shell-snapshots",
                "~/.claude/session-env"]),
    item("B4", "B", 1, T("Desktop app Code / Cowork sessions, pending uploads, space memory"),
         paths=[AS + "/claude-code-sessions", AS + "/local-agent-mode-sessions", AS + "/pending-uploads",
                AS + "/git-shadow", AS + "/git-worktrees.json", AS + "/space-memory-copy",
                AS + "/spaces-present", AS + "/plan-usage-history.json", AS + "/cowork-enabled-cli-ops.json"],
         note=T("local_*.json contains your email, system prompt and mounted folders")),
    item("B5", "B", 2, T("Debug logs, feedback drafts, downloads"), paths=["~/.claude/debug", "~/.claude/feedback",
                                                                        "~/.claude/downloads"]),

    # C telemetry / logs
    item("C1", "C", 1, T("Claude Code telemetry leftovers & stats cache"),
         paths=["~/.claude/telemetry", "~/.claude/statsig", "~/.claude/stats-cache.json",
                "~/.claude/mcp-needs-auth-cache.json", "~/.claude/.last-cleanup",
                "~/.claude/.last-update-result.json"], nobackup=True),
    item("C2", "C", 2, T("Desktop app Sentry / Crashpad / performance observer DB"),
         paths=[AS + "/sentry", AS + "/Crashpad", AS + "/declarative_performance_observer.db",
                AS + "/declarative_performance_observer.db-journal", AS + "/DIPS"], nobackup=True),
    item("C3", "C", 2, T("Desktop app logs"), paths=["~/Library/Logs/Claude"], nobackup=True),
    item("C4", "C", 2, T("macOS crash reports (file names contain the hardware UUID)"),
         paths=["~/Library/Application Support/CrashReporter/Claude_*.plist",
                "~/Library/Application Support/CrashReporter/claude*.plist",
                "~/Library/Logs/DiagnosticReports/*[Cc]laude*"], nobackup=True),
    item("C5", "C", 3, T("System-wide crash reports (requires sudo)"), paths=["/Library/Logs/DiagnosticReports/*[Cc]laude*"],
         sudo=True, nobackup=True),

    # D Cowork
    item("D1", "D", 1, T("Cowork VM images & session data disk (unencrypted, contains copies of secrets)"),
         paths=[AS + "/vm_bundles"], note=T("Usually several GB; holds the VM UUID / MAC address")),
    item("D2", "D", 2, T("Claude Code VM runtime"), paths=[AS + "/claude-code-vm"], nobackup=True),

    # E embedded browser
    item("E1", "E", 1, T("Desktop app cookies & site storage (login state, ajs_*, analytics IDs)"),
         paths=[AS + "/Cookies", AS + "/Cookies-journal", AS + "/Local Storage", AS + "/IndexedDB",
                AS + "/Session Storage", AS + "/Partitions", AS + "/WebStorage", AS + "/SharedStorage",
                AS + "/Trust Tokens", AS + "/Trust Tokens-journal", AS + "/Network Persistent State",
                AS + "/TransportSecurity", AS + "/blob_storage", AS + "/Shared Dictionary",
                AS + "/shared_proto_db", AS + "/Local State", AS + "/Preferences"], nobackup=True),
    item("E2", "E", 3, T("Desktop app caches (HTTP / code / GPU)"),
         paths=[AS + "/Cache", AS + "/Code Cache", AS + "/GPUCache", AS + "/DawnGraphiteCache",
                AS + "/DawnWebGPUCache", AS + "/VideoDecodeStats", AS + "/fcache"], nobackup=True),

    # F config
    item("F1", "F", 1, T("MCP configs and their backups (may contain third-party tokens)"),
         paths=["~/.claude/.mcp.json", "~/.claude/.mcp.json.*", AS + "/claude_desktop_config.json",
                AS + "/claude_desktop_config.json.*"]),
    item("F2", "F", 2, T("Claude Code settings, plugins, skills, subagents, rules (incl. synced skill folders)"),
         paths=["~/.claude/settings.json", "~/.claude/settings.local.json", "~/.claude/plugins",
                "~/.claude/skills", "~/.claude/agents", "~/.claude/rules", "~/.claude/ide",
                "~/.claude/chrome", "~/.claude/state", "~/.claude/cache"]),
    item("F3", "F", 3, T("Desktop app extensions, skills and window state"),
         paths=[AS + "/Claude Extensions", AS + "/Claude Extensions Settings", AS + "/skills",
                AS + "/extensions-blocklist.json", AS + "/extensions-installations.json",
                AS + "/ca-bundle.pem", AS + "/window-state.json"]),

    # G application files
    item("G1", "G", 3, T("Claude desktop application"), paths=["/Applications/Claude.app",
                                                            "~/Applications/Claude Code URL Handler.app"],
         nobackup=True),
    item("G2", "G", 3, T("Claude Code binaries & state"),
         paths=["~/.local/bin/claude", "~/.local/share/claude", "~/.local/state/claude", "~/.cache/claude",
                AS + "/claude-code"], nobackup=True),
    item("G3", "G", 3, T("Application caches & temp files"), paths=["~/Library/Caches/claude-cli-nodejs",
                                                                 "~/Library/Caches/com.anthropic.*",
                                                                 "/private/tmp/claude-mcp-browser-bridge-*",
                                                                 TMP + "/claude*", TMP + "/*anthropic*"],
         nobackup=True),
    item("G4", "G", 2, T("Remove leftover directories entirely (~/.claude, desktop app data dir, Claude-3p)"),
         paths=["~/.claude", AS, "~/Library/Application Support/Claude-3p"],
         note=T("Catch-all item, always runs last"), last=True),

    # H system integration
    item("H1", "H", 2, T("Preference plists (ByHost file name contains the hardware UUID)"), kind="prefs",
         paths=["~/Library/Preferences/com.anthropic.*.plist",
                "~/Library/Preferences/ByHost/com.anthropic.*.plist"]),
    item("H2", "H", 2, T("\"Recent documents\" record"),
         paths=["~/Library/Application Support/com.apple.sharedfilelist/"
                "com.apple.LSSharedFileList.ApplicationRecentDocuments/com.anthropic.*"], nobackup=True),
    item("H3", "H", 2, T("HTTPStorages / saved application state / WebKit / sandbox containers"),
         paths=["~/Library/HTTPStorages/com.anthropic.*",
                "~/Library/Saved Application State/com.anthropic.*",
                "~/Library/WebKit/com.anthropic.*", "~/Library/Containers/*anthropic*",
                "~/Library/Group Containers/*anthropic*"]),
    item("H4", "H", 2, T("Browser native messaging hosts (Claude browser extension bridge)"),
         paths=[os.path.join(r, NMH) for r, _ in BROWSER_ROOTS.values()], nobackup=True),
    item("H5", "H", 2, T("LaunchAgents that invoke Claude"), kind="launchagent",
         paths=["~/Library/LaunchAgents/*.plist"]),

    # I shell
    item("I1", "I", 2, T("Shell history entries mentioning claude / anthropic"), kind="history",
         paths=["~/.zsh_history", "~/.bash_history"]),
    item("I2", "I", 3, T("Claude env vars / aliases in shell rc files (report only, edit manually)"), kind="report_rc",
         paths=["~/.zshrc", "~/.zprofile", "~/.zshenv", "~/.bashrc", "~/.bash_profile", "~/.profile"]),

    # J external browsers
    item("J1", "J", 2, T("claude / anthropic cookies, history, saved passwords, IndexedDB in Chromium browsers"),
         kind="chrome", note=T("Quit the browser first; Safari is covered in the manual checklist")),

    # K third-party
    item("K1", "K", 3, T("Claude plugins & caches in Cursor / Bun / JetBrains"),
         paths=["~/.cursor/plugins/cache/claude-plugins-official",
                "~/.cursor/plugins/marketplaces/claude-plugins-official",
                "~/.bun/install/cache/opencode-anthropic-auth*",
                "~/Library/Application Support/JetBrains/*/plugins/claude-code-jetbrains-plugin"], nobackup=True),
    item("K2", "K", 3, T("Anthropic references in other tools' configs (report only, edit manually)"), kind="report_grep",
         paths=["~/.codex/config.toml", "~/.config/opencode/*.json", "~/.cursor/mcp.json"]),

    # L project repositories
    item("L1", "L", 3, T(".claude folders, CLAUDE.md, .mcp.json inside projects (confirmed one by one)"), kind="repo"),
]
ITEM_BY_ID = {it["id"]: it for it in ITEMS}

MANUAL_TODO = [
    T("Chrome: remove the Claude extension at chrome://extensions (fcoeoabgfenejglbffodgkkbkcdhcgfn); if sync is on, also delete at myactivity.google.com."),
    T("Safari: search history for \"claude\" and delete; Settings > Privacy > Manage Website Data, remove claude.ai / anthropic.com."),
    T("claude.ai > Settings: sign out other devices and sessions; review connected integrations."),
    T("Mobile app: signing out does not wipe local data; delete the app."),
    T("Other computers / remote dev boxes: each has its own set of traces and must be cleaned separately."),
    T("Rotate secrets: API keys, private keys and MCP tokens that appeared in transcripts or the Cowork disk were already sent, even if deleted locally."),
    T("Time Machine: use \"Delete All Backups of\" on the directories above; list local snapshots with `tmutil listlocalsnapshots /`, delete with `tmutil deletelocalsnapshots <date>`."),
    T("iCloud Drive / cloud sync: make sure ~/.claude, project .claude folders and backup archives are not synced."),
    T("System Settings > General > Login Items & Extensions: confirm Claude / ShipIt is gone."),
    T("git: local `claude` branches (git branch -D claude) and \"Co-Authored-By: Claude\" trailers (rewrite only unpushed repos with git filter-repo)."),
    T("Spotlight: after cleaning, rebuild the index with `sudo mdutil -E /`."),
    T("Finally: empty the Trash; this tool's backups/ and reports/ folders contain every fingerprint too, encrypt or delete them."),
]

# ───────────────────────── path resolution & sizes ─────────────────────────
def expand(pattern):
    return os.path.expanduser(pattern)


def matches(pattern):
    p = expand(pattern)
    if any(ch in p for ch in "*?["):
        return sorted(glob.glob(p))
    return [p] if os.path.lexists(p) else []


_size_cache = {}


def du(path):
    if path in _size_cache:
        return _size_cache[path]
    total = 0
    try:
        st = os.lstat(path)
        total = st.st_blocks * 512
        if os.path.isdir(path) and not os.path.islink(path):
            for root, dirs, files in os.walk(path, onerror=lambda e: None):
                for n in dirs + files:
                    try:
                        total += os.lstat(os.path.join(root, n)).st_blocks * 512
                    except OSError:
                        pass
    except OSError:
        pass
    _size_cache[path] = total
    return total


def launchagent_hits(it):
    hits = []
    for f in matches(it["paths"][0]):
        try:
            data = open(f, "rb").read().lower()
        except OSError:
            continue
        if any(k in data for k in KEYWORDS):
            hits.append(f)
    return hits


def history_entries(data):
    lines = data.split(b"\n")
    ext = re.compile(rb"^: \d+:\d+;")
    if not any(ext.match(l) for l in lines[:50]):
        return [[l] for l in lines]
    entries, cur = [], []
    for l in lines:
        if ext.match(l) and cur:
            entries.append(cur)
            cur = []
        cur.append(l)
    if cur:
        entries.append(cur)
    return entries


def entry_hit(entry):
    blob = b"\n".join(entry).lower()
    return any(k in blob for k in KEYWORDS)


def chrome_profiles():
    out = []
    for bname, (root, proc) in BROWSER_ROOTS.items():
        r = expand(root)
        if not os.path.isdir(r):
            continue
        for d in sorted(os.listdir(r)):
            pdir = os.path.join(r, d)
            if (d == "Default" or d.startswith("Profile ")) and os.path.isdir(pdir):
                out.append((bname, proc, d, pdir))
    return out


def domain_where(col):
    parts = []
    for d in DOMAINS:
        parts.append("%s LIKE '%%%s%%'" % (col, d))
    return "(" + " OR ".join(parts) + ")"


def cookie_where():
    parts = []
    for d in DOMAINS:
        parts.append("host_key = '%s' OR host_key = '.%s' OR host_key LIKE '%%.%s'" % (d, d, d))
    return "(" + " OR ".join(parts) + ")"


def chrome_db_files(pdir):
    cookies = [p for p in (os.path.join(pdir, "Network", "Cookies"), os.path.join(pdir, "Cookies"))
               if os.path.exists(p)]
    hist = os.path.join(pdir, "History")
    login = os.path.join(pdir, "Login Data")
    return cookies, (hist if os.path.exists(hist) else None), (login if os.path.exists(login) else None)


def ro_count(db, sql):
    try:
        con = sqlite3.connect("file:%s?immutable=1" % urllib.parse.quote(db), uri=True)
        n = con.execute(sql).fetchone()[0]
        con.close()
        return n
    except sqlite3.Error:
        return 0


def chrome_indexeddb(pdir):
    out = []
    for sub in ("IndexedDB", "Service Worker/CacheStorage"):
        for d in DOMAINS:
            out += glob.glob(os.path.join(pdir, sub, "*%s*" % d))
    return out


def repo_hits():
    hits = []
    for root in SETTINGS["repo_roots"]:
        r = expand(root)
        if not os.path.isdir(r):
            continue
        base_depth = r.rstrip("/").count("/")
        for cur, dirs, files in os.walk(r):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "Pods", "build", ".venv", "venv")]
            if cur.count("/") - base_depth >= 6:
                dirs[:] = []
            if ".claude" in dirs:
                hits.append(os.path.join(cur, ".claude"))
                dirs.remove(".claude")
            for f in ("CLAUDE.md", "CLAUDE.local.md", ".mcp.json"):
                if f in files:
                    hits.append(os.path.join(cur, f))
    return hits


def keychain_present(it):
    found = []
    for s in it.get("generic_services", []):
        if run(["security", "find-generic-password", "-s", s])[0] == 0:
            found.append(("generic-s", s))
    for a in it.get("generic_accounts", []):
        if run(["security", "find-generic-password", "-a", a])[0] == 0:
            found.append(("generic-a", a))
    for s in it.get("internet_servers", []):
        if run(["security", "find-internet-password", "-s", s])[0] == 0:
            found.append(("internet", s))
    return found


def resolve(it):
    """Return (targets, total_bytes, detail_lines). Targets are paths that can be backed up."""
    k = it["kind"]
    if k in ("path", "prefs"):
        targets = []
        for pat in it["paths"]:
            targets += matches(pat)
        return targets, sum(du(t) for t in targets), []
    if k == "launchagent":
        t = launchagent_hits(it)
        return t, sum(du(x) for x in t), []
    if k == "history":
        targets, desc = [], []
        for pat in it["paths"]:
            for f in matches(pat):
                try:
                    n = sum(1 for e in history_entries(open(f, "rb").read()) if entry_hit(e))
                except OSError:
                    n = 0
                if n:
                    targets.append(f)
                    desc.append(T("%s: %d matching entries") % (f.replace(HOME, "~"), n))
        return targets, 0, desc
    if k in ("report_rc", "report_grep"):
        desc = []
        for pat in it["paths"]:
            for f in matches(pat):
                try:
                    for i, line in enumerate(open(f, "r", errors="replace"), 1):
                        if re.search(r"claude|anthropic", line, re.I):
                            desc.append("%s:%d  %s" % (f.replace(HOME, "~"), i, line.strip()[:120]))
                except OSError:
                    pass
        return [], 0, desc
    if k == "keychain":
        found = keychain_present(it)
        return [], 0, [T("%s: %s") % (t, v) for t, v in found]
    if k == "chrome":
        targets, desc = [], []
        for bname, proc, prof, pdir in chrome_profiles():
            cookies, hist, login = chrome_db_files(pdir)
            nc = sum(ro_count(db, "SELECT COUNT(*) FROM cookies WHERE " + cookie_where()) for db in cookies)
            nh = ro_count(hist, "SELECT COUNT(*) FROM urls WHERE " + domain_where("url")) if hist else 0
            nl = ro_count(login, "SELECT COUNT(*) FROM logins WHERE " + domain_where("origin_url")) if login else 0
            idb = chrome_indexeddb(pdir)
            if nc or nh or nl or idb:
                desc.append(T("%s/%s: %d cookies, %d history URLs, %d saved passwords, %d site storage dirs")
                            % (bname, prof, nc, nh, nl, len(idb)))
                targets += cookies + [x for x in (hist, login) if x] + idb
        return targets, sum(du(t) for t in targets), desc
    if k == "repo":
        t = repo_hits()
        return t, sum(du(x) for x in t), [x.replace(HOME, "~") for x in t]
    return [], 0, []


def has_content(it, targets, desc):
    return bool(targets or desc)

# ───────────────────────── selection ─────────────────────────
def print_catalog(items=None, scan=None):
    items = items or ITEMS
    cur = None
    for it in items:
        if it["cat"] != cur:
            cur = it["cat"]
            heading(CAT_NAME[cur])
        if scan is None:
            row(it["name"])
            continue
        targets, size, desc = scan[it["id"]]
        if has_content(it, targets, desc):
            extra = []
            if targets:
                extra.append(T("1 path") if len(targets) == 1 else T("%d paths") % len(targets))
            if desc and not targets:
                extra.append(T("%d hits") % len(desc))
            if size:
                extra.append(BOLD(human(size)))
            row(YELLOW("● ") + it["name"], ", ".join(extra))
        else:
            row(DIM("○ " + it["name"]), DIM(T("○ not found")))


def scan_all(items=None):
    items = items or ITEMS
    res = {}
    total = len(items)
    bar = Progress(T("Scanning"), total)
    for i, it in enumerate(items, 1):
        bar.update(i - 1, it["name"])
        res[it["id"]] = resolve(it)
    bar.done()
    return res


# ───────────────────────── backup ─────────────────────────
def dedupe(paths):
    paths = sorted(set(os.path.abspath(p) for p in paths), key=lambda p: p.rstrip("/") + "/")
    out = []
    for p in paths:
        if out and (p == out[-1] or p.startswith(out[-1].rstrip("/") + "/")):
            continue
        out.append(p)
    return out


def keychain_metadata(it):
    lines = []
    for t, v in keychain_present(it):
        if t == "generic-s":
            cmd = ["security", "find-generic-password", "-s", v]
        elif t == "generic-a":
            cmd = ["security", "find-generic-password", "-a", v]
        else:
            cmd = ["security", "find-internet-password", "-s", v]
        lines.append("$ " + " ".join(cmd) + "\n" + run(cmd)[1])
    return "\n".join(lines)


def do_backup(items, scan=None):
    scan = scan or scan_all(items)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_ROOT, ts)

    def big_ok(name, size):
        if size <= BIG_ITEM:
            return True
        if SETTINGS["assume_yes"] and not SETTINGS["include_big"]:
            log(T("Skipping large item %s (%s); add --include-big to include it") % (name, human(size)))
            return False
        if not SETTINGS["assume_yes"] and not confirm(T("%s is %s. Include it in the backup?") % (name, human(size)), False):
            log(T("Skipping large item %s") % name)
            return False
        return True

    by_cat, sizes, covered, skipped, not_needed = {}, {}, [], [], 0
    for it in items:
        targets, size, _ = scan[it["id"]]
        if not targets or it.get("last"):
            continue
        if it.get("nobackup"):
            skipped += targets
            not_needed += size
            continue
        if it["kind"] == "history":
            size = sum(du(t) for t in targets)
        if not big_ok(it["name"], size):
            skipped += targets
            continue
        by_cat.setdefault(it["cat"], []).extend(targets)
        sizes[it["cat"]] = sizes.get(it["cat"], 0) + size
        covered += targets

    # The catch-all item overlaps everything above: archive only what no other item covers.
    sweep, excludes, sweep_size = [], [], 0
    known = dedupe(covered + skipped)
    for it in items:
        if not it.get("last"):
            continue
        for t in scan[it["id"]][0]:
            root = t.rstrip("/") + "/"
            if any(t == k or root.startswith(k.rstrip("/") + "/") for k in known):
                continue
            inner = [k for k in known if k.startswith(root)]
            sweep.append(t)
            excludes += inner
            sweep_size += max(0, du(t) - sum(du(k) for k in inner))
    if sweep and not big_ok(T("Everything else in the Claude folders"), sweep_size):
        sweep = []

    jobs = [(cat, CAT_NAME[cat], dedupe(ps), [], sizes.get(cat, 0)) for cat, ps in sorted(by_cat.items())]
    if sweep:
        jobs.append(("Z", T("Everything else in the Claude folders"), sweep, excludes, sweep_size))

    kc = [it for it in items if it["kind"] == "keychain"]
    if not jobs and not kc:
        print(YELLOW(T("No Claude traces found on this Mac; nothing to back up.")))
        return None

    heading(T("Backup plan"), T("Destination: %s") % dest.replace(HOME, "~"))
    for _, label, paths, _, size in jobs:
        n = len(paths)
        row(label, (T("1 path") if n == 1 else T("%d paths") % n) + ", " + BOLD(human(size)))
    if kc:
        row(T("Keychain"), T("entry metadata only"))
    if not_needed:
        row(DIM(T("Not backed up: apps, caches, logs, login state (regenerated)")), DIM(human(not_needed)))
    total = sum(j[4] for j in jobs)
    free = shutil.disk_usage(TOOL_DIR).free
    print()
    row(BOLD(T("Total before compression")), BOLD(human(total)))
    row(T("Free disk space"), (RED if total > free * 0.9 else GREEN)(human(free)))
    if total > free * 0.9:
        print("  " + RED(T("Disk space may be insufficient.")))
    print()
    if not confirm(T("Start the backup?"), True):
        return None
    heading(T("Backing up"))

    os.makedirs(dest, exist_ok=True)
    manifest = {"created": ts, "host_user": getpass.getuser(), "archives": {}}
    for key, label, paths, excl, _ in jobs:
        sudo = any(not os.access(p, os.R_OK) for p in paths)
        archive = os.path.join(dest, "%s_%s.tar.gz" % (key, re.sub(r"[^\w]+", "_", label)[:30].strip("_")))
        listfile = archive + ".list"
        with open(listfile, "w", encoding="utf-8") as f:
            for p in paths:
                f.write(p.lstrip("/") + "\n")
        cmd = ["tar", "-czf", archive, "-C", "/"]
        for e in excl:
            cmd += ["--exclude", re.sub(r"([\[\]*?\\])", r"\\\1", e.lstrip("/"))]
        if sys.stdout.isatty():
            sys.stdout.write("  " + DIM("… " + label))
            sys.stdout.flush()
        rc, out = run(cmd + ["-T", listfile], sudo=sudo)
        if sys.stdout.isatty():
            sys.stdout.write("\r\033[K")
        row((GREEN("✓ ") if rc == 0 else YELLOW("! ")) + label, human(du(archive)) if os.path.exists(archive) else "")
        manifest["archives"][os.path.basename(archive)] = {"category": label, "paths": paths, "excluded": excl,
                                                          "tar_rc": rc}
        if rc != 0:
            log(YELLOW(T("  [%s] tar exited with %d (some files may be unreadable or in use); archived what it could") % (label, rc)))
        os.remove(listfile)
    for it in kc:
        with open(os.path.join(dest, "keychain_metadata.txt"), "w", encoding="utf-8") as f:
            f.write(keychain_metadata(it) or T("(no entries found)\n"))
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    with open(os.path.join(dest, "HOW_TO_RESTORE.txt"), "w", encoding="utf-8") as f:
        f.write(T("Every tar.gz stores absolute paths relative to the root directory /.\n"
                "Restore everything:   cd <this folder> && for a in *.tar.gz; do tar -xzf \"$a\" -C /; done\n"
                "List contents:        tar -tzf A_xxx.tar.gz\n"
                "Restore one path:     tar -xzf A_xxx.tar.gz -C / Users/<your-user>/.claude.json\n"
                "Note: restoring a Chrome database overwrites all cookies / history of that browser; quit it first.\n"
                "Keychain secrets were not exported; you will need to sign in again after restoring.\n"))
    os.chmod(dest, 0o700)
    for n in os.listdir(dest):
        os.chmod(os.path.join(dest, n), 0o600)
    print()
    log(BOLD(GREEN("✓ " + T("Backup finished: %s (%s)") % (dest.replace(HOME, "~"), human(du(dest))))))

    if SETTINGS["dmg"] and not sys.stdin.isatty():
        log(YELLOW(T("Skipped the encrypted DMG: it needs a password typed in a terminal (pass --no-dmg to silence this).")))
    elif SETTINGS["dmg"] and confirm(T("Pack the backup into an AES-256 encrypted DMG (you will be asked for a password)?"), True):
        dmg = dest + ".dmg"
        rc, _ = run(["hdiutil", "create", "-encryption", "AES-256", "-srcfolder", dest,
                     "-volname", "claude-backup-" + ts, dmg], capture=False)
        if rc == 0 and os.path.exists(dmg):
            log(GREEN(T("Encrypted DMG: %s") % dmg))
            if confirm(T("Delete the unencrypted backup folder?"), True):
                shutil.rmtree(dest, ignore_errors=True)
                log(T("Deleted plaintext backup folder %s") % dest)
                return dmg
        else:
            log(YELLOW(T("DMG creation failed; the plaintext backup remains at %s") % dest))
    return dest

# ───────────────────────── clean ─────────────────────────
def remove_path(p, sudo=False):
    try:
        if sudo:
            rc, _ = run(["rm", "-rf", p], sudo=True, capture=False)
            ok = rc == 0
        elif SETTINGS["delete_mode"] == "trash" and not p.startswith("/Library/"):
            trash = os.path.join(HOME, ".Trash")
            base = os.path.basename(p.rstrip("/"))
            dst = os.path.join(trash, base)
            if os.path.lexists(dst):
                dst = os.path.join(trash, "%s_%s" % (base, datetime.datetime.now().strftime("%H%M%S%f")))
            shutil.move(p, dst)
            ok = True
        else:
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
            ok = True
    except Exception as e:
        log(RED(T("  FAILED %s: %s") % (p, e)))
        return False
    log((T("  deleted ") if ok else RED(T("  FAILED "))) + p.replace(HOME, "~"))
    return ok


def clean_keychain(it):
    for t, v in keychain_present(it):
        flag = {"generic-s": ("find-generic-password", "delete-generic-password", "-s"),
                "generic-a": ("find-generic-password", "delete-generic-password", "-a"),
                "internet": ("find-internet-password", "delete-internet-password", "-s")}[t]
        for _ in range(20):
            if run(["security", flag[0], flag[2], v])[0] != 0:
                break
            run(["security", flag[1], flag[2], v])
        log(T("  deleted keychain entry %s %s") % (t, v))
    rc, out = run(["security", "dump-keychain"])
    left = [l.strip() for l in out.splitlines() if re.search(r"claude|anthropic", l, re.I)]
    if left:
        print(YELLOW(T("  The keychain still has matches (search in Keychain Access and delete manually):")))
        for l in left[:20]:
            print("    " + l)


def clean_history(f):
    data = open(f, "rb").read()
    entries = history_entries(data)
    keep = [e for e in entries if not entry_hit(e)]
    n = len(entries) - len(keep)
    tmp = f + ".cfd_tmp"
    with open(tmp, "wb") as fp:
        fp.write(b"\n".join(b"\n".join(e) for e in keep))
    os.chmod(tmp, os.stat(f).st_mode & 0o777)
    os.replace(tmp, f)
    log(T("  %s: removed %d commands") % (f.replace(HOME, "~"), n))


def proc_running(name):
    return run(["pgrep", "-x", name])[0] == 0


def clean_chrome():
    import time
    for bname, proc, prof, pdir in chrome_profiles():
        cookies, hist, login = chrome_db_files(pdir)
        idb = chrome_indexeddb(pdir)
        if not (cookies or hist or login or idb):
            continue
        if proc_running(proc):
            if not confirm(T("  %s is running and must quit before its databases can be changed. Quit it now?") % bname, False):
                log(YELLOW(T("  skipped %s/%s") % (bname, prof)))
                continue
            run(["osascript", "-e", 'quit app "%s"' % proc])
            for _ in range(20):
                if not proc_running(proc):
                    break
                time.sleep(0.5)
        stmts = []
        for db in cookies:
            stmts.append((db, ["DELETE FROM cookies WHERE " + cookie_where()]))
        if hist:
            ids = "SELECT id FROM urls WHERE " + domain_where("url")
            stmts.append((hist, [
                "DELETE FROM visits WHERE url IN (%s)" % ids,
                "DELETE FROM keyword_search_terms WHERE url_id IN (%s) OR lower_term LIKE '%%claude%%' "
                "OR lower_term LIKE '%%anthropic%%'" % ids,
                "DELETE FROM segments WHERE url_id IN (%s)" % ids,
                "DELETE FROM urls WHERE " + domain_where("url"),
            ]))
        if login:
            stmts.append((login, ["DELETE FROM logins WHERE " + domain_where("origin_url")]))
        for db, sqls in stmts:
            try:
                con = sqlite3.connect(db, timeout=5)
                n = 0
                for s in sqls:
                    try:
                        n += con.execute(s).rowcount
                    except sqlite3.Error:
                        pass
                con.commit()
                con.execute("VACUUM")
                con.close()
                log(T("  %s/%s %s: deleted %d rows") % (bname, prof, os.path.basename(db), n))
            except sqlite3.Error as e:
                log(RED(T("  failed to modify %s: %s") % (db, e)))
        for d in idb:
            remove_path(d)


def clean_launchagents(it):
    uid = str(os.getuid())
    for f in launchagent_hits(it):
        print("  " + f)
        if SETTINGS["assume_yes"]:
            log(YELLOW(T("  skipped (--yes never removes launch agents; run without --yes to confirm): %s") % f))
            continue
        if not confirm(T("  Unload and delete this launch agent?"), False):
            continue
        run(["launchctl", "bootout", "gui/" + uid, f])
        remove_path(f)


def clean_repo(targets):
    if SETTINGS["assume_yes"]:
        log(YELLOW(T("  skipped %d project files (--yes never removes them; run without --yes to confirm each)") % len(targets)))
        return
    print(YELLOW(T("  Confirm each: y=delete  n=keep  a=delete all remaining  q=stop")))
    all_yes = False
    for p in targets:
        if not all_yes:
            s = ask("  %s  (%s) [y/n/a/q] " % (p.replace(HOME, "~"), human(du(p)))).lower()
            if s == "q":
                break
            if s == "a":
                all_yes = True
            elif s != "y":
                continue
        remove_path(p)


def claude_processes():
    """Match on the executable path so shells whose arguments merely mention "claude" are ignored."""
    rc, out = run(["ps", "-axo", "pid=,comm="])
    res = []
    for l in out.splitlines():
        parts = l.strip().split(None, 1)
        if len(parts) == 2 and re.search(r"(?i)claude|anthropic", parts[1]) and not parts[1].startswith(TOOL_DIR):
            res.append("%s %s" % (parts[0], parts[1]))
    return res


def stop_processes():
    lines = claude_processes()
    if not lines:
        return
    print(YELLOW(T("\nClaude-related processes are running (if left running they will write the files back):")))
    for l in lines[:15]:
        print("  " + l[:150])
    if confirm(T("Quit these processes now?"), True):
        run(["osascript", "-e", 'quit app "Claude"'])
        run(["pkill", "-f", "Claude.app"])
        run(["pkill", "-x", "claude"])
        run(["launchctl", "remove", "com.anthropic.claudefordesktop.ShipIt"])
        log(T("Attempted to quit Claude-related processes"))


def do_clean(items, scan=None):
    scan = scan or scan_all(items)
    todo = [it for it in items if has_content(it, scan[it["id"]][0], scan[it["id"]][2])]
    if not todo:
        print(GREEN(T("No Claude traces found on this Mac; nothing to clean.")))
        return
    todo.sort(key=lambda it: (bool(it.get("last")), it["id"]))

    removed = [t for it in todo if it["kind"] not in ("history", "chrome") for t in scan[it["id"]][0]]
    total = sum(du(p) for p in dedupe(removed))
    cur = None
    for it in sorted(todo, key=lambda it: it["id"]):
        targets, size, desc = scan[it["id"]]
        if it["cat"] != cur:
            cur = it["cat"]
            heading(CAT_NAME[cur])
        row(RED("✗ ") + it["name"], BOLD(human(size)) if size else "")
        lines = desc if it["kind"] == "history" else (targets or desc)
        for t in lines[:3]:
            emit(t.replace(HOME, "~"), 6, color=DIM, hard=True)
        more = len(lines) - 3
        if more > 0:
            print("      " + DIM(T("... and %d more") % more))
    mode = T("move to Trash") if SETTINGS["delete_mode"] == "trash" else RED(T("delete permanently (cannot be undone)"))
    print()
    box([BOLD(RED(T("About to remove everything above, including the Claude apps"))),
         "",
         T("  Items: %d    Size: %s    Mode: %s") % (len(todo), BOLD(human(total)), mode)])

    if not SETTINGS["assume_yes"] and ask("\n" + T("Type %s to continue, anything else cancels: ") % BOLD(RED("DELETE"))) != "DELETE":
        print(DIM(T("Cancelled. Nothing was deleted.")))
        return

    stop_processes()
    heading(T("Cleaning"))
    for it in todo:
        targets, _, desc = scan[it["id"]]
        log(BOLD(CYAN("▶ ") + it["name"]))
        k = it["kind"]
        if k == "path":
            for t in targets:
                if os.path.lexists(t):
                    remove_path(t, sudo=it["sudo"])
        elif k == "prefs":
            for t in targets:
                remove_path(t)
            run(["defaults", "delete", "com.anthropic.claudefordesktop"])
            run(["killall", "cfprefsd"])
        elif k == "keychain":
            clean_keychain(it)
        elif k == "history":
            for f in targets:
                clean_history(f)
            print(YELLOW(T("  Note: close every terminal window and reopen; otherwise running shells write their in-memory history back on exit.")))
        elif k == "chrome":
            clean_chrome()
        elif k == "launchagent":
            clean_launchagents(it)
        elif k == "repo":
            clean_repo(targets)
        elif k in ("report_rc", "report_grep"):
            print(YELLOW(T("  These locations need manual editing:")))
            for d in desc:
                print("    " + d)
    _size_cache.clear()
    print()
    log(BOLD(GREEN("✓ " + T("Cleaning finished."))))
    return True

# ───────────────────────── verify ─────────────────────────
def do_verify():
    _size_cache.clear()
    scan = scan_all()
    left = [it for it in ITEMS if has_content(it, scan[it["id"]][0], scan[it["id"]][2])]
    heading(T("Verify"))
    if not left:
        log(GREEN("✓ " + T("Verification passed: no leftovers at any known risk location.")))
    else:
        log(YELLOW(T("%d items still have leftovers:") % len(left)))
        print_catalog(left, scan)
    rc, out = run(["security", "dump-keychain"])
    n = len([l for l in out.splitlines() if re.search(r"claude|anthropic", l, re.I)])
    procs = claude_processes()
    snaps = run(["tmutil", "listlocalsnapshots", "/"])[1].strip().splitlines()
    print()
    row(T("Keychain matching lines"), (GREEN if not n else YELLOW)(str(n)))
    row(T("Running Claude-related processes"), (GREEN if not procs else YELLOW)(str(len(procs))))
    for l in procs[:10]:
        print("      " + DIM(l[:120]))
    row(T("Time Machine local snapshots (handle manually)"), str(len(snaps)))

# ───────────────────────── menus ─────────────────────────
def show_manual():
    heading(T("Manual checklist"), T("Things this tool cannot do locally"))
    for i, t in enumerate(MANUAL_TODO, 1):
        emit(t, 6, first="  " + CYAN("%2d" % i) + "  ")
    branches = []
    for root in SETTINGS["repo_roots"]:
        r = expand(root)
        if not os.path.isdir(r):
            continue
        for cur, dirs, files in os.walk(r):
            dirs[:] = [d for d in dirs if d not in ("node_modules", "Pods", "build")]
            if ".git" in dirs:
                rc, out = run(["git", "-C", cur, "branch", "--list", "*claude*"])
                if out.strip():
                    branches.append(T("%s: %s") % (cur.replace(HOME, "~"), " ".join(out.split())))
                dirs.remove(".git")
            if cur.count("/") - r.count("/") >= 4:
                dirs[:] = []
    if branches:
        heading(T("Local git branches whose name contains \"claude\""))
        for b in branches:
            emit(b, 4, first="  · ")


def settings_menu():
    while True:
        heading(T("Settings"))
        s = menu([("1", T("Deletion mode"), T("move to Trash") if SETTINGS["delete_mode"] == "trash" else T("delete permanently")),
                  ("2", T("Project scan roots"), ", ".join(SETTINGS["repo_roots"]) or "-"),
                  ("3", T("Language"), i18n.label()),
                  ("0", T("Back"), "")])
        if _stdin_closed:
            return
        if s == "1":
            SETTINGS["delete_mode"] = "rm" if SETTINGS["delete_mode"] == "trash" else "trash"
        elif s == "2":
            v = ask(T("Comma-separated directories> "))
            if v:
                SETTINGS["repo_roots"] = [x.strip() for x in v.replace(FULLWIDTH_COMMA, ",").split(",") if x.strip()]
        elif s == "3":
            switch_language()
        else:
            return


def switch_language():
    """Item names and menus are translated at startup, so restart the menu in the other language."""
    new = "en" if i18n.LANG == "zh" else "zh"
    env = dict(os.environ, CFD_SETTINGS=json.dumps(SETTINGS))
    script = os.path.abspath(__file__)
    os.execve(sys.executable, [sys.executable, script, "--lang", new], env)


def clean_all(backup_first=True):
    scan = scan_all()
    if backup_first and confirm(T("Back up before cleaning?"), True):
        if do_backup(ITEMS, scan) is None and not confirm(T("No backup was created. Continue cleaning anyway?"), False):
            return
    if do_clean(ITEMS, scan):
        do_verify()


def do_health():
    import health_check
    heading(T("Fingerprint check"))
    s = menu([("1", T("Standard"), T("IDs, cookies, device profile, behavior, reporting switches · seconds")),
              ("2", T("+ Extras"), T("+ credentials, secret leaks, external traces, system protection · ~2 min")),
              ("3", T("+ Extras, deep"), T("+ secret scan of the Cowork data disk · ~10 min")),
              ("0", T("Back"), "")], "1")
    mode = {"1": "fp", "2": "fp+extra", "3": "fp+extra_deep"}.get(s)
    if not mode:
        return
    ids, _ = health_check.run(sys.modules[__name__], mode)
    if ids and confirm(T("\nClean everything now (back up first, then confirm)?"), False):
        clean_all()


def main():
    if sys.platform != "darwin":
        print(T("This tool only supports macOS."))
        return
    try:
        SETTINGS.update(json.loads(os.environ.pop("CFD_SETTINGS", "") or "{}"))
    except ValueError:
        pass
    print()
    box([BOLD(T("Claude Fingerprint Detect")) + DIM("  v" + __version__),
         DIM(T("Check · Back up · Clean    data in %s") % TOOL_DIR.replace(HOME, "~"))])
    while True:
        s = menu([("1", T("Fingerprint check"), T("read-only, takes seconds")),
                  ("2", T("Backup"), T("archive every Claude trace")),
                  ("3", T("Clean"), T("back up, remove every Claude trace, verify")),
                  ("4", T("Manual checklist"), T("browser extension, phone, Time Machine, keys")),
                  ("5", T("Settings"), T("deletion mode, project roots, language")),
                  ("0", T("Quit"), "")])
        if _stdin_closed:
            break
        if s == "1":
            do_health()
        elif s == "2":
            do_backup(ITEMS)
        elif s == "3":
            clean_all()
            show_manual()
        elif s == "4":
            show_manual()
        elif s == "5":
            settings_menu()
        elif s == "0":
            break

# ───────────────────────── command-line mode ─────────────────────────
CLI_EPILOG = T("""
examples:
  %(prog)s check     fingerprint check (read-only)
  %(prog)s backup    back up every Claude trace to backups/
  %(prog)s clean     remove every Claude trace (lists everything and asks first)

Run without arguments for the interactive menu.
""")


def cli(argv):
    import argparse
    ap = argparse.ArgumentParser(prog=os.environ.get("CFD_PROG") or os.path.basename(__file__),
                                 description=T("Claude local fingerprint check, backup and clean (macOS)"),
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=CLI_EPILOG)
    ap.add_argument("--version", action="version", version="claude-fingerprint-detect " + __version__)
    ap.add_argument("--lang", choices=["en", "zh", "auto"], help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("check", help=T("fingerprint check (read-only)"))
    p.add_argument("--extra", action="store_true", help=T("extras: credentials, quick secret scan, external traces, system protection"))
    p.add_argument("--deep", action="store_true", help=T("extras (deep): secret scan includes the Cowork data disk"))
    p.add_argument("--json", action="store_true", help=T("JSON output"))
    p.add_argument("--save", action="store_true", help=T("also save a Markdown report to reports/"))

    p = sub.add_parser("backup", help=T("back up every Claude trace"))
    p.add_argument("--yes", action="store_true", help=T("auto-confirm"))
    p.add_argument("--include-big", action="store_true", help=T("include items larger than 2 GB (e.g. the Cowork VM)"))
    p.add_argument("--no-dmg", action="store_true", help=T("skip the encrypted DMG"))

    p = sub.add_parser("clean", help=T("remove every Claude trace"))
    p.add_argument("--rm", action="store_true", help=T("delete permanently (default: move to Trash)"))
    p.add_argument("--yes", action="store_true", help=T("auto-confirm everything (quits Claude / browser processes; never removes launch agents or project files)"))
    p.add_argument("--repo-root", metavar="DIR", action="append", help=T("project scan root, may be repeated"))

    p = sub.add_parser("scan", help=T("list every location that would be cleaned, with sizes"))
    p.add_argument("-v", "--verbose", action="store_true", help=T("show paths"))
    p.add_argument("--json", action="store_true", help=T("JSON output"))

    sub.add_parser("verify", help=T("look for leftovers"))
    sub.add_parser("manual", help=T("manual checklist"))

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 0

    if args.cmd == "check":
        import health_check
        mode = "fp+extra_deep" if args.deep else ("fp+extra" if args.extra else "fp")
        ids, r = health_check.run(sys.modules[__name__], mode, save=args.save, quiet=args.json)
        if args.json:
            print(json.dumps(r.to_dict(health_check.MODES[mode]), ensure_ascii=False, indent=2))
        elif ids:
            print("\n" + BOLD(T("Next steps")))
            print("  " + CYAN(PROG + " backup") + "   " + DIM(T("back up every Claude trace")))
            print("  " + CYAN(PROG + " clean") + "    " + DIM(T("remove every Claude trace")))
        return 0

    if args.cmd == "scan":
        scan = scan_all()
        if args.json:
            out = []
            for it in ITEMS:
                t, size, desc = scan[it["id"]]
                out.append({"category": CAT_NAME[it["cat"]], "name": it["name"],
                            "found": bool(t or desc), "count": len(t), "bytes": size, "paths": t, "details": desc})
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0
        print_catalog(ITEMS, scan)
        if args.verbose:
            for it in ITEMS:
                t, size, desc = scan[it["id"]]
                if t or desc:
                    print("\n" + BOLD(it["name"]))
                    for x in t:
                        print("  %s  %s" % (human(du(x)).rjust(7), x.replace(HOME, "~")))
                    for d in desc:
                        print("  " + d)
        found = [it for it in ITEMS if scan[it["id"]][0] or scan[it["id"]][2]]
        print(T("\nFound %d / %d items, %s in total") % (len(found), len(ITEMS), human(sum(scan[it["id"]][1] for it in found))))
        return 0

    if args.cmd == "verify":
        do_verify()
        return 0

    if args.cmd == "manual":
        show_manual()
        return 0

    SETTINGS["assume_yes"] = args.yes

    if args.cmd == "backup":
        SETTINGS["include_big"] = args.include_big
        SETTINGS["dmg"] = not args.no_dmg
        return 0 if do_backup(ITEMS) else 1

    if args.cmd == "clean":
        SETTINGS["delete_mode"] = "rm" if args.rm else "trash"
        if args.repo_root:
            SETTINGS["repo_roots"] = args.repo_root
        if do_clean(ITEMS):
            do_verify()
        return 0
    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            sys.exit(cli(sys.argv[1:]))
        main()
    except KeyboardInterrupt:
        print(T("\nInterrupted."))
