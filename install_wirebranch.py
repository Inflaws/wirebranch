"""
WireBranch Suite — Cross-Platform Installer
Supports: Windows 10/11 | Linux (CachyOS, Arch, Debian/Ubuntu, Fedora)

Использует ТОЛЬКО встроенный tkinter для GUI на старте —
customtkinter и остальные зависимости ставятся в процессе установки.
"""

import sys
import os
import subprocess
import threading
import platform
import shutil
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

VERSION = "1.1.0"
SYSTEM  = platform.system()

REQUIRED_PACKAGES = [
    ("customtkinter", "customtkinter", "Modern Tkinter UI"),
    ("PyQt5",         "PyQt5",         "Qt5 framework (Blueprint Editor)"),
    ("NodeGraphQt",   "NodeGraphQt",   "Node graph library"),
]

SOURCE_FILES = [
    "wirebranch.py",
    "blueprints_editor.py",
    "nodes_gmod.py",
]

# ── pip helper ────────────────────────────────────────────────────────────────

def pip_install(package: str) -> tuple[bool, str]:
    """Пробует установить пакет тремя способами. Возвращает (успех, сообщение)."""
    strategies = [
        [sys.executable, "-m", "pip", "install", package, "--quiet"],
        [sys.executable, "-m", "pip", "install", package, "--quiet", "--break-system-packages"],
        [sys.executable, "-m", "pip", "install", package, "--quiet", "--user"],
    ]
    for cmd in strategies:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return True, " ".join(cmd[5:])   # какой флаг сработал
    return False, (r.stderr or r.stdout).strip()[:200]

# ── пути ─────────────────────────────────────────────────────────────────────

def default_install_dir() -> Path:
    if SYSTEM == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "WireBranch"
    return Path.home() / ".local" / "share" / "WireBranch"

def desktop_dir() -> Path:
    return Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop" if SYSTEM == "Windows" \
           else Path.home() / "Desktop"

# ── логика установки ──────────────────────────────────────────────────────────

