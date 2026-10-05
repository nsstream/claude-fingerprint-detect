# claude-fingerprint-detect

[简体中文](README.zh-CN.md)

See what Claude (the desktop app, Claude Code and Cowork) has left on your Mac that can identify **you, your device and your account** — and clean it up safely if you want to.

- **Check**: finds account and device IDs, tracking cookies, the hardware / environment profile that gets reported, usage patterns, and whether telemetry is switched off. Gives you a score and a report.
- **Back up**: archives everything before touching it (optionally into an encrypted disk image).
- **Clean**: removes what you choose, by risk level or category, with a preview and confirmation at every step.

> **Unofficial tool.** Not affiliated with, endorsed by, or supported by Anthropic. "Claude" is a trademark of Anthropic.

## Is it safe?

- **The check only reads.** It never changes or deletes anything.
- **No internet.** The tool makes no network requests and sends nothing anywhere.
- **Nothing is deleted without asking.** Every clean shows a preview first. Files go to the Trash by default, and there is a dry-run mode that only shows what would happen.
- **Open source, no dependencies.** Plain Python that ships with macOS — read every line before running it.

## Requirements

- macOS (Apple Silicon or Intel)
- Nothing to install. The first time you run it, macOS may ask to install the *Command Line Tools* (that is where Python comes from) — click **Install** and run it again afterwards.

## Get started

1. On this page click **Code → Download ZIP**, then double-click the ZIP to unzip it.
2. Open the folder and double-click **`start.command`**.
   - If macOS says it cannot be opened: right-click `start.command` → **Open** → **Open**.
   - On newer macOS versions you may instead need **System Settings → Privacy & Security → Open Anyway**.
3. A Terminal window opens with a menu. Type a number and press Enter.

The interface follows your Mac's language (English or Simplified Chinese). You can switch it in **Settings**.

## Recommended steps

1. **Fingerprint check** (menu 1). Takes a few minutes. Read the findings — each one says why it matters and which cleanup items fix it.
2. **Scan** (menu 2) to see every location and how much space it uses.
3. **Settings → Dry run ON**, then try **Clean** (menu 4). You will see exactly what would be removed, without removing anything.
4. Turn dry run off and use **All-in-one** (menu 5): choose → back up → clean → verify.
5. Go through the **Manual checklist** (menu 7) for things the tool cannot do locally (browser extension, phone app, Time Machine, rotating leaked keys).

**Good to know before cleaning**

- The "privacy" preset signs you out: Claude apps keep working, you just log in again.
- If Claude is running, the tool asks to quit it (otherwise it would write the files back).
- After cleaning shell history, close all Terminal windows and open new ones.
- Project files such as `CLAUDE.md` or `.claude/` inside your projects are always confirmed one by one.

## What it looks at

| Category | Examples |
| --- | --- |
| A. Identity & credentials | account / device IDs in `~/.claude.json` and its backups, OAuth tokens, keychain entries |
| B. Sessions & content | prompt history, session transcripts, paste cache, Cowork sessions |
| C. Telemetry & logs | queued telemetry, Sentry data, logs, crash reports |
| D. Cowork virtual machine | VM images and data disk (fixed VM UUID / MAC address) |
| E. Desktop app browser data | cookies, local storage, caches |
| F. Config, MCP, plugins | MCP configs (may hold third-party tokens), settings, skills |
| G. Application files | the apps themselves and leftover folders (full uninstall only) |
| H. macOS integration | preference files, recent documents, browser extension bridges, launch agents |
| I. Shell history | commands mentioning claude / anthropic |
| J. Other browsers | claude.ai / anthropic.com cookies and history in Chrome, Edge, Brave, Arc, Vivaldi, Chromium |
| K. Third-party tools | Claude plugins in Cursor, JetBrains, Bun |
| L. Your projects | `.claude/`, `CLAUDE.md`, `.mcp.json` in common project folders |

## Keep it quiet afterwards

If you keep using Claude Code, add this to `~/.claude/settings.json` (merge with what is already there) to turn off optional reporting and keep Claude away from sensitive files:

```json
{
  "env": {
    "DISABLE_TELEMETRY": "1",
    "DISABLE_ERROR_REPORTING": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_AUTOUPDATER": "1",
    "DISABLE_BUG_COMMAND": "1",
    "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1"
  },
  "permissions": {
    "deny": ["Read(~/.ssh/**)", "Read(~/.aws/**)", "Read(~/.config/gh/**)", "Read(./.env)", "Read(./.env.*)"]
  },
  "cleanupPeriodDays": 7
}
```

Re-apply it if you ever wipe `~/.claude`. In the desktop app, check its settings for crash / usage reporting as well.

## Your data stays in this folder

Reports, backups and logs are written next to the tool, in `reports/`, `backups/` and `logs/`. They contain the same identifiers the tool found, so:

- delete them when you are done, or keep only the encrypted backup (`.dmg`);
- do not put this folder in iCloud Drive / Dropbox (the check warns you if it is);
- if you fork the repository, these folders are already in `.gitignore` — never force-add them.

## Restore from a backup

Each backup folder has a `HOW_TO_RESTORE.txt`. In short: quit Claude, then in Terminal run `tar -xzf <archive>.tar.gz -C /` for the archive you need. Keychain passwords are never exported, so you sign in again after restoring.

## Command line (optional)

Everything in the menu is also available as commands; results print straight to the terminal.

```bash
python3 claude_fingerprint_detect.py check                  # fingerprint check
python3 claude_fingerprint_detect.py check --extra --save   # + credentials, secret leaks, system protection; save report
python3 claude_fingerprint_detect.py check --json           # machine-readable output
python3 claude_fingerprint_detect.py scan -v                # every location and its size
python3 claude_fingerprint_detect.py list                   # all cleanup item IDs
python3 claude_fingerprint_detect.py clean --preset privacy --dry-run
python3 claude_fingerprint_detect.py clean --ids A1,A2 --backup
python3 claude_fingerprint_detect.py verify
python3 claude_fingerprint_detect.py --lang zh check        # force a language (en | zh | auto)
python3 claude_fingerprint_detect.py --help
```

Presets: `privacy` (keep the apps), `uninstall` (remove everything), `high`, `high_mid`. `--yes` auto-confirms but never removes launch agents or files inside your projects. Set `CFD_LANG=zh` or `CFD_LANG=en` to fix the language.

## Limitations

- What Claude stores and reports was observed on current versions and may change with updates. The check reports what it actually finds on your Mac; treat its explanations as best-effort.
- Cleaning your Mac does not delete anything on Anthropic's servers. For that, use the account and privacy settings on claude.ai.
- Secrets that already appeared in conversations have been sent; deleting local copies is not enough — rotate them.
- macOS only.

## License

[MIT](LICENSE). Use at your own risk; the backup step exists for a reason.
