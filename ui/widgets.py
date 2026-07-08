"""
widgets.py — Componentes reutilizáveis para o Sistema de Gestão de Documentos DNE/MIREME
"""
import calendar
import os
import subprocess
import tempfile
import tkinter as tk
from tkinter import messagebox
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
#  Menu de contexto (botão direito): Cortar / Copiar / Colar / Seleccionar Tudo
# ─────────────────────────────────────────────────────────────────────────────

def setup_context_menu(root):
    """Activa o menu de contexto (botão direito do rato) com as opções
    Cortar, Copiar, Colar e Seleccionar Tudo em todos os campos de texto
    (CTkEntry, CTkTextbox e respectivos campos internos) da aplicação.

    Deve ser chamado uma única vez, com a janela principal (CTk) como
    argumento — a ligação aplica-se automaticamente a todos os campos
    existentes e futuros, por se basear em bind_class.
    """

    def _show_menu(event):
        widget = event.widget
        widget.focus_set()
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Cortar", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copiar", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Colar", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        if isinstance(widget, tk.Text):
            menu.add_command(label="Seleccionar Tudo",
                             command=lambda: widget.tag_add("sel", "1.0", "end"))
        else:
            menu.add_command(label="Seleccionar Tudo",
                             command=lambda: (widget.select_range(0, "end"), widget.icursor("end")))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    root.bind_class("Entry", "<Button-3>", _show_menu)
    root.bind_class("Text", "<Button-3>", _show_menu)


# ─────────────────────────────────────────────────────────────────────────────
#  Aviso de alterações não guardadas ao fechar um formulário
# ─────────────────────────────────────────────────────────────────────────────

def _form_snapshot(form):
    """Devolve um dicionário com os valores actuais de todos os campos do
    formulário (form._vars e quaisquer CTkTextbox), para comparação."""
    snap = {k: v.get() for k, v in getattr(form, '_vars', {}).items()}
    for name, val in vars(form).items():
        if isinstance(val, ctk.CTkTextbox):
            snap[name] = val.get("1.0", "end")
    return snap


def enable_unsaved_changes_guard(form):
    """Avisa o utilizador se tentar fechar o formulário (botão X) com
    alterações não guardadas. Deve ser chamado no fim do __init__, depois
    do formulário estar totalmente construído e os dados carregados."""
    form._snapshot = _form_snapshot(form)

    def _on_close():
        if _form_snapshot(form) == form._snapshot:
            form.destroy()
            return
        if messagebox.askyesno(
                "Alterações não guardadas",
                "Existem alterações não guardadas. Deseja fechar sem guardar?",
                parent=form):
            form.destroy()

    form.protocol("WM_DELETE_WINDOW", _on_close)


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


def enable_mousewheel(tree):
    """Permite rolar verticalmente um ttk.Treeview com a roda do rato.

    Mesmo sem foco de teclado, o Treeview passa a responder à roda do rato
    sempre que o cursor está sobre a tabela (Windows/macOS via <MouseWheel>,
    Linux via <Button-4>/<Button-5>). Funciona com Shift premido para rolar
    horizontalmente.
    """
    def _on_wheel(event):
        # Windows: event.delta múltiplo de 120; macOS: valores pequenos.
        if event.delta:
            step = -1 if event.delta > 0 else 1
            if step and abs(event.delta) >= 120:
                step *= abs(event.delta) // 120
        else:
            step = -1 if getattr(event, "num", 5) == 4 else 1
        if getattr(event, "state", 0) & 0x0001:  # Shift → horizontal
            tree.xview_scroll(step, "units")
        else:
            tree.yview_scroll(step, "units")
        return "break"

    tree.bind("<MouseWheel>", _on_wheel)        # Windows / macOS
    tree.bind("<Shift-MouseWheel>", _on_wheel)
    tree.bind("<Button-4>", _on_wheel)          # Linux scroll up
    tree.bind("<Button-5>", _on_wheel)          # Linux scroll down


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


# ─────────────────────────────────────────────────────────────────────────────
#  Impressão com selecção de impressora de rede
# ─────────────────────────────────────────────────────────────────────────────

