# -*- coding: utf-8 -*-
"""Fingerprint check: the identifiers Claude can use to recognize this device / person / account,
with their actual values on this Mac, where they are stored and what gets reported. Read-only."""
import base64
import collections
import glob
import json
import os
import plistlib
import re
import sqlite3
import subprocess
import time
import urllib.parse

from i18n import T

H = os.path.expanduser("~")
AS = H + "/Library/Application Support/Claude"

COOKIE_INFO = {
    "anthropic-device-id": (1, T("Anthropic device ID")),
    "ajs_anonymous_id": (1, T("Segment anonymous ID (long-term cross-session tracking)")),
    "ajs_user_id": (1, T("Segment user ID (bound to the account)")),
    "_cross_domain_anonymous_id": (1, T("cross-domain anonymous ID (links claude.ai / claude.com / anthropic.com)")),
    "__Host-ant_trusted_device": (1, T("trusted-device marker (login risk control)")),
    "__ssid": (1, T("long-term tracking ID")),
    "lastActiveOrg": (1, T("last used organization UUID")),
    "intercom-device-id-": (2, T("Intercom support device ID")),
    "intercom-session-": (2, T("Intercom support session")),
    "activitySessionId": (2, T("activity session ID")),
    "analytics_session_id": (2, T("analytics session ID")),
    "_dd_s": (2, T("Datadog RUM session")),
    "__stripe_mid": (2, T("Stripe device fingerprint (payment risk control)")),
    "m": (2, T("Stripe device fingerprint (m.stripe.com)")),
    "cf_clearance": (2, T("Cloudflare challenge clearance (bound to device / browser fingerprint)")),
    "__cf_bm": (3, T("Cloudflare bot management")),
    "_cfuvid": (3, T("Cloudflare visitor ID")),
    "hmt_id": (2, T("hCaptcha tracking ID")),
    "_fbp": (2, T("Facebook pixel")),
    "IDE": (2, T("DoubleClick ad ID")),
    "NID": (3, T("Google preferences / ad ID")),
    "bcookie": (2, T("LinkedIn browser ID")),
    "bscookie": (2, T("LinkedIn secure browser ID")),
    "_ga": (2, T("Google Analytics client ID")),
    "g_state": (3, T("Google One Tap sign-in state")),
    "inkeepUsagePreferences_userId": (2, T("Inkeep docs assistant user ID")),
    "ion-vk": (3, T("third-party visitor key")),
}

TELEMETRY_ENV_FIELDS = ["platform", "arch", "node_version", "terminal", "shell", "package_managers", "runtimes",
                        "vcs", "version", "deployment_environment", "is_running_with_bun", "is_claude_ai_auth"]

SENTRY_FIELDS = [
    ("device.cpu_description", "CPU"), ("device.processor_count", T("cores")), ("device.memory_size", T("memory")),
    ("device.screen_resolution", T("screen")), ("device.screen_density", T("scale")),
    ("device.boot_time", T("boot time")), ("gpu.vendor_id", T("GPU vendor")),
    ("os.version", T("OS version")), ("os.build", T("OS build")), ("os.kernel_version", T("kernel")),
    ("culture.locale", T("locale")), ("culture.timezone", T("timezone")),
    ("app.app_version", T("app version")), ("runtime.version", "Electron"), ("chrome.version", "Chromium"),
]


def ro_rows(db, sql):
    try:
        con = sqlite3.connect("file:%s?immutable=1" % urllib.parse.quote(db), uri=True)
        rows = con.execute(sql).fetchall()
        con.close()
        return rows
    except sqlite3.Error:
        return []


