# Claude 指纹检测

[English](README.en.md)

查看 Claude（桌面版、Claude Code、Cowork）在你的 Mac 上留下了哪些能识别**你本人、你的设备和你的账号**的东西，并在你需要时安全地清理掉。

- **体检**：找出账号与设备 ID、追踪 Cookie、会被上报的硬件 / 环境画像、使用习惯，以及遥测是否已关闭。给出打分和报告。
- **备份**：动手之前先把会话、配置、凭据等打包（可选加密成磁盘映像）；应用、缓存、日志这类可重新下载或自动生成的内容不备份。
- **清理**：一次清除所有 Claude 痕迹，执行前列出完整清单并请你确认。

> **非官方工具。** 与 Anthropic 无关，未获其认可或支持。“Claude” 是 Anthropic 的商标。

## 快速开始

在终端里安装 `cfd` 命令（装到 `~/.claude-fingerprint-detect`，不碰其他任何东西）：

```bash
curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash
```

然后打开一个新的终端窗口：

```bash
cfd check    # 1. 指纹体检（只读）
cfd backup   # 2. 备份
cfd clean    # 3. 清理（先列出要删除的内容，确认后才执行）
```

清理后运行 `cfd manual`，查看需要手动处理的事项（浏览器扩展、手机 App、轮换泄露的密钥）。不带参数运行 `cfd` 会进入交互菜单。界面语言跟随 Mac 的系统语言（简体中文或英文）。

用 AI agent？直接对它说：

> 按照 https://github.com/nsstream/claude-fingerprint-detect 的 AGENTS.md 安装，并运行一次指纹体检。

## 安全吗？

- **体检只读。** 不会修改或删除任何东西。
- **不联网。** 除了安装和更新时下载代码，工具不发出任何网络请求，不上传任何数据。
- **不经确认不删除。** 每次清理都先列出要删除的内容，输入 `DELETE` 才执行；默认移到废纸篓。
- **开源、无依赖。** 只用 macOS 自带的 Python，运行前可以逐行查看。

## 环境要求

- macOS（Apple 芯片或 Intel 均可）
- 无需安装其他东西。如果提示缺少 Python，先运行 `xcode-select --install` 安装“命令行开发者工具”，再重新运行安装命令。

## 清理前须知

- `clean` 会清除 Claude 留下的**全部**内容，包括应用本身，并退出登录；还要继续用的话，重新安装并登录即可。
- 如果 Claude 正在运行，工具会请你退出它（否则它会把文件写回去）。
- 清理 Shell 历史后，请关闭所有终端窗口再重新打开。
- 项目里的 `CLAUDE.md`、`.claude/`、`.mcp.json` 只检测、不删除，也不备份。

## 检查哪些内容

| 类别 | 示例 |
| --- | --- |
| 身份与凭据 | `~/.claude.json` 及其备份里的账号 / 设备 ID、OAuth 令牌、钥匙串条目 |
| 会话与内容 | 输入历史、会话记录、粘贴缓存、Cowork 会话 |
| 遥测与日志 | 待发送的遥测、Sentry 数据、日志、崩溃报告 |
| Cowork 虚拟机 | 虚拟机镜像与数据盘（固定的虚拟机 UUID / MAC 地址） |
| 桌面版浏览器数据 | Cookie、本地存储、缓存 |
| 配置、MCP、插件 | MCP 配置（可能含第三方令牌）、设置、技能 |
| 应用程序文件 | 应用本身和残留目录 |
| macOS 系统集成 | 偏好设置、最近文档、浏览器扩展桥接、启动项 |
| Shell 历史 | 提到 claude / anthropic 的命令 |
| 其他浏览器 | Chrome、Edge、Brave、Arc、Vivaldi、Chromium 中 claude.ai / anthropic.com 的 Cookie 与历史 |
| 第三方工具 | Cursor、JetBrains、Bun 中的 Claude 插件 |
| 你的项目 | 常见项目目录中的 `.claude/`、`CLAUDE.md`、`.mcp.json`（只列出，不删除） |

## 之后如何减少暴露

如果还要继续使用 Claude Code，把下面内容加入 `~/.claude/settings.json`（与已有内容合并），关闭可选的上报，并禁止 Claude 读取敏感文件：

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

如果清理过 `~/.claude`，需要重新加一次。桌面版也请在其设置中检查崩溃 / 使用数据上报选项。

## 你的数据只在工具目录里

报告、备份和日志写在 `~/.claude-fingerprint-detect/` 下的 `reports/`、`backups/`、`logs/` 中，里面有工具找到的同样那些标识，因此：

- 用完请删除，或只保留加密备份（`.dmg`）；
- 不要把这个目录放进 iCloud 云盘 / Dropbox（体检会提醒）；
- 如果你 fork 了仓库，这些目录已在 `.gitignore` 中，千万不要强制添加。

## 从备份恢复

每个备份目录里都有 `HOW_TO_RESTORE.txt`。简单来说：先退出 Claude，然后在终端对需要的包执行 `tar -xzf <包名>.tar.gz -C /`。钥匙串密码不会被导出，恢复后需要重新登录。想换一个干净的身份，就只恢复会话、配置等需要的包，不要恢复身份与凭据包。

## 全部命令

```bash
cfd check                  # 指纹体检
cfd check --extra --save   # 加凭据、密钥泄露、系统防护，并保存报告
cfd backup                 # 全部备份
cfd clean                  # 全部清理
cfd scan -v                # 查看会被清理的所有位置
cfd verify                 # 检查残留
cfd manual                 # 手动事项清单
cfd --help
```

`clean --yes` 跳过确认，但不会删除启动项和项目中的文件。自动化脚本和 AI agent 请看 [AGENTS.md](AGENTS.md)。

**更新**：再运行一次安装命令。**卸载**：

```bash
curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash -s -- --uninstall
```

（如果目录里还有备份或报告，会保留目录并告诉你如何手动删除。）

## 局限

- Claude 存储和上报哪些内容，是在当前版本上观察到的，可能随更新变化。体检报告的是你 Mac 上实际找到的东西，其中的解释仅供参考。
- 清理本机不会删除 Anthropic 服务器上的任何数据，这需要在 claude.ai 的账号与隐私设置中处理。
- 已经出现在对话里的密钥已经被发送过，删除本地副本不够，必须轮换。
- 仅支持 macOS。

## 许可证

[MIT](LICENSE)。风险自负——这正是有备份步骤的原因。
