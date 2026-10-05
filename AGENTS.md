# AGENTS.md

Instructions for AI coding agents (Codex, Cursor, Claude Code, etc.) that install or run **claude-fingerprint-detect** on behalf of a user, or contribute to it.

## What this tool is

A macOS command-line tool that finds what Claude (desktop app, Claude Code, Cowork) has stored locally that can identify the user, their device and their account, and can back it up and remove it.

- Python 3.9+ standard library only, no dependencies, no network access.
- `check`, `scan`, `verify` and `manual` are read-only.
- `backup` writes archives into `backups/` next to the script. `clean` deletes files (Trash by default).

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash
```

This puts the code in `~/.claude-fingerprint-detect` and a `cfd` command in `~/.local/bin` (added to `PATH` in `~/.zshrc` or `~/.bash_profile` if needed). Running it again updates. Your current shell may not see the new `PATH`, so call the full path:

```bash
~/.local/bin/cfd --version
```

Uninstall: `curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash -s -- --uninstall` (keeps the folder if it holds backups or reports).

If the installer says Python 3 is missing, ask the user to run `xcode-select --install` and retry. Do not install other Python distributions for this.

## Rules for agents

1. **Read-only first.** Run `check` before proposing a cleanup. `clean` removes every Claude trace, including the Claude apps, and signs the user out. Never run it without the user's explicit approval.
2. **Show what will be removed** before asking for approval: `scan --json` lists every location `clean` would touch, with sizes.
3. **Back up first** with `backup`, unless the user declines. Do not add `--rm` (permanent deletion) unless the user asks for it.
4. **Output contains personal identifiers** (email, account / device UUIDs, project paths, cookie names). Summarize findings for the user; do not paste raw reports into issues, commits, PRs, or third-party services, and do not commit `backups/`, `reports/` or `logs/`.
5. **Warn before `clean --yes`**: it quits Claude and any running Chromium-family browser (Chrome, Edge, Brave, Arc, Vivaldi, Chromium).
6. **Use `--lang en`** when you parse text output. JSON keys are always English.
7. **Do not run the interactive menu** (no arguments). Always pass a subcommand.

## Non-interactive behavior

| Situation | Behavior |
| --- | --- |
| `clean` without `--yes` | Asks the user to type `DELETE`; with no TTY it cancels and deletes nothing. |
| `clean --yes` | Skips the confirmation. Never removes launch agents or files inside the user's projects; those are skipped with a message. |
| `backup` with no TTY on stdin | The encrypted DMG step is skipped (it needs a password). Pass `--no-dmg` to make this explicit. |
| `backup --yes`, items larger than 2 GB (usually the Cowork VM) | Skipped unless `--include-big`. `clean` still removes them. |
| System-wide crash reports | Need `sudo`; without a TTY the attempt fails harmlessly. |

Progress messages go to **stderr**; results go to **stdout**.

## Commands

All commands: `~/.local/bin/cfd <command> [options] [--lang en|zh|auto]`

| Command | Purpose | Typical runtime |
| --- | --- | --- |
| `check [--json] [--save]` | Fingerprint check with score and findings (read-only) | 3–5 min |
| `check --extra` / `check --deep` | + credentials, secret scan, external traces, system protection | 6 / 10+ min |
| `backup [--yes] [--no-dmg] [--include-big]` | Archive every Claude trace into `backups/<timestamp>/` | depends on size |
| `clean [--yes] [--rm] [--repo-root DIR]` | Remove every Claude trace (Trash by default), then verify | depends on size |
| `scan [--json] [-v]` | Every location `clean` would touch, with sizes (read-only) | seconds |
| `verify` | Look for leftovers (read-only) | seconds |
| `manual` | Steps the tool cannot do locally (browser extension, phone, Time Machine, key rotation) | instant |

Exit codes: `0` success, `1` backup was not created.

## Recommended workflow

When the user asks to "check / clean my Claude fingerprints":

```bash
P=~/.local/bin/cfd

# 1. Check (read-only). Summarize the score and HIGH findings for the user.
$P check --json --lang en > /tmp/cfd_check.json

# 2. Show what clean would remove (read-only), then ask for explicit approval.
$P scan --json --lang en > /tmp/cfd_scan.json

# 3. Only after approval: back up, then clean (clean verifies at the end).
$P backup --yes --no-dmg --lang en
$P clean --yes --lang en

# 4. Hand over the manual steps.
$P manual --lang en

rm -f /tmp/cfd_check.json /tmp/cfd_scan.json
```

Tell the user where the backup is (`backups/<timestamp>/`, with `HOW_TO_RESTORE.txt`) and that it contains the same identifiers, so it should be deleted or encrypted when no longer needed.

## JSON output

`check --json`:

```json
{
  "time": "2026-01-01T12:00:00",
  "mode": "Fingerprint check",
  "score": 42,
  "counts": {"high": 5, "medium": 7, "low": 3},
  "sections": [
    {"title": "1. Account & device identifiers: ...",
     "rows": [{"kind": "risk", "level": "high", "text": "...", "advice": "..."}]}
  ]
}
```

`kind` is `risk`, `ok` or `info`; `level` is `high`, `medium`, `low` or `null`. Score is 0–100, higher is cleaner.

`scan --json`: a list of `{"category", "name", "found", "count", "bytes", "paths", "details"}`.

## Contributing

- Files: `install.sh` (installer / uninstaller), `claude_fingerprint_detect.py` (catalog, scan, backup, clean, menu, CLI), `fingerprint_check.py` (fingerprint sections), `health_check.py` (report, scoring, extra checks), `i18n.py` (language detection and Chinese strings).
- Keep Python 3.9 compatible (no `match`, no `X | Y` types), standard library only, no network calls.
- Checks must stay read-only: open SQLite with `?immutable=1`, never read keychain secrets (`security find-*-password` without `-g`).
- Never hard-code anything specific to one machine (user names, IDs, sizes, personal paths).
- UI strings: wrap user-facing literals in `T("...")` and add the Simplified Chinese translation to `ZH` in `i18n.py`, keyed by the exact English string. Verify nothing is missing or unused:

```bash
python3 - <<'EOF'
import ast, i18n
used, missing = set(), []
for fn in ["claude_fingerprint_detect.py", "health_check.py", "fingerprint_check.py"]:
    for n in ast.walk(ast.parse(open(fn, encoding="utf-8").read())):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "T" and n.args:
            try:
                v = ast.literal_eval(n.args[0])
            except ValueError:
                continue
            used.add(v)
            if v not in i18n.ZH:
                missing.append((fn, n.lineno, v))
print("missing:", missing)
print("unused:", [k for k in i18n.ZH if k not in used and k != " (follows system)"])
EOF
```

- Smoke test before committing: `python3 -m py_compile *.py`, then `--version`, `scan`, and `clean < /dev/null` (shows the preview and cancels) in both `--lang en` and `--lang zh`.
