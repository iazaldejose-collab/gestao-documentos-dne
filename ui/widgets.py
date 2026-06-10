"""
widgets.py — Componentes reutilizáveis para o Sistema de Gestão de Documentos DNE/MIREME
"""
import calendar
import tkinter as tk
from datetime import datetime, date
import customtkinter as ctk


# ─────────────────────────────────────────────────────────────────────────────
#  Calendário popup
# ─────────────────────────────────────────────────────────────────────────────

class CalendarDialog(ctk.CTkToplevel):
    """Popup de calendário para selecção de data."""

    MESES_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    DIAS_PT  = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    def __init__(self, parent, initial_date=None, callback=None):
        super().__init__(parent)
        self.callback  = callback
        self.overrideredirect(True)
        self.resizable(False, False)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        self.focus_set()

        today = date.today()
        if initial_date:
            try:
                d = datetime.strptime(initial_date, "%d/%m/%Y").date()
                self._year  = d.year
                self._month = d.month
            except Exception:
                self._year  = today.year
                self._month = today.month
        else:
            self._year  = today.year
            self._month = today.month

        self._build()
        self._place_near_parent(parent)

    def _build(self):
        # ── Cabeçalho: navegação mês/ano ─────────────────────────────────────
        hdr = ctk.CTkFrame(self, corner_radius=0, fg_color=("#1F4E79", "#0d2b4e"))
        hdr.pack(fill="x")

        ctk.CTkButton(hdr, text="◀", width=30, height=28,
                      fg_color="transparent", hover_color="#2c6fad",
                      command=self._prev_month).pack(side="left", padx=4, pady=4)

        self._lbl_mes = ctk.CTkLabel(hdr, text="", font=ctk.CTkFont(size=13, weight="bold"),
                                     text_color="white", width=160)
        self._lbl_mes.pack(side="left", expand=True)

        ctk.CTkButton(hdr, text="▶", width=30, height=28,
                      fg_color="transparent", hover_color="#2c6fad",
                      command=self._next_month).pack(side="right", padx=4, pady=4)

        # ── Dias da semana ────────────────────────────────────────────────────
        days_frame = ctk.CTkFrame(self, fg_color=("gray85", "gray25"), corner_radius=0)
        days_frame.pack(fill="x")
        for i, d in enumerate(self.DIAS_PT):
            color = "#c0392b" if i >= 5 else ("#444", "#ccc")
            ctk.CTkLabel(days_frame, text=d, width=36, font=ctk.CTkFont(size=10),
                         text_color=color).grid(row=0, column=i, padx=1, pady=2)

        # ── Grid de dias ──────────────────────────────────────────────────────
        self._grid_frame = ctk.CTkFrame(self, corner_radius=0)
        self._grid_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # ── Botão Hoje ────────────────────────────────────────────────────────
        ctk.CTkButton(self, text="Hoje", height=26, fg_color="#27ae60",
                      command=self._select_today).pack(fill="x", padx=4, pady=(0, 4))

        self._draw_calendar()

    def _draw_calendar(self):
        for w in self._grid_frame.winfo_children():
            w.destroy()

        self._lbl_mes.configure(
            text=f"{self.MESES_PT[self._month]}  {self._year}")

        today = date.today()
        cal   = calendar.monthcalendar(self._year, self._month)

        for r, week in enumerate(cal):
            for c, day in enumerate(week):
                if day == 0:
                    ctk.CTkLabel(self._grid_frame, text="", width=34).grid(
                        row=r, column=c, padx=1, pady=1)
                    continue

                is_today   = (day == today.day and self._month == today.month
                              and self._year == today.year)
                is_weekend = c >= 5

                fg = "#1F4E79" if is_today else ("gray80" if is_weekend else "transparent")
                tc = "white"   if is_today else ("#c0392b" if is_weekend else None)

                btn = ctk.CTkButton(
                    self._grid_frame, text=str(day), width=34, height=28,
                    fg_color=fg, hover_color="#2c6fad",
                    text_color=tc,
                    font=ctk.CTkFont(weight="bold" if is_today else "normal"),
                    command=lambda d=day: self._select_day(d)
                )
                btn.grid(row=r, column=c, padx=1, pady=1)

    def _prev_month(self):
        if self._month == 1:
            self._month = 12; self._year -= 1
        else:
            self._month -= 1
        self._draw_calendar()

    def _next_month(self):
        if self._month == 12:
            self._month = 1; self._year += 1
        else:
            self._month += 1
        self._draw_calendar()

    def _select_day(self, day):
        selected = f"{day:02d}/{self._month:02d}/{self._year}"
        if self.callback:
            self.callback(selected)
        self.destroy()

    def _select_today(self):
        t = date.today()
        self._select_day(t.day)

    def _place_near_parent(self, parent):
        try:
            self.update_idletasks()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty() + parent.winfo_height()
            w  = self.winfo_reqwidth()
            h  = self.winfo_reqheight()
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x  = min(px, sw - w - 10)
            y  = min(py, sh - h - 10)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  Campo de data com botão calendário
