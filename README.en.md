# claude-fingerprint-detect

[简体中文](README.md)

See what Claude (the desktop app, Claude Code and Cowork) has left on your Mac that can identify **you, your device and your account** — and clean it up safely if you want to.

- **Check**: finds account and device IDs, tracking cookies, the hardware / environment profile that gets reported, usage patterns, and whether telemetry is switched off. Gives you a score and a report.
- **Back up**: archives sessions, config and credentials before touching anything (optionally into an encrypted disk image); apps, caches and logs that can be re-downloaded or are regenerated are skipped.
- **Clean**: removes every Claude trace in one go, after showing you the full list and asking for confirmation.

> **Unofficial tool.** Not affiliated with, endorsed by, or supported by Anthropic. "Claude" is a trademark of Anthropic.

## Quick start

Install the `cfd` command in Terminal (into `~/.claude-fingerprint-detect`, nothing else is touched):

```bash
curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash
```

Then, in a new terminal window:

```bash
cfd check    # 1. fingerprint check (read-only)
cfd backup   # 2. back up
cfd clean    # 3. clean (shows what will be removed and asks first)
```

After cleaning, run `cfd manual` for what you have to do by hand (browser extension, phone app, rotating leaked keys). Run `cfd` with no arguments for an interactive menu. The interface follows your Mac's language (English or Simplified Chinese).

Using an AI agent? Ask it:

> Install https://github.com/nsstream/claude-fingerprint-detect following its AGENTS.md and run a fingerprint check.

## Is it safe?

- **The check only reads.** It never changes or deletes anything.
- **No network.** Apart from downloading the code when you install or update, the tool makes no network requests and uploads nothing.
- **Nothing is deleted without asking.** Every clean lists what will be removed and only runs after you type `DELETE`. Files go to the Trash by default.
- **Open source, no dependencies.** Plain Python that ships with macOS; read it before you run it.

## Requirements

- macOS (Apple silicon or Intel).
- Nothing else to install. If the installer says Python is missing, run `xcode-select --install` to get the Command Line Tools, then run the install command again.

## Before you clean

- `clean` removes **everything** Claude left behind, including the apps themselves, and signs you out. Reinstall and log in again if you keep using Claude.
- If Claude is running, the tool asks to quit it (otherwise it would write the files back).
- After cleaning shell history, close all Terminal windows and open new ones.
- Project files such as `CLAUDE.md`, `.claude/` or `.mcp.json` inside your projects are only reported, never deleted or backed up.

## What it looks at

| Category | Examples |
| --- | --- |
| Identity & credentials | account / device IDs in `~/.claude.json` and its backups, OAuth tokens, keychain entries |
| Sessions & content | prompt history, session transcripts, paste cache, Cowork sessions |
| Telemetry & logs | queued telemetry, Sentry data, logs, crash reports |
| Cowork virtual machine | VM images and data disk (fixed VM UUID / MAC address) |
| Desktop app browser data | cookies, local storage, caches |
| Config, MCP, plugins | MCP configs (may hold third-party tokens), settings, skills |
| Application files | the apps themselves and leftover folders |
| macOS integration | preference files, recent documents, browser extension bridges, launch agents |
| Shell history | commands mentioning claude / anthropic |
| Other browsers | claude.ai / anthropic.com cookies and history in Chrome, Edge, Brave, Arc, Vivaldi, Chromium |
| Third-party tools | Claude plugins in Cursor, JetBrains, Bun |
| Your projects | `.claude/`, `CLAUDE.md`, `.mcp.json` in common project folders (listed, never deleted) |

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

## Your data stays in the tool folder

Reports, backups and logs are written to `reports/`, `backups/` and `logs/` inside `~/.claude-fingerprint-detect/`. They contain the same identifiers the tool found, so:

- delete them when you are done, or keep only the encrypted backup (`.dmg`);
- do not put this folder in iCloud Drive / Dropbox (the check warns you if it is);
- if you fork the repository, these folders are already in `.gitignore` — never force-add them.

## Restore from a backup

Each backup folder has a `HOW_TO_RESTORE.txt`. In short: quit Claude, then in Terminal run `tar -xzf <archive>.tar.gz -C /` for the archive you need. Keychain passwords are never exported, so you sign in again after restoring. To start with a fresh identity, restore only what you need (sessions, config) and leave the identity & credentials archive out.

## All commands

```bash
cfd check                  # fingerprint check
cfd check --extra --save   # + credentials, secret leaks, system protection; save report
cfd backup                 # back up everything
cfd clean                  # remove everything
cfd scan -v                # see every location that would be cleaned
cfd verify                 # look for leftovers
cfd manual                 # manual checklist
cfd --help
```

`clean --yes` skips the confirmation but never removes launch agents or files inside your projects. Automation and AI agents: see [AGENTS.md](AGENTS.md).

**Update**: run the install command again. **Uninstall**:

```bash
curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash -s -- --uninstall
```

(If the folder still holds backups or reports, it is kept and you are told how to delete it.)

## Limitations

- What Claude stores and reports was observed on current versions and may change with updates. The check reports what it actually finds on your Mac; treat its explanations as best-effort.
- Cleaning your Mac does not delete anything on Anthropic's servers. For that, use the account and privacy settings on claude.ai.
- Secrets that already appeared in conversations have been sent; deleting local copies is not enough — rotate them.
- macOS only.

## License

[MIT](LICENSE). Use at your own risk; the backup step exists for a reason.
