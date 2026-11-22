<h1 align="center">Windows Computer Use · 原生 Windows 桌面 UIA 语义操控引擎</h1>

<p align="center"><b>Native Windows desktop automation & UI Automation (UIA) control plugin for Google Antigravity (AGY): semantic control targeting, multi-action batching, window management & safety guardrails.</b></p>

<p align="center">🥇 <b>融合 Windows UI Automation 语义控件定位、多步动作批处理、多显示器切换与安全护栏的桌面原生自动化插件。</b> 🥇</p>

<p align="center">
  <a href="./README.zh-CN.md">简体中文</a> ·
  <a href="./INSTALL.md">Install Guide</a> ·
  <a href="./CHANGELOG.md">Changelog</a> ·
  <a href="./LICENSE">License</a>
</p>

<p align="center">
  <a href="https://github.com/1244728102"><img src="https://img.shields.io/badge/author-1244728102%20(%E7%88%B1%E5%93%AD%E7%9A%84%E4%BC%8A%E8%95%BE%E5%A8%9C)-b69cf5?style=flat-square&logo=github" alt="Author"></a>
  <img src="https://img.shields.io/badge/version-1.0.0-e9c27a?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/platform-Google%20Antigravity%20(AGY)-6a56b8?style=flat-square" alt="Platform">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
</p>

---

## ✨ Overview & Highlights

**Windows Computer Use · 原生 Windows 桌面 UIA 语义操控引擎 (`computer-use`)** — Windows 桌面电脑控制插件：截图、鼠标、键盘、UI Automation 控件定位、窗口与剪贴板管理，支持按应用授权、橙色光晕提示与 Esc 暂停。

# Computer Use (Windows Desktop)

You can see and operate the user's Windows computer with the `computer-use` MCP tools:
`computer`, `computer_batch`, `ui_elements`, `open_application`, `windows`, `clipboard`, `switch_display`, `request_access`, `list_granted_applications`, and `app_skill`.

## Core Workflow

1. **Per-app authorization (`request_access`)**:
   - In `per-app` mode (default), call `request_access` once with every app the task needs before acting on those apps.
   - Input to apps that are not granted is refused. Password managers (`1password`, `bitwarden`, `keepass`, etc.) are always blocked.
2. **Starting a task**:
   - If the task begins with an app, open it right away with `open_application` (after `request_access`): it returns a screenshot and any saved app skill notes, so do not take a screenshot first.
   - Otherwise start with `computer(action="screenshot")`.
   - All coordinates are pixels of the latest screenshot; the server handles DPI scaling and multi-monitor offsets automatically.
3. **Opening & tidying windows (`open_application`, `windows`)**:
   - Open or switch apps with `open_application` (by name, exe, or URL; also restores apps from the system tray).
   - Use `windows` (`list`, `focus`, `minimize`, `maximize`, `restore`, `close`, `tidy`) to inspect or arrange windows.
   - When the task is done, call `windows(action="tidy")` to restore windows that were minimized or in the tray before you started. Never close windows the user already had open.
4. **Targeting controls by name or AutomationId**:
   - Prefer `target` over raw coordinates whenever possible:
     - `target: "保存"` or `target: "按钮:保存"` (supports `按钮:`, `输入框:`, `菜单:`, `菜单项:`, `标签:`, `复选框:`, `单选:`, `下拉框:`, `列表项:`, `链接:`, `文本:` as well as English equivalents `button:`, `edit:`, `menu:`, etc.).
     - `target: "id:NavTasksButton"` or `target: "#NavTasksButton"` matches UIA `AutomationId`.
   - Use `ui_elements` (or `ui_elements(text=True)`) to inspect controls and read exact window text instead of zooming screenshots.
5. **Batching & conditional waiting (`computer_batch`)**:
   - Put predictable multi-step sequences into one `computer_batch` call (e.g. `type` -> `type` -> `left_click` -> `wait(until="target:报名成功")`).
   - `wait` supports `until`: `"window:<title/exe>"`, `"target:<control>"`, or `"text:<window text>"`, plus `gone: true` to wait for disappearance.
   - `computer_batch` supports `finish`: `"screenshot"` (default), `"text"`, or `"none"`.
6. **Typing & Saving**:
   - Use `type` (optionally with `target` or `coordinate` to focus the field first) to enter text directly into apps. Long multi-line text is streamed block by block cleanly.
   - In Save As dialogs, press `alt+n`, `ctrl+a`, type the full path, then `Return` (in Office apps, `F12` opens Save As directly).
7. **App skills (`app_skill`)**:
   - Check and reuse app notes returned by `open_application` or `app_skill(action="read")`, and record newly discovered app quirks with `app_skill(action="append" | "write")` (limit 4000 chars).
8. **User safety & Esc pause**:
   - Never enter passwords, payment details, or bypass security verifications — stop and ask the user.
   - The user sees an orange glow border and can press **Esc** at any time to pause/resume. If an action reports it was skipped due to pause or user input, re-check the screen before acting.


---

## 🚀 Quick Install

**Windows PowerShell**:
```powershell
git clone https://github.com/1244728102/computer-use.git "$env:USERPROFILE\.gemini\config\plugins\computer-use"
```

**macOS / Linux**:
```bash
git clone https://github.com/1244728102/computer-use.git "$HOME/.gemini/config/plugins/computer-use"
```

**Or hand the install to your AI agent**:
> Install and configure `computer-use` following https://github.com/1244728102/computer-use/blob/main/INSTALL.md

---

## 📂 Project Files (`27` files)

```text
computer-use/
├── .gitignore
├── assets/icon.svg
├── CHANGELOG.md
├── helper/CuHelper.cs
├── helper/deepseek-black.png
├── helper/deepseek-white.png
├── helper/host.ps1
├── helper/skills/chrome.md
├── helper/skills/excel.md
├── helper/skills/explorer.md
├── helper/skills/notepad.md
├── helper/skills/obsidian.md
├── helper/skills/powerpoint.md
├── helper/skills/qq.md
├── helper/skills/typora.md
├── helper/skills/weixin.md
├── helper/skills/word.md
├── INSTALL.md
├── LICENSE
├── mcp_config.json
├── plugin.json
├── rules/AGENTS.md
├── server/computer.py
├── server/helper_client.py
├── server/server.py
├── settings.json
├── skills/computer-use/SKILL.md
```

---

## 📜 License

MIT © [1244728102 (爱哭的伊蕾娜)](https://github.com/1244728102)