class Installer:
    def __init__(self, install_dir: Path, create_shortcut: bool,
                 log_cb, progress_cb, done_cb):
        self.install_dir    = install_dir
        self.create_shortcut = create_shortcut
        self.log            = log_cb
        self.set_progress   = progress_cb
        self.done           = done_cb
        self._cancelled     = False

    def cancel(self): self._cancelled = True

    def run(self):
        steps = [
            (10, "Проверка Python",           self._check_python),
            (20, "Создание директории",        self._create_dir),
            (55, "Установка зависимостей",     self._install_packages),
            (80, "Копирование файлов",         self._copy_files),
            (95, "Создание ярлыка",            self._make_shortcut),
            (100,"Финализация",               self._finalize),
        ]
        try:
            for pct, name, fn in steps:
                if self._cancelled:
                    self.log("⚠  Установка отменена.", "warn"); self.done(False); return
                self.log(f"\n▶  {name}...")
                fn()
                self.set_progress(pct)
        except Exception as e:
            self.log(f"\n❌ Ошибка: {e}", "error")
            self.done(False)
            return
        self.log("\n✅  Установка успешно завершена!", "ok")
        self.done(True)

    def _check_python(self):
        vi = sys.version_info
        if vi < (3, 8):
            raise RuntimeError(f"Требуется Python 3.8+, обнаружен {vi.major}.{vi.minor}")
        self.log(f"   Python {vi.major}.{vi.minor}.{vi.micro} ✓  |  {SYSTEM} {platform.machine()}")

    def _create_dir(self):
        self.install_dir.mkdir(parents=True, exist_ok=True)
        self.log(f"   {self.install_dir}")

    def _install_packages(self):
        failed = []
        for pkg_import, pkg_pip, pkg_desc in REQUIRED_PACKAGES:
            if self._cancelled: return
            try:
                __import__(pkg_import)
                self.log(f"   ✓ {pkg_desc} — уже установлен")
                continue
            except ImportError:
                pass
            self.log(f"   ⬇  {pkg_desc} ({pkg_pip})...")
            ok, info = pip_install(pkg_pip)
            if ok:
                self.log(f"   ✓ {pkg_desc} установлен  [{info}]")
            else:
                self.log(f"   ✗ {pkg_pip} не установился", "warn")
                self.log(f"     {info}", "warn")
                failed.append(pkg_pip)
        if failed:
            self.log(f"\n   ⚠  Не установились: {', '.join(failed)}", "warn")
            self.log(f"   pip install {' '.join(failed)} --break-system-packages", "warn")

    def _copy_files(self):
        src_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        for fname in SOURCE_FILES:
            src = src_dir / fname
            if src.exists():
                shutil.copy2(src, self.install_dir / fname)
                self.log(f"   ✓ {fname}")
            else:
                self.log(f"   ⚠  {fname} не найден рядом с инсталлятором", "warn")
        shutil.copy2(Path(os.path.abspath(__file__)), self.install_dir / "install_wirebranch.py")

    def _make_shortcut(self):
        if not self.create_shortcut:
            self.log("   (пропущено)"); return
        target = self.install_dir / "wirebranch.py"
        if SYSTEM == "Windows":   self._shortcut_win(target)
        elif SYSTEM == "Linux":   self._shortcut_linux(target)
        else: self.log("   ⚠  Ярлыки на macOS не поддерживаются", "warn")

    def _shortcut_win(self, target: Path):
        bat = self.install_dir / "WireBranch.bat"
        bat.write_text(f'@echo off\ncd /d "{self.install_dir}"\n"{sys.executable}" "{target}"\n', encoding="utf-8")
        lnk = desktop_dir() / "WireBranch.lnk"
        ps  = (f'$ws=$wsh=New-Object -Com WScript.Shell;'
               f'$s=$ws.CreateShortcut("{lnk}");'
               f'$s.TargetPath="{bat}";$s.Save()')
        r = subprocess.run(["powershell","-NoProfile","-Command",ps], capture_output=True)
        self.log(f"   ✓ Ярлык: {lnk}" if r.returncode == 0 else f"   ⚠  .lnk не создан, используй: {bat}")

    def _shortcut_linux(self, target: Path):
        entry = (
            "[Desktop Entry]\nVersion=1.0\nType=Application\n"
            f"Name=WireBranch Suite\nExec={sys.executable} {target}\n"
            f"Path={self.install_dir}\nIcon=applications-games\n"
            "Terminal=false\nCategories=Development;Game;\n"
        )
        apps = Path.home() / ".local/share/applications"
        apps.mkdir(parents=True, exist_ok=True)
        de = apps / "wirebranch.desktop"
        de.write_text(entry, encoding="utf-8"); de.chmod(0o755)
        self.log(f"   ✓ {de}")
        desk = desktop_dir()
        if desk.exists():
            d2 = desk / "WireBranch.desktop"
            shutil.copy2(de, d2); d2.chmod(0o755)
            self.log(f"   ✓ {d2}")
        sh = self.install_dir / "wirebranch.sh"
        sh.write_text(f'#!/usr/bin/env bash\ncd "{self.install_dir}"\n"{sys.executable}" "{target}"\n')
        sh.chmod(0o755); self.log(f"   ✓ {sh}")

    def _finalize(self):
        meta = {"version": VERSION, "install_dir": str(self.install_dir),
                "python": sys.version, "platform": SYSTEM}
        (self.install_dir / "install_meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        self.log(f"   Запуск: {sys.executable} {self.install_dir / 'wirebranch.py'}")


# ── GUI (чистый tkinter — без внешних зависимостей) ──────────────────────────

BG       = "#111318"
BG2      = "#181c24"
BG3      = "#0f1420"
ACCENT   = "#2563eb"
FG       = "#e2e8f0"
FG_DIM   = "#64748b"
C_OK     = "#22c55e"
C_WARN   = "#eab308"
C_ERR    = "#ef4444"
FONT     = ("Segoe UI", 11) if SYSTEM == "Windows" else ("DejaVu Sans", 11)
MONO     = ("Consolas", 10) if SYSTEM == "Windows" else ("DejaVu Sans Mono", 10)


class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WireBranch Suite — Installer")
        self.resizable(True, True)
        self.configure(bg=BG)
        self._installer: Installer | None = None
        self._build()
        self.update_idletasks()
        screen_h = self.winfo_screenheight()
        w = 780
        h = max(520, min(660, int(screen_h * 0.85)))
        x = (self.winfo_screenwidth()  - w) // 2
        y = max(0, (screen_h - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(680, 500)

    # ── build ─────────────────────────────────────────────

    def _build(self):
        self._style()

        # Header
        hdr = tk.Frame(self, bg=BG2, height=72)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="🔷 WireBranch Suite", bg=BG2, fg=FG,
                 font=("Segoe UI", 20, "bold") if SYSTEM=="Windows" else ("DejaVu Sans", 18, "bold")
                 ).pack(side="left", padx=24, pady=(14,4), anchor="w")
        tk.Label(hdr, text=f"Installer v{VERSION}  •  Python {sys.version.split()[0]}  •  {SYSTEM}",
                 bg=BG2, fg=FG_DIM, font=FONT).place(x=24, y=46)

        # Body
        body = tk.Frame(self, bg=BG); body.pack(fill="both", expand=True, padx=16, pady=12)

        # Left panel
        left = tk.Frame(body, bg=BG2, width=280); left.pack(side="left", fill="y", padx=(0,10))
        left.pack_propagate(False)

        tk.Label(left, text="Параметры установки", bg=BG2, fg=FG,
                 font=(*FONT[:1], FONT[1], "bold")).pack(anchor="w", padx=14, pady=(14,6))

        tk.Label(left, text="Папка назначения:", bg=BG2, fg=FG_DIM, font=FONT).pack(anchor="w", padx=14)
        pf = tk.Frame(left, bg=BG2); pf.pack(fill="x", padx=14, pady=(2,10))
        self.var_path = tk.StringVar(value=str(default_install_dir()))
        tk.Entry(pf, textvariable=self.var_path, bg=BG3, fg=FG, insertbackground=FG,
                 relief="flat", font=FONT, bd=4).pack(side="left", fill="x", expand=True)
        tk.Button(pf, text="📁", bg="#1e293b", fg=FG, relief="flat",
                  command=self._browse, cursor="hand2").pack(side="right", padx=(4,0))

        self.var_shortcut = tk.BooleanVar(value=True)
        tk.Checkbutton(left, text="Ярлык на рабочем столе", variable=self.var_shortcut,
                       bg=BG2, fg=FG, selectcolor=BG3, activebackground=BG2,
                       font=FONT).pack(anchor="w", padx=14, pady=(0,12))

        tk.Label(left, text="Зависимости:", bg=BG2, fg=FG,
                 font=(*FONT[:1], FONT[1], "bold")).pack(anchor="w", padx=14, pady=(6,4))
        for pkg_import, _, desc in REQUIRED_PACKAGES:
            try: __import__(pkg_import); sym, col = "✓", C_OK
            except ImportError:          sym, col = "⬇", C_WARN
            row = tk.Frame(left, bg=BG2); row.pack(fill="x", padx=14, pady=1)
            tk.Label(row, text=sym, bg=BG2, fg=col, font=FONT, width=2).pack(side="left")
            tk.Label(row, text=desc, bg=BG2, fg=FG_DIM, font=FONT).pack(side="left")

        tk.Label(left, text="Система:", bg=BG2, fg=FG,
                 font=(*FONT[:1], FONT[1], "bold")).pack(anchor="w", padx=14, pady=(14,4))
        sysinfo = [
            f"OS:      {SYSTEM} {platform.release()}",
            f"Arch:    {platform.machine()}",
            f"Python:  {sys.version.split()[0]}",
        ]
        if SYSTEM == "Linux":
            try:
                d = subprocess.check_output(["lsb_release","-si"], text=True, stderr=subprocess.DEVNULL).strip()
                sysinfo.insert(0, f"Distro:  {d}")
            except Exception: pass
        for line in sysinfo:
            tk.Label(left, text=line, bg=BG2, fg=FG_DIM, font=MONO).pack(anchor="w", padx=14, pady=0)

        # Right panel — log
        right = tk.Frame(body, bg=BG2); right.pack(side="left", fill="both", expand=True)
        tk.Label(right, text="Журнал установки", bg=BG2, fg=FG,
                 font=(*FONT[:1], FONT[1], "bold")).pack(anchor="w", padx=14, pady=(14,4))

        self.log_text = tk.Text(right, bg=BG3, fg=FG, font=MONO, relief="flat",
                                state="disabled", bd=0, wrap="word")
        sb = ttk.Scrollbar(right, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0,8), pady=(0,10))
        self.log_text.pack(fill="both", expand=True, padx=(14,0), pady=(0,10))

        self.log_text.tag_config("ok",    foreground=C_OK)
        self.log_text.tag_config("warn",  foreground=C_WARN)
        self.log_text.tag_config("error", foreground=C_ERR)
        self.log_text.tag_config("dim",   foreground=FG_DIM)

        # Bottom bar
        bot = tk.Frame(self, bg=BG2, height=64); bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)
        row = tk.Frame(bot, bg=BG2); row.pack(expand=True)

        tk.Button(row, text="Отмена", bg="#1e293b", fg=FG, relief="flat",
                  font=FONT, padx=16, cursor="hand2",
                  command=self._cancel).pack(side="left", padx=8, pady=14)

        tk.Button(row, text="Удалить", bg="#7f1d1d", fg=FG, relief="flat",
                  font=FONT, padx=16, cursor="hand2",
                  command=self._uninstall).pack(side="left", padx=8, pady=14)

        self.progress = ttk.Progressbar(row, length=200, mode="determinate")
        self.progress.pack(side="left", padx=14, pady=18)

        self.btn_install = tk.Button(row, text="⚡ Установить", bg=ACCENT, fg="white",
                                     relief="flat", font=(*FONT[:1], FONT[1]+1, "bold"),
                                     padx=20, cursor="hand2", command=self._start)
        self.btn_install.pack(side="left", padx=8, pady=14)

        self._log("WireBranch Installer готов.\n")
        self._log(f"Каталог: {os.path.dirname(os.path.abspath(__file__))}\n", "dim")

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Vertical.TScrollbar", background=BG2, troughcolor=BG3,
                    bordercolor=BG2, arrowcolor=FG_DIM)
        s.configure("TProgressbar", troughcolor=BG3, background=ACCENT, bordercolor=BG2)

    # ── actions ──────────────────────────────────────────

    def _browse(self):
        d = filedialog.askdirectory(title="Папка для установки")
        if d: self.var_path.set(d)

    def _log(self, msg: str, tag: str = ""):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _tlog(self, msg: str, tag: str = ""):
        self.after(0, lambda m=msg, t=tag: self._log(m, t))

    def _set_progress(self, val: int):
        self.after(0, lambda v=val: self.progress.configure(value=v))

    def _start(self):
        if self._installer:
            return
        path = Path(self.var_path.get().strip())
        self.btn_install.configure(state="disabled", text="Установка...")
        self._installer = Installer(
            install_dir=path,
            create_shortcut=self.var_shortcut.get(),
            log_cb=self._tlog,
            progress_cb=self._set_progress,
            done_cb=self._on_done,
        )
        threading.Thread(target=self._installer.run, daemon=True).start()

    def _cancel(self):
        if self._installer: self._installer.cancel()
        else: self.destroy()

    def _on_done(self, success: bool):
        self._installer = None
        def _ui():
            self.btn_install.configure(
                state="normal",
                text="✓ Готово!" if success else "Повторить",
                bg=C_OK if success else ACCENT
            )
            if success:
                path = Path(self.var_path.get().strip())
                if messagebox.askyesno("Готово!", "WireBranch установлен!\n\nЗапустить приложение?"):
                    subprocess.Popen([sys.executable, str(path / "wirebranch.py")])
        self.after(0, _ui)

    def _uninstall(self):
        path = Path(self.var_path.get().strip())
        if not path.exists():
            messagebox.showinfo("Удаление", f"Папка не найдена:\n{path}"); return
        if not messagebox.askyesno("Подтверждение", f"Удалить WireBranch из:\n{path}\n\nНеобратимо!"): return
        try:
            shutil.rmtree(path)
            if SYSTEM == "Linux":
                for f in [Path.home()/".local/share/applications/wirebranch.desktop",
                          desktop_dir()/"WireBranch.desktop"]:
                    f.exists() and f.unlink()
            elif SYSTEM == "Windows":
                lnk = desktop_dir() / "WireBranch.lnk"
                lnk.exists() and lnk.unlink()
            messagebox.showinfo("Удалено", "WireBranch удалён.")
            self._log(f"Удалено: {path}", "warn")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