def load_json(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def tilde(p):
    return p.replace(H, "~")


def run(cmd):
    try:
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode("utf-8", "replace")
    except FileNotFoundError:
        return ""


def cookie_label(name):
    if name in COOKIE_INFO:
        return COOKIE_INFO[name]
    for k, v in COOKIE_INFO.items():
        if k.endswith("-") and name.startswith(k):
            return v
        if k in ("_ga", "_dd_s") and name.startswith(k):
            return v
    return (3, T("UI preference / other"))

# ───────────────────────── collection ─────────────────────────
def collect_ids():
    """Return [(category, name, value, source)] used for the distribution scan."""
    ids = []
    cj = load_json(H + "/.claude.json") or {}
    acct = cj.get("oauthAccount") or {}
    if acct.get("emailAddress"):
        ids.append((T("account"), T("email"), acct["emailAddress"], ""))
    if acct.get("accountUuid"):
        ids.append((T("account"), "accountUuid", acct["accountUuid"], ""))
    if acct.get("organizationUuid"):
        ids.append((T("account"), "organizationUuid", acct["organizationUuid"], ""))
    if cj.get("userID"):
        ids.append((T("device"), T("userID (telemetry device_id)"), cj["userID"], "Claude Code"))
    if cj.get("machineID"):
        ids.append((T("device"), "machineID", cj["machineID"], "Claude Code"))
    did_path = AS + "/ant-did"
    if os.path.exists(did_path):
        raw = open(did_path, "rb").read().strip().decode(errors="replace")
        try:
            dec = base64.b64decode(raw).decode()
        except Exception:
            dec = ""
        ids.append((T("device"), T("ant-did (= Sentry user.id)"), dec or raw, T("desktop app")))
    for v in sorted(set(antalytics_ids())):
        ids.append((T("device"), "antalytics_anonymous_id", v, T("desktop app local storage")))
    vm = vm_identity()
    if vm.get("machineIdentifier"):
        ids.append((T("device"), T("Cowork VM machineIdentifier"), vm["machineIdentifier"], T("VM")))
    hw = hardware_uuid()
    if hw:
        ids.append((T("hardware"), T("hardware UUID"), hw, T("system")))
    ids.append((T("local"), T("home directory path"), H, T("appears in session folder names and environment attachments")))
    email = run(["git", "config", "--global", "user.email"]).strip()
    if email:
        ids.append((T("local"), "git user.email", email, ""))
    return ids


def antalytics_ids():
    out = []
    for f in glob.glob(AS + "/Local Storage/leveldb/*"):
        try:
            b = open(f, "rb").read()
        except OSError:
            continue
        out += [m.group(1).decode() for m in re.finditer(rb"(claudeai\.v1\.[0-9a-f-]{36})", b)]
    return out


def hardware_uuid():
    m = re.search(r'"IOPlatformUUID" = "([0-9A-F-]+)"', run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]))
    return m.group(1) if m else ""


def vm_identity():
    vm = AS + "/vm_bundles/claudevm.bundle"
    out = {}
    if not os.path.isdir(vm):
        return out
    try:
        obj = plistlib.load(open(vm + "/machineIdentifier", "rb"))
        blob = obj if isinstance(obj, bytes) else next(
            (v for v in (obj.values() if isinstance(obj, dict) else []) if isinstance(v, bytes)), b"")
        try:
            inner = plistlib.loads(blob)
            if isinstance(inner, dict):
                blob = next((v for v in inner.values() if isinstance(v, (bytes, int))), blob)
        except Exception:
            pass
        out["machineIdentifier"] = blob.hex() if isinstance(blob, bytes) else str(blob)
    except Exception:
        pass
    for n in ("macAddress", "gvisorMacAddress", "vmIP"):
        p = os.path.join(vm, n)
        if os.path.exists(p):
            out[n] = open(p, errors="replace").read().strip()
    return out


GROUPS = [
    (T("~/.claude.json & backups"), H + "/.claude.json"),
    ("~/.claude/backups", H + "/.claude/backups"),
    (T("CLI transcripts"), H + "/.claude/projects"),
    (T("CLI prompt history"), H + "/.claude/history.jsonl"),
    (T("CLI failed telemetry"), H + "/.claude/telemetry"),
    (T("CLI other files"), H + "/.claude"),
    (T("Cowork session metadata"), AS + "/local-agent-mode-sessions"),
    (T("desktop Code sessions"), AS + "/claude-code-sessions"),
    (T("desktop local storage"), AS + "/Local Storage"),
    (T("desktop IndexedDB"), AS + "/IndexedDB"),
    (T("desktop Sentry"), AS + "/sentry"),
    (T("desktop logs"), H + "/Library/Logs/Claude"),
    (T("desktop other files"), AS),
]
SKIP_DIRS = {AS + "/vm_bundles", AS + "/Cache", AS + "/Code Cache", AS + "/GPUCache", AS + "/claude-code",
             AS + "/claude-code-vm", H + "/.claude/plugins"}


def group_of(path):
    for name, prefix in GROUPS:
        if path == prefix or path.startswith(prefix + "/") or (prefix.endswith(".claude.json") and path.startswith(prefix)):
            return name
    return T("other")


