import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os
import sys
from datetime import datetime

def _now() -> str:
    return datetime.now().strftime("%d/%m/%Y  %H:%M")

# ── Apariencia ────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── Paleta de colores (azules y grises suaves) ────────────────────────────────
C = {
    "bg":           "#EBF2F8",
    "header":       "#C8DAF0",
    "header_border":"#B0C8E8",
    "task_bg":      "#F4F8FC",
    "task_hover":   "#D9EAF7",
    "accent":       "#5B9BD5",
    "accent_hover": "#4A87BF",
    "text":         "#2C3E50",
    "text_muted":   "#8FA8C0",
    "input_bg":     "#FFFFFF",
    "border":       "#C5D5E8",
    "del_hover":    "#FDDEDE",
    "scroll":       "#C5D5E8",
}

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")


class MisTareasApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MisTareas")
        self.geometry("430x932")
        self.minsize(320, 480)
        self.configure(fg_color=C["bg"])
        self._always_on_top = False
        self._menu_popup = None

        self.tasks: list[dict] = []
        self._load_tasks()

        self._build_ui()
        self._build_menubar()
        self._render_tasks()

        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.bind_all("<Command-q>", lambda _: self._quit())

    # ── Construcción de UI ────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────────
        header = ctk.CTkFrame(
            self, fg_color=C["header"],
            corner_radius=0, height=64
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="✓  MisTareas",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=C["text"]
        ).pack(side="left", padx=16)

        # Botón menú
        self._menu_btn = ctk.CTkButton(
            header, text="⋮", width=38, height=38,
            corner_radius=19,
            fg_color="transparent", hover_color=C["task_hover"],
            text_color=C["text"], font=ctk.CTkFont(size=24),
            command=self._show_menu
        )
        self._menu_btn.pack(side="right", padx=8)

        # Botón siempre visible (pin)
        self._pin_btn = ctk.CTkButton(
            header, text="📌", width=38, height=38,
            corner_radius=19,
            fg_color="transparent", hover_color=C["task_hover"],
            text_color=C["text_muted"], font=ctk.CTkFont(size=16),
            command=self._toggle_pin
        )
        self._pin_btn.pack(side="right", padx=4)
        self._update_pin_btn()

        # ── Zona de entrada ──────────────────────────────────────────────
        input_row = ctk.CTkFrame(self, fg_color="transparent")
        input_row.pack(fill="x", padx=14, pady=(14, 6))

        self._entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Añadir nueva tarea…",
            fg_color=C["input_bg"], border_color=C["border"],
            text_color=C["text"], placeholder_text_color=C["text_muted"],
            height=46, corner_radius=14,
            font=ctk.CTkFont(size=14)
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._entry.bind("<Return>", lambda _: self._add_task())

        ctk.CTkButton(
            input_row, text="+", width=46, height=46,
            corner_radius=14,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color="white", font=ctk.CTkFont(size=24, weight="bold"),
            command=self._add_task
        ).pack(side="right")

        # ── Contador ─────────────────────────────────────────────────────
        counter_row = ctk.CTkFrame(self, fg_color="transparent")
        counter_row.pack(fill="x", padx=18, pady=(0, 4))

        self._counter = ctk.CTkLabel(
            counter_row, text="",
            font=ctk.CTkFont(size=12),
            text_color=C["text_muted"]
        )
        self._counter.pack(side="left")

        # ── Lista de tareas ──────────────────────────────────────────────
        self._list = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=C["scroll"],
            scrollbar_button_hover_color=C["accent"]
        )
        self._list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ── Lógica de tareas ──────────────────────────────────────────────────────

    def _add_task(self):
        text = self._entry.get().strip()
        if not text:
            return
        self.tasks.append({"text": text, "done": False, "created_at": _now(), "done_at": None})
        self._entry.delete(0, "end")
        self._save_tasks()
        self._render_tasks()

    def _toggle_task(self, index: int, var: ctk.BooleanVar):
        done = var.get()
        self.tasks[index]["done"] = done
        self.tasks[index]["done_at"] = _now() if done else None
        self._save_tasks()
        self._render_tasks()

    def _delete_task(self, index: int):
        self.tasks.pop(index)
        self._save_tasks()
        self._render_tasks()

    def _render_tasks(self):
        for w in self._list.winfo_children():
            w.destroy()

        if not self.tasks:
            ctk.CTkLabel(
                self._list,
                text="Sin tareas por el momento.\n¡Añade una arriba!",
                font=ctk.CTkFont(size=14),
                text_color=C["text_muted"]
            ).pack(pady=50)
        else:
            for i, task in enumerate(self.tasks):
                self._task_row(i, task)

        self._update_counter()

    def _task_row(self, index: int, task: dict):
        row = ctk.CTkFrame(
            self._list, fg_color=C["task_bg"],
            corner_radius=14
        )
        row.pack(fill="x", pady=3, padx=2)

        var = ctk.BooleanVar(value=task["done"])

        ctk.CTkCheckBox(
            row, text="", variable=var,
            width=24, height=24,
            checkbox_width=22, checkbox_height=22,
            corner_radius=6,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            border_color=C["border"],
            command=lambda i=index, v=var: self._toggle_task(i, v)
        ).pack(side="left", padx=(12, 8), pady=10)

        # Columna central: texto + timestamps
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=6, padx=(0, 4))

        ctk.CTkLabel(
            info,
            text=task["text"],
            font=ctk.CTkFont(size=14, overstrike=task["done"]),
            text_color=C["text_muted"] if task["done"] else C["text"],
            anchor="w"
        ).pack(fill="x")

        # Timestamps
        created = task.get("created_at", "")
        done_at = task.get("done_at", "")

        if created:
            ts_text = f"🕐 Creada: {created}"
            if done_at:
                ts_text += f"   ✅ Hecha: {done_at}"
            ctk.CTkLabel(
                info,
                text=ts_text,
                font=ctk.CTkFont(size=10),
                text_color=C["text_muted"],
                anchor="w"
            ).pack(fill="x", pady=(1, 0))

        ctk.CTkButton(
            row, text="✕", width=30, height=30,
            corner_radius=8,
            fg_color="transparent", hover_color=C["del_hover"],
            text_color=C["text_muted"], font=ctk.CTkFont(size=12),
            command=lambda i=index: self._delete_task(i)
        ).pack(side="right", padx=8)

    def _update_counter(self):
        total = len(self.tasks)
        done  = sum(1 for t in self.tasks if t["done"])
        self._counter.configure(
            text=f"{done} de {total} completada{'s' if total != 1 else ''}" if total else ""
        )

    # ── Barra de menús nativa ─────────────────────────────────────────────────

    def _build_menubar(self):
        menubar = tk.Menu(self)

        # Menú de la app (macOS: aparece con el nombre de la app a la izquierda)
        app_menu = tk.Menu(menubar, name="apple", tearoff=False)
        menubar.add_cascade(label="Archivo", menu=app_menu)
        app_menu.add_command(label="Acerca de MisTareas", command=self._show_about)
        app_menu.add_separator()
        app_menu.add_command(label="Salir", command=self._quit, accelerator="Cmd+Q")

        # Menú Tareas
        tasks_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Tareas", menu=tasks_menu)
        tasks_menu.add_command(label="Borrar completadas", command=self._clear_done)
        tasks_menu.add_command(label="Borrar todas",       command=self._clear_all)

        self.config(menu=menubar)

    # ── Menú contextual (botón ⋮) ─────────────────────────────────────────────

    def _show_menu(self):
        # Si ya hay un menú abierto, cerrarlo (toggle)
        if self._menu_popup is not None:
            try:
                self._menu_popup.destroy()
            except Exception:
                pass
            self._menu_popup = None
            return

        menu = ctk.CTkToplevel(self)
        menu.title("")
        menu.geometry("220x175")
        menu.resizable(False, False)
        menu.configure(fg_color=C["bg"])
        menu.attributes("-topmost", True)
        menu.overrideredirect(True)
        self._menu_popup = menu

        # Posición justo debajo del botón ⋮
        self.update_idletasks()
        bx = self._menu_btn.winfo_rootx()
        by = self._menu_btn.winfo_rooty() + self._menu_btn.winfo_height() + 4
        menu.geometry(f"+{bx - 180}+{by}")

        def close_menu():
            if self._menu_popup is not None:
                try:
                    self._menu_popup.destroy()
                except Exception:
                    pass
                self._menu_popup = None
            self.unbind_all("<Button-1>")

        def on_click_outside(event):
            try:
                mx, my = menu.winfo_rootx(), menu.winfo_rooty()
                mw, mh = menu.winfo_width(), menu.winfo_height()
                if not (mx <= event.x_root <= mx + mw and my <= event.y_root <= my + mh):
                    close_menu()
            except Exception:
                close_menu()

        menu.after(150, lambda: self.bind_all("<Button-1>", on_click_outside))
        menu.bind("<Destroy>", lambda e: self.unbind_all("<Button-1>"))

        ctk.CTkFrame(menu, fg_color=C["border"], height=1).pack(fill="x", pady=(0, 4))

        items = [
            ("🗑   Borrar completadas", self._clear_done),
            ("🗑   Borrar todas",        self._clear_all),
            ("✕    Salir",              self._quit),
        ]

        for label, cmd in items:
            def _action(c=cmd):
                close_menu()
                c()

            ctk.CTkButton(
                menu, text=label,
                fg_color="transparent", hover_color=C["task_hover"],
                text_color=C["text"], anchor="w",
                height=44, corner_radius=10,
                font=ctk.CTkFont(size=13),
                command=_action
            ).pack(fill="x", padx=8, pady=2)

    # ── Acciones del menú ─────────────────────────────────────────────────────

    def _show_about(self):
        win = ctk.CTkToplevel(self)
        win.title("Acerca de MisTareas")
        win.geometry("320x200")
        win.resizable(False, False)
        win.configure(fg_color=C["bg"])
        win.attributes("-topmost", True)
        win.grab_set()

        # Centrar sobre la ventana principal
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 320) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        win.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            win, text="✓  MisTareas",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=C["accent"]
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            win, text="Creado por Fabián Viera",
            font=ctk.CTkFont(size=13),
            text_color=C["text"]
        ).pack()

        ctk.CTkLabel(
            win, text="2026  ·  Versión beta 0.1",
            font=ctk.CTkFont(size=12),
            text_color=C["text_muted"]
        ).pack(pady=(2, 20))

        ctk.CTkButton(
            win, text="Cerrar", width=100, height=34,
            corner_radius=10,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color="white",
            command=win.destroy
        ).pack()

    def _clear_done(self):
        count = sum(1 for t in self.tasks if t["done"])
        if count == 0:
            messagebox.showinfo("MisTareas", "No hay tareas completadas.")
            return
        if messagebox.askyesno("Confirmar", f"¿Borrar {count} tarea(s) completada(s)?"):
            self.tasks = [t for t in self.tasks if not t["done"]]
            self._save_tasks()
            self._render_tasks()

    def _clear_all(self):
        if not self.tasks:
            messagebox.showinfo("MisTareas", "No hay tareas.")
            return
        if messagebox.askyesno("Confirmar", f"¿Borrar las {len(self.tasks)} tarea(s)?"):
            self.tasks = []
            self._save_tasks()
            self._render_tasks()

    def _quit(self):
        self._save_tasks()
        self.destroy()

    # ── Siempre visible ───────────────────────────────────────────────────────

    def _toggle_pin(self):
        self._always_on_top = not self._always_on_top
        self.attributes("-topmost", self._always_on_top)
        self._update_pin_btn()

    def _update_pin_btn(self):
        if self._always_on_top:
            self._pin_btn.configure(
                text="📍",
                fg_color=C["accent"],
                text_color="white"
            )
        else:
            self._pin_btn.configure(
                text="📌",
                fg_color="transparent",
                text_color=C["text_muted"]
            )

    # ── Persistencia ──────────────────────────────────────────────────────────

    def _save_tasks(self):
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)

    def _load_tasks(self):
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
            except Exception:
                self.tasks = []
        else:
            self.tasks = []


# ── Entrada ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = MisTareasApp()
    app.mainloop()