# ─────────────────────────────────────────────────────────────────────────────

class DateEntry(ctk.CTkFrame):
    """Entry de data DD/MM/AAAA com botão 📅 que abre o calendário."""

    def __init__(self, parent, textvariable=None, width=160, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._var = textvariable or tk.StringVar()

        self._entry = ctk.CTkEntry(self, textvariable=self._var, width=width,
                                   placeholder_text="DD/MM/AAAA")
        self._entry.pack(side="left")

        ctk.CTkButton(self, text="📅", width=32, height=28,
                      fg_color=("gray75", "gray30"),
                      hover_color="#2c6fad",
                      command=self._open_calendar).pack(side="left", padx=(2, 0))

    def _open_calendar(self):
        CalendarDialog(self._entry, initial_date=self._var.get(),
                       callback=self._var.set)

    def get(self):
        return self._var.get()

    def set(self, value):
        self._var.set(value)


# ─────────────────────────────────────────────────────────────────────────────
#  Ordenação de colunas em Treeview (clique no cabeçalho)
# ─────────────────────────────────────────────────────────────────────────────

def enable_sorting(tree, columns=None):
    """Activa a ordenação por clique no cabeçalho de um ttk.Treeview.

    Ao clicar num cabeçalho, a tabela é ordenada por essa coluna; um novo
    clique inverte a ordem (ascendente/descendente). Detecta automaticamente
    números, datas (DD/MM/AAAA) e texto para uma ordenação correcta.

    columns: lista opcional de chaves de coluna a tornar ordenáveis
             (por omissão, todas as colunas do Treeview).
    """
    cols = list(columns) if columns else list(tree["columns"])
    original_text = {c: tree.heading(c, "text") for c in cols}
    state = {"col": None, "reverse": False}

    def _sort_key(value):
        v = (value or "").strip()
        if not v:
            return (3, "")
        cleaned = v.replace("%", "").replace(" ", "")
        try:
            return (0, float(cleaned.replace(",", ".")))
        except ValueError:
            pass
        try:
            return (1, datetime.strptime(v, "%d/%m/%Y"))
        except ValueError:
            pass
        return (2, v.lower())

    def _sort_by(col):
        items = [(tree.set(k, col), k) for k in tree.get_children("")]
        reverse = (state["col"] == col and not state["reverse"])
        items.sort(key=lambda t: _sort_key(t[0]), reverse=reverse)
        for index, (_, k) in enumerate(items):
            tree.move(k, "", index)
        state["col"] = col
        state["reverse"] = reverse
        arrow = " ▼" if reverse else " ▲"
        for c in cols:
            tree.heading(c, text=original_text[c] + (arrow if c == col else ""))

    for c in cols:
        tree.heading(c, command=lambda c=c: _sort_by(c))


# ─────────────────────────────────────────────────────────────────────────────
#  Indicador de "a processar..." para operações longas
# ─────────────────────────────────────────────────────────────────────────────

class BusyDialog(ctk.CTkToplevel):
    """Pequena janela flutuante com indicador de progresso indeterminado,
    a apresentar durante operações que demoram (importações, exportações,
    geração de relatórios, etc.) para o utilizador saber que o sistema
    está a trabalhar.

    Uso:
        busy = BusyDialog(self, "A importar dados...")
        try:
            ... operação longa ...
        finally:
            busy.fechar()
    """

    def __init__(self, parent, mensagem="A processar..."):
        super().__init__(parent)
        self.overrideredirect(True)
        self.resizable(False, False)
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        frame = ctk.CTkFrame(self, corner_radius=10, border_width=1)
        frame.pack(padx=2, pady=2)
        ctk.CTkLabel(frame, text=f"⏳  {mensagem}",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(padx=28, pady=(18, 8))
        self._bar = ctk.CTkProgressBar(frame, mode="indeterminate", width=220)
        self._bar.pack(padx=28, pady=(0, 18))
        self._bar.start()

        self._place_center(parent)
        self.update_idletasks()
        self.update()

    def _place_center(self, parent):
        try:
            self.update_idletasks()
            top = parent.winfo_toplevel()
            px, py = top.winfo_rootx(), top.winfo_rooty()
            pw, ph = top.winfo_width(), top.winfo_height()
            w, h = self.winfo_reqwidth(), self.winfo_reqheight()
            x = px + max((pw - w) // 2, 0)
            y = py + max((ph - h) // 2, 0)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def fechar(self):
        try:
            self._bar.stop()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