def _listar_impressoras():
    """Devolve lista de impressoras instaladas (locais e de rede) via PowerShell."""
    try:
        r = subprocess.run(
            ["powershell", "-Command",
             "Get-Printer | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=8,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return [p.strip() for p in r.stdout.strip().splitlines() if p.strip()]
    except Exception:
        return []


def _imprimir_em_impressora(ficheiro, impressora):
    """Envia o ficheiro .txt para a impressora especificada via notepad /pt."""
    try:
        subprocess.Popen(
            ["notepad.exe", "/pt", ficheiro, impressora],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False


class PrinterDialog(ctk.CTkToplevel):
    """Dialog para seleccionar uma impressora (local ou de rede) e imprimir."""

    def __init__(self, parent, ficheiro):
        super().__init__(parent)
        self.title("🖨️ Seleccionar Impressora")
        self.geometry("440x380")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()

        self.ficheiro = ficheiro
        self._build()
        self._carregar_impressoras()

    def _build(self):
        ctk.CTkLabel(self, text="🖨️  Seleccionar Impressora",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(14, 2))
        ctk.CTkLabel(self, text="Escolha a impressora para enviar o documento:",
                     font=ctk.CTkFont(size=11), text_color="gray").pack(pady=(0, 6))

        list_frame = ctk.CTkFrame(self, corner_radius=6)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        sb = tk.Scrollbar(list_frame, orient="vertical")
        self._lb = tk.Listbox(list_frame, yscrollcommand=sb.set,
                              font=('Segoe UI', 11), relief='flat',
                              selectmode="browse", activestyle='dotbox',
                              bg='#2b2b2b', fg='white',
                              selectbackground='#1F4E79', selectforeground='white',
                              borderwidth=0, highlightthickness=0)
        sb.config(command=self._lb.yview)
        self._lb.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        sb.pack(side="right", fill="y", pady=6, padx=(0, 4))
        self._lb.bind("<Double-1>", lambda e: self._imprimir())

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=6)
        ctk.CTkButton(btn_frame, text="🖨️ Imprimir", width=120,
                      command=self._imprimir, fg_color="#1F4E79").pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="🔄 Actualizar", width=110,
                      command=self._carregar_impressoras, fg_color="#27ae60").pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="❌ Cancelar", width=100,
                      command=self.destroy, fg_color="gray50").pack(side="left", padx=6)

        self._status = ctk.CTkLabel(self, text="",
                                    font=ctk.CTkFont(size=10), text_color="gray")
        self._status.pack(pady=(0, 8))

    def _carregar_impressoras(self):
        self._lb.delete(0, "end")
        self._status.configure(text="A carregar impressoras...", text_color="gray")
        self.update()
        impressoras = _listar_impressoras()
        if impressoras:
            for p in impressoras:
                self._lb.insert("end", p)
            self._lb.selection_set(0)
            self._status.configure(text=f"{len(impressoras)} impressora(s) encontrada(s).")
        else:
            self._status.configure(
                text="Nenhuma impressora encontrada.", text_color="orange")

    def _imprimir(self):
        sel = self._lb.curselection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione uma impressora.", parent=self)
            return
        impressora = self._lb.get(sel[0])
        ok = _imprimir_em_impressora(self.ficheiro, impressora)
        if ok:
            messagebox.showinfo("Enviado para impressão",
                                f"Documento enviado para:\n{impressora}", parent=self)
            self.destroy()
        else:
            messagebox.showerror("Erro de impressão",
                                 f"Não foi possível imprimir em:\n{impressora}\n\n"
                                 "Verifique se a impressora está ligada e acessível.",
                                 parent=self)


def imprimir_com_dialogo(parent, conteudo_txt):
    """Escreve conteúdo para ficheiro temporário e abre o diálogo de impressora."""
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                      delete=False, encoding='utf-8')
    tmp.write(conteudo_txt)
    tmp.close()
    PrinterDialog(parent, tmp.name)


# ─────────────────────────────────────────────────────────────────────────────
#  Autocomplete em campos de texto
# ─────────────────────────────────────────────────────────────────────────────

