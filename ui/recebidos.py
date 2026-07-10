import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import customtkinter as ctk
from ui.email_dialog import EmailDialog
from ui.widgets import DateEntry, enable_sorting, enable_mousewheel, BusyDialog, enable_unsaved_changes_guard, imprimir_com_dialogo, attach_autocomplete
from ui.doc_extract import extrair_dados_recebido
from utils import (DEPARTAMENTOS_RECEBIDOS, iso_to_display, display_to_iso,
                   parse_clipboard_fields, dias_uteis, data_limite, guardar_anexo)


def calc_dias(data_recepcao, data_resposta):
    try:
        d1 = datetime.strptime(data_recepcao, "%Y-%m-%d").date()
        d2 = datetime.strptime(data_resposta, "%Y-%m-%d").date() if data_resposta else date.today()
        return (d2 - d1).days
    except Exception:
        return None


class RecebidosFrame(ctk.CTkFrame):
    def __init__(self, parent, db, config):
        super().__init__(parent, corner_radius=0)
        self.db = db
        self.config = config
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_toolbar()
        self._build_filter_bar()
        self._build_table()
        self.refresh()

    # ── Toolbar principal ─────────────────────────────────────────────────────
    def _build_toolbar(self):
        tb = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color=("gray90", "gray20"))
        tb.grid(row=0, column=0, sticky="ew")
        tb.grid_columnconfigure(2, weight=1)

        self.search_var = tk.StringVar()
        ctk.CTkLabel(tb, text="🔍").grid(row=0, column=0, padx=(10, 2), pady=8)
        self._search_entry = ctk.CTkEntry(tb, textvariable=self.search_var,
                                          placeholder_text="Pesquisar...", width=220)
        self._search_entry.grid(row=0, column=1, padx=4, pady=8)
        self._search_entry.bind("<Return>", lambda e: self.refresh())
        self._search_entry.bind("<Escape>", lambda e: (self.search_var.set(""), self.refresh()))

        btn_frame = ctk.CTkFrame(tb, fg_color="transparent")
        btn_frame.grid(row=0, column=3, padx=10, pady=6, sticky="e")

        ctk.CTkButton(btn_frame, text="+ Novo",      width=75, command=self.open_new,
                      fg_color="#1F4E79").pack(side="left", padx=1)
        ctk.CTkButton(btn_frame, text="✏️ Editar",   width=80, command=self.open_edit,
                      fg_color="#2c6fad").pack(side="left", padx=1)
        ctk.CTkButton(btn_frame, text="📋 Duplicar", width=86, command=self.duplicate_selected,
                      fg_color="#5a6e8a").pack(side="left", padx=1)
        ctk.CTkButton(btn_frame, text="🗑️ Eliminar", width=88, command=self.delete_selected,
                      fg_color="#c0392b").pack(side="left", padx=1)
        ctk.CTkButton(btn_frame, text="📂 Abrir",    width=74, command=self.abrir_ficheiro,
                      fg_color="#e67e22").pack(side="left", padx=1)
        ctk.CTkButton(btn_frame, text="🖨️ Imprimir", width=88, command=self.imprimir,
                      fg_color="#16a085").pack(side="left", padx=1)
        ctk.CTkButton(btn_frame, text="📤 Exportar", width=84, command=self.exportar,
                      fg_color="#27ae60").pack(side="left", padx=1)
        ctk.CTkButton(btn_frame, text="✉️ Email",    width=72, command=self.enviar_email,
                      fg_color="#8e44ad").pack(side="left", padx=1)
        ctk.CTkButton(btn_frame, text="🔄 Actualizar", width=90, command=self.refresh,
                      fg_color="gray50").pack(side="left", padx=1)

    # ── Barra de filtros ──────────────────────────────────────────────────────
    def _build_filter_bar(self):
        fb = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color=("gray85", "gray18"))
        fb.grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(fb, text="Técnico:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(10, 2))
        self.tecnico_var = tk.StringVar(value="Todos")
        self.cmb_tecnico = ctk.CTkComboBox(fb, values=["Todos"], variable=self.tecnico_var,
                                           width=170, command=lambda e: self.refresh())
        self.cmb_tecnico.pack(side="left", padx=4, pady=4)

        ctk.CTkLabel(fb, text="Status:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(8, 2))
        self.status_var = tk.StringVar(value="Todos")
        ctk.CTkComboBox(fb, values=["Todos", "Dentro do Prazo", "Fora do Prazo", "Pendente", "Arquivado", "Arquivo"],
                        variable=self.status_var, width=150,
                        command=lambda e: self.refresh()).pack(side="left", padx=4, pady=4)

        ctk.CTkLabel(fb, text="De:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(8, 2))
        self._de_var = tk.StringVar()
        DateEntry(fb, textvariable=self._de_var, width=110).pack(side="left", padx=2, pady=4)
        self._de_var.trace_add("write", lambda *a: self.refresh())

        ctk.CTkLabel(fb, text="Até:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(4, 2))
        self._ate_var = tk.StringVar()
        DateEntry(fb, textvariable=self._ate_var, width=110).pack(side="left", padx=2, pady=4)
        self._ate_var.trace_add("write", lambda *a: self.refresh())

        ctk.CTkButton(fb, text="✖ Limpar Filtros", width=110, height=26,
                      fg_color="gray50", command=self._clear_filters).pack(side="left", padx=8)

        self.lbl_count = ctk.CTkLabel(fb, text="", font=ctk.CTkFont(size=11),
                                      text_color=("#1F4E79", "#5ba3d9"))
        self.lbl_count.pack(side="right", padx=12)

    def _clear_filters(self):
        self.search_var.set("")
        self.tecnico_var.set("Todos")
        self.status_var.set("Todos")
        self._de_var.set("")
        self._ate_var.set("")
        self.refresh()

    def _get_tecnicos(self):
        return self.db.get_autocomplete('tecnico')

    # ── Tabela ────────────────────────────────────────────────────────────────
    def _build_table(self):
        frame = ctk.CTkFrame(self, corner_radius=0)
        frame.grid(row=2, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview", rowheight=26, font=('Segoe UI', 10))
        style.configure("Custom.Treeview.Heading", font=('Segoe UI', 10, 'bold'),
                        background="#1F4E79", foreground="white")
        style.map("Custom.Treeview", background=[("selected", "#2c6fad")])
        style.configure("Custom.Treeview", background="#f8f9fa", fieldbackground="#f8f9fa")

        cols = ("id", "numero", "proveniencia", "remetente", "assunto",
                "data_rec", "despacho", "tecnico", "data_resp", "dias", "status", "fich")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings",
                                 style="Custom.Treeview", selectmode="browse")

        col_config = [
            ("id",         "ID",             40),
            ("numero",     "Nº Documento",  210),
            ("proveniencia","Proveniência",  110),
            ("remetente",  "Remetente",     140),
            ("assunto",    "Assunto",        250),
            ("data_rec",   "Data Recepção",  95),
            ("despacho",   "Despacho",      140),
            ("tecnico",    "Técnico",       140),
            ("data_resp",  "Data Resposta",  95),
            ("dias",       "Dias",           45),
            ("status",     "Status",        115),
            ("fich",       "📎",             30),
        ]
        for col, heading, width in col_config:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=30)

        self.tree.tag_configure("dentro",    background="#d4edda")
        self.tree.tag_configure("fora",      background="#f8d7da")
        self.tree.tag_configure("pendente",  background="#fff3cd")
        self.tree.tag_configure("a_vencer",  background="#fdd0a0")  # D1: prazo próximo
        self.tree.tag_configure("arquivado", background="#e2e3e5")

        vsb = ttk.Scrollbar(frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>",  lambda e: self.open_edit())
        self.tree.bind("<Button-3>",  self._context_menu)
        self.tree.bind("<Return>",    lambda e: self.open_edit())
        self.tree.bind("<Delete>",    lambda e: self.delete_selected())
        enable_sorting(self.tree, [c for c in cols if c not in ("id", "fich")])
        enable_mousewheel(self.tree)

        # Menu de contexto
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label="✏️  Editar",          command=self.open_edit)
        self._menu.add_command(label="📂  Abrir Ficheiro Recebido", command=self.abrir_ficheiro)
        self._menu.add_command(label="📂  Abrir Ficheiro Resposta", command=self.abrir_ficheiro_resposta)
        self._menu.add_command(label="🖨️  Imprimir Ficha",   command=self.imprimir)
        self._menu.add_command(label="✉️  Enviar por Email", command=self.enviar_email)
        self._menu.add_separator()
        self._menu.add_command(label="📋  Copiar Nº Documento", command=self._copy_numero)
        self._menu.add_separator()
        self._menu.add_command(label="🗑️  Eliminar",         command=self.delete_selected)

    def _context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            try:
                self._menu.tk_popup(event.x_root, event.y_root)
            finally:
                self._menu.grab_release()

    def _copy_numero(self):
        rid = self._get_selected_id()
        if rid is None:
            return
        doc = self.db.get_recebido(rid)
        if doc:
            self.clipboard_clear()
            self.clipboard_append(doc.get('numero', ''))

    # ── Refresh ───────────────────────────────────────────────────────────────
    def refresh(self, *args):
        # Actualiza lista de técnicos
        tecnicos = ["Todos"] + self._get_tecnicos()
        self.cmb_tecnico.configure(values=tecnicos)

        filters = {}
        s = self.search_var.get().strip()
        if s:
            filters['search'] = s
        tec = self.tecnico_var.get()
        if tec and tec != "Todos":
            filters['tecnico'] = tec
        st = self.status_var.get()
        if st and st != "Todos":
            filters['prazo_status'] = st

        de  = display_to_iso(self._de_var.get().strip())
        ate = display_to_iso(self._ate_var.get().strip())
        if de:  filters['data_inicio'] = de
        if ate: filters['data_fim']    = ate

        rows = self.db.get_all_recebidos(filters)
        for item in self.tree.get_children():
            self.tree.delete(item)

        prazo_padrao = self.config.get('prazo_padrao', 5)
        usar_dias_uteis = self.config.get('dias_uteis', False)
        for r in rows:
            if usar_dias_uteis:
                dias = dias_uteis(r.get('data_recepcao', ''), r.get('data_resposta') or None)
            else:
                dias = calc_dias(r.get('data_recepcao', ''), r.get('data_resposta', ''))
            status = r.get('prazo_status', '')
            tag    = {"Dentro do Prazo": "dentro", "Fora do Prazo": "fora",
                      "Arquivado": "arquivado", "Arquivo": "arquivado"}.get(status, "pendente")
            # D1: pendente a aproximar-se do prazo (ou já vencido) → cor laranja
            if tag == "pendente" and not r.get('data_resposta'):
                limite = data_limite(r.get('data_recepcao', ''), r.get('prazo_data'),
                                     prazo_padrao, usar_dias_uteis)
                if limite:
                    try:
                        dl = datetime.strptime(limite, '%Y-%m-%d').date()
                        if (dl - date.today()).days <= 1:
                            tag = "a_vencer"
                    except Exception:
                        pass
            self.tree.insert("", "end", iid=str(r['id']), tags=(tag,), values=(
                r['id'],
                r.get('numero', ''),
                r.get('proveniencia', ''),
                r.get('remetente_nome', ''),
                r.get('assunto', ''),
                iso_to_display(r.get('data_recepcao', '')),
                r.get('despacho', ''),
                r.get('tecnico', ''),
                iso_to_display(r.get('data_resposta', '')),
                str(dias) if dias is not None else "",
                status,
                "📎" if r.get('ficheiro_path') else "",
            ))

        total = len(rows)
        self.lbl_count.configure(text=f"📄 {total} documento{'s' if total != 1 else ''}")

        # Actualiza também os indicadores globais (alertas, crachás, rodapé)
        app = self.winfo_toplevel()
        if hasattr(app, 'refresh_indicators'):
            app.refresh_indicators()

    # ── Acções ────────────────────────────────────────────────────────────────
    def _get_selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def open_new(self):
        RecebidoForm(self, self.db, self.config, None, self.refresh)

    def duplicate_selected(self):
        rid = self._get_selected_id()
        if rid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento para duplicar.", parent=self)
            return
        RecebidoForm(self, self.db, self.config, None, self.refresh, clone_id=rid)

    def open_edit(self):
        rid = self._get_selected_id()
        if rid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento primeiro.", parent=self)
            return
        RecebidoForm(self, self.db, self.config, rid, self.refresh)

    def delete_selected(self):
        rid = self._get_selected_id()
        if rid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento primeiro.", parent=self)
            return
        doc = self.db.get_recebido(rid)
        num = doc.get('numero', str(rid)) if doc else str(rid)
        if messagebox.askyesno("Confirmar",
                               f"Eliminar o documento:\n{num}?\n\n"
                               "(Poderá restaurá-lo em Configurações → ♻️ Reciclagem "
                               "durante 30 dias.)", parent=self):
            self.db.delete_recebido(rid)
            self.refresh()

    def abrir_ficheiro(self):
        """Abre o ficheiro anexado ao documento seleccionado."""
        rid = self._get_selected_id()
        if rid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento primeiro.", parent=self)
            return
        doc = self.db.get_recebido(rid)
        if not doc:
            return
        path = doc.get('ficheiro_path', '')
        if not path or not os.path.exists(path):
            messagebox.showwarning("Ficheiro não encontrado",
                                   "Nenhum ficheiro anexado ou o ficheiro foi movido/eliminado.\n"
                                   f"Caminho registado: {path or '—'}", parent=self)
            return
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o ficheiro:\n{e}", parent=self)

    def abrir_ficheiro_resposta(self):
        """Abre o ficheiro de resposta anexado ao documento seleccionado."""
        rid = self._get_selected_id()
        if rid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento primeiro.", parent=self)
            return
        doc = self.db.get_recebido(rid)
        if not doc:
            return
        path = doc.get('ficheiro_resposta_path', '')
        if not path or not os.path.exists(path):
            messagebox.showwarning("Ficheiro não encontrado",
                                   "Nenhum ficheiro de resposta anexado ou o ficheiro foi movido/eliminado.\n"
                                   f"Caminho registado: {path or '—'}", parent=self)
            return
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o ficheiro:\n{e}", parent=self)

    def imprimir(self):
        """Gera e abre uma ficha de impressão do documento seleccionado."""
        rid = self._get_selected_id()
        if rid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento primeiro.", parent=self)
            return
        doc = self.db.get_recebido(rid)
        if not doc:
            return

        dias = calc_dias(doc.get('data_recepcao', ''), doc.get('data_resposta', ''))
        conteudo = f"""
================================================================================
             FICHA DE DOCUMENTO RECEBIDO — DNE | MIREME
================================================================================

  Nº Documento   : {doc.get('numero', '—')}
  Proveniência   : {doc.get('proveniencia', '—')}
  Remetente      : {doc.get('remetente_nome', '—')}  ({doc.get('remetente_cargo', '—')})
  Assunto        : {doc.get('assunto', '—')}

  Data Recepção  : {iso_to_display(doc.get('data_recepcao', ''))}
  Despacho       : {doc.get('despacho', '—')}
  Ao Departamento: {doc.get('endereçado_a', '—')}
  Técnico        : {doc.get('tecnico', '—')}
  Data Resposta  : {iso_to_display(doc.get('data_resposta', '')) or 'Pendente'}
  Dias           : {dias if dias is not None else '—'}
  Data-limite    : {iso_to_display(data_limite(doc.get('data_recepcao', ''), doc.get('prazo_data'), self.config.get('prazo_padrao', 5), bool(self.config.get('dias_uteis', False)))) or '—'}
  Status         : {doc.get('prazo_status', '—')}

  Ficheiro       : {doc.get('ficheiro_path', '—')}

  Observação:
  {doc.get('observacao', '—')}

================================================================================
  Impresso em: {datetime.now().strftime('%d/%m/%Y %H:%M')}
================================================================================
"""
        imprimir_com_dialogo(self, conteudo)

    def exportar(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="documentos_recebidos.xlsx", parent=self)
        if filepath:
            busy = BusyDialog(self, "A exportar para Excel...")
            try:
                ok = self.db.export_recebidos_excel(filepath)
            finally:
                busy.fechar()
            if ok:
                messagebox.showinfo("Sucesso", f"Exportado para:\n{filepath}", parent=self)
            else:
                messagebox.showerror("Erro", "Falha ao exportar.", parent=self)

    def enviar_email(self):
        rid = self._get_selected_id()
        if rid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento primeiro.", parent=self)
            return
        doc = self.db.get_recebido(rid)
        if not doc:
            return
        EmailDialog(self, config=self.config, ficheiro_path=doc.get('ficheiro_path', ''),
                    assunto=f"Ref: {doc.get('numero', '')} — {doc.get('assunto', '')}",
                    corpo=f"Exmo(a) Senhor(a),\n\nEnvio em anexo o documento:\n"
                          f"Nº: {doc.get('numero', '')}\nAssunto: {doc.get('assunto', '')}\n"
                          f"Data de Recepção: {iso_to_display(doc.get('data_recepcao', ''))}\n\n"
                          f"Com os melhores cumprimentos,\n{self.config.get('utilizador', 'DNE/MIREME')}")

    def focus_search(self):
        self._search_entry.focus_set()

    def on_activate(self):
        self.refresh()


# ─────────────────────────────────────────────────────────────────────────────
#  Formulário de Documento Recebido
# ─────────────────────────────────────────────────────────────────────────────

class RecebidoForm(ctk.CTkToplevel):
    # Directores fixos para Despacho
    DIRECTORES = [
        "Dir. Ortigio Nhanombe",
        "Dir. Marcelina Mataveia",
    ]

    # Departamentos fixos para "Ao Departamento"
    DEPARTAMENTOS = DEPARTAMENTOS_RECEBIDOS

    # Templates de assunto predefinidos (D2)
    TEMPLATES_ASSUNTO = [
        "Encaminhamento de documentação",
        "Solicitação de informação/dados",
        "Pedido de colaboração institucional",
        "Convocatória para reunião",
        "Aprovação de relatório/proposta",
        "Informação sobre actividades do sector",
        "Solicitação de autorização",
        "Resposta à solicitação recebida",
    ]

    def __init__(self, parent, db, config, record_id, callback, clone_id=None):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.record_id = record_id
        self.callback = callback
        self.title("Novo Documento Recebido" if not record_id else "Editar Documento Recebido")
        self.geometry("820x720")
        self.resizable(True, True)
        self.grab_set()

        self._vars = {}
        self._nomes_contactos = self.db.get_nomes_contactos()
        self._build_form()

        if record_id:
            self._load_data(record_id)
        elif clone_id:
            self._clone_data(clone_id)

        self.bind("<Control-s>", lambda e: self._save())
        enable_unsaved_changes_guard(self)

    # ── Helpers de layout ────────────────────────────────────────────────────

    def _lbl_entry(self, parent, row, col, label, var_key, width=280, required=False):
        lbl_text = label + (" *" if required else "")
        ctk.CTkLabel(parent, text=lbl_text, anchor="e", width=140).grid(
            row=row, column=col * 2, padx=(10, 4), pady=6, sticky="e")
        var = tk.StringVar()
        entry = ctk.CTkEntry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=col * 2 + 1, padx=(0, 10), pady=6, sticky="w")
        self._vars[var_key] = var
        return entry

    def _lbl_combo(self, parent, row, col, label, var_key, values, width=280):
        """Cria label + ComboBox editável."""
        ctk.CTkLabel(parent, text=label, anchor="e", width=140).grid(
            row=row, column=col * 2, padx=(10, 4), pady=6, sticky="e")
        var = tk.StringVar()
        combo = ctk.CTkComboBox(parent, values=values, variable=var, width=width)
        combo.grid(row=row, column=col * 2 + 1, padx=(0, 10), pady=6, sticky="w")
        self._vars[var_key] = var
        return combo

    # ── Construção do formulário ─────────────────────────────────────────────

    def _build_form(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self)
        scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        f = scroll

        # ── Linha 0: Nº Documento + sugestão automática (A1) ─────────────────
        ctk.CTkLabel(f, text="Nº Documento *", anchor="e", width=140).grid(
            row=0, column=0, padx=(10, 4), pady=6, sticky="e")
        self._vars['numero'] = tk.StringVar()
        num_frame = ctk.CTkFrame(f, fg_color="transparent")
        num_frame.grid(row=0, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")
        ctk.CTkEntry(num_frame, textvariable=self._vars['numero'], width=280).pack(side="left")
        ctk.CTkButton(num_frame, text="🔢 Sugerir", width=90, height=28,
                      fg_color="#5a6e8a",
                      command=self._sugerir_numero).pack(side="left", padx=(6, 0))

        # ── Linha 1: Proveniência ─────────────────────────────────────────────
        e_prov = self._lbl_entry(f, 1, 0, "Proveniência", "proveniencia", 340)
        attach_autocomplete(e_prov, self._vars['proveniencia'],
                            lambda: self.db.get_autocomplete('proveniencia'))

        # ── Linha 2: Nome + Cargo do Remetente ───────────────────────────────
        e_nome = self._lbl_entry(f, 2, 0, "Nome do Remetente", "remetente_nome", 300)
        attach_autocomplete(e_nome, self._vars['remetente_nome'],
                            lambda: self.db.get_autocomplete('remetente_nome'),
                            on_select=self._autofill_remetente)
        # Também preenche ao sair do campo depois de digitar o nome à mão
        e_nome.bind('<FocusOut>', lambda e: self._autofill_remetente(), add='+')
        e_cargo = self._lbl_entry(f, 2, 1, "Cargo do Remetente", "remetente_cargo", 220)
        attach_autocomplete(e_cargo, self._vars['remetente_cargo'],
                            lambda: self.db.get_autocomplete('remetente_cargo'))

        # ── Linha 3: Assunto + templates (D2) ────────────────────────────────
        ctk.CTkLabel(f, text="Assunto *", anchor="e", width=140).grid(
            row=3, column=0, padx=(10, 4), pady=6, sticky="e")
        self._vars['assunto'] = tk.StringVar()
        assunto_frame = ctk.CTkFrame(f, fg_color="transparent")
        assunto_frame.grid(row=3, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")
        ctk.CTkEntry(assunto_frame, textvariable=self._vars['assunto'], width=440).pack(side="left")
        ctk.CTkButton(assunto_frame, text="💡", width=32, height=28,
                      fg_color="#5a6e8a",
                      command=self._mostrar_templates).pack(side="left", padx=(4, 0))

        # ── Linha 4: Datas com calendário ─────────────────────────────────────
        ctk.CTkLabel(f, text="Data Recepção", anchor="e", width=140).grid(
            row=4, column=0, padx=(10, 4), pady=6, sticky="e")
        self._vars['data_recepcao'] = tk.StringVar()
        DateEntry(f, textvariable=self._vars['data_recepcao'], width=140).grid(
            row=4, column=1, padx=(0, 10), pady=6, sticky="w")

        ctk.CTkLabel(f, text="Data Resposta", anchor="e", width=140).grid(
            row=4, column=2, padx=(10, 4), pady=6, sticky="e")
        self._vars['data_resposta'] = tk.StringVar()
        DateEntry(f, textvariable=self._vars['data_resposta'], width=140).grid(
            row=4, column=3, padx=(0, 10), pady=6, sticky="w")

        # ── Linha 5: Despacho (ComboBox com Directores fixos) ─────────────────
        self._lbl_combo(f, 5, 0, "Despacho", "despacho",
                        self.DIRECTORES + [""], width=300)

        # ── Linha 6: Ao Departamento (ComboBox com Departamentos) ────────────
        self._lbl_combo(f, 6, 0, "Ao Departamento", "endereçado_a",
                        self.DEPARTAMENTOS, width=300)

        # ── Linha 7: Técnico (ComboBox com Contactos) ─────────────────────────
        self._lbl_combo(f, 7, 0, "Técnico", "tecnico",
                        self._nomes_contactos, width=300)

        # ── Linha 8: Status Prazo + Prazo específico do documento ─────────────
        ctk.CTkLabel(f, text="Status Prazo", anchor="e", width=140).grid(
            row=8, column=0, padx=(10, 4), pady=6, sticky="ne")
        prazo_padrao = self.config.get('prazo_padrao', 5)
        box = ctk.CTkFrame(f, fg_color="transparent")
        box.grid(row=8, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")
        top = ctk.CTkFrame(box, fg_color="transparent")
        top.pack(anchor="w")
        self._vars['prazo_status'] = tk.StringVar(value="Pendente")
        ctk.CTkComboBox(top, values=["Pendente", "Dentro do Prazo", "Fora do Prazo", "Arquivado", "Arquivo"],
                        variable=self._vars['prazo_status'], width=180,
                        command=self._update_dias).pack(side="left")
        ctk.CTkLabel(top, text="Data-limite:").pack(side="left", padx=(16, 4))
        self._vars['prazo_data'] = tk.StringVar()
        DateEntry(top, textvariable=self._vars['prazo_data'], width=140).pack(side="left")
        self._vars['prazo_data'].trace_add("write", self._update_dias)
        ctk.CTkLabel(box, text=f"Vazio = usa o padrão global de {prazo_padrao} dias após a recepção. "
                               "'Arquivado'/'Arquivo': não conta prazo e conta como Dentro do Prazo.",
                     font=ctk.CTkFont(size=10), text_color="gray60").pack(anchor="w", pady=(3, 0))

        # ── Linha 9: Observação ───────────────────────────────────────────────
        ctk.CTkLabel(f, text="Observação", anchor="e", width=140).grid(
            row=9, column=0, padx=(10, 4), pady=6, sticky="ne")
        self._obs_text = ctk.CTkTextbox(f, width=520, height=80)
        self._obs_text.grid(row=9, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")

        # ── Linha 10: Ficheiro Recebido + botão Procurar ─────────────────────
        ctk.CTkLabel(f, text="Ficheiro Recebido", anchor="e", width=140).grid(
            row=10, column=0, padx=(10, 4), pady=6, sticky="e")
        file_frame = ctk.CTkFrame(f, fg_color="transparent")
        file_frame.grid(row=10, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")
        self._vars['ficheiro_path'] = tk.StringVar()
        ctk.CTkEntry(file_frame, textvariable=self._vars['ficheiro_path'],
                     width=380).pack(side="left", padx=(0, 6))
        ctk.CTkButton(file_frame, text="📂 Procurar", width=110,
                      command=self._pick_file_and_extract,
                      fg_color="#2c6fad").pack(side="left", padx=(0, 4))

        # ── Indicador de extracção automática ────────────────────────────────
        self.lbl_extracao = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=11),
                                          text_color="#27ae60")
        self.lbl_extracao.grid(row=11, column=0, columnspan=4, pady=(0, 4))

        # ── Linha 12: Ficheiro Resposta + botão Procurar ─────────────────────
        ctk.CTkLabel(f, text="Ficheiro Resposta", anchor="e", width=140).grid(
            row=12, column=0, padx=(10, 4), pady=6, sticky="e")
        resp_frame = ctk.CTkFrame(f, fg_color="transparent")
        resp_frame.grid(row=12, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")
        self._vars['ficheiro_resposta_path'] = tk.StringVar()
        ctk.CTkEntry(resp_frame, textvariable=self._vars['ficheiro_resposta_path'],
                     width=380).pack(side="left", padx=(0, 6))
        ctk.CTkButton(resp_frame, text="📂 Procurar", width=110,
                      command=self._pick_file_resposta,
                      fg_color="#2c6fad").pack(side="left", padx=(0, 4))

        # ── Contador de dias ──────────────────────────────────────────────────
        self.lbl_dias = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=12))
        self.lbl_dias.grid(row=13, column=0, columnspan=4, pady=6)

        self._vars['data_recepcao'].trace_add("write", self._update_dias)
        self._vars['data_resposta'].trace_add("write", self._update_dias)

        # ── Botões ────────────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=1, column=0, pady=10)
        ctk.CTkButton(btn_frame, text="💾 Guardar", width=120, command=self._save,
                      fg_color="#1F4E79").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="📋 Copiar Tudo", width=130, command=self._copiar_tudo,
                      fg_color="#5a6e8a").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="📥 Colar Tudo", width=130, command=self._colar_tudo,
                      fg_color="#5a6e8a").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="❌ Cancelar", width=100, command=self.destroy,
                      fg_color="gray50").pack(side="left", padx=10)

    # ── Lógica ───────────────────────────────────────────────────────────────

    def _autofill_remetente(self, *_):
        """Ao reconhecer o nome do remetente na base de dados, preenche
        automaticamente o Cargo do Remetente e a Proveniência (só se estiverem
        vazios, para não apagar o que foi escrito à mão)."""
        nome = self._vars.get('remetente_nome')
        if nome is None:
            return
        dados = self.db.lookup_remetente(nome.get())
        if not dados:
            return
        if dados.get('remetente_cargo') and not self._vars['remetente_cargo'].get().strip():
            self._vars['remetente_cargo'].set(dados['remetente_cargo'])
        if dados.get('proveniencia') and not self._vars['proveniencia'].get().strip():
            self._vars['proveniencia'].set(dados['proveniencia'])

    def _sugerir_numero(self):
        sugestao = self.db.suggest_next_numero('recebidos')
        if sugestao:
            self._vars['numero'].set(sugestao)
        else:
            messagebox.showinfo("Sugestão", "Sem documentos anteriores para inferir o padrão.", parent=self)

    def _mostrar_templates(self):
        top = tk.Toplevel(self)
        top.title("Sugestões de Assunto")
        top.geometry("360x260")
        top.resizable(False, False)
        top.grab_set()
        top.transient(self)
        tk.Label(top, text="Seleccione um modelo de assunto:", font=('Segoe UI', 10)).pack(pady=(10, 4))
        lb = tk.Listbox(top, font=('Segoe UI', 10), selectbackground="#2c6fad",
                        relief='flat', highlightthickness=1, activestyle='none')
        lb.pack(fill="both", expand=True, padx=10, pady=4)
        for t in self.TEMPLATES_ASSUNTO:
            lb.insert("end", t)
        def _aplicar(evt=None):
            sel = lb.curselection()
            if sel:
                self._vars['assunto'].set(lb.get(sel[0]))
                top.destroy()
        lb.bind('<Double-Button-1>', _aplicar)
        lb.bind('<Return>', _aplicar)
        tk.Button(top, text="Aplicar", command=_aplicar,
                  bg="#1F4E79", fg="white", relief='flat', padx=10).pack(pady=(0, 10))

    def _clone_data(self, clone_id):
        r = self.db.get_recebido(clone_id)
        if not r:
            return
        for key in ('proveniencia', 'remetente_nome', 'remetente_cargo',
                    'despacho', 'endereçado_a', 'tecnico'):
            if key in self._vars and r.get(key):
                self._vars[key].set(r[key])
        obs = r.get('observacao', '') or ''
        if obs:
            self._obs_text.delete("1.0", "end")
            self._obs_text.insert("1.0", obs)

    def _data_limite(self, dr_iso):
        """Data-limite (ISO) deste documento: a específica escolhida no calendário,
        ou, se vazia, a Data de Recepção mais o prazo padrão global."""
        prazo_data = display_to_iso((self._vars['prazo_data'].get() or '').strip())
        return data_limite(dr_iso, prazo_data or None,
                           self.config.get('prazo_padrao', 5),
                           bool(self.config.get('dias_uteis', False)))

    def _update_dias(self, *args):
        status_actual = self._vars['prazo_status'].get()
        arquivar = status_actual in ('Arquivado', 'Arquivo')
        try:
            dr = display_to_iso(self._vars['data_recepcao'].get())
            resp = display_to_iso(self._vars['data_resposta'].get())
            limite = self._data_limite(dr) if dr else None
            # Documentos para arquivar não contam prazo
            if arquivar:
                self.lbl_dias.configure(
                    text="Documento para arquivar — prazo não contado (conta como Dentro do Prazo)",
                    text_color="gray50")
            else:
                dias = calc_dias(dr, resp if resp else None)
                lim_txt = f"  |  Data-limite: {iso_to_display(limite)}" if limite else ""
                if dias is not None:
                    if dias < 0:
                        self.lbl_dias.configure(text="Data resposta inválida (anterior à recepção)", text_color="orange")
                    else:
                        dentro = (limite is not None) and ((resp or date.today().isoformat()) <= limite)
                        color = "green" if dentro else "red"
                        self.lbl_dias.configure(text=f"Dias decorridos: {dias}{lim_txt}", text_color=color)
        except Exception:
            pass

        # ── Actualiza automaticamente o Status Prazo a partir das datas ──────────
        # (preserva 'Arquivado'/'Arquivo' quando seleccionados manualmente)
        try:
            if not arquivar:
                if not resp:
                    novo_status = "Pendente"
                elif not limite or resp < dr:
                    novo_status = status_actual
                else:
                    novo_status = ("Dentro do Prazo" if resp <= limite else "Fora do Prazo")
                if novo_status != status_actual:
                    self._vars['prazo_status'].set(novo_status)
        except Exception:
            pass

    def _pick_file_and_extract(self):
        """Abre diálogo de ficheiro e tenta preencher campos automaticamente."""
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[
                ("Documentos", "*.pdf *.docx *.doc"),
                ("PDF", "*.pdf"),
                ("Word", "*.docx *.doc"),
                ("Todos os ficheiros", "*.*"),
            ]
        )
        if not path:
            return

        # Copia para a pasta gerida de anexos (não se perde se o original mudar)
        path = guardar_anexo(path)
        self._vars['ficheiro_path'].set(path)
        self.lbl_extracao.configure(text="⏳ A analisar ficheiro...", text_color="#f39c12")
        self.update_idletasks()

        try:
            dados = extrair_dados_recebido(path)
        except Exception as e:
            self.lbl_extracao.configure(
                text=f"⚠️ Erro inesperado: {e}", text_color="#e74c3c")
            return

        # Erros de biblioteca ou formato
        if '_erro' in dados:
            self.lbl_extracao.configure(
                text=f"⚠️ {dados['_erro']}", text_color="#e74c3c")
            return

        if '_formato' in dados and len(dados) == 1:
            self.lbl_extracao.configure(
                text=f"ℹ️ {dados['_formato']} Preencha os campos manualmente.",
                text_color="#e67e22")
            return

        # Preenche apenas os campos vazios
        nomes_pt = {
            'numero': 'Nº Documento',
            'proveniencia': 'Proveniência',
            'remetente_nome': 'Nome Remetente',
            'remetente_cargo': 'Cargo Remetente',
            'assunto': 'Assunto',
        }
        preenchidos = []
        for campo, var_key in nomes_pt.items():
            valor = dados.get(campo, '').strip()
            if valor and not self._vars[campo].get().strip():
                self._vars[campo].set(valor)
                preenchidos.append(var_key)

        if preenchidos:
            self.lbl_extracao.configure(
                text=f"✅ Preenchido: {', '.join(preenchidos)}",
                text_color="#27ae60")
        else:
            self.lbl_extracao.configure(
                text="ℹ️ Campos já preenchidos — dados do ficheiro não foram aplicados.",
                text_color="#7f8c8d")

    def _pick_file_resposta(self):
        """Abre diálogo de ficheiro para anexar o documento de resposta."""
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[
                ("Documentos", "*.pdf *.docx *.doc"),
                ("PDF", "*.pdf"),
                ("Word", "*.docx *.doc"),
                ("Todos os ficheiros", "*.*"),
            ]
        )
        if path:
            # Copia para a pasta gerida de anexos (não se perde se o original mudar)
            self._vars['ficheiro_resposta_path'].set(guardar_anexo(path))

    def _load_data(self, rid):
        r = self.db.get_recebido(rid)
        if not r:
            return
        for key in ('numero', 'proveniencia', 'remetente_nome', 'remetente_cargo',
                    'assunto', 'despacho', 'endereçado_a', 'tecnico',
                    'prazo_status', 'ficheiro_path', 'ficheiro_resposta_path'):
            if key in self._vars and r.get(key):
                self._vars[key].set(r[key])
        self._vars['prazo_data'].set(iso_to_display(r.get('prazo_data', '')))
        self._vars['data_recepcao'].set(iso_to_display(r.get('data_recepcao', '')))
        self._vars['data_resposta'].set(iso_to_display(r.get('data_resposta', '')))
        obs = r.get('observacao', '') or ''
        self._obs_text.delete("1.0", "end")
        self._obs_text.insert("1.0", obs)

    def _save(self):
        numero = self._vars['numero'].get().strip()
        assunto = self._vars['assunto'].get().strip()
        if not numero or not assunto:
            messagebox.showerror("Erro", "Nº Documento e Assunto são obrigatórios.", parent=self)
            return

        data_recepcao = display_to_iso(self._vars['data_recepcao'].get().strip())
        data_resposta = display_to_iso(self._vars['data_resposta'].get().strip())
        if data_recepcao and data_resposta and data_resposta < data_recepcao:
            messagebox.showerror(
                "Datas inválidas",
                "A Data de Resposta não pode ser anterior à Data de Recepção.",
                parent=self)
            return

        assunto_dup = self.db.find_numero_duplicado('recebidos', numero, self.record_id)
        if assunto_dup is not None:
            if not messagebox.askyesno(
                "Número já existe",
                f"O nº de documento \"{numero}\" já está atribuído a:\n"
                f"{assunto_dup or '(sem assunto)'}\n\n"
                f"Deseja continuar e guardar mesmo assim?",
                parent=self):
                return

        data = {
            'numero': numero,
            'proveniencia': self._vars['proveniencia'].get().strip(),
            'remetente_nome': self._vars['remetente_nome'].get().strip(),
            'remetente_cargo': self._vars['remetente_cargo'].get().strip(),
            'assunto': assunto,
            'data_recepcao': data_recepcao,
            'despacho': self._vars['despacho'].get().strip(),
            'endereçado_a': self._vars['endereçado_a'].get().strip(),
            'tecnico': self._vars['tecnico'].get().strip(),
            'data_resposta': data_resposta,
            'prazo_status': self._vars['prazo_status'].get(),
            'prazo_data': display_to_iso(self._vars['prazo_data'].get().strip()) or None,
            'observacao': self._obs_text.get("1.0", "end").strip(),
            'ficheiro_path': self._vars['ficheiro_path'].get().strip(),
            'ficheiro_resposta_path': self._vars['ficheiro_resposta_path'].get().strip(),
        }
        try:
            if self.record_id:
                self.db.update_recebido(self.record_id, data)
            else:
                self.db.insert_recebido(data)
            self.callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao guardar:\n{e}", parent=self)

    def _colar_tudo(self):
        try:
            texto = self.clipboard_get()
        except Exception:
            messagebox.showwarning("Aviso", "Área de transferência vazia ou inválida.", parent=self)
            return
        labels = ["Nº Documento", "Proveniência", "Nome do Remetente", "Cargo do Remetente",
                  "Assunto", "Data de Recepção", "Data de Resposta", "Despacho",
                  "Ao Departamento", "Técnico", "Status Prazo", "Observação",
                  "Ficheiro Recebido", "Ficheiro Resposta"]
        vals = parse_clipboard_fields(texto, labels)
        MAP = {
            "Nº Documento": "numero", "Proveniência": "proveniencia",
            "Nome do Remetente": "remetente_nome", "Cargo do Remetente": "remetente_cargo",
            "Assunto": "assunto", "Data de Recepção": "data_recepcao",
            "Data de Resposta": "data_resposta", "Despacho": "despacho",
            "Ao Departamento": "endereçado_a", "Técnico": "tecnico",
            "Status Prazo": "prazo_status", "Ficheiro Recebido": "ficheiro_path",
            "Ficheiro Resposta": "ficheiro_resposta_path",
        }
        for label, var_key in MAP.items():
            if label in vals and var_key in self._vars:
                self._vars[var_key].set(vals[label])
        if "Observação" in vals:
            self._obs_text.delete("1.0", "end")
            self._obs_text.insert("1.0", vals["Observação"])
        messagebox.showinfo("Colado", "Conteúdo colado com sucesso nos campos.", parent=self)

    def _copiar_tudo(self):
        linhas = [
            f"Nº Documento: {self._vars['numero'].get().strip()}",
            f"Proveniência: {self._vars['proveniencia'].get().strip()}",
            f"Nome do Remetente: {self._vars['remetente_nome'].get().strip()}",
            f"Cargo do Remetente: {self._vars['remetente_cargo'].get().strip()}",
            f"Assunto: {self._vars['assunto'].get().strip()}",
            f"Data de Recepção: {self._vars['data_recepcao'].get().strip()}",
            f"Data de Resposta: {self._vars['data_resposta'].get().strip()}",
            f"Despacho: {self._vars['despacho'].get().strip()}",
            f"Ao Departamento: {self._vars['endereçado_a'].get().strip()}",
            f"Técnico: {self._vars['tecnico'].get().strip()}",
            f"Status Prazo: {self._vars['prazo_status'].get().strip()}",
            f"Observação:\n{self._obs_text.get('1.0', 'end').strip()}",
            f"Ficheiro Recebido: {self._vars['ficheiro_path'].get().strip()}",
            f"Ficheiro Resposta: {self._vars['ficheiro_resposta_path'].get().strip()}",
        ]
        texto = "\n".join(linhas)
        self.clipboard_clear()
        self.clipboard_append(texto)
        messagebox.showinfo("Copiado", "Conteúdo copiado para a área de transferência.", parent=self)