def distribution(ids, cc):
    """Count, per identifier, how many files in each location contain it."""
    files = glob.glob(H + "/.claude.json*")
    for root in (H + "/.claude", AS, H + "/Library/Logs/Claude"):
        for cur, dirs, fs in os.walk(root):
            dirs[:] = [d for d in dirs if os.path.join(cur, d) not in SKIP_DIRS]
            files += [os.path.join(cur, f) for f in fs]
    needles = []
    for _, _, v, _ in ids:
        forms = {v.encode()}
        if re.fullmatch(r"[0-9a-fA-F-]{32,36}", v):
            forms.add(v.lower().encode())
            forms.add(v.upper().encode())
        if v == H:
            forms = {v.encode(), v.replace("/", "-").encode()}
        needles.append(forms)
    dist = [collections.Counter() for _ in ids]
    t0 = time.time()
    bar = cc.Progress(T("Searching for your IDs"), len(files))
    for n, f in enumerate(files):
        bar.update(n)
        try:
            if os.path.getsize(f) > 30 * 1024 * 1024:
                continue
            with open(f, "rb") as fp:
                data = fp.read()
        except OSError:
            continue
        g = group_of(f)
        for i, forms in enumerate(needles):
            if any(x in data for x in forms):
                dist[i][g] += 1
    bar.done()
    return dist, len(files), time.time() - t0

# ───────────────────────── sections ─────────────────────────
def sec_ids(r, cc, ids, dist):
    r.section(T("1. Account & device identifiers: value, persistence, where they appear on this Mac"))
    persist = {T("account"): T("comes back as soon as you sign in again"),
               T("device"): T("randomly generated, persisted; regenerated after deletion"),
               T("hardware"): T("system-level, cannot be changed"),
               T("local"): T("depends on your user name / git config")}
    items = {T("email"): ["A1", "B4"], "accountUuid": ["A1", "E1"], "organizationUuid": ["A1", "E1"],
             T("userID (telemetry device_id)"): ["A1", "A2", "C1"], "machineID": ["A1", "A2"],
             T("ant-did (= Sentry user.id)"): ["A4", "C2"], "antalytics_anonymous_id": ["E1"],
             T("Cowork VM machineIdentifier"): ["D1"], T("hardware UUID"): ["H1", "C4"]}
    lvl_of = {T("account"): 1, T("device"): 1, T("hardware"): 2, T("local"): 2}
    for (cat, name, val, src), d in zip(ids, dist):
        top = d.most_common()
        where = ", ".join(T("%s x%d") % (g, n) for g, n in top[:4]) or T("only in its source file")
        if len(top) > 4:
            where += T(" and %d more places") % (len(top) - 4)
        total = sum(d.values())
        text = T("[%s] %s = %s\n            persistence: %s; found in %d files: %s") % (cat, name, val, persist[cat], total, where)
        if name == T("hardware UUID"):
            text += T("\n            note: Claude itself does not read it (only a custom OTel exporter would), but macOS embeds it in Claude-related file names")
        if name == T("home directory path"):
            text += T("\n            note: session folder names (-Users-<name>-<project>) and the working directory attached to every request expose your user name and project layout")
        r.risk(lvl_of[cat], text, "", items.get(name, []))


def sec_cookies(r, cc):
    r.section(T("2. Tracking identifiers in cookies (values are Chromium-encrypted; only names and expiry are read)"))
    stores = []
    if os.path.exists(AS + "/Cookies"):
        stores.append((T("Desktop app embedded browser"), AS + "/Cookies", "E1"))
    for bname, proc, prof, pdir in cc.chrome_profiles():
        for db in cc.chrome_db_files(pdir)[0]:
            stores.append(("%s/%s" % (bname, prof), db, "J1"))
    if not stores:
        r.ok(T("No cookie databases found"))
        return
    for label, db, iid in stores:
        where = "" if iid == "E1" else " WHERE " + cc.cookie_where()
        rows = ro_rows(db, "SELECT host_key, name, datetime(expires_utc/1000000-11644473600,'unixepoch') "
                           "FROM cookies%s ORDER BY host_key, name" % where)
        if not rows:
            continue
        by_lvl = collections.defaultdict(list)
        names = collections.defaultdict(list)
        for host, name, exp in rows:
            lvl, desc = cookie_label(name)
            by_lvl[lvl].append(T("%s %s (%s, until %s)") % (host, name, desc, (exp or "")[:10]))
            if name not in names[lvl]:
                names[lvl].append(name)
        hi, mid, lo = by_lvl.get(1, []), by_lvl.get(2, []), by_lvl.get(3, [])
        r.risk(1 if hi else 2, T("%s: %d cookies; %d identity / device IDs, %d third-party tracking & risk control, %d other")
               % (label, len(rows), len(hi), len(mid), len(lo)), "", [iid])
        for line in hi:
            r.info("    ● " + line)
        if mid:
            r.info("    ○ " + T("third-party tracking & risk control: %s") % ", ".join(names[2]))
    r.info(T("Note: anthropic-device-id / ajs_anonymous_id exist in both the desktop app and Chrome; once both sign in to "
           "the same account they are linked. Risk-control cookies such as cf_clearance and __stripe_mid are bound to "
           "the browser environment fingerprint."))


