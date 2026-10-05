# claude-fingerprint-detect

[简体中文](README.zh-CN.md)

See what Claude (the desktop app, Claude Code and Cowork) has left on your Mac that can identify **you, your device and your account** — and clean it up safely if you want to.

- **Check**: finds account and device IDs, tracking cookies, the hardware / environment profile that gets reported, usage patterns, and whether telemetry is switched off. Gives you a score and a report.
- **Back up**: archives everything before touching it (optionally into an encrypted disk image).
- **Clean**: removes every Claude trace in one go, after showing you the full list and asking for confirmation.

> **Unofficial tool.** Not affiliated with, endorsed by, or supported by Anthropic. "Claude" is a trademark of Anthropic.

## Quick start

Install the `claude-fingerprint-detect` command (into `~/.claude-fingerprint-detect`, nothing else is touched):

```bash
curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash
```

Then, in a new terminal window:

```bash
claude-fingerprint-detect check    # 1. fingerprint check (read-only)
claude-fingerprint-detect backup   # 2. back up
claude-fingerprint-detect clean    # 3. clean (shows what will be removed and asks first)
```

`clean` removes **everything** Claude left behind, including the apps themselves — reinstall Claude afterwards if you want to keep using it. Prefer clicking? See [Get started](#get-started). Using an AI agent? Ask it:

> Install https://github.com/nsstream/claude-fingerprint-detect following its AGENTS.md and run a fingerprint check.

## Is it safe?

- **The check only reads.** It never changes or deletes anything.
- **No internet.** The tool makes no network requests and sends nothing anywhere.
- **Nothing is deleted without asking.** Every clean lists what will be removed and waits for your confirmation. Files go to the Trash by default.
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

1. **Fingerprint check** (menu 1). Takes a few minutes. Each finding says why it matters.
2. **Clean** (menu 3): backs up, lists everything that will be removed, asks you to type `DELETE`, cleans, then verifies.
3. Go through the **Manual checklist** (menu 4) for things the tool cannot do locally (browser extension, phone app, Time Machine, rotating leaked keys).

**Good to know before cleaning**

- Cleaning removes the Claude apps and signs you out. Reinstall and log in again if you keep using Claude.
- If Claude is running, the tool asks to quit it (otherwise it would write the files back).
- After cleaning shell history, close all Terminal windows and open new ones.
- Project files such as `CLAUDE.md` or `.claude/` inside your projects are always confirmed one by one.

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
| Your projects | `.claude/`, `CLAUDE.md`, `.mcp.json` in common project folders |

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

## Command line

Installed with the Quick start command above (run it again to update; uninstall with `curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash -s -- --uninstall`).

```bash
claude-fingerprint-detect check                  # fingerprint check
claude-fingerprint-detect check --extra --save   # + credentials, secret leaks, system protection; save report
claude-fingerprint-detect backup                 # back up everything
claude-fingerprint-detect clean                  # remove everything
claude-fingerprint-detect scan -v                # see every location that would be cleaned
claude-fingerprint-detect verify                 # look for leftovers
claude-fingerprint-detect --lang zh check        # force a language (en | zh | auto)
claude-fingerprint-detect --help
```

`clean --yes` skips the confirmation but never removes launch agents or files inside your projects. Set `CFD_LANG=zh` or `CFD_LANG=en` to fix the language. Automation and AI agents: see [AGENTS.md](AGENTS.md).

## Limitations

- What Claude stores and reports was observed on current versions and may change with updates. The check reports what it actually finds on your Mac; treat its explanations as best-effort.
- Cleaning your Mac does not delete anything on Anthropic's servers. For that, use the account and privacy settings on claude.ai.
- Secrets that already appeared in conversations have been sent; deleting local copies is not enough — rotate them.
- macOS only.

## License

[MIT](LICENSE). Use at your own risk; the backup step exists for a reason.
