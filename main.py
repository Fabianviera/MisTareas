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

# ── Paleta de colores ─────────────────────────────────────────────────────────
C = {
    "bg":            "#EBF2F8",
    "header":        "#C8DAF0",
    "header_border": "#B0C8E8",
    "task_bg":       "#F4F8FC",
    "task_hover":    "#D9EAF7",
    "task_priority": "#FFF5F5",
    "task_selected": "#D0E8F5",
    "accent":        "#5B9BD5",
    "accent_hover":  "#4A87BF",
    "text":          "#2C3E50",
    "text_muted":    "#8FA8C0",
    "text_priority": "#C0392B",
    "drag_handle":   "#A0B8D0",
    "drag_source":   "#D0D8E0",
    "drag_target":   "#A8CCE8",
    "input_bg":      "#FFFFFF",
    "border":        "#C5D5E8",
    "del_hover":     "#FDDEDE",
    "scroll":        "#C5D5E8",
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
        self._menu_popup    = None
        self._selected      = None
        self._drag_data     = {}
        self._row_widgets   = []
        self._drag_anim     = {"target": None, "old_target": None,
                               "old_gap": 0, "step": 0, "after_id": None}

        self.tasks: list[dict] = []
        self._load_tasks()

        self._build_ui()
        self._build_menubar()
        self._render_tasks()

        self.protocol("WM_DELETE_WINDOW", self._quit)
        quit_key = "<Command-q>" if sys.platform == "darwin" else "<Control-q>"
        self.bind_all(quit_key, lambda _: self._quit())
        self.bind_all("<Button-1>", self._on_global_click)
        self.bind_all("<Up>",   self._on_key_up)
        self.bind_all("<Down>", self._on_key_down)

    # ── Construcción de UI ────────────────────────────────────────────────────

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=C["header"], corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="✓  MisTareas",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=C["text"]
        ).pack(side="left", padx=16)

        self._menu_btn = ctk.CTkButton(
            header, text="⋮", width=38, height=38, corner_radius=19,
            fg_color="transparent", hover_color=C["task_hover"],
            text_color=C["text"], font=ctk.CTkFont(size=24),
            command=self._show_menu
        )
        self._menu_btn.pack(side="right", padx=8)

        self._pin_btn = ctk.CTkButton(
            header, text="📌", width=38, height=38, corner_radius=19,
            fg_color="transparent", hover_color=C["task_hover"],
            text_color=C["text_muted"], font=ctk.CTkFont(size=16),
            command=self._toggle_pin
        )
        self._pin_btn.pack(side="right", padx=4)
        self._update_pin_btn()

        input_row = ctk.CTkFrame(self, fg_color="transparent")
        input_row.pack(fill="x", padx=14, pady=(14, 6))

        self._entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Añadir nueva tarea…",
            fg_color=C["input_bg"], border_color=C["border"],
            text_color=C["text"], placeholder_text_color=C["text_muted"],
            height=46, corner_radius=14, font=ctk.CTkFont(size=14)
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._entry.bind("<Return>", lambda _: self._add_task())

        ctk.CTkButton(
            input_row, text="+", width=46, height=46, corner_radius=14,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color="white", font=ctk.CTkFont(size=24, weight="bold"),
            command=self._add_task
        ).pack(side="right")

        counter_row = ctk.CTkFrame(self, fg_color="transparent")
        counter_row.pack(fill="x", padx=18, pady=(0, 4))

        self._counter = ctk.CTkLabel(
            counter_row, text="",
            font=ctk.CTkFont(size=12),
            text_color=C["text_muted"]
        )
        self._counter.pack(side="left")

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
        if len(text) > 200:
            messagebox.showwarning("MisTareas", "El texto no puede superar los 200 caracteres.")
            return
        self.tasks.append({
            "text": text, "done": False,
            "created_at": _now(), "done_at": None,
            "priority": False, "priority_at": None
        })
        self._entry.delete(0, "end")
        self._save_tasks()
        self._render_tasks()

    def _toggle_task(self, index: int, var: ctk.BooleanVar):
        task = self.tasks[index]
        task["done"]    = var.get()
        task["done_at"] = _now() if var.get() else None

        # Al marcar como hecha, quitar la prioridad y mover fuera de la sección prioritaria
        if var.get() and task.get("priority"):
            task["priority"]    = False
            task["priority_at"] = None
            self.tasks.pop(index)
            # Insertar justo después del bloque de prioritarias
            insert_pos = sum(1 for t in self.tasks if t["priority"])
            self.tasks.insert(insert_pos, task)
            if self._selected == index:
                self._selected = insert_pos

        self._save_tasks()
        self._render_tasks()

    def _delete_task(self, index: int):
        self.tasks.pop(index)
        if self._selected == index:
            self._selected = None
        elif self._selected is not None and self._selected > index:
            self._selected -= 1
        self._save_tasks()
        self._render_tasks()

    def _toggle_priority(self, index: int):
        task = self.tasks[index]
        task["priority"]    = not task["priority"]
        task["priority_at"] = _now() if task["priority"] else None
        self.tasks.pop(index)
        insert_pos = sum(1 for t in self.tasks if t["priority"])
        self.tasks.insert(insert_pos, task)
        self._selected = insert_pos
        self._save_tasks()
        self._render_tasks()

    def _select_task(self, index: int):
        old = self._selected
        self._selected = None if self._selected == index else index
        for idx in (old, self._selected):
            if idx is not None and idx < len(self._row_widgets):
                task = self.tasks[idx]
                is_priority = task.get("priority", False)
                is_selected = (self._selected == idx)
                if is_selected:
                    bg = C["task_selected"]
                elif is_priority:
                    bg = C["task_priority"]
                else:
                    bg = C["task_bg"]
                try:
                    self._row_widgets[idx].configure(fg_color=bg)
                except Exception:
                    pass

    def _on_key_up(self, event):
        if not isinstance(event.widget, (ctk.CTkEntry, tk.Entry)):
            self._move_selected(-1)

    def _on_key_down(self, event):
        if not isinstance(event.widget, (ctk.CTkEntry, tk.Entry)):
            self._move_selected(1)

    def _move_selected(self, direction: int):
        if self._selected is None:
            return
        i = self._selected
        j = i + direction
        if 0 <= j < len(self.tasks):
            ti, tj = self.tasks[i], self.tasks[j]
            if ti.get("priority") == tj.get("priority"):
                self.tasks[i], self.tasks[j] = self.tasks[j], self.tasks[i]
                self._selected = j
                self._save_tasks()
                self._render_tasks()

    # ── Menú: cerrar al hacer clic fuera ─────────────────────────────────────

    def _on_global_click(self, event):
        if self._menu_popup is None or getattr(self, "_menu_just_opened", False):
            return
        menu = self._menu_popup
        try:
            mx, my = menu.winfo_rootx(), menu.winfo_rooty()
            mw, mh = menu.winfo_width(), menu.winfo_height()
            if not (mx <= event.x_root <= mx + mw and my <= event.y_root <= my + mh):
                try:
                    menu.destroy()
                except Exception:
                    pass
                self._menu_popup = None
        except Exception:
            try:
                menu.destroy()
            except Exception:
                pass
            self._menu_popup = None

    # ── Drag & Drop ───────────────────────────────────────────────────────────

    # ── Helpers de Canvas redondeado ─────────────────────────────────────────

    @staticmethod
    def _rounded_rect(cv, x1, y1, x2, y2, r, fill, outline=""):
        cv.create_arc(x1,    y1,    x1+2*r, y1+2*r, start=90,  extent=90, fill=fill, outline=fill)
        cv.create_arc(x2-2*r,y1,    x2,     y1+2*r, start=0,   extent=90, fill=fill, outline=fill)
        cv.create_arc(x1,    y2-2*r,x1+2*r, y2,     start=180, extent=90, fill=fill, outline=fill)
        cv.create_arc(x2-2*r,y2-2*r,x2,     y2,     start=270, extent=90, fill=fill, outline=fill)
        cv.create_rectangle(x1+r, y1,   x2-r, y2,   fill=fill, outline="")
        cv.create_rectangle(x1,   y1+r, x2,   y2-r, fill=fill, outline="")
        if outline:
            cv.create_arc(x1,    y1,    x1+2*r, y1+2*r, start=90,  extent=90, outline=outline, style="arc")
            cv.create_arc(x2-2*r,y1,    x2,     y1+2*r, start=0,   extent=90, outline=outline, style="arc")
            cv.create_arc(x1,    y2-2*r,x1+2*r, y2,     start=180, extent=90, outline=outline, style="arc")
            cv.create_arc(x2-2*r,y2-2*r,x2,     y2,     start=270, extent=90, outline=outline, style="arc")
            cv.create_line(x1+r, y1,   x2-r, y1,   fill=outline)
            cv.create_line(x1+r, y2,   x2-r, y2,   fill=outline)
            cv.create_line(x1,   y1+r, x1,   y2-r, fill=outline)
            cv.create_line(x2,   y1+r, x2,   y2-r, fill=outline)

    def _create_ghost(self, index: int, x_root: int, y_root: int):
        task = self.tasks[index]
        self.update_idletasks()
        row_w, row_h = 380, 52
        list_x = x_root - row_w // 2
        if index < len(self._row_widgets):
            try:
                row_w  = self._row_widgets[index].winfo_width()
                row_h  = self._row_widgets[index].winfo_height()
                list_x = self._list.winfo_rootx()
            except Exception:
                pass

        y = y_root - row_h // 2
        TRANS = "#F0EFF0"   # color clave de transparencia (no existe en nuestra paleta)
        r = 12

        # ── Sombra con esquinas redondeadas ──
        shadow = tk.Toplevel(self)
        shadow.overrideredirect(True)
        shadow.attributes("-topmost", True)
        shadow.configure(bg=TRANS)
        try:
            shadow.wm_attributes("-transparentcolor", TRANS)
            shadow.attributes("-alpha", 0.35)
        except Exception:
            pass
        shadow.geometry(f"{row_w}x{row_h}+{list_x + 5}+{y + 5}")
        scv = tk.Canvas(shadow, width=row_w, height=row_h, bg=TRANS, highlightthickness=0)
        scv.pack(fill="both", expand=True)
        self._rounded_rect(scv, 0, 0, row_w, row_h, r, "#222222")

        # ── Ghost principal con esquinas redondeadas ──
        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        ghost.configure(bg=TRANS)
        try:
            ghost.wm_attributes("-transparentcolor", TRANS)
            ghost.attributes("-alpha", 0.95)
        except Exception:
            pass
        ghost.geometry(f"{row_w}x{row_h}+{list_x}+{y}")

        is_priority = task.get("priority", False)
        bg         = C["task_priority"] if is_priority else "#FFFFFF"
        text_color = C["text_priority"] if is_priority else C["text"]
        label_text = ("⭐  " if is_priority else "") + task["text"]

        gcv = tk.Canvas(ghost, width=row_w, height=row_h, bg=TRANS, highlightthickness=0)
        gcv.pack(fill="both", expand=True)
        self._rounded_rect(gcv, 0, 0, row_w, row_h, r, bg, C["accent"])
        gcv.create_text(16, row_h//2, text="≡",       fill=C["drag_handle"],
                        font=("Segoe UI", 15), anchor="w")
        gcv.create_text(36, row_h//2, text=label_text, fill=text_color,
                        font=("Segoe UI", 12), anchor="w")

        self._drag_data.update(ghost=ghost, shadow=shadow,
                               list_x=list_x, row_h=row_h, row_w=row_w)

    def _start_drag(self, event, index: int):
        self._drag_data = {"index": index, "target": index,
                           "current_y": float(event.y_root)}
        if self._selected != index:
            self._selected = index
            self._render_tasks()

        self._create_ghost(index, event.x_root, event.y_root)

        if index < len(self._row_widgets):
            try:
                self._row_widgets[index].configure(fg_color=C["drag_source"])
            except Exception:
                pass

        # Iniciar bucle de movimiento suave
        self._drag_data["loop_id"] = self.after(16, self._ghost_anim_loop)

        # Resetear animación
        if self._drag_anim.get("after_id"):
            try:
                self.after_cancel(self._drag_anim["after_id"])
            except Exception:
                pass
        self._drag_anim = {"target": None, "old_target": None,
                           "old_gap": 0, "step": 0, "after_id": None}

        try:
            self.config(cursor="fleur")
        except Exception:
            pass

        self.bind_all("<B1-Motion>",       self._on_drag)
        self.bind_all("<ButtonRelease-1>", self._end_drag_global)

    def _ghost_anim_loop(self):
        """Bucle a ~60 fps que mueve el ghost con lerp para eliminar saltos."""
        if not self._drag_data or "ghost" not in self._drag_data:
            return
        try:
            x_root, y_root = self.winfo_pointerxy()
        except Exception:
            self._drag_data["loop_id"] = self.after(16, self._ghost_anim_loop)
            return

        # Interpolación suave hacia la posición real del cursor
        LERP = 0.55
        cy = self._drag_data.get("current_y", float(y_root))
        cy = cy + (y_root - cy) * LERP
        self._drag_data["current_y"] = cy

        list_x = self._drag_data.get("list_x", x_root)
        row_h  = self._drag_data.get("row_h", 52)
        iy     = int(cy) - row_h // 2

        for key, dx, dy in [("ghost", 0, 0), ("shadow", 5, 5)]:
            w = self._drag_data.get(key)
            if w:
                try:
                    w.geometry(f"+{list_x + dx}+{iy + dy}")
                except Exception:
                    pass

        # Detectar nuevo destino y animar apertura
        new_target = self._get_drag_target(y_root)
        if new_target != self._drag_data.get("target"):
            self._drag_data["target"] = new_target
            self._start_gap_anim(new_target)

        self._drag_data["loop_id"] = self.after(16, self._ghost_anim_loop)

    def _on_drag(self, event):
        # El movimiento del ghost lo gestiona _ghost_anim_loop; aquí no hace falta nada.
        pass

    def _start_gap_anim(self, new_idx: int):
        anim = self._drag_anim
        MAX_GAP = 44
        STEPS   = 10
        DELAY   = 13   # ~75fps

        if anim.get("after_id"):
            try:
                self.after_cancel(anim["after_id"])
            except Exception:
                pass

        old_idx     = anim.get("target")
        old_gap_now = anim.get("old_gap", 0)  # gap actual del viejo destino

        anim["old_target"] = old_idx
        anim["old_gap"]    = old_gap_now
        anim["target"]     = new_idx
        anim["step"]       = 0

        def step():
            if not self._drag_data:
                return
            anim["step"] += 1
            t = min(anim["step"] / STEPS, 1.0)
            # Smoothstep (S-curve)
            t_s = t * t * (3 - 2 * t)

            # Cerrar gap anterior
            o = anim["old_target"]
            if o is not None and o != new_idx and o < len(self._row_widgets):
                try:
                    self._row_widgets[o].pack_configure(
                        pady=(int(anim["old_gap"] * (1 - t_s)) + 3, 3))
                except Exception:
                    pass

            # Abrir gap nuevo
            if new_idx < len(self._row_widgets):
                gap = int(MAX_GAP * t_s)
                anim["old_gap"] = gap   # actualizar para la próxima transición
                try:
                    self._row_widgets[new_idx].pack_configure(pady=(gap + 3, 3))
                except Exception:
                    pass

            if anim["step"] < STEPS:
                anim["after_id"] = self.after(DELAY, step)
            else:
                anim["after_id"] = None

        step()

    def _end_drag_global(self, event):
        self.unbind_all("<B1-Motion>")
        self.unbind_all("<ButtonRelease-1>")
        self._end_drag(event)

    def _end_drag(self, event):
        if not self._drag_data:
            return

        # Cancelar bucle de movimiento del ghost
        loop_id = self._drag_data.get("loop_id")
        if loop_id:
            try:
                self.after_cancel(loop_id)
            except Exception:
                pass

        # Cancelar animación pendiente
        if self._drag_anim.get("after_id"):
            try:
                self.after_cancel(self._drag_anim["after_id"])
            except Exception:
                pass
        self._drag_anim = {"target": None, "old_target": None,
                           "old_gap": 0, "step": 0, "after_id": None}

        for key in ("ghost", "shadow"):
            w = self._drag_data.get(key)
            if w:
                try:
                    w.destroy()
                except Exception:
                    pass
        try:
            self.config(cursor="")
        except Exception:
            pass

        src = self._drag_data.get("index")
        tgt = self._drag_data.get("target", src)
        if src is not None and src != tgt and 0 <= tgt < len(self.tasks):
            task     = self.tasks[src]
            tgt_task = self.tasks[tgt]
            if task.get("priority") == tgt_task.get("priority"):
                self.tasks.pop(src)
                insert_at = tgt if tgt < src else tgt - 1
                insert_at = max(0, min(insert_at, len(self.tasks)))
                self.tasks.insert(insert_at, task)
                self._selected = insert_at
                self._save_tasks()
        self._drag_data = {}
        self._render_tasks()

    def _get_drag_target(self, y_root: int) -> int:
        if not self._row_widgets:
            return self._drag_data.get("index", 0)
        for i, w in enumerate(self._row_widgets):
            try:
                if y_root < w.winfo_rooty() + w.winfo_height() // 2:
                    return i
            except Exception:
                pass
        return len(self._row_widgets) - 1

    # ── Renderizado ───────────────────────────────────────────────────────────

    def _render_tasks(self):
        for w in self._list.winfo_children():
            w.destroy()
        self._row_widgets = []

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
        is_priority = task.get("priority", False)
        is_selected = (self._selected == index)

        if is_selected:
            bg = C["task_selected"]
        elif is_priority:
            bg = C["task_priority"]
        else:
            bg = C["task_bg"]

        row = ctk.CTkFrame(self._list, fg_color=bg, corner_radius=14)
        row.pack(fill="x", pady=3, padx=2)
        self._row_widgets.append(row)
        row.bind("<Button-1>", lambda e, i=index: self._select_task(i))

        # Asa de arrastre (≡)
        handle = ctk.CTkButton(
            row, text="≡", width=22, height=30, corner_radius=6,
            fg_color="transparent", hover_color=C["task_hover"],
            text_color=C["drag_handle"], font=ctk.CTkFont(size=16),
            command=lambda: None
        )
        handle.pack(side="left", padx=(6, 0), pady=10)
        handle.bind("<ButtonPress-1>", lambda e, i=index: self._start_drag(e, i))

        # Checkbox
        var = ctk.BooleanVar(value=task["done"])
        ctk.CTkCheckBox(
            row, text="", variable=var,
            width=24, height=24, checkbox_width=22, checkbox_height=22,
            corner_radius=6,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            border_color=C["border"],
            command=lambda i=index, v=var: self._toggle_task(i, v)
        ).pack(side="left", padx=(4, 8), pady=10)

        # Botones de la derecha (deben empaquetarse ANTES que el frame expandible)
        ctk.CTkButton(
            row, text="✕", width=30, height=30, corner_radius=8,
            fg_color="transparent", hover_color=C["del_hover"],
            text_color=C["text_muted"], font=ctk.CTkFont(size=12),
            command=lambda i=index: self._delete_task(i)
        ).pack(side="right", padx=(0, 4))

        if not task["done"]:
            star_text  = "★" if is_priority else "☆"
            star_color = "#E67E22" if is_priority else C["text_muted"]
            ctk.CTkButton(
                row, text=star_text, width=30, height=30, corner_radius=8,
                fg_color="transparent", hover_color=C["task_hover"],
                text_color=star_color, font=ctk.CTkFont(size=16),
                command=lambda i=index: self._toggle_priority(i)
            ).pack(side="right", padx=(0, 2))

        # Columna central
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=6, padx=(0, 4))
        info.bind("<Button-1>", lambda e, i=index: self._select_task(i))

        text_color = (C["text_priority"] if is_priority
                      else C["text_muted"] if task["done"]
                      else C["text"])
        label_text = ("⭐ " if is_priority else "") + task["text"]

        ctk.CTkLabel(
            info, text=label_text,
            font=ctk.CTkFont(size=14, overstrike=task["done"]),
            text_color=text_color, anchor="w"
        ).pack(fill="x")

        created = task.get("created_at", "")
        done_at = task.get("done_at", "")
        if created:
            ts = f"🕐 Creada: {created}"
            if done_at:
                ts += f"   ✅ Hecha: {done_at}"
            ctk.CTkLabel(
                info, text=ts,
                font=ctk.CTkFont(size=10),
                text_color=C["text_muted"], anchor="w"
            ).pack(fill="x", pady=(1, 0))

    def _update_counter(self):
        total    = len(self.tasks)
        done     = sum(1 for t in self.tasks if t["done"])
        priority = sum(1 for t in self.tasks if t.get("priority"))
        if total:
            text = f"{done} de {total} completada{'s' if total != 1 else ''}"
            if priority:
                text += f"  ·  {priority} prioritaria{'s' if priority != 1 else ''}"
        else:
            text = ""
        self._counter.configure(text=text)

    # ── Barra de menús nativa ─────────────────────────────────────────────────

    def _build_menubar(self):
        menubar = tk.Menu(self)

        if sys.platform == "darwin":
            # ── macOS: menú de aplicación estándar ──
            app_menu = tk.Menu(menubar, name="apple", tearoff=False)
            menubar.add_cascade(label="MisTareas", menu=app_menu)
            app_menu.add_command(label="Acerca de MisTareas", command=self._show_about)
            app_menu.add_separator()
            app_menu.add_command(label="Salir", command=self._quit, accelerator="Cmd+Q")

            tasks_menu = tk.Menu(menubar, tearoff=False)
            menubar.add_cascade(label="Tareas", menu=tasks_menu)
            tasks_menu.add_command(label="Borrar completadas", command=self._clear_done)
            tasks_menu.add_command(label="Borrar todas",       command=self._clear_all)

            help_menu = tk.Menu(menubar, tearoff=False)
            menubar.add_cascade(label="Ayuda", menu=help_menu)
            help_menu.add_command(label="Ayuda de MisTareas", command=self._show_help)
            help_menu.add_command(label="Licencia",            command=self._show_license)

        else:
            # ── Windows / Linux ──
            file_menu = tk.Menu(menubar, tearoff=False)
            menubar.add_cascade(label="Archivo", menu=file_menu)
            file_menu.add_command(label="Salir", command=self._quit, accelerator="Ctrl+Q")

            tasks_menu = tk.Menu(menubar, tearoff=False)
            menubar.add_cascade(label="Tareas", menu=tasks_menu)
            tasks_menu.add_command(label="Borrar completadas", command=self._clear_done)
            tasks_menu.add_command(label="Borrar todas",       command=self._clear_all)

            help_menu = tk.Menu(menubar, tearoff=False)
            menubar.add_cascade(label="Ayuda", menu=help_menu)
            help_menu.add_command(label="Ayuda de MisTareas", command=self._show_help)
            help_menu.add_separator()
            help_menu.add_command(label="Acerca de MisTareas", command=self._show_about)
            help_menu.add_command(label="Licencia",            command=self._show_license)

        self.config(menu=menubar)

    # ── Menú contextual (botón ⋮) ─────────────────────────────────────────────

    def _show_menu(self):
        if self._menu_popup is not None:
            try:
                self._menu_popup.destroy()
            except Exception:
                pass
            self._menu_popup = None
            return

        menu = ctk.CTkToplevel(self)
        menu.title("")
        menu.geometry("220x110")
        menu.resizable(False, False)
        menu.configure(fg_color=C["bg"])
        menu.attributes("-topmost", True)
        menu.overrideredirect(True)
        self._menu_popup = menu
        self._menu_just_opened = True
        menu.after(200, lambda: setattr(self, "_menu_just_opened", False))

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

        ctk.CTkFrame(menu, fg_color=C["border"], height=1).pack(fill="x", pady=(0, 4))

        for label, cmd in [
            ("🗑   Borrar completadas", self._clear_done),
            ("🗑   Borrar todas",        self._clear_all),
        ]:
            def _action(c=cmd):
                close_menu()
                c()
            ctk.CTkButton(
                menu, text=label,
                fg_color="transparent", hover_color=C["task_hover"],
                text_color=C["text"], anchor="w",
                height=44, corner_radius=10, font=ctk.CTkFont(size=13),
                command=_action
            ).pack(fill="x", padx=8, pady=2)

    # ── Ventanas de información ───────────────────────────────────────────────

    def _info_window(self, title: str, w: int, h: int):
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry(f"{w}x{h}")
        win.resizable(False, False)
        win.configure(fg_color=C["bg"])
        win.attributes("-topmost", True)
        win.grab_set()
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        win.geometry(f"+{x}+{y}")
        return win

    def _show_about(self):
        win = self._info_window("Acerca de MisTareas", 320, 200)
        ctk.CTkLabel(win, text="✓  MisTareas",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=C["accent"]).pack(pady=(28, 4))
        ctk.CTkLabel(win, text="Creado por Fabián Viera",
                     font=ctk.CTkFont(size=13), text_color=C["text"]).pack()
        ctk.CTkLabel(win, text="2026  ·  Versión beta 0.2  ·  Para uso no comercial",
                     font=ctk.CTkFont(size=12), text_color=C["text_muted"]).pack(pady=(2, 20))
        ctk.CTkButton(win, text="Cerrar", width=100, height=34, corner_radius=10,
                      fg_color=C["accent"], hover_color=C["accent_hover"],
                      text_color="white", command=win.destroy).pack()

    def _show_license(self):
        win = self._info_window("Licencia", 560, 440)
        ctk.CTkLabel(win, text="Licencia — GNU General Public License v3",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["accent"]).pack(pady=(16, 8), padx=16)

        box = ctk.CTkTextbox(win, fg_color=C["input_bg"], border_color=C["border"],
                             text_color=C["text"], font=ctk.CTkFont(size=11),
                             corner_radius=10, border_width=1, wrap="word")
        box.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        if getattr(sys, 'frozen', False):
            lpath = os.path.join(sys._MEIPASS, "LICENSE")
        else:
            lpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LICENSE")

        if os.path.exists(lpath):
            with open(lpath, "r", encoding="utf-8") as f:
                box.insert("end", f.read())
        else:
            box.insert("end", "GNU General Public License v3\n\nhttps://www.gnu.org/licenses/gpl-3.0.html")
        box.configure(state="disabled")
        ctk.CTkButton(win, text="Cerrar", width=100, height=34, corner_radius=10,
                      fg_color=C["accent"], hover_color=C["accent_hover"],
                      text_color="white", command=win.destroy).pack(pady=(0, 16))

    def _show_help(self):
        win = self._info_window("Ayuda — MisTareas", 520, 620)

        # ── Cabecera ──
        header = ctk.CTkFrame(win, fg_color=C["accent"], corner_radius=0, height=68)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text="✓  MisTareas  —  Guía rápida",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        ).pack(expand=True)

        # ── Área desplazable ──
        scroll = ctk.CTkScrollableFrame(
            win, fg_color=C["bg"],
            scrollbar_button_color=C["scroll"],
            scrollbar_button_hover_color=C["accent"]
        )
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        def section(icon, title, color, items):
            """Dibuja una sección con cabecera coloreada y lista de items."""
            # Cabecera de sección
            sh = ctk.CTkFrame(scroll, fg_color=color, corner_radius=10, height=36)
            sh.pack(fill="x", padx=14, pady=(12, 0))
            sh.pack_propagate(False)
            ctk.CTkLabel(
                sh, text=f"  {icon}  {title}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="white", anchor="w"
            ).pack(fill="x", padx=8, expand=True)

            # Tarjeta de contenido
            card = ctk.CTkFrame(scroll, fg_color=C["input_bg"],
                                corner_radius=10, border_width=1,
                                border_color=C["border"])
            card.pack(fill="x", padx=14, pady=(0, 2))

            for bullet, text in items:
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=(6, 0))
                ctk.CTkLabel(
                    row, text=bullet,
                    font=ctk.CTkFont(size=14),
                    text_color=color, width=24, anchor="w"
                ).pack(side="left", padx=(0, 6))
                ctk.CTkLabel(
                    row, text=text,
                    font=ctk.CTkFont(size=12),
                    text_color=C["text"], anchor="w", wraplength=380, justify="left"
                ).pack(side="left", fill="x", expand=True)
            ctk.CTkFrame(card, fg_color="transparent", height=6).pack()

        section("📝", "Crear una tarea", "#5B9BD5", [
            ("+",     "Escribe el texto en el campo superior."),
            ("↵",     "Pulsa [+] o la tecla Enter para añadirla."),
        ])

        section("✅", "Completar y descompletar", "#27AE60", [
            ("☑",     "Haz clic en el checkbox (☐) para marcarla como hecha. El texto aparecerá tachado."),
            ("↩",     "Vuelve a hacer clic en el checkbox para desmarcarla."),
            ("🕐",    "Se registra automáticamente la fecha y hora de creación y de finalización."),
        ])

        section("⭐", "Tareas prioritarias", "#E67E22", [
            ("☆",     "Pulsa la estrella (☆) en el lado derecho de la tarea para marcarla como prioritaria."),
            ("⬆",     "Las tareas prioritarias suben automáticamente al inicio de la lista con texto en rojo."),
            ("★",     "Pulsa [★] de nuevo para quitar la prioridad."),
            ("ℹ",     "Al marcar una tarea prioritaria como completada, pierde la prioridad automáticamente."),
        ])

        section("↕", "Ordenar tareas", "#8E44AD", [
            ("≡",     "Arrastra el icono [≡] (izquierda de la fila) para reordenar con el ratón."),
            ("↑↓",    "Selecciona una tarea haciendo clic en ella (se resalta en azul) y usa ↑ ↓ para moverla con el teclado."),
            ("⚠",     "Solo puedes mover tareas dentro de su sección: prioritarias con prioritarias, normales con normales."),
        ])

        section("🗑", "Eliminar tareas", "#C0392B", [
            ("✕",     "Pulsa [✕] en la fila para eliminar esa tarea."),
            ("⋮",     "Menú [⋮] o menú Tareas → «Borrar completadas» para limpiar las tareas hechas."),
            ("⚠",     "Menú Tareas → «Borrar todas» elimina toda la lista sin posibilidad de recuperación."),
        ])

        section("📌", "Fijar la ventana", "#2980B9", [
            ("📌",    "El botón [📌] de la cabecera mantiene la ventana siempre encima de las demás apps."),
            ("📍",    "Al activarse el botón cambia a [📍] con fondo azul. Pulsa de nuevo para desactivarlo."),
        ])

        ctk.CTkFrame(scroll, fg_color="transparent", height=8).pack()

        # ── Pie ──
        footer = ctk.CTkFrame(win, fg_color=C["header"], corner_radius=0, height=52)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        ctk.CTkLabel(
            footer, text="Fabián Viera · 2026 · Versión beta 0.2",
            font=ctk.CTkFont(size=11), text_color=C["text_muted"]
        ).pack(side="left", padx=16, expand=True)
        ctk.CTkButton(
            footer, text="Cerrar", width=90, height=34, corner_radius=10,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color="white", font=ctk.CTkFont(size=13),
            command=win.destroy
        ).pack(side="right", padx=16)

    # ── Acciones del menú Tareas ──────────────────────────────────────────────

    def _clear_done(self):
        count = sum(1 for t in self.tasks if t["done"])
        if count == 0:
            messagebox.showinfo("MisTareas", "No hay tareas completadas.")
            return
        if messagebox.askyesno("Confirmar", f"¿Borrar {count} tarea(s) completada(s)?"):
            self.tasks     = [t for t in self.tasks if not t["done"]]
            self._selected = None
            self._save_tasks()
            self._render_tasks()

    def _clear_all(self):
        if not self.tasks:
            messagebox.showinfo("MisTareas", "No hay tareas.")
            return
        if messagebox.askyesno("Confirmar", f"¿Borrar las {len(self.tasks)} tarea(s)?"):
            self.tasks     = []
            self._selected = None
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
            self._pin_btn.configure(text="📍", fg_color=C["accent"], text_color="white")
        else:
            self._pin_btn.configure(text="📌", fg_color="transparent", text_color=C["text_muted"])

    # ── Persistencia ──────────────────────────────────────────────────────────

    def _save_tasks(self):
        tmp = TASKS_FILE + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
            os.replace(tmp, TASKS_FILE)
        except Exception as e:
            try:
                os.remove(tmp)
            except Exception:
                pass
            messagebox.showerror("MisTareas", f"Error al guardar las tareas:\n{e}")

    def _load_tasks(self):
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
                for t in self.tasks:
                    t.setdefault("priority",    False)
                    t.setdefault("priority_at", None)
            except Exception as e:
                self.tasks = []
                messagebox.showerror(
                    "MisTareas",
                    f"No se pudo leer el archivo de tareas.\n"
                    f"Se empezará con la lista vacía.\n\nDetalle: {e}"
                )
        else:
            self.tasks = []


# ── Entrada ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = MisTareasApp()
    app.mainloop()
