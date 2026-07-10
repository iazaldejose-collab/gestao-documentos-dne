import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import customtkinter as ctk
from ui.email_dialog import EmailDialog
from ui.widgets import DateEntry, enable_sorting, enable_mousewheel, BusyDialog, enable_unsaved_changes_guard, imprimir_com_dialogo, attach_autocomplete
from ui.doc_extract import extrair_dados_enviado
from utils import iso_to_display, display_to_iso, parse_clipboard_fields, guardar_anexo


class EnviadosFrame(ctk.CTkFrame):
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

    def _get_assinantes(self):
        return self.db.get_autocomplete('assinante')

    def _get_preparados(self):
        return self.db.get_autocomplete('preparado_por')

    def _build_filter_bar(self):
        fb = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color=("gray85", "gray18"))
        fb.grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(fb, text="Preparado Por:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(10, 2))
        self.preparado_var = tk.StringVar(value="Todos")
        self.cmb_preparado = ctk.CTkComboBox(fb, values=["Todos"], variable=self.preparado_var,
                                             width=160, command=lambda e: self.refresh())
        self.cmb_preparado.pack(side="left", padx=4, pady=4)

        ctk.CTkLabel(fb, text="Assinante:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(8, 2))
        self.assinante_var = tk.StringVar(value="Todos")
        self.cmb_assinante = ctk.CTkComboBox(fb, values=["Todos"], variable=self.assinante_var,
                                             width=160, command=lambda e: self.refresh())
        self.cmb_assinante.pack(side="left", padx=4, pady=4)

        ctk.CTkLabel(fb, text="De:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(8, 2))
        self._de_var = tk.StringVar()
        DateEntry(fb, textvariable=self._de_var, width=110).pack(side="left", padx=2, pady=4)
        self._de_var.trace_add("write", lambda *a: self.refresh())

        ctk.CTkLabel(fb, text="Até:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(4, 2))
        self._ate_var = tk.StringVar()
        DateEntry(fb, textvariable=self._ate_var, width=110).pack(side="left", padx=2, pady=4)
        self._ate_var.trace_add("write", lambda *a: self.refresh())

        ctk.CTkButton(fb, text="✖ Limpar", width=80, height=26,
                      fg_color="gray50",
                      command=lambda: (self.search_var.set(""), self.assinante_var.set("Todos"),
                                       self.preparado_var.set("Todos"),
                                       self._de_var.set(""), self._ate_var.set(""), self.refresh())
                      ).pack(side="left", padx=8)

        self.lbl_count = ctk.CTkLabel(fb, text="", font=ctk.CTkFont(size=11),
                                      text_color=("#1F4E79", "#5ba3d9"))
        self.lbl_count.pack(side="right", padx=12)

    def _build_table(self):
        frame = ctk.CTkFrame(self, corner_radius=0)
        frame.grid(row=2, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Env.Treeview", rowheight=26, font=('Segoe UI', 10))
        style.configure("Env.Treeview.Heading", font=('Segoe UI', 10, 'bold'),
                        background="#1F4E79", foreground="white")
        style.map("Env.Treeview", background=[("selected", "#2c6fad")])

        cols = ("id", "numero", "assunto", "preparado_por", "assinante",
                "destinatario", "instituicao", "data_envio", "ficheiro")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings",
                                 style="Env.Treeview", selectmode="browse")

        col_config = [
            ("id", "ID", 40), ("numero", "Nº Doc", 200), ("assunto", "Assunto", 280),
            ("preparado_por", "Preparado Por", 140), ("assinante", "Assinante", 140),
            ("destinatario", "Destinatário", 140), ("instituicao", "Instituição", 140),
            ("data_envio", "Data Envio", 100), ("ficheiro", "Ficheiro", 80),
        ]
        for col, heading, width in col_config:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=40)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<Double-1>", lambda e: self.open_edit())
        self.tree.bind("<Return>",   lambda e: self.open_edit())
        self.tree.bind("<Delete>",   lambda e: self.delete_selected())
        enable_sorting(self.tree, [c for c in cols if c != "id"])
        enable_mousewheel(self.tree)

    def refresh(self, *args):
        assinantes = ["Todos"] + self._get_assinantes()
        self.cmb_assinante.configure(values=assinantes)
        preparados = ["Todos"] + self._get_preparados()
        self.cmb_preparado.configure(values=preparados)

        filters = {}
        s = self.search_var.get().strip()
        if s:
            filters['search'] = s
        ass = self.assinante_var.get()
        if ass and ass != "Todos":
            filters['assinante'] = ass
        prep = self.preparado_var.get()
        if prep and prep != "Todos":
            filters['preparado_por'] = prep
        de  = display_to_iso(self._de_var.get().strip())
        ate = display_to_iso(self._ate_var.get().strip())
        if de:  filters['data_inicio'] = de
        if ate: filters['data_fim']    = ate

        rows = self.db.get_all_enviados(filters)
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in rows:
            self.tree.insert("", "end", iid=str(r['id']), values=(
                r['id'], r.get('numero', ''), r.get('assunto', ''),
                r.get('preparado_por', ''), r.get('assinante', ''),
                r.get('destinatario_nome', ''), r.get('instituicao', ''),
                iso_to_display(r.get('data_envio', '')),
                "📎" if r.get('ficheiro_path') else "",
            ))
        total = len(rows)
        self.lbl_count.configure(text=f"📄 {total} documento{'s' if total != 1 else ''}")

        # Actualiza também os indicadores globais (alertas, crachás, rodapé)
        app = self.winfo_toplevel()
        if hasattr(app, 'refresh_indicators'):
            app.refresh_indicators()

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def open_new(self):
        EnviadoForm(self, self.db, self.config, None, self.refresh)

    def duplicate_selected(self):
        eid = self._get_selected_id()
        if eid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento para duplicar.", parent=self)
            return
        EnviadoForm(self, self.db, self.config, None, self.refresh, clone_id=eid)

    def open_edit(self):
        eid = self._get_selected_id()
        if eid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento.", parent=self)
            return
        EnviadoForm(self, self.db, self.config, eid, self.refresh)

    def delete_selected(self):
        eid = self._get_selected_id()
        if eid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento.", parent=self)
            return
        doc = self.db.get_enviado(eid)
        num = doc.get('numero', str(eid)) if doc else str(eid)
        if messagebox.askyesno("Confirmar",
                               f"Eliminar o documento:\n{num}?\n\n"
                               "(Poderá restaurá-lo em Configurações → ♻️ Reciclagem "
                               "durante 30 dias.)", parent=self):
            self.db.delete_enviado(eid)
            self.refresh()

    def exportar(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="documentos_enviados.xlsx",
            parent=self
        )
        if filepath:
            busy = BusyDialog(self, "A exportar para Excel...")
            try:
                ok = self.db.export_enviados_excel(filepath)
            finally:
                busy.fechar()
            if ok:
                messagebox.showinfo("Sucesso", f"Exportado para:\n{filepath}", parent=self)
            else:
                messagebox.showerror("Erro", "Falha ao exportar.", parent=self)

    def enviar_email(self):
        eid = self._get_selected_id()
        if eid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento primeiro.", parent=self)
            return
        doc = self.db.get_enviado(eid)
        if not doc:
            return
        EmailDialog(self, config=self.config, ficheiro_path=doc.get('ficheiro_path', ''),
                    assunto=f"Ref: {doc.get('numero', '')} — {doc.get('assunto', '')}",
                    corpo=f"Exmo(a) Senhor(a),\n\nEnvio em anexo o documento:\n"
                          f"Nº: {doc.get('numero', '')}\nAssunto: {doc.get('assunto', '')}\n"
                          f"Data de Envio: {doc.get('data_envio', '')}\n\n"
                          f"Com os melhores cumprimentos,\n{self.config.get('utilizador', 'DNE/MIREME')}")

    def abrir_ficheiro(self):
        eid = self._get_selected_id()
        if eid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento primeiro.", parent=self)
            return
        doc = self.db.get_enviado(eid)
        if not doc:
            return
        path = doc.get('ficheiro_path', '')
        if not path or not os.path.exists(path):
            messagebox.showwarning("Ficheiro não encontrado",
                                   f"Nenhum ficheiro anexado ou o ficheiro foi movido.\n"
                                   f"Caminho: {path or '—'}", parent=self)
            return
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir:\n{e}", parent=self)

    def imprimir(self):
        eid = self._get_selected_id()
        if eid is None:
            messagebox.showwarning("Aviso", "Seleccione um documento primeiro.", parent=self)
            return
        doc = self.db.get_enviado(eid)
        if not doc:
            return
        conteudo = f"""
================================================================================
             FICHA DE DOCUMENTO ENVIADO — DNE | MIREME
================================================================================

  Nº Documento   : {doc.get('numero', '—')}
  Assunto        : {doc.get('assunto', '—')}
  Preparado Por  : {doc.get('preparado_por', '—')}
  Assinante      : {doc.get('assinante', '—')}

  Destinatário   : {doc.get('destinatario_nome', '—')}  ({doc.get('destinatario_cargo', '—')})
  Instituição    : {doc.get('instituicao', '—')}
  Data de Envio  : {iso_to_display(doc.get('data_envio', ''))}

  Ficheiro       : {doc.get('ficheiro_path', '—')}

  Observação:
  {doc.get('observacao', '—')}

================================================================================
  Impresso em: {datetime.now().strftime('%d/%m/%Y %H:%M')}
================================================================================
"""
        imprimir_com_dialogo(self, conteudo)

    def focus_search(self):
        self._search_entry.focus_set()

    def on_activate(self):
        self.refresh()


class EnviadoForm(ctk.CTkToplevel):
    TEMPLATES_ASSUNTO = [
        "Encaminhamento de documentação",
        "Resposta à solicitação recebida",
        "Nota de serviço interna",
        "Relatório de actividades do sector",
        "Informação sobre actividades",
        "Solicitação de dados/informação",
        "Carta de apresentação",
    ]

    def __init__(self, parent, db, config, record_id, callback, clone_id=None):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.record_id = record_id
        self.callback = callback
        self.title("Novo Documento Enviado" if not record_id else "Editar Documento Enviado")
        self.geometry("740x580")
        self.grab_set()

        self._vars = {}
        self._nomes_contactos = self._get_nomes()
        self._build_form()

        if record_id:
            self._load_data(record_id)
        elif clone_id:
            self._clone_data(clone_id)

        self.bind("<Control-s>", lambda e: self._save())
        enable_unsaved_changes_guard(self)

    def _get_nomes(self):
        rows = self.db.get_all_contactos()
        return [r['nome'] for r in rows]

    def _lbl_entry(self, parent, row, col, label, var_key, width=280):
        ctk.CTkLabel(parent, text=label, anchor="e", width=130).grid(
            row=row, column=col * 2, padx=(10, 4), pady=6, sticky="e")
        var = tk.StringVar()
        entry = ctk.CTkEntry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=col * 2 + 1, padx=(0, 10), pady=6, sticky="w")
        self._vars[var_key] = var
        return entry

    def _build_form(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(self)
        scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        f = scroll

        # Nº Documento + sugestão automática (A1)
        ctk.CTkLabel(f, text="Nº Documento", anchor="e", width=130).grid(
            row=0, column=0, padx=(10, 4), pady=6, sticky="e")
        self._vars['numero'] = tk.StringVar()
        num_frame = ctk.CTkFrame(f, fg_color="transparent")
        num_frame.grid(row=0, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")
        ctk.CTkEntry(num_frame, textvariable=self._vars['numero'], width=240).pack(side="left")
        ctk.CTkButton(num_frame, text="🔢 Sugerir", width=90, height=28,
                      fg_color="#5a6e8a",
                      command=self._sugerir_numero).pack(side="left", padx=(6, 0))

        # Assunto + templates (D2)
        ctk.CTkLabel(f, text="Assunto *", anchor="e", width=130).grid(row=1, column=0, padx=(10, 4), pady=6, sticky="e")
        self._vars['assunto'] = tk.StringVar()
        assunto_frame = ctk.CTkFrame(f, fg_color="transparent")
        assunto_frame.grid(row=1, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")
        ctk.CTkEntry(assunto_frame, textvariable=self._vars['assunto'], width=400).pack(side="left")
        ctk.CTkButton(assunto_frame, text="💡", width=32, height=28,
                      fg_color="#5a6e8a",
                      command=self._mostrar_templates).pack(side="left", padx=(4, 0))

        ctk.CTkLabel(f, text="Preparado Por", anchor="e", width=130).grid(row=2, column=0, padx=(10, 4), pady=6, sticky="e")
        self._vars['preparado_por'] = tk.StringVar()
        ctk.CTkComboBox(f, values=self._nomes_contactos, variable=self._vars['preparado_por'],
                        width=240).grid(row=2, column=1, padx=(0, 10), pady=6, sticky="w")

        ctk.CTkLabel(f, text="Assinante", anchor="e", width=130).grid(row=2, column=2, padx=(10, 4), pady=6, sticky="e")
        self._vars['assinante'] = tk.StringVar()
        ctk.CTkComboBox(f, values=self._nomes_contactos, variable=self._vars['assinante'],
                        width=240).grid(row=2, column=3, padx=(0, 10), pady=6, sticky="w")

        e_dest = self._lbl_entry(f, 3, 0, "Nome do Destinatário", "destinatario_nome", 240)
        attach_autocomplete(e_dest, self._vars['destinatario_nome'],
                            lambda: self.db.get_autocomplete('destinatario_nome'),
                            on_select=self._autofill_destinatario)
        # Também preenche ao sair do campo depois de digitar o nome à mão
        e_dest.bind('<FocusOut>', lambda e: self._autofill_destinatario(), add='+')
        e_dcargo = self._lbl_entry(f, 3, 1, "Cargo do Destinatário", "destinatario_cargo", 240)
        attach_autocomplete(e_dcargo, self._vars['destinatario_cargo'],
                            lambda: self.db.get_autocomplete('destinatario_cargo'))
        e_inst = self._lbl_entry(f, 4, 0, "Instituição", "instituicao", 300)
        attach_autocomplete(e_inst, self._vars['instituicao'],
                            lambda: self.db.get_autocomplete('instituicao'))

        ctk.CTkLabel(f, text="Data Envio", anchor="e", width=130).grid(
            row=5, column=0, padx=(10, 4), pady=6, sticky="e")
        self._vars['data_envio'] = tk.StringVar()
        DateEntry(f, textvariable=self._vars['data_envio'], width=160).grid(
            row=5, column=1, padx=(0, 10), pady=6, sticky="w")

        ctk.CTkLabel(f, text="Observação", anchor="e", width=130).grid(row=6, column=0, padx=(10, 4), pady=6, sticky="ne")
        self._obs_text = ctk.CTkTextbox(f, width=480, height=70)
        self._obs_text.grid(row=6, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")

        ctk.CTkLabel(f, text="Ficheiro", anchor="e", width=130).grid(row=7, column=0, padx=(10, 4), pady=6, sticky="e")
        ff = ctk.CTkFrame(f, fg_color="transparent")
        ff.grid(row=7, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")
        self._vars['ficheiro_path'] = tk.StringVar()
        ctk.CTkEntry(ff, textvariable=self._vars['ficheiro_path'], width=360).pack(side="left", padx=(0, 6))
        ctk.CTkButton(ff, text="📂 Procurar", width=100, command=self._pick_file_and_extract).pack(side="left")

        # ── Indicador de extracção automática ────────────────────────────────
        self.lbl_extracao = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=11),
                                          text_color="#27ae60")
        self.lbl_extracao.grid(row=8, column=0, columnspan=4, pady=(0, 4))

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

    def _autofill_destinatario(self, *_):
        """Ao reconhecer o nome do destinatário na base de dados, preenche
        automaticamente o Cargo do Destinatário e a Instituição (só se estiverem
        vazios, para não apagar o que foi escrito à mão)."""
        nome = self._vars.get('destinatario_nome')
        if nome is None:
            return
        dados = self.db.lookup_destinatario(nome.get())
        if not dados:
            return
        if dados.get('destinatario_cargo') and not self._vars['destinatario_cargo'].get().strip():
            self._vars['destinatario_cargo'].set(dados['destinatario_cargo'])
        if dados.get('instituicao') and not self._vars['instituicao'].get().strip():
            self._vars['instituicao'].set(dados['instituicao'])

    def _sugerir_numero(self):
        sugestao = self.db.suggest_next_numero('enviados')
        if sugestao:
            self._vars['numero'].set(sugestao)
        else:
            messagebox.showinfo("Sugestão", "Sem documentos anteriores para inferir o padrão.", parent=self)

    def _mostrar_templates(self):
        top = tk.Toplevel(self)
        top.title("Sugestões de Assunto")
        top.geometry("360x240")
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
        r = self.db.get_enviado(clone_id)
        if not r:
            return
        for key in ('preparado_por', 'assinante', 'destinatario_nome',
                    'destinatario_cargo', 'instituicao'):
            if key in self._vars and r.get(key):
                self._vars[key].set(r[key])
        obs = r.get('observacao', '') or ''
        if obs:
            self._obs_text.delete("1.0", "end")
            self._obs_text.insert("1.0", obs)

    def _pick_file_and_extract(self):
        """Abre diálogo de ficheiro e tenta preencher Nº, Assunto e
        Destinatário (via "Att.") automaticamente a partir do documento."""
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
            dados = extrair_dados_enviado(path)
        except Exception as e:
            self.lbl_extracao.configure(
                text=f"⚠️ Erro inesperado: {e}", text_color="#e74c3c")
            return

        if '_erro' in dados:
            self.lbl_extracao.configure(
                text=f"⚠️ {dados['_erro']}", text_color="#e74c3c")
            return

        if '_formato' in dados and len(dados) == 1:
            self.lbl_extracao.configure(
                text=f"ℹ️ {dados['_formato']} Preencha os campos manualmente.",
                text_color="#e67e22")
            return

        nomes_pt = {
            'numero': 'Nº Documento',
            'assunto': 'Assunto',
            'destinatario_nome': 'Nome do Destinatário',
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

    def _load_data(self, rid):
        r = self.db.get_enviado(rid)
        if not r:
            return
        for key in ('numero', 'assunto', 'preparado_por', 'assinante',
                    'destinatario_nome', 'destinatario_cargo', 'instituicao', 'ficheiro_path'):
            if key in self._vars and r.get(key):
                self._vars[key].set(r[key])
        self._vars['data_envio'].set(iso_to_display(r.get('data_envio', '')))
        obs = r.get('observacao', '') or ''
        self._obs_text.delete("1.0", "end")
        self._obs_text.insert("1.0", obs)

    def _save(self):
        assunto = self._vars['assunto'].get().strip()
        if not assunto:
            messagebox.showerror("Erro", "Assunto é obrigatório.", parent=self)
            return

        numero = self._vars['numero'].get().strip()
        if numero:
            assunto_dup = self.db.find_numero_duplicado('enviados', numero, self.record_id)
            if assunto_dup is not None:
                if not messagebox.askyesno(
                    "Número já existe",
                    f"O nº de documento \"{numero}\" já está atribuído a:\n"
                    f"{assunto_dup or '(sem assunto)'}\n\n"
                    f"Deseja continuar e guardar mesmo assim?",
                    parent=self):
                    return

        data = {
            'numero': self._vars['numero'].get().strip(),
            'assunto': assunto,
            'preparado_por': self._vars['preparado_por'].get().strip(),
            'assinante': self._vars['assinante'].get().strip(),
            'destinatario_nome': self._vars['destinatario_nome'].get().strip(),
            'destinatario_cargo': self._vars['destinatario_cargo'].get().strip(),
            'instituicao': self._vars['instituicao'].get().strip(),
            'data_envio': display_to_iso(self._vars['data_envio'].get().strip()),
            'ficheiro_path': self._vars['ficheiro_path'].get().strip(),
            'observacao': self._obs_text.get("1.0", "end").strip(),
        }
        try:
            if self.record_id:
                self.db.update_enviado(self.record_id, data)
            else:
                self.db.insert_enviado(data)
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
        labels = ["Nº Documento", "Assunto", "Preparado Por", "Assinante",
                  "Nome do Destinatário", "Cargo do Destinatário", "Instituição",
                  "Data de Envio", "Observação", "Ficheiro"]
        vals = parse_clipboard_fields(texto, labels)
        MAP = {
            "Nº Documento": "numero", "Assunto": "assunto",
            "Preparado Por": "preparado_por", "Assinante": "assinante",
            "Nome do Destinatário": "destinatario_nome",
            "Cargo do Destinatário": "destinatario_cargo",
            "Instituição": "instituicao", "Data de Envio": "data_envio",
            "Ficheiro": "ficheiro_path",
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
            f"Assunto: {self._vars['assunto'].get().strip()}",
            f"Preparado Por: {self._vars['preparado_por'].get().strip()}",
            f"Assinante: {self._vars['assinante'].get().strip()}",
            f"Nome do Destinatário: {self._vars['destinatario_nome'].get().strip()}",
            f"Cargo do Destinatário: {self._vars['destinatario_cargo'].get().strip()}",
            f"Instituição: {self._vars['instituicao'].get().strip()}",
            f"Data de Envio: {self._vars['data_envio'].get().strip()}",
            f"Observação:\n{self._obs_text.get('1.0', 'end').strip()}",
            f"Ficheiro: {self._vars['ficheiro_path'].get().strip()}",
        ]
        texto = "\n".join(linhas)
        self.clipboard_clear()
        self.clipboard_append(texto)
        messagebox.showinfo("Copiado", "Conteúdo copiado para a área de transferência.", parent=self)
