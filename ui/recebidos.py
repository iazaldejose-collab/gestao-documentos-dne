import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
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
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_toolbar()
        self._build_table()
        self.refresh()

    def _build_toolbar(self):
        tb = ctk.CTkFrame(self, height=56, corner_radius=0, fg_color=("gray90", "gray20"))
        tb.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        tb.grid_columnconfigure(3, weight=1)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        ctk.CTkLabel(tb, text="🔍").grid(row=0, column=0, padx=(10, 2), pady=10)
        ctk.CTkEntry(tb, textvariable=self.search_var, placeholder_text="Pesquisar...",
                     width=200).grid(row=0, column=1, padx=4, pady=10)

        self.tecnico_var = tk.StringVar(value="Todos")
        tecnicos = ["Todos"] + self._get_tecnicos()
        self.cmb_tecnico = ctk.CTkComboBox(tb, values=tecnicos, variable=self.tecnico_var,
                                           width=180, command=lambda e: self.refresh())
        self.cmb_tecnico.grid(row=0, column=2, padx=4, pady=10)

        self.status_var = tk.StringVar(value="Todos")
        statuses = ["Todos", "Dentro do Prazo", "Fora do Prazo", "Pendente", "Arquivado"]
        self.cmb_status = ctk.CTkComboBox(tb, values=statuses, variable=self.status_var,
                                          width=160, command=lambda e: self.refresh())
        self.cmb_status.grid(row=0, column=3, padx=4, pady=10, sticky="w")

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

    def _get_tecnicos(self):
        rows = self.db.get_all_recebidos()
        seen = set()
        result = []
        for r in rows:
            t = r.get('tecnico', '')
            if t and t not in seen:
                seen.add(t)
                result.append(t)
        return result

    def _build_table(self):
        frame = ctk.CTkFrame(self, corner_radius=0)
        frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
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
                "data_rec", "despacho", "tecnico", "data_resp", "dias", "status")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings",
                                 style="Custom.Treeview", selectmode="browse")

        col_config = [
            ("id", "ID", 40), ("numero", "Nº Documento", 220), ("proveniencia", "Proveniência", 120),
            ("remetente", "Remetente", 140), ("assunto", "Assunto", 260),
            ("data_rec", "Data Recepção", 100), ("despacho", "Despacho", 140),
            ("tecnico", "Técnico", 140), ("data_resp", "Data Resposta", 100),
            ("dias", "Dias", 50), ("status", "Status", 120),
        ]
        for col, heading, width in col_config:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=40)

        self.tree.tag_configure("dentro", background="#d4edda")
        self.tree.tag_configure("fora", background="#f8d7da")
        self.tree.tag_configure("pendente", background="#fff3cd")
        self.tree.tag_configure("arquivado", background="#e2e3e5")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", lambda e: self.open_edit())

    def refresh(self, *args):
        filters = {}
        search = self.search_var.get().strip()
        if search:
            filters['search'] = search
        tec = self.tecnico_var.get()
        if tec and tec != "Todos":
            filters['tecnico'] = tec
        st = self.status_var.get()
        if st and st != "Todos":
            filters['prazo_status'] = st

        rows = self.db.get_all_recebidos(filters)
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in rows:
            dias = calc_dias(r.get('data_recepcao', ''), r.get('data_resposta', ''))
            dias_str = str(dias) if dias is not None else ""
            status = r.get('prazo_status', '')
            tag = "pendente"
            if status == "Dentro do Prazo":
                tag = "dentro"
            elif status == "Fora do Prazo":
                tag = "fora"
            elif status == "Arquivado":
                tag = "arquivado"
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
                dias_str,
                status,
            ))

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def open_new(self):
        RecebidoForm(self, self.db, self.config, None, self.refresh)

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
        if messagebox.askyesno("Confirmar", "Eliminar este documento?", parent=self):
            self.db.delete_recebido(rid)
            self.refresh()

    def exportar(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="documentos_recebidos.xlsx",
            parent=self
        )
        if filepath:
            if self.db.export_recebidos_excel(filepath):
                messagebox.showinfo("Sucesso", f"Exportado para:\n{filepath}", parent=self)
            else:
                messagebox.showerror("Erro", "Falha ao exportar.", parent=self)

    def focus_search(self):
        try:
            for w in self.winfo_children():
                if hasattr(w, 'winfo_children'):
                    for child in w.winfo_children():
                        if isinstance(child, ctk.CTkEntry):
                            child.focus_set()
                            return
        except Exception:
            pass

    def on_activate(self):
        self.refresh()