def sec_profile(r, cc):
    r.section(T("3. Device profile: hardware & environment actually sent in reports"))
    scope = load_json(AS + "/sentry/scope_v3.json")
    if scope:
        ctx = (scope.get("event") or {}).get("contexts") or {}
        vals = []
        for path, label in SENTRY_FIELDS:
            a, b = path.split(".")
            v = (ctx.get(a) or {}).get(b)
            if v is None:
                continue
            if b == "memory_size":
                v = "%d GB" % round(int(v) / 1024 ** 3)
            vals.append("%s=%s" % (label, v))
        uid = ((scope.get("scope") or {}).get("user") or {}).get("id")
        r.risk(1, T("Desktop app Sentry error reports (user.id=%s) carry: %s") % (uid, ", ".join(vals)),
               T("delete the sentry folder; error reporting can be turned off in settings afterwards"), ["C2"])
        r.info(T("    note: CPU model + memory + screen resolution + timezone together are highly distinctive"))
    env, top = {}, collections.defaultdict(set)
    for f in glob.glob(H + "/.claude/telemetry/*.json"):
        try:
            txt = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        try:
            data = json.loads(txt)
            data = data if isinstance(data, list) else data.get("events", [data])
        except Exception:
            data = []
            for line in txt.splitlines():
                try:
                    data.append(json.loads(line))
                except Exception:
                    pass
        for e in data:
            if not isinstance(e, dict):
                continue
            ed = (e or {}).get("event_data") or {}
            for k in TELEMETRY_ENV_FIELDS:
                v = (ed.get("env") or {}).get(k)
                if v is not None:
                    env.setdefault(k, set()).add(str(v))
            for k in ("device_id", "session_id", "entrypoint", "model", "user_type"):
                if ed.get(k):
                    top[k].add(str(ed[k]))
            auth = ed.get("auth") or {}
            for k in ("account_uuid", "organization_uuid"):
                if auth.get(k):
                    top[k].add(auth[k])
    if env or top:
        parts = ["%s=%s" % (k, "/".join(sorted(v))) for k, v in env.items()]
        r.risk(1, T("Every Claude Code telemetry event carries: device_id=%s, account_uuid=%s, organization_uuid=%s; environment: %s") % (
            "/".join(top.get("device_id", [])) or "?", "/".join(top.get("account_uuid", [])) or "?",
            "/".join(top.get("organization_uuid", [])) or "?", ", ".join(parts)),
               T("delete the telemetry leftovers; set DISABLE_TELEMETRY after reinstalling"), ["C1"])
        r.info(T("    note: taken from events that failed to send and are queued locally; successfully sent events have the same content"))
    probe = load_json(AS + "/vm-support-probe.json")
    if probe:
        key = probe.get("key") or probe.get("hardwareKey") or ""
        r.risk(3, T("Desktop app hardwareKey=%s (= app version|kernel version|arch; identical on same-config machines, low distinctiveness)") % key, "", ["A4"])
    vm = vm_identity()
    if vm:
        r.risk(2, T("Cowork VM persistent identity: %s") % ", ".join("%s=%s" % kv for kv in vm.items()),
               T("delete vm_bundles; a new one is generated next time"), ["D1"])
    hw = hardware_uuid()
    hits = [p for pat in ("~/Library/Preferences/ByHost/*anthropic*", "~/Library/Application Support/CrashReporter/*[Cc]laude*")
            for p in glob.glob(os.path.expanduser(pat)) if hw and hw in p]
    if hits:
        r.risk(2, T("Claude files whose names contain the hardware UUID: %s") % ", ".join(tilde(h) for h in hits), T("delete"), ["H1", "C4"])


