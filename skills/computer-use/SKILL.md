---
name: computer-use
description: Operate the Windows desktop with screenshot, mouse, keyboard, UI Automation control targeting, window management, clipboard, and per-app skills. Use when the user asks to control desktop applications, click UI controls, type into apps, or inspect screen/window state.
---

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