def attach_autocomplete(entry_widget, textvariable, get_suggestions, on_select=None):
    """Liga um dropdown de sugestões a um CTkEntry.

    Mostra valores previamente introduzidos à medida que o utilizador digita.
    Navega com ↓/↑, selecciona com clique ou Enter, fecha com Escape.

    entry_widget  : CTkEntry ao qual ligar o autocomplete
    textvariable  : tk.StringVar associado ao entry
    get_suggestions: callable() → list[str] com todos os valores possíveis
    on_select     : callable() opcional, chamado após o utilizador escolher um
                    valor da lista (clique ou Enter) — útil para preenchimento
                    automático de campos relacionados.
    """
    _s = {'popup': None, 'lb': None, 'cancel_id': None}

    def _fire_select():
        if on_select:
            try:
                on_select()
            except Exception:
                pass

    def _destroy():
        if _s['cancel_id']:
            try:
                entry_widget.after_cancel(_s['cancel_id'])
            except Exception:
                pass
            _s['cancel_id'] = None
        if _s['popup']:
            try:
                _s['popup'].destroy()
            except Exception:
                pass
            _s['popup'] = None
            _s['lb'] = None

    def _show(suggestions):
        _destroy()
        if not suggestions:
            return
        entry_widget.update_idletasks()
        x = entry_widget.winfo_rootx()
        y = entry_widget.winfo_rooty() + entry_widget.winfo_height() + 1
        w = max(entry_widget.winfo_width(), 200)
        h = min(len(suggestions), 8) * 22 + 4

        top = tk.Toplevel(entry_widget.winfo_toplevel())
        top.wm_overrideredirect(True)
        top.wm_geometry(f"{w}x{h}+{x}+{y}")
        top.wm_attributes('-topmost', True)

        border = tk.Frame(top, bd=1, relief='solid', bg='#cccccc')
        border.pack(fill='both', expand=True)

        lb = tk.Listbox(border, selectbackground='#2c6fad', selectforeground='white',
                        activestyle='none', font=('Segoe UI', 10),
                        relief='flat', borderwidth=0, highlightthickness=0)
        sb = tk.Scrollbar(border, orient='vertical', command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        if len(suggestions) > 8:
            sb.pack(side='right', fill='y')
        lb.pack(fill='both', expand=True)
        for s in suggestions:
            lb.insert('end', s)

        def _pick(evt=None):
            sel = lb.curselection()
            if sel:
                textvariable.set(lb.get(sel[0]))
                _destroy()
                entry_widget.focus_set()
                _fire_select()

        lb.bind('<ButtonRelease-1>', _pick)

        _s['popup'] = top
        _s['lb'] = lb

    def _refresh(evt=None):
        if evt and evt.keysym in ('Escape', 'Return', 'Tab',
                                   'Up', 'Down', 'Left', 'Right', 'Home', 'End'):
            return
        text = textvariable.get().strip()
        try:
            all_vals = get_suggestions()
        except Exception:
            return
        if text:
            matches = [v for v in all_vals if text.lower() in v.lower()][:20]
        else:
            matches = all_vals[:20]
        if matches:
            _show(matches)
        else:
            _destroy()

    def _on_focus_in(evt=None):
        text = textvariable.get().strip()
        if not text:
            return
        try:
            all_vals = get_suggestions()
        except Exception:
            return
        matches = [v for v in all_vals if text.lower() in v.lower()][:20]
        if matches:
            _show(matches)

    def _schedule_hide(evt=None):
        _s['cancel_id'] = entry_widget.after(200, _destroy)

    def _nav_down(evt):
        if _s['lb']:
            lb = _s['lb']
            sel = lb.curselection()
            idx = min((sel[0] + 1) if sel else 0, lb.size() - 1)
            lb.selection_clear(0, 'end')
            lb.selection_set(idx)
            lb.see(idx)
            return 'break'

    def _nav_up(evt):
        if _s['lb']:
            lb = _s['lb']
            sel = lb.curselection()
            if sel and sel[0] > 0:
                idx = sel[0] - 1
                lb.selection_clear(0, 'end')
                lb.selection_set(idx)
                lb.see(idx)
            return 'break'

    def _on_return(evt):
        if _s['lb']:
            sel = _s['lb'].curselection()
            if sel:
                textvariable.set(_s['lb'].get(sel[0]))
                _destroy()
                _fire_select()
                return 'break'

    entry_widget.bind('<KeyRelease>', _refresh)
    entry_widget.bind('<FocusIn>',   _on_focus_in)
    entry_widget.bind('<FocusOut>',  _schedule_hide)
    entry_widget.bind('<Escape>',    lambda e: _destroy())
    entry_widget.bind('<Down>',      _nav_down)
    entry_widget.bind('<Up>',        _nav_up)
    entry_widget.bind('<Return>',    _on_return)


def carregar_foto_circular(path, size):
    """Devolve um CTkImage circular (size×size) a partir de um ficheiro de
    imagem, ou None se o caminho não existir/não for uma imagem válida.
    Recorta ao quadrado central, redimensiona e aplica uma máscara circular
    (cantos transparentes). Usado para o avatar do utilizador no cabeçalho."""
    try:
        import customtkinter as ctk
        from PIL import Image, ImageDraw
        if not path or not os.path.isfile(path):
            return None
        img = Image.open(path).convert('RGBA')
        w, h = img.size
        lado = min(w, h)
        esq, topo = (w - lado) // 2, (h - lado) // 2
        img = img.crop((esq, topo, esq + lado, topo + lado)).resize(
            (size, size), Image.LANCZOS)
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        img.putalpha(mask)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception:
        return None