class RecebidoForm(ctk.CTkToplevel):
    def __init__(self, parent, db, config, record_id, callback):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.record_id = record_id
        self.callback = callback
        self.title("Novo Documento Recebido" if not record_id else "Editar Documento Recebido")
        self.geometry("780x700")
        self.resizable(True, True)
        self.grab_set()

        self._vars = {}
        self._build_form()

        if record_id:
            self._load_data(record_id)

    def _lbl_entry(self, parent, row, col, label, var_key, width=280, required=False):
        lbl_text = label + (" *" if required else "")
        ctk.CTkLabel(parent, text=lbl_text, anchor="e", width=140).grid(
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
        self._lbl_entry(f, 0, 0, "Nº Documento", "numero", 320, required=True)
        self._lbl_entry(f, 1, 0, "Proveniência", "proveniencia", 320)
        self._lbl_entry(f, 2, 0, "Nome do Remetente", "remetente_nome", 320)
        self._lbl_entry(f, 3, 0, "Cargo do Remetente", "remetente_cargo", 320)

        ctk.CTkLabel(f, text="Assunto *", anchor="e", width=140).grid(row=4, column=0, padx=(10, 4), pady=6, sticky="e")
        self._vars['assunto'] = tk.StringVar()
        ctk.CTkEntry(f, textvariable=self._vars['assunto'], width=500).grid(
            row=4, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")

        self._lbl_entry(f, 5, 0, "Data Recepção (DD/MM/AAAA)", "data_recepcao", 160)
        self._lbl_entry(f, 5, 1, "Data Resposta (DD/MM/AAAA)", "data_resposta", 160)

        self._lbl_entry(f, 6, 0, "Despacho", "despacho", 320)
        self._lbl_entry(f, 7, 0, "Endereçado A", "endereçado_a", 320)
        self._lbl_entry(f, 8, 0, "Técnico", "tecnico", 320)

        ctk.CTkLabel(f, text="Status Prazo", anchor="e", width=140).grid(
            row=9, column=0, padx=(10, 4), pady=6, sticky="e")
        self._vars['prazo_status'] = tk.StringVar(value="Pendente")
        ctk.CTkComboBox(f, values=["Pendente", "Dentro do Prazo", "Fora do Prazo", "Arquivado"],
                        variable=self._vars['prazo_status'], width=200).grid(
            row=9, column=1, padx=(0, 10), pady=6, sticky="w")

        ctk.CTkLabel(f, text="Observação", anchor="e", width=140).grid(
            row=10, column=0, padx=(10, 4), pady=6, sticky="ne")
        self._obs_text = ctk.CTkTextbox(f, width=500, height=80)
        self._obs_text.grid(row=10, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")

        ctk.CTkLabel(f, text="Ficheiro", anchor="e", width=140).grid(
            row=11, column=0, padx=(10, 4), pady=6, sticky="e")
        file_frame = ctk.CTkFrame(f, fg_color="transparent")
        file_frame.grid(row=11, column=1, columnspan=3, padx=(0, 10), pady=6, sticky="w")
        self._vars['ficheiro_path'] = tk.StringVar()
        ctk.CTkEntry(file_frame, textvariable=self._vars['ficheiro_path'], width=380).pack(side="left", padx=(0, 6))
        ctk.CTkButton(file_frame, text="📂 Procurar", width=100, command=self._pick_file).pack(side="left")

        # Days info label
        self.lbl_dias = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=12))
        self.lbl_dias.grid(row=12, column=0, columnspan=4, pady=6)

        self._vars['data_recepcao'].trace_add("write", self._update_dias)
        self._vars['data_resposta'].trace_add("write", self._update_dias)

        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=1, column=0, pady=10)
        ctk.CTkButton(btn_frame, text="💾 Guardar", width=120, command=self._save,
                      fg_color="#1F4E79").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="❌ Cancelar", width=100, command=self.destroy,
                      fg_color="gray50").pack(side="left", padx=10)

    def _update_dias(self, *args):
        try:
            dr = display_to_iso(self._vars['data_recepcao'].get())
            resp = display_to_iso(self._vars['data_resposta'].get())
            dias = calc_dias(dr, resp if resp else None)
            if dias is not None:
                color = "green" if dias <= 5 else "red"
                self.lbl_dias.configure(text=f"Dias decorridos: {dias}", text_color=color)
        except Exception:
            pass

    def _pick_file(self):
        path = filedialog.askopenfilename(parent=self)
        if path:
            self._vars['ficheiro_path'].set(path)

    def _load_data(self, rid):
        r = self.db.get_recebido(rid)
        if not r:
            return
        for key in ('numero', 'proveniencia', 'remetente_nome', 'remetente_cargo',
                    'assunto', 'despacho', 'endereçado_a', 'tecnico', 'prazo_status', 'ficheiro_path'):
            if key in self._vars and r.get(key):
                self._vars[key].set(r[key])
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

        data = {
            'numero': numero,
            'proveniencia': self._vars['proveniencia'].get().strip(),
            'remetente_nome': self._vars['remetente_nome'].get().strip(),
            'remetente_cargo': self._vars['remetente_cargo'].get().strip(),
            'assunto': assunto,
            'data_recepcao': display_to_iso(self._vars['data_recepcao'].get().strip()),
            'despacho': self._vars['despacho'].get().strip(),
            'endereçado_a': self._vars['endereçado_a'].get().strip(),
            'tecnico': self._vars['tecnico'].get().strip(),
            'data_resposta': display_to_iso(self._vars['data_resposta'].get().strip()),
            'prazo_status': self._vars['prazo_status'].get(),
            'observacao': self._obs_text.get("1.0", "end").strip(),
            'ficheiro_path': self._vars['ficheiro_path'].get().strip(),
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
