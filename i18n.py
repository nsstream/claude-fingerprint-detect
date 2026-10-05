# -*- coding: utf-8 -*-
"""UI language: English by default, Simplified Chinese when the macOS preferred language is Chinese.

Priority: --lang en|zh|auto  >  CFD_LANG environment variable  >  macOS AppleLanguages  >  LC_ALL / LANG.
Strings are looked up by their English text; anything missing from the table is shown in English.
"""
import os
import re
import subprocess

SUPPORTED = ("en", "zh")
LANG = "en"
SOURCE = "system"


def system_lang():
    try:
        out = subprocess.run(["defaults", "read", "-g", "AppleLanguages"], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL).stdout.decode("utf-8", "replace")
        m = re.search(r'"?([A-Za-z]{2,3})[-_A-Za-z]*"?\s*[,)]', out)
        if m:
            return "zh" if m.group(1).lower() == "zh" else "en"
    except (OSError, FileNotFoundError):
        pass
    loc = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    return "zh" if loc.lower().startswith("zh") else "en"


def set_lang(value, source):
    global LANG, SOURCE
    value = (value or "auto").lower()
    if value.startswith("zh") or value in ("cn", "chinese"):
        LANG, SOURCE = "zh", source
    elif value.startswith("en"):
        LANG, SOURCE = "en", source
    else:
        LANG, SOURCE = system_lang(), "system"


def init(argv):
    """Pick the language and remove --lang from argv in place."""
    chosen, i = None, 1
    while i < len(argv):
        a = argv[i]
        if a == "--lang" and i + 1 < len(argv):
            chosen = argv[i + 1]
            del argv[i:i + 2]
            continue
        if a.startswith("--lang="):
            chosen = a.split("=", 1)[1]
            del argv[i]
            continue
        i += 1
    if chosen:
        set_lang(chosen, "flag")
    elif os.environ.get("CFD_LANG"):
        set_lang(os.environ["CFD_LANG"], "env")
    else:
        set_lang("auto", "system")


def label():
    name = "中文" if LANG == "zh" else "English"
    return name + (T(" (follows system)") if SOURCE == "system" else "")


def T(s):
    if LANG == "zh":
        return ZH.get(s, s)
    return s