def sec_behavior(r, cc):
    r.section(T("4. Behavioral fingerprint: usage habits & local environment"))
    cj = load_json(H + "/.claude.json") or {}
    facts = []
    for k, label in (("firstStartTime", T("first launch")), ("numStartups", T("launches")), ("installMethod", T("install method")),
                     ("autoUpdates", T("auto-update")), ("hasCompletedOnboarding", T("onboarding done")),
                     ("lastReleaseNotesSeen", T("last release notes seen"))):
        if k in cj:
            facts.append("%s=%s" % (label, cj[k]))
    for k, label in (("skillUsage", T("skill usage records")), ("pluginUsage", T("plugin usage records")),
                     ("tipsHistory", T("tips shown")), ("projects", T("projects")),
                     ("cachedGrowthBookFeatures", T("GrowthBook experiment flags"))):
        v = cj.get(k)
        if isinstance(v, (dict, list)) and v:
            facts.append(T("%s: %d") % (label, len(v)))
    if facts:
        r.risk(2, T("Usage profile in ~/.claude.json: ") + ", ".join(facts), "", ["A1"])
    lam = glob.glob(AS + "/local-agent-mode-sessions/**/local_*.json", recursive=True)
    if lam:
        folders, models = collections.Counter(), collections.Counter()
        for p in lam:
            d = load_json(p) or {}
            for f in d.get("userSelectedFolders") or []:
                folders[tilde(f)] += 1
            if d.get("model"):
                models[d["model"]] += 1
        r.risk(2, T("%d Cowork sessions; mounted folders: %s; models: %s") % (
            len(lam), ", ".join(T("%s x%d") % kv for kv in folders.most_common(6)),
            ", ".join(T("%s x%d") % kv for kv in models.most_common(3))), "", ["B4"])
    hist = H + "/.claude/history.jsonl"
    if os.path.exists(hist):
        hours = collections.Counter()
        n = 0
        for line in open(hist, "rb"):
            m = re.search(rb'"timestamp":\s*(\d{10,13})', line)
            if m:
                ts = int(m.group(1))
                hours[time.localtime(ts / 1000 if ts > 1e12 else ts).tm_hour] += 1
                n += 1
        if n:
            peak = ", ".join(T("%02d:00 x%d") % kv for kv in sorted(hours.most_common(4)))
            r.risk(3, T("%d prompt history entries; active hours: %s (time-of-day patterns are a behavioral trait too)") % (n, peak), "", ["B1"])
    projs = sorted(set(os.path.basename(p) for p in glob.glob(H + "/.claude/projects/*")))
    if projs:
        r.risk(2, T("Session folder names expose %d project paths, e.g. %s") % (len(projs), ", ".join(projs[:5])), "", ["B2"])


def sec_system(r, cc):
    r.section(T("5. Identifiers left by system integration"))
    for iid, label in (("H1", T("preference plists")), ("H2", T("recent documents record")), ("H3", T("HTTPStorages etc.")),
                       ("H4", T("browser native messaging hosts")), ("C4", T("crash reports"))):
        targets, size, desc = cc.resolve(cc.ITEM_BY_ID[iid])
        if targets:
            r.risk(3, T("%s: %s") % (label, ", ".join(tilde(t) for t in targets[:4]) + (T(" ...") if len(targets) > 4 else "")), "", [iid])
    found = cc.keychain_present(cc.ITEM_BY_ID["A6"])
    if found:
        r.risk(2, T("Keychain entries: %s (Claude Safe Storage is the key that encrypts the desktop app cookies)")
               % ", ".join(v for _, v in found), "", ["A6"])
    targets, _, desc = cc.resolve(cc.ITEM_BY_ID["I1"])
    if desc:
        r.risk(3, T("Shell history: ") + "; ".join(desc), "", ["I1"])


def sec_reporting(r, cc, check_telemetry):
    r.section(T("6. Reporting switches"))
    check_telemetry(r, cc, section=False)


def run_fingerprint(r, cc, check_telemetry):
    ids = collect_ids()
    dist, nfiles, secs = distribution(ids, cc)
    sec_ids(r, cc, ids, dist)
    r.info(T("(checked %d files in %.0f s)") % (nfiles, secs))
    sec_cookies(r, cc)
    sec_profile(r, cc)
    sec_behavior(r, cc)
    sec_system(r, cc)
    sec_reporting(r, cc, check_telemetry)
