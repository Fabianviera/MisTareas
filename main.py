import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os
import sys
from datetime import datetime

def _ahora() -> str:
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
    DIR_BASE = os.path.dirname(sys.executable)
else:
    DIR_BASE = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_TAREAS = os.path.join(DIR_BASE, "tasks.json")


class MisTareasApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MisTareas")
        self.geometry("430x932")
        self.minsize(320, 480)
        self.configure(fg_color=C["bg"])
        self._siempre_visible    = False
        self._menu_emergente     = None
        self._seleccionada       = None
        self._datos_arrastre     = {}
        self._widgets_fila       = []
        self._anim_arrastre      = {"target": None, "old_target": None,
                                    "old_gap": 0, "step": 0, "after_id": None}

        self.tareas: list[dict] = []
        self._cargar_tareas()

        self._construir_ui()
        self._construir_barra_menus()
        self._renderizar_tareas()

        self.protocol("WM_DELETE_WINDOW", self._salir)
        tecla_salir = "<Command-q>" if sys.platform == "darwin" else "<Control-q>"
        self.bind_all(tecla_salir, lambda _: self._salir())
        self.bind_all("<Button-1>", self._al_clic_global)
        self.bind_all("<Up>",   self._al_pulsar_arriba)
        self.bind_all("<Down>", self._al_pulsar_abajo)

    # ── Construcción de UI ────────────────────────────────────────────────────

    def _construir_ui(self):
        cabecera = ctk.CTkFrame(self, fg_color=C["header"], corner_radius=0, height=64)
        cabecera.pack(fill="x")
        cabecera.pack_propagate(False)

        ctk.CTkLabel(
            cabecera, text="✓  MisTareas",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=C["text"]
        ).pack(side="left", padx=16)

        self._btn_menu = ctk.CTkButton(
            cabecera, text="⋮", width=38, height=38, corner_radius=19,
            fg_color="transparent", hover_color=C["task_hover"],
            text_color=C["text"], font=ctk.CTkFont(size=24),
            command=self._mostrar_menu
        )
        self._btn_menu.pack(side="right", padx=8)

        self._btn_pin = ctk.CTkButton(
            cabecera, text="📌", width=38, height=38, corner_radius=19,
            fg_color="transparent", hover_color=C["task_hover"],
            text_color=C["text_muted"], font=ctk.CTkFont(size=16),
            command=self._alternar_pin
        )
        self._btn_pin.pack(side="right", padx=4)
        self._actualizar_btn_pin()

        fila_entrada = ctk.CTkFrame(self, fg_color="transparent")
        fila_entrada.pack(fill="x", padx=14, pady=(14, 6))

        self._entrada = ctk.CTkEntry(
            fila_entrada,
            placeholder_text="Añadir nueva tarea…",
            fg_color=C["input_bg"], border_color=C["border"],
            text_color=C["text"], placeholder_text_color=C["text_muted"],
            height=46, corner_radius=14, font=ctk.CTkFont(size=14)
        )
        self._entrada.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._entrada.bind("<Return>", lambda _: self._añadir_tarea())

        ctk.CTkButton(
            fila_entrada, text="+", width=46, height=46, corner_radius=14,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color="white", font=ctk.CTkFont(size=24, weight="bold"),
            command=self._añadir_tarea
        ).pack(side="right")

        fila_contador = ctk.CTkFrame(self, fg_color="transparent")
        fila_contador.pack(fill="x", padx=18, pady=(0, 4))

        self._contador = ctk.CTkLabel(
            fila_contador, text="",
            font=ctk.CTkFont(size=12),
            text_color=C["text_muted"]
        )
        self._contador.pack(side="left")

        self._lista = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=C["scroll"],
            scrollbar_button_hover_color=C["accent"]
        )
        self._lista.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ── Lógica de tareas ──────────────────────────────────────────────────────

    def _añadir_tarea(self):
        texto = self._entrada.get().strip()
        if not texto:
            return
        if len(texto) > 200:
            messagebox.showwarning("MisTareas", "El texto no puede superar los 200 caracteres.")
            return
        self.tareas.append({
            "text": texto, "done": False,
            "created_at": _ahora(), "done_at": None,
            "priority": False, "priority_at": None
        })
        self._entrada.delete(0, "end")
        self._guardar_tareas()
        self._renderizar_tareas()

    def _alternar_tarea(self, indice: int, var: ctk.BooleanVar):
        tarea = self.tareas[indice]
        tarea["done"]    = var.get()
        tarea["done_at"] = _ahora() if var.get() else None

        # Al marcar como hecha, quitar la prioridad y mover fuera de la sección prioritaria
        if var.get() and tarea.get("priority"):
            tarea["priority"]    = False
            tarea["priority_at"] = None
            self.tareas.pop(indice)
            # Insertar justo después del bloque de prioritarias
            pos_insercion = sum(1 for t in self.tareas if t["priority"])
            self.tareas.insert(pos_insercion, tarea)
            if self._seleccionada == indice:
                self._seleccionada = pos_insercion

        self._guardar_tareas()
        self._renderizar_tareas()

    def _eliminar_tarea(self, indice: int):
        self.tareas.pop(indice)
        if self._seleccionada == indice:
            self._seleccionada = None
        elif self._seleccionada is not None and self._seleccionada > indice:
            self._seleccionada -= 1
        self._guardar_tareas()
        self._renderizar_tareas()

    def _alternar_prioridad(self, indice: int):
        tarea = self.tareas[indice]
        tarea["priority"]    = not tarea["priority"]
        tarea["priority_at"] = _ahora() if tarea["priority"] else None
        self.tareas.pop(indice)
        pos_insercion = sum(1 for t in self.tareas if t["priority"])
        self.tareas.insert(pos_insercion, tarea)
        self._seleccionada = pos_insercion
        self._guardar_tareas()
        self._renderizar_tareas()

    def _seleccionar_tarea(self, indice: int):
        anterior = self._seleccionada
        self._seleccionada = None if self._seleccionada == indice else indice
        for idx in (anterior, self._seleccionada):
            if idx is not None and idx < len(self._widgets_fila):
                tarea = self.tareas[idx]
                es_prioritaria = tarea.get("priority", False)
                es_seleccionada = (self._seleccionada == idx)
                if es_seleccionada:
                    fondo = C["task_selected"]
                elif es_prioritaria:
                    fondo = C["task_priority"]
                else:
                    fondo = C["task_bg"]
                try:
                    self._widgets_fila[idx].configure(fg_color=fondo)
                except Exception:
                    pass

    def _al_pulsar_arriba(self, event):
        if not isinstance(event.widget, (ctk.CTkEntry, tk.Entry)):
            self._mover_seleccionada(-1)

    def _al_pulsar_abajo(self, event):
        if not isinstance(event.widget, (ctk.CTkEntry, tk.Entry)):
            self._mover_seleccionada(1)

    def _mover_seleccionada(self, direccion: int):
        if self._seleccionada is None:
            return
        i = self._seleccionada
        j = i + direccion
        if 0 <= j < len(self.tareas):
            ti, tj = self.tareas[i], self.tareas[j]
            if ti.get("priority") == tj.get("priority"):
                self.tareas[i], self.tareas[j] = self.tareas[j], self.tareas[i]
                self._seleccionada = j
                self._guardar_tareas()
                self._renderizar_tareas()

    # ── Menú: cerrar al hacer clic fuera ─────────────────────────────────────

    def _al_clic_global(self, event):
        if self._menu_emergente is None or getattr(self, "_menu_recien_abierto", False):
            return
        menu = self._menu_emergente
        try:
            mx, my = menu.winfo_rootx(), menu.winfo_rooty()
            mw, mh = menu.winfo_width(), menu.winfo_height()
            if not (mx <= event.x_root <= mx + mw and my <= event.y_root <= my + mh):
                try:
                    menu.destroy()
                except Exception:
                    pass
                self._menu_emergente = None
        except Exception:
            try:
                menu.destroy()
            except Exception:
                pass
            self._menu_emergente = None

    # ── Drag & Drop ───────────────────────────────────────────────────────────

    # ── Helpers de Canvas redondeado ─────────────────────────────────────────

    @staticmethod
    def _rect_redondeado(cv, x1, y1, x2, y2, r, fill, outline=""):
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

    def _crear_fantasma(self, indice: int, x_root: int, y_root: int):
        tarea = self.tareas[indice]
        self.update_idletasks()
        ancho_fila, alto_fila = 380, 52
        x_lista = x_root - ancho_fila // 2
        if indice < len(self._widgets_fila):
            try:
                ancho_fila = self._widgets_fila[indice].winfo_width()
                alto_fila  = self._widgets_fila[indice].winfo_height()
                x_lista    = self._lista.winfo_rootx()
            except Exception:
                pass

        y = y_root - alto_fila // 2
        TRANS = "#F0EFF0"   # color clave de transparencia (no existe en nuestra paleta)
        r = 12

        # ── Sombra con esquinas redondeadas ──
        sombra = tk.Toplevel(self)
        sombra.overrideredirect(True)
        sombra.attributes("-topmost", True)
        sombra.configure(bg=TRANS)
        try:
            sombra.wm_attributes("-transparentcolor", TRANS)
            sombra.attributes("-alpha", 0.35)
        except Exception:
            pass
        sombra.geometry(f"{ancho_fila}x{alto_fila}+{x_lista + 5}+{y + 5}")
        scv = tk.Canvas(sombra, width=ancho_fila, height=alto_fila, bg=TRANS, highlightthickness=0)
        scv.pack(fill="both", expand=True)
        self._rect_redondeado(scv, 0, 0, ancho_fila, alto_fila, r, "#222222")

        # ── Ghost principal con esquinas redondeadas ──
        fantasma = tk.Toplevel(self)
        fantasma.overrideredirect(True)
        fantasma.attributes("-topmost", True)
        fantasma.configure(bg=TRANS)
        try:
            fantasma.wm_attributes("-transparentcolor", TRANS)
            fantasma.attributes("-alpha", 0.95)
        except Exception:
            pass
        fantasma.geometry(f"{ancho_fila}x{alto_fila}+{x_lista}+{y}")

        es_prioritaria = tarea.get("priority", False)
        fondo          = C["task_priority"] if es_prioritaria else "#FFFFFF"
        color_texto    = C["text_priority"] if es_prioritaria else C["text"]
        texto_etiqueta = ("⭐  " if es_prioritaria else "") + tarea["text"]

        gcv = tk.Canvas(fantasma, width=ancho_fila, height=alto_fila, bg=TRANS, highlightthickness=0)
        gcv.pack(fill="both", expand=True)
        self._rect_redondeado(gcv, 0, 0, ancho_fila, alto_fila, r, fondo, C["accent"])
        gcv.create_text(16, alto_fila//2, text="≡",           fill=C["drag_handle"],
                        font=("Segoe UI", 15), anchor="w")
        gcv.create_text(36, alto_fila//2, text=texto_etiqueta, fill=color_texto,
                        font=("Segoe UI", 12), anchor="w")

        self._datos_arrastre.update(ghost=fantasma, shadow=sombra,
                                    list_x=x_lista, row_h=alto_fila, row_w=ancho_fila)

    def _iniciar_arrastre(self, event, indice: int):
        self._datos_arrastre = {"index": indice, "target": indice,
                                "current_y": float(event.y_root)}
        if self._seleccionada != indice:
            self._seleccionada = indice
            self._renderizar_tareas()

        self._crear_fantasma(indice, event.x_root, event.y_root)

        if indice < len(self._widgets_fila):
            try:
                self._widgets_fila[indice].configure(fg_color=C["drag_source"])
            except Exception:
                pass

        # Iniciar bucle de movimiento suave
        self._datos_arrastre["loop_id"] = self.after(16, self._bucle_anim_fantasma)

        # Resetear animación
        if self._anim_arrastre.get("after_id"):
            try:
                self.after_cancel(self._anim_arrastre["after_id"])
            except Exception:
                pass
        self._anim_arrastre = {"target": None, "old_target": None,
                               "old_gap": 0, "step": 0, "after_id": None}

        try:
            self.config(cursor="fleur")
        except Exception:
            pass

        self.bind_all("<B1-Motion>",       self._al_arrastrar)
        self.bind_all("<ButtonRelease-1>", self._fin_arrastre_global)

    def _bucle_anim_fantasma(self):
        """Bucle a ~60 fps que mueve el ghost con lerp para eliminar saltos."""
        if not self._datos_arrastre or "ghost" not in self._datos_arrastre:
            return
        try:
            x_root, y_root = self.winfo_pointerxy()
        except Exception:
            self._datos_arrastre["loop_id"] = self.after(16, self._bucle_anim_fantasma)
            return

        # Interpolación suave hacia la posición real del cursor
        LERP = 0.55
        cy = self._datos_arrastre.get("current_y", float(y_root))
        cy = cy + (y_root - cy) * LERP
        self._datos_arrastre["current_y"] = cy

        x_lista = self._datos_arrastre.get("list_x", x_root)
        alto_fila = self._datos_arrastre.get("row_h", 52)
        iy     = int(cy) - alto_fila // 2

        for key, dx, dy in [("ghost", 0, 0), ("shadow", 5, 5)]:
            w = self._datos_arrastre.get(key)
            if w:
                try:
                    w.geometry(f"+{x_lista + dx}+{iy + dy}")
                except Exception:
                    pass

        # Detectar nuevo destino y animar apertura
        nuevo_destino = self._obtener_destino_arrastre(y_root)
        if nuevo_destino != self._datos_arrastre.get("target"):
            self._datos_arrastre["target"] = nuevo_destino
            self._iniciar_anim_hueco(nuevo_destino)

        self._datos_arrastre["loop_id"] = self.after(16, self._bucle_anim_fantasma)

    def _al_arrastrar(self, event):
        # El movimiento del ghost lo gestiona _bucle_anim_fantasma; aquí no hace falta nada.
        pass

    def _iniciar_anim_hueco(self, new_idx: int):
        anim = self._anim_arrastre
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
            if not self._datos_arrastre:
                return
            anim["step"] += 1
            t = min(anim["step"] / STEPS, 1.0)
            # Smoothstep (S-curve)
            t_s = t * t * (3 - 2 * t)

            # Cerrar gap anterior
            o = anim["old_target"]
            if o is not None and o != new_idx and o < len(self._widgets_fila):
                try:
                    self._widgets_fila[o].pack_configure(
                        pady=(int(anim["old_gap"] * (1 - t_s)) + 3, 3))
                except Exception:
                    pass

            # Abrir gap nuevo
            if new_idx < len(self._widgets_fila):
                gap = int(MAX_GAP * t_s)
                anim["old_gap"] = gap   # actualizar para la próxima transición
                try:
                    self._widgets_fila[new_idx].pack_configure(pady=(gap + 3, 3))
                except Exception:
                    pass

            if anim["step"] < STEPS:
                anim["after_id"] = self.after(DELAY, step)
            else:
                anim["after_id"] = None

        step()

    def _fin_arrastre_global(self, event):
        self.unbind_all("<B1-Motion>")
        self.unbind_all("<ButtonRelease-1>")
        self._fin_arrastre(event)

    def _fin_arrastre(self, event):
        if not self._datos_arrastre:
            return

        # Cancelar bucle de movimiento del ghost
        id_bucle = self._datos_arrastre.get("loop_id")
        if id_bucle:
            try:
                self.after_cancel(id_bucle)
            except Exception:
                pass

        # Cancelar animación pendiente
        if self._anim_arrastre.get("after_id"):
            try:
                self.after_cancel(self._anim_arrastre["after_id"])
            except Exception:
                pass
        self._anim_arrastre = {"target": None, "old_target": None,
                               "old_gap": 0, "step": 0, "after_id": None}

        for key in ("ghost", "shadow"):
            w = self._datos_arrastre.get(key)
            if w:
                try:
                    w.destroy()
                except Exception:
                    pass
        try:
            self.config(cursor="")
        except Exception:
            pass

        origen  = self._datos_arrastre.get("index")
        destino = self._datos_arrastre.get("target", origen)
        if origen is not None and origen != destino and 0 <= destino < len(self.tareas):
            tarea      = self.tareas[origen]
            tarea_dest = self.tareas[destino]
            if tarea.get("priority") == tarea_dest.get("priority"):
                self.tareas.pop(origen)
                pos_insercion = destino if destino < origen else destino - 1
                pos_insercion = max(0, min(pos_insercion, len(self.tareas)))
                self.tareas.insert(pos_insercion, tarea)
                self._seleccionada = pos_insercion
                self._guardar_tareas()
        self._datos_arrastre = {}
        self._renderizar_tareas()

    def _obtener_destino_arrastre(self, y_root: int) -> int:
        if not self._widgets_fila:
            return self._datos_arrastre.get("index", 0)
        for i, w in enumerate(self._widgets_fila):
            try:
                if y_root < w.winfo_rooty() + w.winfo_height() // 2:
                    return i
            except Exception:
                pass
        return len(self._widgets_fila) - 1

    # ── Renderizado ───────────────────────────────────────────────────────────

    def _renderizar_tareas(self):
        for w in self._lista.winfo_children():
            w.destroy()
        self._widgets_fila = []

        if not self.tareas:
            ctk.CTkLabel(
                self._lista,
                text="Sin tareas por el momento.\n¡Añade una arriba!",
                font=ctk.CTkFont(size=14),
                text_color=C["text_muted"]
            ).pack(pady=50)
        else:
            for i, tarea in enumerate(self.tareas):
                self._fila_tarea(i, tarea)

        self._actualizar_contador()

    def _fila_tarea(self, indice: int, tarea: dict):
        es_prioritaria = tarea.get("priority", False)
        es_seleccionada = (self._seleccionada == indice)

        if es_seleccionada:
            fondo = C["task_selected"]
        elif es_prioritaria:
            fondo = C["task_priority"]
        else:
            fondo = C["task_bg"]

        fila = ctk.CTkFrame(self._lista, fg_color=fondo, corner_radius=14)
        fila.pack(fill="x", pady=3, padx=2)
        self._widgets_fila.append(fila)
        fila.bind("<Button-1>", lambda e, i=indice: self._seleccionar_tarea(i))

        # Asa de arrastre (≡)
        asa = ctk.CTkButton(
            fila, text="≡", width=22, height=30, corner_radius=6,
            fg_color="transparent", hover_color=C["task_hover"],
            text_color=C["drag_handle"], font=ctk.CTkFont(size=16),
            command=lambda: None
        )
        asa.pack(side="left", padx=(6, 0), pady=10)
        asa.bind("<ButtonPress-1>", lambda e, i=indice: self._iniciar_arrastre(e, i))

        # Checkbox
        var = ctk.BooleanVar(value=tarea["done"])
        ctk.CTkCheckBox(
            fila, text="", variable=var,
            width=24, height=24, checkbox_width=22, checkbox_height=22,
            corner_radius=6,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            border_color=C["border"],
            command=lambda i=indice, v=var: self._alternar_tarea(i, v)
        ).pack(side="left", padx=(4, 8), pady=10)

        # Botones de la derecha (deben empaquetarse ANTES que el frame expandible)
        ctk.CTkButton(
            fila, text="✕", width=30, height=30, corner_radius=8,
            fg_color="transparent", hover_color=C["del_hover"],
            text_color=C["text_muted"], font=ctk.CTkFont(size=12),
            command=lambda i=indice: self._eliminar_tarea(i)
        ).pack(side="right", padx=(0, 4))

        if not tarea["done"]:
            texto_estrella = "★" if es_prioritaria else "☆"
            color_estrella = "#E67E22" if es_prioritaria else C["text_muted"]
            ctk.CTkButton(
                fila, text=texto_estrella, width=30, height=30, corner_radius=8,
                fg_color="transparent", hover_color=C["task_hover"],
                text_color=color_estrella, font=ctk.CTkFont(size=16),
                command=lambda i=indice: self._alternar_prioridad(i)
            ).pack(side="right", padx=(0, 2))

        # Columna central
        info = ctk.CTkFrame(fila, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=6, padx=(0, 4))
        info.bind("<Button-1>", lambda e, i=indice: self._seleccionar_tarea(i))

        color_texto    = (C["text_priority"] if es_prioritaria
                          else C["text_muted"] if tarea["done"]
                          else C["text"])
        texto_etiqueta = ("⭐ " if es_prioritaria else "") + tarea["text"]

        ctk.CTkLabel(
            info, text=texto_etiqueta,
            font=ctk.CTkFont(size=14, overstrike=tarea["done"]),
            text_color=color_texto, anchor="w"
        ).pack(fill="x")

        creada   = tarea.get("created_at", "")
        hecha_el = tarea.get("done_at", "")
        if creada:
            marca_tiempo = f"🕐 Creada: {creada}"
            if hecha_el:
                marca_tiempo += f"   ✅ Hecha: {hecha_el}"
            ctk.CTkLabel(
                info, text=marca_tiempo,
                font=ctk.CTkFont(size=10),
                text_color=C["text_muted"], anchor="w"
            ).pack(fill="x", pady=(1, 0))

    def _actualizar_contador(self):
        total      = len(self.tareas)
        hechas     = sum(1 for t in self.tareas if t["done"])
        prioritarias = sum(1 for t in self.tareas if t.get("priority"))
        if total:
            texto = f"{hechas} de {total} completada{'s' if total != 1 else ''}"
            if prioritarias:
                texto += f"  ·  {prioritarias} prioritaria{'s' if prioritarias != 1 else ''}"
        else:
            texto = ""
        self._contador.configure(text=texto)

    # ── Barra de menús nativa ─────────────────────────────────────────────────

    def _construir_barra_menus(self):
        barra_menus = tk.Menu(self)

        if sys.platform == "darwin":
            # ── macOS: menú de aplicación estándar ──
            menu_app = tk.Menu(barra_menus, name="apple", tearoff=False)
            barra_menus.add_cascade(label="MisTareas", menu=menu_app)
            menu_app.add_command(label="Acerca de MisTareas", command=self._mostrar_acerca_de)
            menu_app.add_separator()
            menu_app.add_command(label="Salir", command=self._salir, accelerator="Cmd+Q")

            menu_tareas = tk.Menu(barra_menus, tearoff=False)
            barra_menus.add_cascade(label="Tareas", menu=menu_tareas)
            menu_tareas.add_command(label="Borrar completadas", command=self._borrar_completadas)
            menu_tareas.add_command(label="Borrar todas",       command=self._borrar_todas)

            menu_ayuda = tk.Menu(barra_menus, tearoff=False)
            barra_menus.add_cascade(label="Ayuda", menu=menu_ayuda)
            menu_ayuda.add_command(label="Ayuda de MisTareas", command=self._mostrar_ayuda)
            menu_ayuda.add_command(label="Licencia",            command=self._mostrar_licencia)

        else:
            # ── Windows / Linux ──
            menu_archivo = tk.Menu(barra_menus, tearoff=False)
            barra_menus.add_cascade(label="Archivo", menu=menu_archivo)
            menu_archivo.add_command(label="Salir", command=self._salir, accelerator="Ctrl+Q")

            menu_tareas = tk.Menu(barra_menus, tearoff=False)
            barra_menus.add_cascade(label="Tareas", menu=menu_tareas)
            menu_tareas.add_command(label="Borrar completadas", command=self._borrar_completadas)
            menu_tareas.add_command(label="Borrar todas",       command=self._borrar_todas)

            menu_ayuda = tk.Menu(barra_menus, tearoff=False)
            barra_menus.add_cascade(label="Ayuda", menu=menu_ayuda)
            menu_ayuda.add_command(label="Ayuda de MisTareas", command=self._mostrar_ayuda)
            menu_ayuda.add_separator()
            menu_ayuda.add_command(label="Acerca de MisTareas", command=self._mostrar_acerca_de)
            menu_ayuda.add_command(label="Licencia",            command=self._mostrar_licencia)

        self.config(menu=barra_menus)

    # ── Menú contextual (botón ⋮) ─────────────────────────────────────────────

    def _mostrar_menu(self):
        if self._menu_emergente is not None:
            try:
                self._menu_emergente.destroy()
            except Exception:
                pass
            self._menu_emergente = None
            return

        menu = ctk.CTkToplevel(self)
        menu.title("")
        menu.geometry("220x110")
        menu.resizable(False, False)
        menu.configure(fg_color=C["bg"])
        menu.attributes("-topmost", True)
        menu.overrideredirect(True)
        self._menu_emergente = menu
        self._menu_recien_abierto = True
        menu.after(200, lambda: setattr(self, "_menu_recien_abierto", False))

        self.update_idletasks()
        bx = self._btn_menu.winfo_rootx()
        by = self._btn_menu.winfo_rooty() + self._btn_menu.winfo_height() + 4
        menu.geometry(f"+{bx - 180}+{by}")

        def close_menu():
            if self._menu_emergente is not None:
                try:
                    self._menu_emergente.destroy()
                except Exception:
                    pass
                self._menu_emergente = None

        ctk.CTkFrame(menu, fg_color=C["border"], height=1).pack(fill="x", pady=(0, 4))

        for label, cmd in [
            ("🗑   Borrar completadas", self._borrar_completadas),
            ("🗑   Borrar todas",        self._borrar_todas),
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

    def _ventana_info(self, title: str, w: int, h: int):
        ventana = ctk.CTkToplevel(self)
        ventana.title(title)
        ventana.geometry(f"{w}x{h}")
        ventana.resizable(False, False)
        ventana.configure(fg_color=C["bg"])
        ventana.attributes("-topmost", True)
        ventana.grab_set()
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        ventana.geometry(f"+{x}+{y}")
        return ventana

    def _mostrar_acerca_de(self):
        ventana = self._ventana_info("Acerca de MisTareas", 320, 200)
        ctk.CTkLabel(ventana, text="✓  MisTareas",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=C["accent"]).pack(pady=(28, 4))
        ctk.CTkLabel(ventana, text="Creado por Fabián Viera",
                     font=ctk.CTkFont(size=13), text_color=C["text"]).pack()
        ctk.CTkLabel(ventana, text="2026  ·  Versión beta 0.2  ·  Para uso no comercial",
                     font=ctk.CTkFont(size=12), text_color=C["text_muted"]).pack(pady=(2, 20))
        ctk.CTkButton(ventana, text="Cerrar", width=100, height=34, corner_radius=10,
                      fg_color=C["accent"], hover_color=C["accent_hover"],
                      text_color="white", command=ventana.destroy).pack()

    def _mostrar_licencia(self):
        ventana = self._ventana_info("Licencia", 560, 440)
        ctk.CTkLabel(ventana, text="Licencia — GNU General Public License v3",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["accent"]).pack(pady=(16, 8), padx=16)

        box = ctk.CTkTextbox(ventana, fg_color=C["input_bg"], border_color=C["border"],
                             text_color=C["text"], font=ctk.CTkFont(size=11),
                             corner_radius=10, border_width=1, wrap="word")
        box.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        if getattr(sys, 'frozen', False):
            ruta_licencia = os.path.join(sys._MEIPASS, "LICENSE")
        else:
            ruta_licencia = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LICENSE")

        if os.path.exists(ruta_licencia):
            with open(ruta_licencia, "r", encoding="utf-8") as f:
                box.insert("end", f.read())
        else:
            box.insert("end", "GNU General Public License v3\n\nhttps://www.gnu.org/licenses/gpl-3.0.html")
        box.configure(state="disabled")
        ctk.CTkButton(ventana, text="Cerrar", width=100, height=34, corner_radius=10,
                      fg_color=C["accent"], hover_color=C["accent_hover"],
                      text_color="white", command=ventana.destroy).pack(pady=(0, 16))

    def _mostrar_ayuda(self):
        ventana = self._ventana_info("Ayuda — MisTareas", 520, 620)

        # ── Cabecera ──
        cabecera = ctk.CTkFrame(ventana, fg_color=C["accent"], corner_radius=0, height=68)
        cabecera.pack(fill="x")
        cabecera.pack_propagate(False)
        ctk.CTkLabel(
            cabecera, text="✓  MisTareas  —  Guía rápida",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        ).pack(expand=True)

        # ── Área desplazable ──
        desplazable = ctk.CTkScrollableFrame(
            ventana, fg_color=C["bg"],
            scrollbar_button_color=C["scroll"],
            scrollbar_button_hover_color=C["accent"]
        )
        desplazable.pack(fill="both", expand=True, padx=0, pady=0)

        def seccion(icon, title, color, items):
            """Dibuja una sección con cabecera coloreada y lista de items."""
            # Cabecera de sección
            cab_seccion = ctk.CTkFrame(desplazable, fg_color=color, corner_radius=10, height=36)
            cab_seccion.pack(fill="x", padx=14, pady=(12, 0))
            cab_seccion.pack_propagate(False)
            ctk.CTkLabel(
                cab_seccion, text=f"  {icon}  {title}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="white", anchor="w"
            ).pack(fill="x", padx=8, expand=True)

            # Tarjeta de contenido
            tarjeta = ctk.CTkFrame(desplazable, fg_color=C["input_bg"],
                                   corner_radius=10, border_width=1,
                                   border_color=C["border"])
            tarjeta.pack(fill="x", padx=14, pady=(0, 2))

            for bullet, texto in items:
                fila = ctk.CTkFrame(tarjeta, fg_color="transparent")
                fila.pack(fill="x", padx=12, pady=(6, 0))
                ctk.CTkLabel(
                    fila, text=bullet,
                    font=ctk.CTkFont(size=14),
                    text_color=color, width=24, anchor="w"
                ).pack(side="left", padx=(0, 6))
                ctk.CTkLabel(
                    fila, text=texto,
                    font=ctk.CTkFont(size=12),
                    text_color=C["text"], anchor="w", wraplength=380, justify="left"
                ).pack(side="left", fill="x", expand=True)
            ctk.CTkFrame(tarjeta, fg_color="transparent", height=6).pack()

        seccion("📝", "Crear una tarea", "#5B9BD5", [
            ("+",     "Escribe el texto en el campo superior."),
            ("↵",     "Pulsa [+] o la tecla Enter para añadirla."),
        ])

        seccion("✅", "Completar y descompletar", "#27AE60", [
            ("☑",     "Haz clic en el checkbox (☐) para marcarla como hecha. El texto aparecerá tachado."),
            ("↩",     "Vuelve a hacer clic en el checkbox para desmarcarla."),
            ("🕐",    "Se registra automáticamente la fecha y hora de creación y de finalización."),
        ])

        seccion("⭐", "Tareas prioritarias", "#E67E22", [
            ("☆",     "Pulsa la estrella (☆) en el lado derecho de la tarea para marcarla como prioritaria."),
            ("⬆",     "Las tareas prioritarias suben automáticamente al inicio de la lista con texto en rojo."),
            ("★",     "Pulsa [★] de nuevo para quitar la prioridad."),
            ("ℹ",     "Al marcar una tarea prioritaria como completada, pierde la prioridad automáticamente."),
        ])

        seccion("↕", "Ordenar tareas", "#8E44AD", [
            ("≡",     "Arrastra el icono [≡] (izquierda de la fila) para reordenar con el ratón."),
            ("↑↓",    "Selecciona una tarea haciendo clic en ella (se resalta en azul) y usa ↑ ↓ para moverla con el teclado."),
            ("⚠",     "Solo puedes mover tareas dentro de su sección: prioritarias con prioritarias, normales con normales."),
        ])

        seccion("🗑", "Eliminar tareas", "#C0392B", [
            ("✕",     "Pulsa [✕] en la fila para eliminar esa tarea."),
            ("⋮",     "Menú [⋮] o menú Tareas → «Borrar completadas» para limpiar las tareas hechas."),
            ("⚠",     "Menú Tareas → «Borrar todas» elimina toda la lista sin posibilidad de recuperación."),
        ])

        seccion("📌", "Fijar la ventana", "#2980B9", [
            ("📌",    "El botón [📌] de la cabecera mantiene la ventana siempre encima de las demás apps."),
            ("📍",    "Al activarse el botón cambia a [📍] con fondo azul. Pulsa de nuevo para desactivarlo."),
        ])

        ctk.CTkFrame(desplazable, fg_color="transparent", height=8).pack()

        # ── Pie ──
        pie = ctk.CTkFrame(ventana, fg_color=C["header"], corner_radius=0, height=52)
        pie.pack(fill="x", side="bottom")
        pie.pack_propagate(False)
        ctk.CTkLabel(
            pie, text="Fabián Viera · 2026 · Versión beta 0.2",
            font=ctk.CTkFont(size=11), text_color=C["text_muted"]
        ).pack(side="left", padx=16, expand=True)
        ctk.CTkButton(
            pie, text="Cerrar", width=90, height=34, corner_radius=10,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color="white", font=ctk.CTkFont(size=13),
            command=ventana.destroy
        ).pack(side="right", padx=16)

    # ── Acciones del menú Tareas ──────────────────────────────────────────────

    def _borrar_completadas(self):
        cantidad = sum(1 for t in self.tareas if t["done"])
        if cantidad == 0:
            messagebox.showinfo("MisTareas", "No hay tareas completadas.")
            return
        if messagebox.askyesno("Confirmar", f"¿Borrar {cantidad} tarea(s) completada(s)?"):
            self.tareas    = [t for t in self.tareas if not t["done"]]
            self._seleccionada = None
            self._guardar_tareas()
            self._renderizar_tareas()

    def _borrar_todas(self):
        if not self.tareas:
            messagebox.showinfo("MisTareas", "No hay tareas.")
            return
        if messagebox.askyesno("Confirmar", f"¿Borrar las {len(self.tareas)} tarea(s)?"):
            self.tareas    = []
            self._seleccionada = None
            self._guardar_tareas()
            self._renderizar_tareas()

    def _salir(self):
        self._guardar_tareas()
        self.destroy()

    # ── Siempre visible ───────────────────────────────────────────────────────

    def _alternar_pin(self):
        self._siempre_visible = not self._siempre_visible
        self.attributes("-topmost", self._siempre_visible)
        self._actualizar_btn_pin()

    def _actualizar_btn_pin(self):
        if self._siempre_visible:
            self._btn_pin.configure(text="📍", fg_color=C["accent"], text_color="white")
        else:
            self._btn_pin.configure(text="📌", fg_color="transparent", text_color=C["text_muted"])

    # ── Persistencia ──────────────────────────────────────────────────────────

    def _guardar_tareas(self):
        temporal = ARCHIVO_TAREAS + ".tmp"
        try:
            with open(temporal, "w", encoding="utf-8") as f:
                json.dump(self.tareas, f, ensure_ascii=False, indent=2)
            os.replace(temporal, ARCHIVO_TAREAS)
        except Exception as e:
            try:
                os.remove(temporal)
            except Exception:
                pass
            messagebox.showerror("MisTareas", f"Error al guardar las tareas:\n{e}")

    def _cargar_tareas(self):
        if os.path.exists(ARCHIVO_TAREAS):
            try:
                with open(ARCHIVO_TAREAS, "r", encoding="utf-8") as f:
                    self.tareas = json.load(f)
                for t in self.tareas:
                    t.setdefault("priority",    False)
                    t.setdefault("priority_at", None)
            except Exception as e:
                self.tareas = []
                messagebox.showerror(
                    "MisTareas",
                    f"No se pudo leer el archivo de tareas.\n"
                    f"Se empezará con la lista vacía.\n\nDetalle: {e}"
                )
        else:
            self.tareas = []


# ── Entrada ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = MisTareasApp()
    app.mainloop()
