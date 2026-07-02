import re
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk

from ui.widgets import enable_sorting, enable_mousewheel, BusyDialog, enable_unsaved_changes_guard


class ContactosFrame(ctk.CTkFrame):
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
        tb.grid_columnconfigure(2, weight=1)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        ctk.CTkLabel(tb, text="🔍").grid(row=0, column=0, padx=(10, 2), pady=10)
        ctk.CTkEntry(tb, textvariable=self.search_var, placeholder_text="Pesquisar por nome, departamento, telefone...",
                     width=260).grid(row=0, column=1, padx=4, pady=10)

        btn_frame = ctk.CTkFrame(tb, fg_color="transparent")
        btn_frame.grid(row=0, column=3, padx=10, pady=6, sticky="e")
        ctk.CTkButton(btn_frame, text="+ Adicionar", width=100, command=self.open_new,
                      fg_color="#1F4E79").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="✏️ Editar", width=90, command=self.open_edit,
                      fg_color="#2c6fad").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="🗑️ Eliminar", width=100, command=self.delete_selected,
                      fg_color="#c0392b").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="📞 Chamar", width=90, command=self.call_contact,
                      fg_color="#16a085").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="💬 WhatsApp", width=105, command=self.whatsapp_contact,
                      fg_color="#25D366", text_color="white", hover_color="#1da851").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="📧 Email", width=80, command=self.send_email,
                      fg_color="#8e44ad").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="📋 Copiar", width=80, command=self.copy_contact,
                      fg_color="#e67e22").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="📤 Exportar", width=100, command=self.exportar,
                      fg_color="#27ae60").pack(side="left", padx=3)

    def _build_table(self):
        frame = ctk.CTkFrame(self, corner_radius=0)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Cont.Treeview", rowheight=26, font=('Segoe UI', 10))
        style.configure("Cont.Treeview.Heading", font=('Segoe UI', 10, 'bold'),
                        background="#1F4E79", foreground="white")
        style.map("Cont.Treeview", background=[("selected", "#2c6fad")])

        cols = ("numero", "nome", "email", "telefone", "departamento", "cargo")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings",
                                 style="Cont.Treeview", selectmode="browse")

        col_config = [
            ("numero", "Nº", 40), ("nome", "Nome", 200), ("email", "Email", 220),
            ("telefone", "Telefone", 140), ("departamento", "Departamento", 220), ("cargo", "Cargo", 100),
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
        self.tree.bind("<Button-3>", self._context_menu)
        self.tree.bind("<Return>",   lambda e: self.open_edit())
        self.tree.bind("<Delete>",   lambda e: self.delete_selected())
        enable_sorting(self.tree, cols)
        enable_mousewheel(self.tree)

        # Menu de contexto (clique direito)
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label="📞  Chamar",   command=self.call_contact)
        self._menu.add_command(label="💬  WhatsApp", command=self.whatsapp_contact)
        self._menu.add_command(label="📧  Email",    command=self.send_email)
        self._menu.add_command(label="📋  Copiar",   command=self.copy_contact)
        self._menu.add_separator()
        self._menu.add_command(label="✏️  Editar",   command=self.open_edit)
        self._menu.add_command(label="🗑️  Eliminar", command=self.delete_selected)

    def _context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            try:
                self._menu.tk_popup(event.x_root, event.y_root)
            finally:
                self._menu.grab_release()

    def refresh(self, *args):
        s = self.search_var.get().strip() or None
        rows = self.db.get_all_contactos(s)
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in rows:
            self.tree.insert("", "end", iid=str(r['id']), values=(
                r.get('numero', ''), r.get('nome', ''), r.get('email', ''),
                r.get('telefone', ''), r.get('departamento', ''), r.get('cargo', ''),
            ))

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def _get_selected_row(self):
        rid = self._get_selected_id()
        if rid is None:
            return None
        return self.db.get_contacto(rid)

    def open_new(self):
        ContactoForm(self, self.db, None, self.refresh)

    def open_edit(self):
        rid = self._get_selected_id()
        if rid is None:
            messagebox.showwarning("Aviso", "Seleccione um contacto.", parent=self)
            return
        ContactoForm(self, self.db, rid, self.refresh)

    def delete_selected(self):
        rid = self._get_selected_id()
        if rid is None:
            messagebox.showwarning("Aviso", "Seleccione um contacto.", parent=self)
            return
        contacto = self.db.get_contacto(rid)
        nome = contacto.get('nome', str(rid)) if contacto else str(rid)
        if messagebox.askyesno("Confirmar", f"Eliminar o contacto:\n{nome}?", parent=self):
            self.db.delete_contacto(rid)
            self.refresh()

    def send_email(self):
        row = self._get_selected_row()
        if not row:
            messagebox.showwarning("Aviso", "Seleccione um contacto.", parent=self)
            return
        email = row.get('email', '')
        if email:
            webbrowser.open(f"mailto:{email}")
        else:
            messagebox.showwarning("Aviso", "Este contacto não tem email.", parent=self)

    def _numeros_do_contacto(self, row):
        """Extrai os números de telefone do campo 'telefone', que pode conter
        vários números separados por / , ; ou 'ou' (ex: '824195400 / 840495452').
        Devolve lista de números limpos (só dígitos e + inicial)."""
        telefone = (row.get('telefone') or '').strip()
        if not telefone:
            return []
        numeros = []
        for parte in re.split(r'[/,;]|\bou\b', telefone, flags=re.IGNORECASE):
            n = re.sub(r'[^\d+]', '', parte)
            if n.startswith('+'):
                n = '+' + n[1:].replace('+', '')
            else:
                n = n.replace('+', '')
            if len(re.sub(r'\D', '', n)) >= 6:
                numeros.append(n)
        return numeros

    def _escolher_numero(self, numeros, titulo, callback):
        """Se o contacto tiver vários números, deixa o utilizador escolher
        qual usar; com um único número, usa-o directamente."""
        if len(numeros) == 1:
            callback(numeros[0])
            return
        win = ctk.CTkToplevel(self)
        win.title(titulo)
        win.resizable(False, False)
        win.grab_set()
        ctk.CTkLabel(win, text="Este contacto tem vários números.\nEscolha qual usar:",
                     font=ctk.CTkFont(size=12)).pack(padx=24, pady=(16, 8))
        for n in numeros:
            ctk.CTkButton(win, text=f"📱 {n}", width=200, fg_color="#1F4E79",
                          command=lambda nn=n: (win.destroy(), callback(nn))).pack(padx=24, pady=4)
        ctk.CTkButton(win, text="Cancelar", width=120, fg_color="gray50",
                      command=win.destroy).pack(padx=24, pady=(10, 16))

    def call_contact(self):
        row = self._get_selected_row()
        if not row:
            messagebox.showwarning("Aviso", "Seleccione um contacto.", parent=self)
            return
        numeros = self._numeros_do_contacto(row)
        if not numeros:
            messagebox.showwarning("Aviso", "Este contacto não tem telefone válido.", parent=self)
            return
        nome = row.get('nome', '')

        def _ligar(numero):
            if not messagebox.askyesno(
                    "Confirmar chamada",
                    f"Ligar para:\n{nome}\n{numero}\n\n"
                    f"A chamada será feita através do telemóvel emparelhado "
                    f"(Vínculo do Telemóvel).",
                    parent=self):
                return
            try:
                webbrowser.open(f"tel:{numero}")
            except Exception as e:
                messagebox.showerror(
                    "Erro",
                    f"Não foi possível iniciar a chamada:\n{e}\n\n"
                    f"Verifique se o Vínculo do Telemóvel está instalado, "
                    f"o telemóvel ligado e as chamadas activadas.",
                    parent=self)

        self._escolher_numero(numeros, "Escolher número", _ligar)

    def whatsapp_contact(self):
        """Abre uma conversa de WhatsApp com o contacto seleccionado
        (WhatsApp Desktop se instalado, senão WhatsApp Web)."""
        row = self._get_selected_row()
        if not row:
            messagebox.showwarning("Aviso", "Seleccione um contacto.", parent=self)
            return
        numeros = self._numeros_do_contacto(row)
        if not numeros:
            messagebox.showwarning("Aviso", "Este contacto não tem telefone válido.", parent=self)
            return

        def _abrir(numero):
            digitos = re.sub(r'\D', '', numero)
            # wa.me exige formato internacional sem '+'; números moçambicanos
            # de 9 dígitos começados por 8 recebem o indicativo 258
            if len(digitos) == 9 and digitos.startswith('8'):
                digitos = '258' + digitos
            webbrowser.open(f"https://wa.me/{digitos}")

        self._escolher_numero(numeros, "Escolher número", _abrir)

    def copy_contact(self):
        row = self._get_selected_row()
        if not row:
            messagebox.showwarning("Aviso", "Seleccione um contacto.", parent=self)
            return
        text = f"{row.get('nome', '')} | {row.get('email', '')} | {row.get('telefone', '')}"
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copiado", f"Contacto copiado:\n{text}", parent=self)

    def exportar(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="contactos.xlsx",
            parent=self
        )
        if filepath:
            busy = BusyDialog(self, "A exportar para Excel...")
            try:
                ok = self.db.export_contactos_excel(filepath)
            finally:
                busy.fechar()
            if ok:
                messagebox.showinfo("Sucesso", f"Exportado para:\n{filepath}", parent=self)
            else:
                messagebox.showerror("Erro", "Falha ao exportar.", parent=self)

    def on_activate(self):
        self.refresh()


