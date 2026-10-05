# claude-fingerprint-detect

[English](README.md)

查看 Claude（桌面版、Claude Code、Cowork）在你的 Mac 上留下了哪些能识别**你本人、你的设备和你的账号**的东西，并在你需要时安全地清理掉。

- **体检**：找出账号与设备 ID、追踪 Cookie、会被上报的硬件 / 环境画像、使用习惯，以及遥测是否已关闭。给出打分和报告。
- **备份**：动手之前先全部打包（可选加密成磁盘映像）。
- **清理**：一次清除所有 Claude 痕迹，执行前列出完整清单并请你确认。

> **非官方工具。** 与 Anthropic 无关，未获其认可或支持。“Claude” 是 Anthropic 的商标。

## 快速开始

安装 `claude-fingerprint-detect` 命令（装到 `~/.claude-fingerprint-detect`，不碰其他任何东西）：

```bash
curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash
```

然后打开一个新的终端窗口：

```bash
claude-fingerprint-detect check    # 1. 指纹体检（只读）
claude-fingerprint-detect backup   # 2. 备份
claude-fingerprint-detect clean    # 3. 清理（先列出要删除的内容，确认后才执行）
```

`clean` 会清除 Claude 留下的**全部**内容，包括应用本身；之后如果还要用 Claude，重新安装即可。想用鼠标操作？见[开始使用](#开始使用)。用 AI agent？直接对它说：

> 按照 https://github.com/nsstream/claude-fingerprint-detect 的 AGENTS.md 安装，并运行一次指纹体检。

## 安全吗？

- **体检只读。** 不会修改或删除任何东西。
- **不联网。** 工具不发出任何网络请求，不上传任何数据。
- **不经确认不删除。** 每次清理都先列出要删除的内容，确认后才执行；默认移到废纸篓。
- **开源、无依赖。** 只用 macOS 自带的 Python，运行前可以逐行查看。

## 环境要求

- macOS（Apple 芯片或 Intel 均可）
- 无需安装任何东西。第一次运行时，macOS 可能提示安装“命令行开发者工具”（Python 来自这里），点**安装**，装好后再运行一次即可。

## 开始使用

1. 在本页点击 **Code → Download ZIP**，下载后双击 ZIP 解压。
2. 打开文件夹，双击 **`start.command`**。
   - 如果提示无法打开：右键 `start.command` → **打开** → **打开**。
   - 较新的 macOS 可能需要到 **系统设置 → 隐私与安全性 → 仍要打开**。
3. 会弹出一个终端窗口和菜单，输入数字后按回车。

界面语言跟随 Mac 的系统语言（简体中文或英文），也可以在**设置**里切换。

## 推荐步骤

1. **指纹体检**（菜单 1），需要几分钟。每条发现都会说明为什么重要。
2. **清理**（菜单 3）：先备份，列出将删除的全部内容，输入 `DELETE` 确认后清理，最后自动验证。
3. 按**手动事项清单**（菜单 4）处理工具在本地做不到的部分（浏览器扩展、手机 App、Time Machine、轮换泄露的密钥）。

**清理前须知**

- 清理会移除 Claude 应用并退出登录；还要继续用的话，重新安装并登录即可。
- 如果 Claude 正在运行，工具会请你退出它（否则它会把文件写回去）。
- 清理 Shell 历史后，请关闭所有终端窗口再重新打开。
- 项目里的 `CLAUDE.md`、`.claude/` 等文件总是逐个确认。

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
| 你的项目 | 常见项目目录中的 `.claude/`、`CLAUDE.md`、`.mcp.json` |

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

## 你的数据只在这个文件夹里

报告、备份和日志写在工具旁边的 `reports/`、`backups/`、`logs/` 中，里面有工具找到的同样那些标识，因此：

- 用完请删除，或只保留加密备份（`.dmg`）；
- 不要把这个文件夹放进 iCloud 云盘 / Dropbox（体检会提醒）；
- 如果你 fork 了仓库，这些目录已在 `.gitignore` 中，千万不要强制添加。

## 从备份恢复

每个备份目录里都有 `HOW_TO_RESTORE.txt`。简单来说：先退出 Claude，然后在终端对需要的包执行 `tar -xzf <包名>.tar.gz -C /`。钥匙串密码不会被导出，恢复后需要重新登录。

## 命令行

用上面“快速开始”的命令安装（再运行一次即可更新；卸载：`curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash -s -- --uninstall`）。

```bash
claude-fingerprint-detect check                  # 指纹体检
claude-fingerprint-detect check --extra --save   # 加凭据、密钥泄露、系统防护，并保存报告
claude-fingerprint-detect backup                 # 全部备份
claude-fingerprint-detect clean                  # 全部清理
claude-fingerprint-detect scan -v                # 查看会被清理的所有位置
claude-fingerprint-detect verify                 # 检查残留
claude-fingerprint-detect --lang en check        # 指定语言（en | zh | auto）
claude-fingerprint-detect --help
```

`clean --yes` 跳过确认，但不会删除启动项和项目中的文件。设置环境变量 `CFD_LANG=zh` 或 `CFD_LANG=en` 可固定语言。自动化脚本和 AI agent 请看 [AGENTS.md](AGENTS.md)。

## 局限

- Claude 存储和上报哪些内容，是在当前版本上观察到的，可能随更新变化。体检报告的是你 Mac 上实际找到的东西，其中的解释仅供参考。
- 清理本机不会删除 Anthropic 服务器上的任何数据，这需要在 claude.ai 的账号与隐私设置中处理。
- 已经出现在对话里的密钥已经被发送过，删除本地副本不够，必须轮换。
- 仅支持 macOS。

## 许可证

[MIT](LICENSE)。风险自负——这正是有备份步骤的原因。