ZH = {
    # ───────────── shared ─────────────
    " (follows system)": "（跟随系统）",
    "%s [auto: yes]": "%s [自动：是]",
    "%s: %s": "%s：%s",
    "%s x%d": "%s×%d",
    "delete": "删除",
    "not found": "未发现",
    "%d paths, %s": "%d 个路径，%s",

    # ───────────── categories ─────────────
    "Identity & credentials": "身份与凭据",
    "Sessions & content": "会话与内容",
    "Telemetry, logs & crash reports": "遥测、日志与崩溃报告",
    "Cowork virtual machine": "Cowork 虚拟机",
    "Desktop app embedded browser data (cookies / storage / cache)": "桌面版内嵌浏览器数据（Cookie / 存储 / 缓存）",
    "Config, MCP, plugins & skills": "配置、MCP、插件与技能",
    "Application files & leftover directories": "应用程序文件与残留目录",
    "macOS system integration traces": "macOS 系统集成痕迹",
    "Shell history": "Shell 历史",
    "External browsers (Chromium family)": "外部浏览器（Chromium 系）",
    "Claude leftovers in third-party tools": "第三方工具中的 Claude 残留",
    "Claude files inside project repositories": "项目仓库中的 Claude 文件",

    # ───────────── items ─────────────
    "Claude Code account & device IDs (userID / machineID / oauthAccount / email) and all backups":
        "Claude Code 账号与设备 ID（userID / machineID / oauthAccount / 邮箱）及所有备份",
    "Deleting only the main file is not enough: .backup / .bak* hold the same userID":
        "只删主文件不够：.backup / .bak* 里是同一个 userID",
    "Claude Code config backup directory": "Claude Code 配置备份目录",
    "Claude Code plaintext OAuth tokens": "Claude Code 明文 OAuth 令牌",
    "Desktop app device ID (ant-did), device registry, hardware probe": "桌面版设备 ID（ant-did）、设备注册、硬件探测",
    "Desktop app account config, tokens and remote-session bridge state": "桌面版账号配置、令牌与远程会话桥接状态",
    "Claude / Anthropic keychain entries": "Claude / Anthropic 钥匙串条目",
    "Backups record entry metadata only; secrets are not exported": "备份只记录条目信息，不导出密钥",
    "Claude Code prompt history (every prompt you typed)": "Claude Code 输入历史（你输入过的每一条提示）",
    "Claude Code full session transcripts": "Claude Code 完整会话记录",
    "File snapshots, paste cache, shell / environment snapshots (may contain secrets)":
        "文件快照、粘贴缓存、Shell / 环境快照（可能含密钥）",
    "Desktop app Code / Cowork sessions, pending uploads, space memory": "桌面版 Code / Cowork 会话、待上传文件、空间记忆",
    "local_*.json contains your email, system prompt and mounted folders": "local_*.json 里有邮箱、系统提示词和挂载目录",
    "Debug logs, feedback drafts, downloads": "调试日志、反馈草稿、下载文件",
    "Claude Code telemetry leftovers & stats cache": "Claude Code 遥测残留与统计缓存",
    "Desktop app Sentry / Crashpad / performance observer DB": "桌面版 Sentry / Crashpad / 性能观测数据库",
    "Desktop app logs": "桌面版日志",
    "macOS crash reports (file names contain the hardware UUID)": "macOS 崩溃报告（文件名含硬件 UUID）",
    "System-wide crash reports (requires sudo)": "系统级崩溃报告（需要 sudo）",
    "Cowork VM images & session data disk (unencrypted, contains copies of secrets)":
        "Cowork 虚拟机镜像与会话数据盘（未加密，含密钥副本）",
    "Usually several GB; holds the VM UUID / MAC address":
        "通常有几个 GB，包含虚拟机 UUID / MAC 地址",
    "Claude Code VM runtime": "Claude Code 虚拟机运行时",
    "Desktop app cookies & site storage (login state, ajs_*, analytics IDs)": "桌面版 Cookie 与站点存储（登录态、ajs_*、分析 ID）",
    "Desktop app caches (HTTP / code / GPU)": "桌面版缓存（HTTP / 代码 / GPU）",
    "MCP configs and their backups (may contain third-party tokens)": "MCP 配置及其备份（可能含第三方令牌）",
    "Claude Code settings, plugins, skills, subagents, rules (incl. synced skill folders)":
        "Claude Code 设置、插件、技能、子代理、规则（含同步的技能目录）",
    "Desktop app extensions, skills and window state": "桌面版扩展、技能与窗口状态",
    "Claude desktop application": "Claude 桌面应用",
    "Claude Code binaries & state": "Claude Code 程序与状态",
    "Application caches & temp files": "应用缓存与临时文件",
    "Remove leftover directories entirely (~/.claude, desktop app data dir, Claude-3p)":
        "整体删除残留目录（~/.claude、桌面版数据目录、Claude-3p）",
    "Catch-all item, always runs last": "兜底项，总是最后执行",
    "Preference plists (ByHost file name contains the hardware UUID)": "偏好设置 plist（ByHost 文件名含硬件 UUID）",
    "\"Recent documents\" record": "“最近使用的文档”记录",
    "HTTPStorages / saved application state / WebKit / sandbox containers": "HTTPStorages / 已存储的应用状态 / WebKit / 沙盒容器",
    "Browser native messaging hosts (Claude browser extension bridge)": "浏览器原生消息宿主（Claude 浏览器扩展桥接）",
    "LaunchAgents that invoke Claude": "调用 Claude 的 LaunchAgents",
    "Shell history entries mentioning claude / anthropic": "提到 claude / anthropic 的 Shell 历史记录",
    "Claude env vars / aliases in shell rc files (report only, edit manually)":
        "Shell 配置文件里的 Claude 环境变量 / 别名（只报告，需手动修改）",
    "claude / anthropic cookies, history, saved passwords, IndexedDB in Chromium browsers":
        "Chromium 系浏览器中 claude / anthropic 的 Cookie、历史、已存密码、IndexedDB",
    "Quit the browser first; Safari is covered in the manual checklist": "需先退出浏览器；Safari 见手动事项清单",
    "Claude plugins & caches in Cursor / Bun / JetBrains": "Cursor / Bun / JetBrains 中的 Claude 插件与缓存",
    "Anthropic references in other tools' configs (report only, edit manually)":
        "其他工具配置中对 Anthropic 的引用（只报告，需手动修改）",
    ".claude folders, CLAUDE.md, .mcp.json inside projects (confirmed one by one)":
        "项目中的 .claude 目录、CLAUDE.md、.mcp.json（逐个确认）",

    # ───────────── manual checklist ─────────────
    "Chrome: remove the Claude extension at chrome://extensions (fcoeoabgfenejglbffodgkkbkcdhcgfn); if sync is on, also delete at myactivity.google.com.":
        "Chrome：在 chrome://extensions 移除 Claude 扩展（fcoeoabgfenejglbffodgkkbkcdhcgfn）；开了同步的话，还要到 myactivity.google.com 删除。",
    "Safari: search history for \"claude\" and delete; Settings > Privacy > Manage Website Data, remove claude.ai / anthropic.com.":
        "Safari：在历史记录中搜索“claude”并删除；设置 > 隐私 > 管理网站数据，移除 claude.ai / anthropic.com。",
    "claude.ai > Settings: sign out other devices and sessions; review connected integrations.":
        "claude.ai > 设置：退出其他设备和会话，检查已连接的集成。",
    "Mobile app: signing out does not wipe local data; delete the app.": "手机 App：退出登录不会清除本地数据，需要删除 App。",
    "Other computers / remote dev boxes: each has its own set of traces and must be cleaned separately.":
        "其他电脑 / 远程开发机：每台都有自己的一套痕迹，需要分别清理。",
    "Rotate secrets: API keys, private keys and MCP tokens that appeared in transcripts or the Cowork disk were already sent, even if deleted locally.":
        "轮换密钥：出现在会话记录或 Cowork 数据盘里的 API Key、私钥、MCP 令牌已经发送过，本地删除也无济于事。",
    "Time Machine: use \"Delete All Backups of\" on the directories above; list local snapshots with `tmutil listlocalsnapshots /`, delete with `tmutil deletelocalsnapshots <date>`.":
        "Time Machine：对上述目录使用“删除…的所有备份”；用 `tmutil listlocalsnapshots /` 查看本地快照，用 `tmutil deletelocalsnapshots <日期>` 删除。",
    "iCloud Drive / cloud sync: make sure ~/.claude, project .claude folders and backup archives are not synced.":
        "iCloud 云盘 / 网盘同步：确认 ~/.claude、项目里的 .claude 目录和备份包没有被同步。",
    "System Settings > General > Login Items & Extensions: confirm Claude / ShipIt is gone.":
        "系统设置 > 通用 > 登录项与扩展：确认 Claude / ShipIt 已经消失。",
    "git: local `claude` branches (git branch -D claude) and \"Co-Authored-By: Claude\" trailers (rewrite only unpushed repos with git filter-repo).":
        "git：本地 `claude` 分支（git branch -D claude）和 “Co-Authored-By: Claude” 尾注（只对未推送的仓库用 git filter-repo 改写）。",
    "Spotlight: after cleaning, rebuild the index with `sudo mdutil -E /`.": "聚焦搜索：清理后用 `sudo mdutil -E /` 重建索引。",
    "Finally: empty the Trash; this tool's backups/ and reports/ folders contain every fingerprint too, encrypt or delete them.":
        "最后：清空废纸篓；本工具的 backups/ 和 reports/ 同样含全部指纹，请加密或删除。",

    # ───────────── scan / selection ─────────────
    "%s: %d matching entries": "%s：%d 条命中",
    "%s/%s: %d cookies, %d history URLs, %d saved passwords, %d site storage dirs":
        "%s/%s：Cookie %d 个，历史 URL %d 条，已存密码 %d 个，站点存储目录 %d 个",
    "%d paths": "%d 个路径",
    "%d hits": "%d 处命中",
    "○ not found": "○ 未发现",
    "Scanning": "扫描中",
    "Scanning for secrets": "扫描密钥",
    "Searching for your IDs": "查找你的标识",
    "%s left": "剩余 %s",

    # ───────────── backup ─────────────
    "Skipping large item %s (%s); add --include-big to include it": "跳过大项 %s（%s）；加 --include-big 可包含",
    "Skipping large item %s": "跳过大项 %s",
    "Disk space may be insufficient.": "磁盘空间可能不足。",
    "Start the backup?": "开始备份？",
    "  [%s] tar exited with %d (some files may be unreadable or in use); archived what it could":
        "  [%s] tar 返回 %d（部分文件可能无法读取或正在使用），已尽量打包",
    "(no entries found)\n": "（未找到条目）\n",
    "Every tar.gz stores absolute paths relative to the root directory /.\n"
    "Restore everything:   cd <this folder> && for a in *.tar.gz; do tar -xzf \"$a\" -C /; done\n"
    "List contents:        tar -tzf A_xxx.tar.gz\n"
    "Restore one path:     tar -xzf A_xxx.tar.gz -C / Users/<your-user>/.claude.json\n"
    "Note: restoring a Chrome database overwrites all cookies / history of that browser; quit it first.\n"
    "Keychain secrets were not exported; you will need to sign in again after restoring.\n":
        "每个 tar.gz 都以根目录 / 为基准保存绝对路径。\n"
        "全部恢复：   cd <本目录> && for a in *.tar.gz; do tar -xzf \"$a\" -C /; done\n"
        "查看内容：   tar -tzf A_xxx.tar.gz\n"
        "恢复单个路径：tar -xzf A_xxx.tar.gz -C / Users/<用户名>/.claude.json\n"
        "注意：恢复 Chrome 数据库会覆盖该浏览器的全部 Cookie / 历史，请先退出浏览器。\n"
        "钥匙串密钥没有导出，恢复后需要重新登录。\n",
    "Backup finished: %s (%s)": "备份完成：%s（%s）",
    "Pack the backup into an AES-256 encrypted DMG (you will be asked for a password)?":
        "把备份打包成 AES-256 加密 DMG 吗（会要求设置密码）？",
    "Encrypted DMG: %s": "加密 DMG：%s",
    "Delete the unencrypted backup folder?": "删除未加密的备份文件夹？",
    "Deleted plaintext backup folder %s": "已删除明文备份文件夹 %s",
    "DMG creation failed; the plaintext backup remains at %s": "DMG 创建失败，明文备份仍在 %s",

    # ───────────── clean ─────────────
    "  FAILED %s: %s": "  失败 %s：%s",
    "  deleted ": "  已删除 ",
    "  FAILED ": "  失败 ",
    "  deleted keychain entry %s %s": "  已删除钥匙串条目 %s %s",
    "  The keychain still has matches (search in Keychain Access and delete manually):":
        "  钥匙串里仍有匹配项（请在“钥匙串访问”中搜索并手动删除）：",
    "  %s: removed %d commands": "  %s：已删除 %d 条命令",
    "  %s is running and must quit before its databases can be changed. Quit it now?":
        "  %s 正在运行，修改数据库前必须退出。现在退出吗？",
    "  skipped %s/%s": "  已跳过 %s/%s",
    "  %s/%s %s: deleted %d rows": "  %s/%s %s：删除 %d 行",
    "  failed to modify %s: %s": "  修改 %s 失败：%s",
    "  skipped (--yes never removes launch agents; run without --yes to confirm): %s": "  已跳过（--yes 不会删除启动项，去掉 --yes 可逐个确认）：%s",
    "  skipped %d project files (--yes never removes them; run without --yes to confirm each)": "  已跳过 %d 个项目文件（--yes 不会删除它们，去掉 --yes 可逐个确认）",
    "  Unload and delete this launch agent?": "  卸载并删除这个启动项？",
    "  Confirm each: y=delete  n=keep  a=delete all remaining  q=stop": "  逐个确认：y=删除  n=保留  a=剩余全部删除  q=停止",
    "\nClaude-related processes are running (if left running they will write the files back):":
        "\n检测到 Claude 相关进程在运行（不退出的话会把文件重新写回）：",
    "Quit these processes now?": "现在退出这些进程？",
    "Attempted to quit Claude-related processes": "已尝试退出 Claude 相关进程",
    "... and %d more": "…… 另有 %d 个",
    "move to Trash": "移到废纸篓",
    "delete permanently (cannot be undone)": "直接删除（不可恢复）",
    "  Note: close every terminal window and reopen; otherwise running shells write their in-memory history back on exit.":
        "  注意：关闭所有终端窗口后再重开，否则正在运行的 Shell 退出时会把内存里的历史写回去。",
    "  These locations need manual editing:": "  以下位置需要手动修改：",

    # ───────────── verify / manual / settings ─────────────
    "Verification passed: no leftovers at any known risk location.": "验证通过：所有已知风险位置都没有残留。",
    "%d items still have leftovers:": "仍有 %d 项存在残留：",
    "delete permanently": "直接删除",
    "Comma-separated directories> ": "逗号分隔的目录> ",
    "No backup was created. Continue cleaning anyway?": "没有生成备份，仍然继续清理吗？",

    # ───────────── check menu / main menu ─────────────
    "This tool only supports macOS.": "本工具仅支持 macOS。",
    "\nInterrupted.": "\n已中断。",

    # ───────────── CLI ─────────────
    "Claude local fingerprint check, backup and clean (macOS)": "Claude 本机指纹体检、备份与清理（macOS）",
    "extras: credentials, quick secret scan, external traces, system protection": "附加项：凭据、快速密钥扫描、外部痕迹、系统防护",
    "extras (deep): secret scan includes the Cowork data disk": "附加项（深度）：密钥扫描包含 Cowork 数据盘",
    "JSON output": "JSON 输出",
    "also save a Markdown report to reports/": "同时在 reports/ 保存 Markdown 报告",
    "show paths": "显示路径",
    "auto-confirm": "自动确认",
    "include items larger than 2 GB (e.g. the Cowork VM)": "包含大于 2 GB 的项（如 Cowork 虚拟机）",
    "skip the encrypted DMG": "不做加密 DMG",
    "delete permanently (default: move to Trash)": "直接删除（默认移到废纸篓）",
    "auto-confirm everything (quits Claude / browser processes; never removes launch agents or project files)":
        "全部自动确认（会退出 Claude / 浏览器进程；不会删除启动项和项目文件）",
    "project scan root, may be repeated": "项目扫描目录，可重复指定",
    "look for leftovers": "检查残留",
    "manual checklist": "手动事项清单",
    "\nFound %d / %d items, %s in total": "\n发现 %d / %d 项，共 %s",
    "Skipped the encrypted DMG: it needs a password typed in a terminal (pass --no-dmg to silence this).":
        "已跳过加密 DMG：它需要在终端中输入密码（加 --no-dmg 可不再提示）。",

    # ───────────── health_check ─────────────
    "Alibaba Cloud AccessKey": "阿里云 AccessKey",
    "Anthropic API key": "Anthropic API Key",
    "sk- API key (OpenAI / DeepSeek etc.)": "sk- 开头的 API Key（OpenAI / DeepSeek 等）",
    "GitHub token": "GitHub 令牌",
    "GitLab token": "GitLab 令牌",
    "Slack token": "Slack 令牌",
    "Google API key": "Google API Key",
    "Private key": "私钥",
    ".env files": ".env 文件",
    "Advice: ": "建议：",
    "# Claude local fingerprint report": "# Claude 本机指纹体检报告",
    "- Time: %s": "- 时间：%s",
    "- Mode: %s": "- 模式：%s",
    "- Score: **%d / 100** (high %d, medium %d, low %d)": "- 得分：**%d / 100**（高风险 %d，中风险 %d，低风险 %d）",
    "- OK: ": "- 正常：",
    " (length %d)": "（长度 %d）",
    "Extra · Credentials & tokens": "附加 · 凭据与令牌",
    "~/.claude/.credentials.json stores OAuth access / refresh tokens in plaintext (mode %o%s)":
        "~/.claude/.credentials.json 以明文保存 OAuth 访问 / 刷新令牌（权限 %o%s）",
    ", readable by other users": "，其他用户可读",
    "sign out and delete": "退出登录并删除",
    "%d keychain entries: %s": "钥匙串中有 %d 个条目：%s",
    "delete the entries": "删除这些条目",
    "No Claude keychain entries": "钥匙串中没有 Claude 条目",
    "%s.%s (in %d files)": "%s.%s（出现在 %d 个文件）",
    "%d likely secret fields in MCP configs: %s": "MCP 配置中有 %d 个疑似密钥字段：%s",
    "delete the configs and their .bak copies, and rotate these third-party tokens": "删除配置及其 .bak 备份，并轮换这些第三方令牌",
    "No plaintext secret fields in MCP configs": "MCP 配置中没有明文密钥字段",
    "Extra · Secret leaks in sessions & caches (%s)": "附加 · 会话与缓存中的密钥泄露（%s）",
    "deep: includes the Cowork data disk": "深度：含 Cowork 数据盘",
    "quick": "快速",
    "Scanned %d files, %s, in %.0f s%s": "共扫描 %d 个文件、%s，用时 %.0f 秒%s",
    " (files over 30 MB skipped; deep mode scans everything incl. the Cowork disk)":
        "（跳过 30 MB 以上的文件；深度模式会扫描全部，包括 Cowork 数据盘）",
    "No secrets in common formats": "未发现常见格式的密钥",
    "%s: %d distinct values in %d files. Examples: %s": "%s：%d 个不同值，分布在 %d 个文件。示例：%s",
    "these were already sent in conversations; deleting local files is not enough, rotate them at the provider":
        "这些值已经随对话发送过，删除本地文件不够，需要到对应平台轮换",
    "Telemetry & reporting settings": "遥测与上报设置",
    "environment": "环境变量",
    "shell rc": "Shell 配置文件",
    "%s is set (%s)": "已设置 %s（%s）",
    "Not set: %s": "未设置：%s",
    "add them to the env field of ~/.claude/settings.json (template in the README); re-apply after wiping ~/.claude":
        "写入 ~/.claude/settings.json 的 env 字段（README 里有模板）；清理 ~/.claude 后需要重新配置",
    "%d failed-telemetry files (about %d events) may be re-sent on next launch": "有 %d 个遥测失败事件文件（约 %d 条事件），下次启动可能补发",
    "permissions.deny does not block: %s; Claude can read them and send the content as context":
        "permissions.deny 没有屏蔽：%s，Claude 可以读取并把内容发到上下文",
    "add rules such as Read(~/.ssh/**) to permissions.deny in settings.json": "在 settings.json 的 permissions.deny 中加入 Read(~/.ssh/**) 等规则",
    "permissions.deny blocks the common sensitive paths": "permissions.deny 已屏蔽常见敏感路径",
    "cleanupPeriodDays is not set; transcripts are kept long-term by default": "未设置 cleanupPeriodDays，会话记录默认长期保留",
    "set a short retention, e.g. 7": "设置较短的保留天数，例如 7",
    "Extra · Traces outside the Claude directories": "附加 · Claude 目录之外的痕迹",
    "Shell history: %s": "Shell 历史：%s",
    "filter out the matching commands": "过滤掉相关命令",
    "Browser: %s": "浏览器：%s",
    "delete the related cookies / history; remove the extension inside the browser": "删除相关 Cookie / 历史；在浏览器里移除扩展",
    "Browser native messaging hosts: %s": "浏览器原生消息宿主：%s",
    "Other tools' configs referencing Anthropic: %s": "其他工具配置中引用了 Anthropic：%s",
    "edit manually": "手动修改",
    "Claude files in project repositories: %s": "项目仓库中的 Claude 文件：%s",
    "confirm and delete one by one": "逐个确认后删除",
    "This tool has %d unencrypted backups (%s)": "本工具有 %d 份未加密备份（%s）",
    "convert to an encrypted DMG or delete": "转成加密 DMG 或删除",
    "Extra · System protection": "附加 · 系统防护",
    "FileVault is on (deleted data is hard to recover from the SSD)": "FileVault 已开启（删除的数据很难从 SSD 恢复）",
    "FileVault is off: %s": "FileVault 未开启：%s",
    "turn on FileVault, otherwise deleted files may be recoverable": "开启 FileVault，否则删除的文件可能被恢复",
    "No Time Machine destination configured": "未配置 Time Machine 备份目标",
    "~/.claude is excluded from Time Machine": "~/.claude 已从 Time Machine 中排除",
    "Time Machine is configured and ~/.claude is not excluded; old snapshots keep all the data":
        "已配置 Time Machine 且未排除 ~/.claude，旧快照里保留着全部数据",
    "delete the related backups in Time Machine and run `tmutil addexclusion ~/.claude`":
        "在 Time Machine 中删除相关备份，并运行 `tmutil addexclusion ~/.claude`",
    "%d APFS local snapshots exist; cleaned files can still be recovered from them": "存在 %d 个 APFS 本地快照，已清理的文件仍可从中恢复",
    "tmutil deletelocalsnapshots <date>": "tmutil deletelocalsnapshots <日期>",
    "This tool's folder is cloud-synced: its backups, reports and logs are uploaded too (%s)":
        "本工具目录处于云同步位置，备份、报告和日志也会被上传（%s）",
    "move this tool folder somewhere unsynced, or turn off Desktop & Documents sync": "把工具目录移到不同步的位置，或关闭“桌面与文稿”同步",
    "This tool's folder is not in a cloud-synced location":
        "本工具目录不在云同步位置",
    "%s lives in a cloud-synced folder (%s)": "%s 位于云同步目录（%s）",
    "move it out of the synced folder": "移出同步目录",
    "Fingerprint check": "指纹体检",
    "Fingerprint check + extras (credentials, quick secret scan, external traces, system protection)":
        "指纹体检 + 附加项（凭据、快速密钥扫描、外部痕迹、系统防护）",
    "Fingerprint check + extras (secret scan incl. the Cowork data disk)": "指纹体检 + 附加项（密钥扫描含 Cowork 数据盘）",
    "Report saved: %s\n": "报告已保存：%s\n",

    # ───────────── fingerprint_check ─────────────
    "Anthropic device ID": "Anthropic 设备 ID",
    "Segment anonymous ID (long-term cross-session tracking)": "Segment 匿名 ID（跨会话长期追踪）",
    "Segment user ID (bound to the account)": "Segment 用户 ID（绑定账号）",
    "cross-domain anonymous ID (links claude.ai / claude.com / anthropic.com)": "跨域匿名 ID（claude.ai / claude.com / anthropic.com 之间关联）",
    "trusted-device marker (login risk control)": "受信任设备标记（登录风控用）",
    "long-term tracking ID": "长期追踪 ID",
    "last used organization UUID": "最近使用的组织 UUID",
    "Intercom support device ID": "Intercom 客服设备 ID",
    "Intercom support session": "Intercom 客服会话",
    "activity session ID": "活动会话 ID",
    "analytics session ID": "分析会话 ID",
    "Datadog RUM session": "Datadog RUM 会话",
    "Stripe device fingerprint (payment risk control)": "Stripe 设备指纹（支付风控）",
    "Stripe device fingerprint (m.stripe.com)": "Stripe 设备指纹（m.stripe.com）",
    "Cloudflare challenge clearance (bound to device / browser fingerprint)": "Cloudflare 人机验证通过凭证（与设备 / 浏览器指纹绑定）",
    "Cloudflare bot management": "Cloudflare Bot 管理",
    "Cloudflare visitor ID": "Cloudflare 访客 ID",
    "hCaptcha tracking ID": "hCaptcha 追踪 ID",
    "Facebook pixel": "Facebook 像素",
    "DoubleClick ad ID": "DoubleClick 广告 ID",
    "Google preferences / ad ID": "Google 偏好 / 广告 ID",
    "LinkedIn browser ID": "LinkedIn 浏览器 ID",
    "LinkedIn secure browser ID": "LinkedIn 安全浏览器 ID",
    "Google Analytics client ID": "Google Analytics 客户端 ID",
    "Google One Tap sign-in state": "Google 一键登录状态",
    "Inkeep docs assistant user ID": "Inkeep 文档助手用户 ID",
    "third-party visitor key": "第三方访客标识",
    "UI preference / other": "界面偏好 / 其他",
    "cores": "核心数", "memory": "内存", "screen": "屏幕分辨率", "scale": "屏幕缩放", "boot time": "开机时间",
    "GPU vendor": "GPU 厂商", "OS version": "系统版本", "OS build": "系统构建号", "kernel": "内核版本",
    "locale": "语言区域", "timezone": "时区", "app version": "应用版本",
    "account": "账号", "device": "设备", "hardware": "硬件", "local": "本地",
    "email": "邮箱",
    "userID (telemetry device_id)": "userID（遥测 device_id）",
    "ant-did (= Sentry user.id)": "ant-did（= Sentry user.id）",
    "desktop app": "桌面版",
    "desktop app local storage": "桌面版本地存储",
    "Cowork VM machineIdentifier": "Cowork 虚拟机 machineIdentifier",
    "VM": "虚拟机",
    "hardware UUID": "硬件 UUID",
    "system": "系统",
    "home directory path": "用户目录路径",
    "appears in session folder names and environment attachments": "出现在会话目录名和环境附件里",
    "~/.claude.json & backups": "~/.claude.json 及备份",
    "CLI transcripts": "CLI 会话记录",
    "CLI prompt history": "CLI 输入历史",
    "CLI failed telemetry": "CLI 遥测失败事件",
    "CLI other files": "CLI 其他文件",
    "Cowork session metadata": "Cowork 会话元数据",
    "desktop Code sessions": "桌面版 Code 会话",
    "desktop local storage": "桌面版本地存储",
    "desktop IndexedDB": "桌面版 IndexedDB",
    "desktop Sentry": "桌面版 Sentry",
    "desktop logs": "桌面版日志",
    "desktop other files": "桌面版其他文件",
    "other": "其他",
    "1. Account & device identifiers: value, persistence, where they appear on this Mac": "1. 账号与设备标识：取值、持久性、在本机的分布",
    "comes back as soon as you sign in again": "重新登录即恢复关联",
    "randomly generated, persisted; regenerated after deletion": "随机生成，持久保存，删除后重新生成",
    "system-level, cannot be changed": "系统级，不可更改",
    "depends on your user name / git config": "取决于你的用户名 / git 配置",
    "only in its source file": "仅在源文件中",
    "[%s] %s = %s\n            persistence: %s; found in %d files: %s": "[%s] %s = %s\n            持久性：%s；出现在 %d 个文件：%s",
    "\n            note: Claude itself does not read it (only a custom OTel exporter would), but macOS embeds it in Claude-related file names":
        "\n            说明：Claude 本身不读取它（仅自定义 OTel 导出时使用），但 macOS 会把它拼进 Claude 相关文件名",
    "\n            note: session folder names (-Users-<name>-<project>) and the working directory attached to every request expose your user name and project layout":
        "\n            说明：会话目录名（-Users-用户名-项目）以及每次请求附带的工作目录都会暴露用户名和项目结构",
    "2. Tracking identifiers in cookies (values are Chromium-encrypted; only names and expiry are read)":
        "2. Cookie 中的追踪标识（值已由 Chromium 加密，这里只读名称与过期时间）",
    "Desktop app embedded browser": "桌面版内嵌浏览器",
    "No cookie databases found": "未发现 Cookie 数据库",
    "%s %s (%s, until %s)": "%s %s（%s，至 %s）",
    "%s: %d cookies; %d identity / device IDs, %d third-party tracking & risk control, %d other":
        "%s：%d 个 Cookie，其中身份 / 设备标识 %d 个，第三方追踪与风控 %d 个，其他 %d 个",
    "Note: anthropic-device-id / ajs_anonymous_id exist in both the desktop app and Chrome; once both sign in to "
    "the same account they are linked. Risk-control cookies such as cf_clearance and __stripe_mid are bound to "
    "the browser environment fingerprint.":
        "说明：同一个 anthropic-device-id / ajs_anonymous_id 会同时出现在桌面版与 Chrome 中，"
        "两边都登录同一账号后即被关联；cf_clearance、__stripe_mid 等风控 Cookie 与浏览器环境指纹绑定。",
    "3. Device profile: hardware & environment actually sent in reports": "3. 设备画像：实际随上报发送的硬件与环境信息",
    "Desktop app Sentry error reports (user.id=%s) carry: %s": "桌面版 Sentry 错误上报（user.id=%s）携带：%s",
    "delete the sentry folder; error reporting can be turned off in settings afterwards": "删除 sentry 目录；之后可在设置中关闭错误上报",
    "    note: CPU model + memory + screen resolution + timezone together are highly distinctive":
        "    说明：CPU 型号 + 内存 + 屏幕分辨率 + 时区 的组合区分度很高",
    "Every Claude Code telemetry event carries: device_id=%s, account_uuid=%s, organization_uuid=%s; environment: %s":
        "Claude Code 每个遥测事件附带：device_id=%s，account_uuid=%s，organization_uuid=%s；环境：%s",
    "delete the telemetry leftovers; set DISABLE_TELEMETRY after reinstalling": "删除遥测残留；重新安装后设置 DISABLE_TELEMETRY",
    "    note: taken from events that failed to send and are queued locally; successfully sent events have the same content":
        "    说明：以上取自本机发送失败、暂存的事件，发送成功的事件内容相同",
    "Desktop app hardwareKey=%s (= app version|kernel version|arch; identical on same-config machines, low distinctiveness)":
        "桌面版硬件键 hardwareKey=%s（= 应用版本|内核版本|架构，同配置机器相同，区分度低）",
    "Cowork VM persistent identity: %s": "Cowork 虚拟机固定身份：%s",
    "delete vm_bundles; a new one is generated next time": "删除 vm_bundles，下次重新生成",
    "Claude files whose names contain the hardware UUID: %s": "文件名中含硬件 UUID 的 Claude 文件：%s",
    "4. Behavioral fingerprint: usage habits & local environment": "4. 行为指纹：使用习惯与本地环境",
    "first launch": "首次启动", "launches": "启动次数", "install method": "安装方式", "auto-update": "自动更新",
    "onboarding done": "完成引导", "last release notes seen": "最近看到的版本",
    "skill usage records": "技能使用记录", "plugin usage records": "插件使用记录", "tips shown": "提示展示记录",
    "projects": "项目", "GrowthBook experiment flags": "GrowthBook 实验开关",
    "%s: %d": "%s %d 项",
    "Usage profile in ~/.claude.json: ": "~/.claude.json 中的使用画像：",
    "%d Cowork sessions; mounted folders: %s; models: %s": "Cowork 会话 %d 个；挂载目录：%s；模型：%s",
    "%02d:00 x%d": "%02d 点×%d",
    "%d prompt history entries; active hours: %s (time-of-day patterns are a behavioral trait too)":
        "输入历史 %d 条，活跃时段：%s（时段规律也是一种行为特征）",
    "Session folder names expose %d project paths, e.g. %s": "会话目录名暴露了 %d 个项目路径，例如：%s",
    "5. Identifiers left by system integration": "5. 系统集成留下的标识",
    "preference plists": "偏好设置 plist",
    "recent documents record": "最近使用文档记录",
    "HTTPStorages etc.": "HTTPStorages 等",
    "browser native messaging hosts": "浏览器原生消息宿主",
    "crash reports": "崩溃报告",
    " ...": "……",
    "Keychain entries: %s (Claude Safe Storage is the key that encrypts the desktop app cookies)":
        "钥匙串条目：%s（其中 Claude Safe Storage 是桌面版 Cookie 的加密密钥）",
    "Shell history: ": "Shell 历史：",
    "6. Reporting switches": "6. 上报开关",
    "(checked %d files in %.0f s)": "（共检查 %d 个文件，用时 %.0f 秒）",
    '\nClean everything now (back up first, then confirm)?': '\n现在全部清理吗（先备份，再确认）？',
    "HIGH": "高危", "MED": "中危", "LOW": "低危",
    '  - Advice: %s': '  - 建议：%s',
    '%s is %s. Include it in the backup?': '%s 有 %s，要包含进备份吗？',
    'Back up before cleaning?': '清理前先备份吗？',
    'Cleaning finished.': '清理完成。',
    'No Claude traces found on this Mac; nothing to back up.': '这台 Mac 上没有发现 Claude 痕迹，无需备份。',
    'No Claude traces found on this Mac; nothing to clean.': '这台 Mac 上没有发现 Claude 痕迹，无需清理。',
    'back up every Claude trace': '备份所有 Claude 痕迹',
    'fingerprint check (read-only)': '指纹体检（只读）',
    'list every location that would be cleaned, with sizes': '列出所有会被清理的位置及大小',
    'remove every Claude trace': '清除所有 Claude 痕迹',
    " and %d more places": "，另有 %d 处",
    "Claude Fingerprint Detect": "Claude 指纹检测",
    "Fingerprint exposure score": "指纹暴露得分",
    "higher is cleaner": "越高越干净",
    "third-party tracking & risk control: %s": "第三方追踪与风控：%s",
    "Next steps": "下一步",
    "  Items: %d    Size: %s    Mode: %s": "  项目：%d    大小：%s    方式：%s",
    "+ Extras": "+ 附加项",
    "+ Extras, deep": "+ 附加项（深度）",
    "+ credentials, secret leaks, external traces, system protection · ~2 min": "+ 凭据、密钥泄露、外部痕迹、系统防护 · 约 2 分钟",
    "+ secret scan of the Cowork data disk · ~10 min": "+ 扫描 Cowork 数据盘中的密钥 · 约 10 分钟",
    "About to remove everything above, including the Claude apps": "即将删除以上全部内容，包括 Claude 应用",
    "Back": "返回",
    "Backup": "备份",
    "Cancelled. Nothing was deleted.": "已取消，没有删除任何东西。",
    "Check · Back up · Clean    data in %s": "体检 · 备份 · 清理    数据保存在 %s",
    "Clean": "清理",
    "Cleaning": "正在清理",
    "Deletion mode": "删除方式",
    "IDs, cookies, device profile, behavior, reporting switches · seconds": "标识、Cookie、设备画像、行为、上报开关 · 几秒钟",
    "Keychain matching lines": "钥匙串匹配行数",
    "Language": "语言",
    "Local git branches whose name contains \"claude\"": "名称含 \"claude\" 的本地 git 分支",
    "Manual checklist": "手动事项清单",
    "Project scan roots": "项目扫描目录",
    "Quit": "退出",
    "Running Claude-related processes": "运行中的 Claude 相关进程",
    "Settings": "设置",
    "Standard": "标准",
    "Things this tool cannot do locally": "工具在本地做不到、需要你手动处理的事项",
    "Time Machine local snapshots (handle manually)": "Time Machine 本地快照（需手动处理）",
    "Type %s to continue, anything else cancels: ": "输入 %s 继续，输入其他内容取消：",
    "Verify": "验证",
    "archive every Claude trace": "打包所有 Claude 痕迹",
    "back up, remove every Claude trace, verify": "先备份，清除所有 Claude 痕迹，再验证",
    "browser extension, phone, Time Machine, keys": "浏览器扩展、手机、Time Machine、密钥",
    "deletion mode, project roots, language": "删除方式、项目目录、语言",
    "read-only, takes seconds": "只读，几秒钟",
    "1 path": "1 个路径",
    "Backing up": "正在备份",
    "Backup plan": "备份计划",
    "Destination: %s": "保存到：%s",
    "Free disk space": "磁盘可用空间",
    "Keychain": "钥匙串",
    "Total before compression": "压缩前合计",
    "entry metadata only": "仅条目元数据",
    "\nexamples:\n  %(prog)s check     fingerprint check (read-only)\n  %(prog)s backup    back up every Claude trace to backups/\n  %(prog)s clean     remove every Claude trace (lists everything and asks first)\n\nRun without arguments for the interactive menu.\n": "\n示例：\n  %(prog)s check     指纹体检（只读）\n  %(prog)s backup    把所有 Claude 痕迹备份到 backups/\n  %(prog)s clean     清除所有 Claude 痕迹（先列出全部内容并确认）\n\n不带参数运行进入交互菜单。\n",
    "Everything else in the Claude folders": "Claude 目录里的其余文件",
}
