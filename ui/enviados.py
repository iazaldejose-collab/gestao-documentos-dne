import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import customtkinter as ctk


def iso_to_display(iso_str):
    if not iso_str:
        return ""
    try:
        return datetime.strptime(iso_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return iso_str


def display_to_iso(disp):
    if not disp:
        return ""
    try:
        return datetime.strptime(disp, "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        return disp


class EnviadosFrame(ctk.CTkFrame):
    def __init__(self, parent, db, config):
        super().__init__(parent, corner_radius=0)
        self.db = db
        self.config = config
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_toolbar()
        self._build_table()
        self.refresh()

    def _build_toolbar(self):
        tb = ctk.CTkFrame(self, height=56, corner_radius=0, fg_color=("gray90", "gray20"))
        tb.grid(row=0, column=0, sticky="ew")
        tb.grid_columnconfigure(3, weight=1)

        self.search_var = tk.StringVar()
        ctk.CTkLabel(tb, text="🔍").grid(row=0, column=0, padx=(10, 2), pady=10)
        search_entry = ctk.CTkEntry(tb, textvariable=self.search_var, placeholder_text="Pesquisar e pressionar Enter...",
                     width=230)
        search_entry.grid(row=0, column=1, padx=4, pady=10)
        search_entry.bind("<Return>", lambda e: self.refresh())

        self.assinante_var = tk.StringVar(value="Todos")
        assinantes = ["Todos"] + self._get_assinantes()
        self.cmb_assinante = ctk.CTkComboBox(tb, values=assinantes, variable=self.assinante_var,
                                             width=200, command=lambda e: self.refresh())
        self.cmb_assinante.grid(row=0, column=2, padx=4, pady=10)

        btn_frame = ctk.CTkFrame(tb, fg_color="transparent")
        btn_frame.grid(row=0, column=4, padx=10, pady=6, sticky="e")
        ctk.CTkButton(btn_frame, text="+ Novo", width=80, command=self.open_new,
                      fg_color="#1F4E79").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="✏️ Editar", width=90, command=self.open_edit,
                      fg_color="#2c6fad").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="🗑️ Eliminar", width=100, command=self.delete_selected,
                      fg_color="#c0392b").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="📤 Exportar", width=100, command=self.exportar,
                      fg_color="#27ae60").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="🔄", width=36, command=self.refresh,
                      fg_color="gray50").pack(side="left", padx=3)

    def _get_assinantes(self):
        rows = self.db.get_all_enviados()
        seen = set()
        result = []
        for r in rows:
            a = r.get('assinante', '')
            if a and a not in seen:
                seen.add(a)
                result.append(a)
        return result

    def _build_table(self):
        frame = ctk.CTkFrame(self, corner_radius=0)
        frame.grid(row=1, column=0, sticky="nsew")
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

    def refresh(self, *args):
        filters = {}
        s = self.search_var.get().strip()
        if s:
            filters['search'] = s
        ass = self.assinante_var.get()
        if ass and ass != "Todos":
            filters['assinante'] = ass

        rows = self.db.get_all_enviados(filters)
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in rows:
            has_file = "✔" if r.get('ficheiro_path') else ""
            self.tree.insert("", "end", iid=str(r['id']), values=(
                r['id'], r.get('numero', ''), r.get('assunto', ''),
                r.get('preparado_por', ''), r.get('assinante', ''),
                r.get('destinatario_nome', ''), r.get('instituicao', ''),
                iso_to_display(r.get('data_envio', '')), has_file,
            ))

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def open_new(self):
        EnviadoForm(self, self.db, self.config, None, self.refresh)

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
        if messagebox.askyesno("Confirmar", "Eliminar este documento?", parent=self):
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
            if self.db.export_enviados_excel(filepath):
                messagebox.showinfo("Sucesso", f"Exportado para:\n{filepath}", parent=self)
            else:
                messagebox.showerror("Erro", "Falha ao exportar.", parent=self)

    def on_activate(self):
        self.refresh()


class EnviadoForm(ctk.CTkToplevel):
    def __init__(self, parent, db, config, record_id, callback):
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

        self._lbl_entry(f, 0, 0, "Nº Documento", "numero", 300)

        ctk.CTkLabel(f, text="Assunto *", anchor="e", width=130).grid(row=1, column=0, padx=(10, 4), pady=6, sticky="e")
        self._vars['assunto'] = tk.StringVar()
        ctk.CTkEntry(f, textvariable=self._vars['assunto'], width=480).grid(
            row=1, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")

        ctk.CTkLabel(f, text="Preparado Por", anchor="e", width=130).grid(row=2, column=0, padx=(10, 4), pady=6, sticky="e")
        self._vars['preparado_por'] = tk.StringVar()
        ctk.CTkComboBox(f, values=self._nomes_contactos, variable=self._vars['preparado_por'],
                        width=240).grid(row=2, column=1, padx=(0, 10), pady=6, sticky="w")

        ctk.CTkLabel(f, text="Assinante", anchor="e", width=130).grid(row=2, column=2, padx=(10, 4), pady=6, sticky="e")
        self._vars['assinante'] = tk.StringVar()
        ctk.CTkComboBox(f, values=self._nomes_contactos, variable=self._vars['assinante'],
                        width=240).grid(row=2, column=3, padx=(0, 10), pady=6, sticky="w")

        self._lbl_entry(f, 3, 0, "Nome do Destinatário", "destinatario_nome", 240)
        self._lbl_entry(f, 3, 1, "Cargo do Destinatário", "destinatario_cargo", 240)
        self._lbl_entry(f, 4, 0, "Instituição", "instituicao", 300)
        self._lbl_entry(f, 5, 0, "Data Envio (DD/MM/AAAA)", "data_envio", 160)

        ctk.CTkLabel(f, text="Observação", anchor="e", width=130).grid(row=6, column=0, padx=(10, 4), pady=6, sticky="ne")
        self._obs_text = ctk.CTkTextbox(f, width=480, height=70)
        self._obs_text.grid(row=6, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")

        ctk.CTkLabel(f, text="Ficheiro", anchor="e", width=130).grid(row=7, column=0, padx=(10, 4), pady=6, sticky="e")
        ff = ctk.CTkFrame(f, fg_color="transparent")
        ff.grid(row=7, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")
        self._vars['ficheiro_path'] = tk.StringVar()
        ctk.CTkEntry(ff, textvariable=self._vars['ficheiro_path'], width=360).pack(side="left", padx=(0, 6))
        ctk.CTkButton(ff, text="📂 Procurar", width=100, command=self._pick_file).pack(side="left")

        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=1, column=0, pady=10)
        ctk.CTkButton(btn_frame, text="💾 Guardar", width=120, command=self._save,
                      fg_color="#1F4E79").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="❌ Cancelar", width=100, command=self.destroy,
                      fg_color="gray50").pack(side="left", padx=10)

    def _pick_file(self):
        path = filedialog.askopenfilename(parent=self)
        if path:
            self._vars['ficheiro_path'].set(path)

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
        self._obs_text.insert("1.0", obs)

    def _save(self):
        assunto = self._vars['assunto'].get().strip()
        if not assunto:
            messagebox.showerror("Erro", "Assunto é obrigatório.", parent=self)
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
