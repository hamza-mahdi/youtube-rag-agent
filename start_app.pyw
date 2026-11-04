"""Desktop launcher for the YouTube RAG Agent (no terminal required)."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "pythonw.exe"
URL = "http://127.0.0.1:8000"


class Launcher(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.server: subprocess.Popen[str] | None = None
        self.title("YouTube RAG Agent")
        self.geometry("460x245")
        self.resizable(False, False)
        self.configure(padx=28, pady=28, bg="#151b25")

        tk.Label(
            self,
            text="وكيل YouTube الذكي",
            font=("Tahoma", 20, "bold"),
            fg="#edf2f7",
            bg="#151b25",
        ).pack(pady=(0, 10))
        tk.Label(
            self,
            text="شغّل التطبيق وافتح واجهة المحادثة من دون استخدام الطرفية.",
            font=("Tahoma", 10),
            fg="#bac7d8",
            bg="#151b25",
        ).pack(pady=(0, 18))
        self.status = tk.StringVar(value="جاهز للتشغيل")
        tk.Label(self, textvariable=self.status, fg="#b9fbc0", bg="#151b25").pack(pady=(0, 16))

        buttons = tk.Frame(self, bg="#151b25")
        buttons.pack()
        self.start_button = tk.Button(buttons, text="تشغيل وفتح التطبيق", command=self.start, padx=14, pady=8)
        self.start_button.grid(row=0, column=0, padx=5)
        tk.Button(buttons, text="فتح الواجهة", command=lambda: webbrowser.open(URL), padx=14, pady=8).grid(row=0, column=1, padx=5)
        tk.Button(buttons, text="إيقاف", command=self.stop, padx=14, pady=8).grid(row=0, column=2, padx=5)
        self.protocol("WM_DELETE_WINDOW", self.close)

    @staticmethod
    def running() -> bool:
        try:
            with urllib.request.urlopen(f"{URL}/api/health", timeout=0.5) as response:
                return response.status == 200
        except OSError:
            return False

    def start(self) -> None:
        if not PYTHON.exists():
            messagebox.showerror("بيئة ناقصة", "لم تُعثر على بيئة المشروع. شغّل إعداد المشروع مرة واحدة.")
            return
        if self.running():
            self.status.set("التطبيق يعمل بالفعل — جارٍ فتح الواجهة")
            webbrowser.open(URL)
            return
        self.status.set("جارٍ تشغيل الخادم…")
        self.start_button.configure(state="disabled")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.server = subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=BACKEND_DIR,
            creationflags=flags,
        )
        threading.Thread(target=self.wait_for_server, daemon=True).start()

    def wait_for_server(self) -> None:
        for _ in range(30):
            if self.running():
                self.after(0, lambda: self.status.set("التطبيق يعمل الآن"))
                self.after(0, lambda: self.start_button.configure(state="normal"))
                webbrowser.open(URL)
                return
            time.sleep(0.25)
        self.after(0, lambda: self.status.set("تعذر تشغيل الخادم"))
        self.after(0, lambda: self.start_button.configure(state="normal"))

    def stop(self) -> None:
        if self.server and self.server.poll() is None:
            self.server.terminate()
            self.server = None
            self.status.set("تم إيقاف التطبيق")
        else:
            self.status.set("لا توجد جلسة بدأها هذا المشغّل")

    def close(self) -> None:
        self.stop()
        self.destroy()


if __name__ == "__main__":
    Launcher().mainloop()
