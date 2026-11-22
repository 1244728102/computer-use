"""
Pure-Python MCP stdio server for Windows Computer Use.
Exposes the full toolset of dsh-computer-use to Antigravity.
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from computer import ACTIONS, ComputerEngine, Shot

BATCH_ACTIONS = [a for a in ACTIONS if a != "screenshot"]

ACTION_PROPS: dict[str, Any] = {
    "action": {"type": "string", "enum": ACTIONS, "description": "What to do."},
    "coordinate": {"type": "array", "items": {"type": "number"}, "description": "[x, y] in pixels of the latest screenshot."},
    "start_coordinate": {"type": "array", "items": {"type": "number"}, "description": "Drag start [x, y] (left_click_drag)."},
    "text": {"type": "string", "description": 'type: text to enter. key/hold_key: xdotool-style keys like "ctrl+s", "Return", "alt+Tab".'},
    "modifiers": {"type": "string", "description": 'Modifier keys held during click/scroll, e.g. "shift" or "ctrl+shift".'},
    "scroll_direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
    "scroll_amount": {"type": "integer", "description": "Wheel notches (default 3)."},
    "duration": {"type": "number", "description": "Seconds for wait / hold_key (with until: timeout, default 10)."},
    "target": {"type": "string", "description": 'Control name or AutomationId instead of coordinate, e.g. "保存", "按钮:保存", "id:NavTasksButton", "#NavTasksButton".'},
    "until": {"type": "string", "description": 'wait: observe "window:<title/exe>", "target:<control>", or "text:<window text>".'},
    "gone": {"type": "boolean", "description": "wait until: wait for it to disappear instead."},
    "region": {"type": "array", "items": {"type": "number"}, "description": "zoom: [x1, y1, x2, y2] in screenshot pixels."},
}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "computer",
        "description": "Control the Windows desktop with mouse, keyboard, screenshot, zoom, and wait. Coordinates are pixels of the latest screenshot (DPI and multi-display handled automatically). Mutating actions return a fresh settled screenshot.",
        "inputSchema": {
            "type": "object",
            "properties": ACTION_PROPS,
            "required": ["action"],
        },
    },
    {
        "name": "computer_batch",
        "description": "Run several computer actions in order, stopping on error. Returns one settled screenshot (or window text) at the end.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {**ACTION_PROPS, "action": {"type": "string", "enum": BATCH_ACTIONS}},
                        "required": ["action"],
                    },
                },
                "finish": {"type": "string", "enum": ["screenshot", "text", "none"], "description": "What to return after the last action (default screenshot)."},
            },
            "required": ["actions"],
        },
    },
    {
        "name": "ui_elements",
        "description": "Read UI Automation controls (with coordinates and AutomationId) or exact window text (when text=true) of the foreground or specified window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hwnd": {"type": "integer", "description": "Optional window handle from windows list."},
                "text": {"type": "boolean", "description": "If true, read window text instead of listing controls."},
                "tail": {"type": "integer", "description": "Max trailing characters when text=true (default 4000)."},
                "max": {"type": "integer", "description": "Max controls to return (default 120, up to 400)."},
            },
        },
    },
    {
        "name": "open_application",
        "description": "Launch an application by name/exe/URL, focus an existing window, or restore it from the system tray. Returns a screenshot and any saved app skill notes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "application": {"type": "string", "description": 'App name, exe, or HTTP(S) URL (e.g. "计算器", "notepad", "https://example.com").'},
                "new_instance": {"type": "boolean", "description": "Set true to open a new instance instead of focusing an existing window."},
            },
            "required": ["application"],
        },
    },
    {
        "name": "windows",
        "description": "List, focus, minimize, maximize, restore, close windows, or tidy up (restore minimized/tray state and hide overlay).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "focus", "minimize", "maximize", "restore", "close", "tidy"]},
                "hwnd": {"type": "integer", "description": "Window handle from windows list."},
                "title": {"type": "string", "description": "Window title substring or app name."},
            },
            "required": ["action"],
        },
    },
    {
        "name": "clipboard",
        "description": "Read or write Windows clipboard text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["read", "write"]},
                "text": {"type": "string", "description": "Text to write when action is write."},
            },
            "required": ["action"],
        },
    },
    {
        "name": "switch_display",
        "description": "Switch the active monitor for screenshots and coordinate mapping, or list available displays.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "description": "0-based display index to switch to. Omit to list displays."},
            },
        },
    },
    {
        "name": "request_access",
        "description": "Request permission to control specific desktop applications in this session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "applications": {"type": "array", "items": {"type": "string"}, "description": "Application names to authorize."},
            },
            "required": ["applications"],
        },
    },
    {
        "name": "list_granted_applications",
        "description": "List applications currently authorized for computer control in this session.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "app_skill",
        "description": "List, read, append, or write per-application operation notes (max 4000 chars).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "read", "append", "write"]},
                "app": {"type": "string", "description": "Application name."},
                "content": {"type": "string", "description": "Markdown notes for append/write."},
                "summary": {"type": "string", "description": "Short summary for write."},
                "match": {"type": "array", "items": {"type": "string"}, "description": "Process/app names to match."},
            },
            "required": ["action"],
        },
    },
]


def format_result(res: dict[str, Any]) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": str(res.get("text") or "")}]
    img = res.get("image")
    if isinstance(img, Shot):
        content.append({"type": "image", "data": img.data_b64, "mimeType": "image/jpeg"})
    return {"content": content, "isError": False}


def dispatch_tool(engine: ComputerEngine, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "computer":
        return format_result(engine.tool_computer(args))
    if name == "computer_batch":
        return format_result(engine.tool_computer_batch(args))
    if name == "ui_elements":
        return format_result(engine.tool_ui_elements(args))
    if name == "open_application":
        return format_result(engine.tool_open_application(args))
    if name == "windows":
        return format_result(engine.tool_windows(args))
    if name == "clipboard":
        return format_result(engine.tool_clipboard(args))
    if name == "switch_display":
        if args.get("index") is None:
            displays = engine.refresh_displays()
            lines = [
                f"- [{i}] {d['width']}x{d['height']} at ({d['x']}, {d['y']}) dpi={d['dpi']}"
                + (" [primary]" if d.get("primary") else "")
                + (" [active]" if i == engine.display_index else "")
                for i, d in enumerate(displays)
            ]
            return format_result({"text": "\n".join(lines)})
        d = engine.switch_display(int(args["index"]))
        shot = engine.screenshot()
        return format_result({"text": f"Switched to display {args['index']} ({d['width']}x{d['height']}).", "image": shot})
    if name == "request_access":
        return format_result(engine.tool_request_access(args))
    if name == "list_granted_applications":
        return format_result(engine.tool_list_granted())
    if name == "app_skill":
        return format_result(engine.tool_app_skill(args))
    raise ValueError(f"Unknown tool: {name}")


def send(msg: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    engine = ComputerEngine()
    try:
        for raw in sys.stdin:
            line = raw.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                continue

            req_id = req.get("id")
            method = req.get("method", "")
            params = req.get("params") or {}

            if req_id is None:
                continue

            try:
                if method == "initialize":
                    proto = params.get("protocolVersion") or "2024-11-05"
                    send({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": proto,
                            "capabilities": {"tools": {"listChanged": False}},
                            "serverInfo": {"name": "computer-use", "version": "1.0.0"},
                        },
                    })
                elif method == "ping":
                    send({"jsonrpc": "2.0", "id": req_id, "result": {}})
                elif method == "tools/list":
                    send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})
                elif method == "tools/call":
                    tool_name = params.get("name", "")
                    tool_args = params.get("arguments") or {}
                    try:
                        result = dispatch_tool(engine, tool_name, tool_args)
                    except Exception as exc:
                        result = {
                            "content": [{"type": "text", "text": f"Error: {exc}"}],
                            "isError": True,
                        }
                    send({"jsonrpc": "2.0", "id": req_id, "result": result})
                else:
                    send({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                    })
            except Exception as exc:
                traceback.print_exc(file=sys.stderr)
                send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": str(exc)},
                })
    finally:
        engine.hide_overlay()
        engine.helper.dispose()


if __name__ == "__main__":
    main()