class ContactoForm(ctk.CTkToplevel):
    def __init__(self, parent, db, record_id, callback):
        super().__init__(parent)
        self.db = db
        self.record_id = record_id
        self.callback = callback
        self.title("Novo Contacto" if not record_id else "Editar Contacto")
        self.geometry("520x400")
        self.grab_set()
        self._vars = {}
        self._build_form()
        if record_id:
            self._load_data(record_id)

        self.bind("<Control-s>", lambda e: self._save())
        enable_unsaved_changes_guard(self)

    def _lbl_entry(self, parent, row, label, var_key, width=300):
        ctk.CTkLabel(parent, text=label, anchor="e", width=120).grid(
            row=row, column=0, padx=(15, 4), pady=8, sticky="e")
        var = tk.StringVar()
        entry = ctk.CTkEntry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=1, padx=(0, 15), pady=8, sticky="w")
        self._vars[var_key] = var
        return entry

    def _build_form(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        f = ctk.CTkFrame(self)
        f.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        f.grid_columnconfigure(1, weight=1)

        self._lbl_entry(f, 0, "Número", "numero", 80)
        self._lbl_entry(f, 1, "Nome *", "nome", 300)
        self._lbl_entry(f, 2, "Email", "email", 300)
        self._lbl_entry(f, 3, "Telefone", "telefone", 200)

        ctk.CTkLabel(f, text="Departamento", anchor="e", width=120).grid(
            row=4, column=0, padx=(15, 4), pady=8, sticky="e")
        self._vars['departamento'] = tk.StringVar()
        depts = [
            "Direcção", "Dep. Planeamento Energético", "Dep. Estudos e Projectos",
            "Dep. Licenciamento e Fiscalização", "Dep. Eficiência Energética",
            "Dep. Energias Renováveis", "Rep. Administração e Finanças",
            "Transição Energética", "UIPCE"
        ]
        ctk.CTkComboBox(f, values=depts, variable=self._vars['departamento'],
                        width=300).grid(row=4, column=1, padx=(0, 15), pady=8, sticky="w")

        self._lbl_entry(f, 5, "Cargo", "cargo", 200)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=1, column=0, pady=10)
        ctk.CTkButton(btn_frame, text="💾 Guardar", width=120, command=self._save,
                      fg_color="#1F4E79").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="❌ Cancelar", width=100, command=self.destroy,
                      fg_color="gray50").pack(side="left", padx=10)

    def _load_data(self, rid):
        r = self.db.get_contacto(rid)
        if not r:
            return
        for key in ('nome', 'email', 'telefone', 'departamento', 'cargo'):
            if key in self._vars and r.get(key):
                self._vars[key].set(r[key])
        if r.get('numero'):
            self._vars['numero'].set(str(r['numero']))

    def _save(self):
        nome = self._vars['nome'].get().strip()
        if not nome:
            messagebox.showerror("Erro", "Nome é obrigatório.", parent=self)
            return

        email = self._vars['email'].get().strip()
        if email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            messagebox.showerror(
                "Email inválido",
                f'O endereço "{email}" não parece um email válido.\n\n'
                f"Use o formato: nome@dominio.com",
                parent=self)
            return

        telefone = self._vars['telefone'].get().strip()
        if telefone and not re.match(r'^[0-9+\s()\-]{6,20}$', telefone):
            messagebox.showerror(
                "Telefone inválido",
                f'O número "{telefone}" não parece um telefone válido.\n\n'
                f"Use apenas dígitos, espaços e os símbolos + ( ) -",
                parent=self)
            return
        try:
            numero = int(self._vars['numero'].get().strip()) if self._vars['numero'].get().strip() else None
        except ValueError:
            numero = None

        if numero is not None:
            for c in self.db.get_all_contactos():
                if c.get('numero') == numero and c.get('id') != self.record_id:
                    messagebox.showwarning(
                        "Número já existe",
                        f"O número de ordem {numero} já está atribuído a:\n"
                        f"{c.get('nome', '(sem nome)')}\n\n"
                        f"Por favor escolha outro número.",
                        parent=self)
                    return

        data = {
            'numero': numero,
            'nome': nome,
            'email': self._vars['email'].get().strip(),
            'telefone': self._vars['telefone'].get().strip(),
            'departamento': self._vars['departamento'].get().strip(),
            'cargo': self._vars['cargo'].get().strip(),
        }
        try:
            if self.record_id:
                self.db.update_contacto(self.record_id, data)
            else:
                self.db.insert_contacto(data)
            self.callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao guardar:\n{e}", parent=self)
