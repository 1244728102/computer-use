"""
Builds and drives the Windows helper (helper/CuHelper.cs): compiled once
with the in-box .NET Framework csc.exe into a per-source-hash cache folder,
then kept running and spoken to as JSON lines over stdio.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

REFERENCES = [
    "System.dll",
    "System.Core.dll",
    "Microsoft.CSharp.dll",
    "System.Drawing.dll",
    "System.Windows.Forms.dll",
    "System.Web.Extensions.dll",
    "UIAutomationClient.dll",
    "UIAutomationTypes.dll",
    "WindowsBase.dll",
]

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def helper_asset_path(name: str) -> Path:
    return PLUGIN_ROOT / "helper" / name


def framework_dir() -> Path:
    windir = Path(os.environ.get("SystemRoot") or os.environ.get("windir") or r"C:\Windows")
    for arch in ("Framework64", "Framework"):
        d = windir / "Microsoft.NET" / arch / "v4.0.30319"
        if (d / "csc.exe").exists():
            return d
    raise RuntimeError(
        'The .NET Framework 4 C# compiler (csc.exe) was not found. Enable ".NET Framework 4.8" in Windows Features.'
    )


def cache_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP") or "."
    return Path(base) / "agy-computer-use"


def ensure_helper_exe(source: Path | None = None) -> Path:
    src = source or helper_asset_path("CuHelper.cs")
    code = src.read_bytes()
    digest = hashlib.sha256(code).hexdigest()[:12]
    out_dir = cache_root() / f"helper-{digest}"
    exe = out_dir / "cu-helper.exe"
    if exe.exists():
        return exe
    out_dir.mkdir(parents=True, exist_ok=True)
    fw = framework_dir()
    temp = out_dir / f"build-{os.getpid()}-{int(time.time() * 1000)}.exe"
    args = [
        str(fw / "csc.exe"),
        "-nologo",
        "-optimize+",
        "-target:exe",
        f"-out:{temp}",
        f"-lib:{fw / 'WPF'}",
        *[f"-r:{ref}" for ref in REFERENCES],
        str(src),
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=120,
        creationflags=creationflags,
    )
    if proc.returncode != 0:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        msg = (proc.stdout or proc.stderr or "").strip() or f"exit code {proc.returncode}"
        raise RuntimeError(f"Compiling the computer-use helper failed: {msg}")
    try:
        temp.replace(exe)
    except OSError:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        if not exe.exists():
            raise
    return exe


class HelperClient:
    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        self._log = log or (lambda msg: print(msg, file=sys.stderr, flush=True))
        self._lock = threading.Lock()
        self._start_lock = threading.Lock()
        self._proc: subprocess.Popen[str] | None = None
        self._hosted = False
        self._next_id = 0
        self._disposed = False
        self._pending: dict[int, tuple[threading.Event, dict[str, Any]]] = {}
        self._ready_event = threading.Event()
        self._listeners: list[Callable[[dict[str, Any]], None]] = []

    def on_event(self, listener: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(listener)

        def remove() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return remove

    def _powershell_path(self) -> str:
        windir = Path(os.environ.get("SystemRoot") or os.environ.get("windir") or r"C:\Windows")
        return str(windir / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")

    def _ensure_started(self) -> subprocess.Popen[str]:
        with self._start_lock:
            if self._disposed:
                raise RuntimeError("computer-use helper is shut down")
            if self._proc is not None and self._proc.poll() is None:
                return self._proc
            exe = ensure_helper_exe()
            if not self._hosted:
                try:
                    return self._launch([str(exe)])
                except OSError as exc:
                    self._log(f"starting cu-helper.exe failed ({exc}); falling back to powershell.exe")
                    self._hosted = True
            return self._launch(
                [
                    self._powershell_path(),
                    "-NoProfile",
                    "-NonInteractive",
                    "-STA",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(helper_asset_path("host.ps1")),
                    str(exe),
                ]
            )

    def _launch(self, cmd: list[str]) -> subprocess.Popen[str]:
        self._ready_event.clear()
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
        )
        self._proc = proc
        threading.Thread(target=self._read_stdout, args=(proc,), daemon=True).start()
        threading.Thread(target=self._read_stderr, args=(proc,), daemon=True).start()
        if not self._ready_event.wait(timeout=15.0):
            self._kill_proc(proc)
            raise RuntimeError("computer-use helper did not become ready in time")
        if proc.poll() is not None:
            raise RuntimeError(f"computer-use helper exited during startup (code {proc.returncode})")
        return proc

    def _read_stderr(self, proc: subprocess.Popen[str]) -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            text = line.strip()
            if text:
                self._log(f"helper stderr: {text}")

    def _read_stdout(self, proc: subprocess.Popen[str]) -> None:
        assert proc.stdout is not None
        try:
            for raw in proc.stdout:
                line = raw.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    self._log(f"helper non-JSON: {line[:200]}")
                    continue
                if isinstance(msg.get("event"), str):
                    if msg["event"] == "ready":
                        self._ready_event.set()
                    else:
                        with self._lock:
                            listeners = list(self._listeners)
                        for fn in listeners:
                            try:
                                fn(msg)
                            except Exception:
                                pass
                    continue
                req_id = msg.get("id")
                if isinstance(req_id, int):
                    with self._lock:
                        entry = self._pending.pop(req_id, None)
                    if entry is not None:
                        ev, box = entry
                        box["msg"] = msg
                        ev.set()
        finally:
            self._ready_event.set()
            with self._lock:
                if self._proc is proc:
                    self._proc = None
                pending_items = list(self._pending.items())
                self._pending.clear()
            for _, (ev, box) in pending_items:
                box["error"] = f"computer-use helper exited (code {proc.poll()})"
                ev.set()

    def _kill_proc(self, proc: subprocess.Popen[str] | None) -> None:
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except OSError:
            pass
        if proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass

    def call(self, cmd: str, args: dict[str, Any] | None = None, timeout_ms: int = 20000) -> Any:
        if self._disposed:
            raise RuntimeError("computer-use helper is shut down")
        proc = self._ensure_started()
        ev = threading.Event()
        box: dict[str, Any] = {}
        with self._lock:
            self._next_id += 1
            req_id = self._next_id
            self._pending[req_id] = (ev, box)
        payload = json.dumps({**(args or {}), "id": req_id, "cmd": cmd}, ensure_ascii=False) + "\n"
        try:
            assert proc.stdin is not None
            proc.stdin.write(payload)
            proc.stdin.flush()
        except OSError as exc:
            with self._lock:
                self._pending.pop(req_id, None)
            raise RuntimeError(f'failed writing "{cmd}" to helper: {exc}') from exc

        if not ev.wait(timeout=timeout_ms / 1000.0):
            with self._lock:
                self._pending.pop(req_id, None)
            self._kill_proc(proc)
            raise TimeoutError(f'computer-use helper timed out on "{cmd}"')

        if "error" in box:
            raise RuntimeError(box["error"])
        msg = box["msg"]
        if msg.get("ok"):
            return msg.get("result")
        raise RuntimeError(msg.get("error") or f'helper error on "{cmd}"')

    def dispose(self) -> None:
        self._disposed = True
        self._kill_proc(self._proc)
        self._proc = None
