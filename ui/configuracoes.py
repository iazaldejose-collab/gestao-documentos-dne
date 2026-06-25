import os
import json
import shutil
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

from ui.widgets import BusyDialog
from version import VERSION_FULL


class ConfiguracoesFrame(ctk.CTkFrame):
    def __init__(self, parent, db, config, config_path, on_save_callback):
        super().__init__(parent, corner_radius=0)
        self.db = db
        self.config = config
        self.config_path = config_path
        self.on_save_callback = on_save_callback

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._vars = {}
        self._build_ui()
        self._load_current()

    def _build_ui(self):
        header = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color=("gray90", "gray20"))
        header.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(header, text="⚙️  Configurações do Sistema",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=15, pady=10)

        scroll = ctk.CTkScrollableFrame(self, corner_radius=0)
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(1, weight=1)

        # Section: User
        self._section_label(scroll, "👤 Utilizador", 0)

        ctk.CTkLabel(scroll, text="Nome do Utilizador:", anchor="e", width=180).grid(
            row=1, column=0, padx=(20, 8), pady=10, sticky="e")
        self._vars['utilizador'] = tk.StringVar()
        ctk.CTkEntry(scroll, textvariable=self._vars['utilizador'], width=320).grid(
            row=1, column=1, padx=(0, 20), pady=10, sticky="w")

        # Section: Archive
        self._section_label(scroll, "📁 Pasta de Arquivo", 2)

        ctk.CTkLabel(scroll, text="Pasta de Arquivo:", anchor="e", width=180).grid(
            row=3, column=0, padx=(20, 8), pady=10, sticky="e")
        folder_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        folder_frame.grid(row=3, column=1, padx=(0, 20), pady=10, sticky="w")
        self._vars['pasta_arquivo'] = tk.StringVar()
        ctk.CTkEntry(folder_frame, textvariable=self._vars['pasta_arquivo'], width=280).pack(side="left", padx=(0, 8))
        ctk.CTkButton(folder_frame, text="📂 Escolher", width=100,
                      command=self._pick_folder).pack(side="left")

        # Section: Deadline
        self._section_label(scroll, "⏱️ Prazos", 4)

        ctk.CTkLabel(scroll, text="Prazo Padrão (dias):", anchor="e", width=180).grid(
            row=5, column=0, padx=(20, 8), pady=10, sticky="e")
        self._vars['prazo_padrao'] = tk.IntVar(value=5)
        prazo_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        prazo_frame.grid(row=5, column=1, padx=(0, 20), pady=10, sticky="w")
        ctk.CTkButton(prazo_frame, text="−", width=32, command=lambda: self._adj_prazo(-1)).pack(side="left")
        self.lbl_prazo = ctk.CTkLabel(prazo_frame, text="5", width=40, font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_prazo.pack(side="left", padx=6)
        ctk.CTkButton(prazo_frame, text="+", width=32, command=lambda: self._adj_prazo(1)).pack(side="left")

        # Section: Theme
        self._section_label(scroll, "🎨 Aparência", 6)

        ctk.CTkLabel(scroll, text="Tema:", anchor="e", width=180).grid(
            row=7, column=0, padx=(20, 8), pady=10, sticky="e")
        tema_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        tema_frame.grid(row=7, column=1, padx=(0, 20), pady=10, sticky="w")
        self._vars['tema'] = tk.StringVar(value="dark")
        ctk.CTkRadioButton(tema_frame, text="Escuro", variable=self._vars['tema'],
                           value="dark", command=self._apply_tema).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(tema_frame, text="Claro", variable=self._vars['tema'],
                           value="light", command=self._apply_tema).pack(side="left")

        ctk.CTkLabel(scroll, text="Esquema de Cor:", anchor="e", width=180).grid(
            row=8, column=0, padx=(20, 8), pady=(2, 16), sticky="ne")
        cor_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        cor_frame.grid(row=8, column=1, padx=(0, 20), pady=(2, 16), sticky="nw")
        self._vars['cor_tema'] = tk.StringVar(value="blue")
        cores = [
            ("🔵 Azul (padrão)", "blue", ["#1F4E79"]),
            ("🟢 Verde", "green", ["#1B5E3A"]),
            ("🔷 Azul-escuro", "dark-blue", ["#0d2b4e"]),
            ("🟣 Roxo", "purple", ["#5B2C83"]),
            ("🌅 Pôr-do-sol", "sunset", ["#B33939", "#E67E22"]),
            ("🌈 Arco-íris", "rainbow", ["#E53935", "#FB8C00", "#FDD835", "#43A047", "#1E88E5", "#8E24AA"]),
        ]
        for i, (label, value, colors) in enumerate(cores):
            row_f = ctk.CTkFrame(cor_frame, fg_color="transparent")
            row_f.grid(row=i // 2, column=i % 2, padx=(0, 18), pady=3, sticky="w")
            ctk.CTkRadioButton(row_f, text=label, variable=self._vars['cor_tema'],
                               value=value).pack(side="left")
            for c in colors:
                ctk.CTkLabel(row_f, text="⬤", text_color=c,
                             font=ctk.CTkFont(size=14), width=14).pack(side="left")
        ctk.CTkLabel(cor_frame, text="(reinicie o aplicativo para aplicar a nova cor)",
                     font=ctk.CTkFont(size=10), text_color="gray").grid(
            row=3, column=0, columnspan=2, pady=(6, 0), sticky="w")

        # D4: Tema automático por hora
        auto_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        auto_frame.grid(row=9, column=0, columnspan=2, padx=(20, 0), pady=(4, 0), sticky="w")
        self._vars['tema_auto'] = tk.BooleanVar()
        ctk.CTkCheckBox(auto_frame, text="Tema automático (escuro após 18h, claro antes das 8h)",
                        variable=self._vars['tema_auto']).pack(side="left")

        # Section: Email SMTP
        self._section_label(scroll, "✉️ Configuração de Email (SMTP)", 9)

        campos_smtp = [
            ("Servidor SMTP:",  "smtp_server",   "smtp.gmail.com", 10),
            ("Porta:",          "smtp_port",      "587",            11),
            ("Email:",          "smtp_email",     "email@gmail.com",12),
            ("Senha / App Key:","smtp_password",  "",               13),
        ]
        for label, key, placeholder, row in campos_smtp:
            ctk.CTkLabel(scroll, text=label, anchor="e", width=180).grid(
                row=row, column=0, padx=(20, 8), pady=6, sticky="e")
            self._vars[key] = tk.StringVar()
            show = "*" if key == "smtp_password" else ""
            ctk.CTkEntry(scroll, textvariable=self._vars[key], width=300,
                         placeholder_text=placeholder, show=show).grid(
                row=row, column=1, padx=(0, 20), pady=6, sticky="w")

        # C3: Dias úteis
        uteis_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        uteis_frame.grid(row=6, column=0, columnspan=2, padx=(20, 0), pady=(0, 8), sticky="w")
        self._vars['dias_uteis'] = tk.BooleanVar()
        ctk.CTkCheckBox(uteis_frame,
                        text="Calcular prazos em dias úteis (seg–sex, exclui fins-de-semana)",
                        variable=self._vars['dias_uteis']).pack(side="left")

        ctk.CTkLabel(scroll, text="",
                     font=ctk.CTkFont(size=10),
                     text_color="gray").grid(row=14, column=0, columnspan=2, padx=20, sticky="w")

        # Section: Tools
        self._section_label(scroll, "🛠️ Ferramentas", 15)

        tools_outer = ctk.CTkFrame(scroll, fg_color="transparent")
        tools_outer.grid(row=16, column=0, columnspan=2, padx=20, pady=10, sticky="w")

        tools_frame = ctk.CTkFrame(tools_outer, fg_color="transparent")
        tools_frame.pack(anchor="w")

        ctk.CTkButton(tools_frame, text="🔄 Fazer Backup BD", width=160,
                      command=self._backup_db, fg_color="#1F4E79").pack(side="left", padx=(0, 10))
        ctk.CTkButton(tools_frame, text="📥 Restaurar Backup", width=160,
                      command=self._restaurar_backup, fg_color="#8e44ad").pack(side="left", padx=(0, 10))
        ctk.CTkButton(tools_frame, text="📤 Importar Excel", width=160,
                      command=self._import_excel, fg_color="#2c6fad").pack(side="left", padx=(0, 10))
        ctk.CTkButton(tools_frame, text="📊 Exportar Tudo", width=150,
                      command=self._exportar_tudo, fg_color="#27ae60").pack(side="left", padx=(0, 10))

        tools_frame2 = ctk.CTkFrame(tools_outer, fg_color="transparent")
        tools_frame2.pack(anchor="w", pady=(6, 0))
        ctk.CTkButton(tools_frame2, text="📁 Abrir Pasta de Dados", width=180,
                      command=self._abrir_pasta_dados, fg_color="#555").pack(side="left", padx=(0, 10))
        ctk.CTkButton(tools_frame2, text="🗄️ Abrir Pasta de Backups", width=180,
                      command=self._abrir_pasta_backups, fg_color="#555").pack(side="left", padx=(0, 10))
        ctk.CTkButton(tools_frame2, text="🧹 Optimizar BD (VACUUM)", width=190,
                      command=self._vacuum_db, fg_color="#555").pack(side="left")

        from database import DB_PATH
        ctk.CTkLabel(tools_outer,
                     text=f"📍 Os seus dados (base de dados, configurações e backups) ficam guardados em:\n{os.path.dirname(DB_PATH)}",
                     font=ctk.CTkFont(size=10), text_color="gray",
                     justify="left", anchor="w").pack(anchor="w", pady=(10, 0))

        # Section: Save
        save_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        save_frame.grid(row=17, column=0, columnspan=2, pady=20)
        ctk.CTkButton(save_frame, text="💾 Guardar Configurações", width=200,
                      command=self._save_config, fg_color="#27ae60",
                      font=ctk.CTkFont(size=13, weight="bold")).pack()

        # Section: Credits — bloqueado, não editável
        self._section_label(scroll, "ℹ️ Informações", 18)

        creditos_frame = ctk.CTkFrame(scroll, fg_color=("#1F4E79", "#0d2b4e"), corner_radius=10)
        creditos_frame.grid(row=19, column=0, columnspan=2, padx=30, pady=(8, 20), sticky="ew")

        ctk.CTkLabel(creditos_frame,
                     text="Sistema de Gestão de Documentos",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="white").pack(pady=(14, 2))

        ctk.CTkLabel(creditos_frame,
                     text=f"DNE | MIREME  —  {VERSION_FULL}",
                     font=ctk.CTkFont(size=11),
                     text_color="#adc8e6").pack()

        ctk.CTkLabel(creditos_frame,
                     text="© Desenvolvido por",
                     font=ctk.CTkFont(size=11),
                     text_color="#adc8e6").pack(pady=(10, 0))

        ctk.CTkLabel(creditos_frame,
                     text="Iazalde Jose Jeremias",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#ffffff").pack()

        ctk.CTkLabel(creditos_frame,
                     text="Dep. Planeamento Energético\niazaldejose@gmail.com",
                     font=ctk.CTkFont(size=10),
                     text_color="#adc8e6", justify="center").pack(pady=(2, 14))

    def _section_label(self, parent, text, row):
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=("#1F4E79", "#5ba3d9")).grid(
            row=row, column=0, columnspan=2, padx=20, pady=(18, 2), sticky="w")

    def _load_current(self):
        self._vars['utilizador'].set(self.config.get('utilizador', ''))
        self._vars['pasta_arquivo'].set(self.config.get('pasta_arquivo', ''))
        prazo = self.config.get('prazo_padrao', 5)
        self._vars['prazo_padrao'].set(prazo)
        self.lbl_prazo.configure(text=str(prazo))
        self._vars['tema'].set(self.config.get('tema', 'dark'))
        self._vars['cor_tema'].set(self.config.get('cor_tema', 'blue'))
        self._vars['smtp_server'].set(self.config.get('smtp_server', ''))
        self._vars['smtp_port'].set(str(self.config.get('smtp_port', '587')))
        self._vars['smtp_email'].set(self.config.get('smtp_email', ''))
        self._vars['smtp_password'].set(self.config.get('smtp_password', ''))
        self._vars['dias_uteis'].set(bool(self.config.get('dias_uteis', False)))
        self._vars['tema_auto'].set(bool(self.config.get('tema_auto', False)))

    def _adj_prazo(self, delta):
        current = self._vars['prazo_padrao'].get()
        new_val = max(1, min(30, current + delta))
        self._vars['prazo_padrao'].set(new_val)
        self.lbl_prazo.configure(text=str(new_val))

    def _pick_folder(self):
        path = filedialog.askdirectory(parent=self)
        if path:
            self._vars['pasta_arquivo'].set(path)

    def _apply_tema(self):
        import customtkinter as ctk2
        ctk2.set_appearance_mode(self._vars['tema'].get())

    def _backup_db(self):
        dest_folder = filedialog.askdirectory(title="Escolher pasta para backup", parent=self)
        if not dest_folder:
            return
        try:
            from datetime import datetime
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            dest = os.path.join(dest_folder, f"gestao_documentos_backup_{ts}.db")
            from database import DB_PATH
            shutil.copy2(DB_PATH, dest)
            messagebox.showinfo("Sucesso", f"Backup guardado em:\n{dest}", parent=self)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha no backup:\n{e}", parent=self)

    def _abrir_pasta_dados(self):
        from database import DB_PATH
        pasta = os.path.dirname(DB_PATH)
        try:
            os.startfile(pasta)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta:\n{e}", parent=self)

    def _abrir_pasta_backups(self):
        from database import DB_PATH
        pasta = os.path.join(os.path.dirname(DB_PATH), "Backups")
        os.makedirs(pasta, exist_ok=True)
        try:
            os.startfile(pasta)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta:\n{e}", parent=self)

    def _import_excel(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Excel", "*.xlsx *.xls")],
            title="Importar Excel",
            parent=self
        )
        if not filepath:
            return
        busy = BusyDialog(self, "A importar dados do Excel...")
        try:
            import openpyxl
            wb = openpyxl.load_workbook(filepath)
            ws = wb.active
            rows = list(ws.iter_rows(min_row=2, values_only=True))
            count = 0
            for row in rows:
                if row and row[0]:
                    # Attempt basic import as recebido if columns match
                    try:
                        data = {
                            'numero': str(row[0]) if row[0] else '',
                            'proveniencia': str(row[1]) if len(row) > 1 and row[1] else '',
                            'remetente_nome': str(row[2]) if len(row) > 2 and row[2] else '',
                            'remetente_cargo': str(row[3]) if len(row) > 3 and row[3] else '',
                            'assunto': str(row[4]) if len(row) > 4 and row[4] else 'Importado',
                            'data_recepcao': str(row[5]) if len(row) > 5 and row[5] else '',
                            'despacho': str(row[6]) if len(row) > 6 and row[6] else '',
                            'endereçado_a': str(row[7]) if len(row) > 7 and row[7] else '',
                            'tecnico': str(row[8]) if len(row) > 8 and row[8] else '',
                            'data_resposta': str(row[9]) if len(row) > 9 and row[9] else '',
                            'prazo_status': str(row[10]) if len(row) > 10 and row[10] else 'Pendente',
                            'observacao': str(row[11]) if len(row) > 11 and row[11] else '',
                            'ficheiro_path': '',
                        }
                        if data['numero'] and data['assunto']:
                            self.db.insert_recebido(data)
                            count += 1
                    except Exception:
                        pass
            busy.fechar()
            messagebox.showinfo("Importação", f"{count} registro(s) importado(s) de Documentos Recebidos.",
                                parent=self)
        except Exception as e:
            busy.fechar()
            messagebox.showerror("Erro", f"Falha na importação:\n{e}", parent=self)

    def _save_config(self):
        cor_anterior = self.config.get('cor_tema', 'blue')
        prazo_anterior = self.config.get('prazo_padrao', 5)
        new_config = {
            'utilizador':    self._vars['utilizador'].get().strip(),
            'pasta_arquivo': self._vars['pasta_arquivo'].get().strip(),
            'prazo_padrao':  self._vars['prazo_padrao'].get(),
            'tema':          self._vars['tema'].get(),
            'cor_tema':      self._vars['cor_tema'].get(),
            'smtp_server':   self._vars['smtp_server'].get().strip(),
            'smtp_port':     self._vars['smtp_port'].get().strip(),
            'smtp_email':    self._vars['smtp_email'].get().strip(),
            'smtp_password': self._vars['smtp_password'].get(),
            'dias_uteis':    bool(self._vars['dias_uteis'].get()),
            'tema_auto':     bool(self._vars['tema_auto'].get()),
        }
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, ensure_ascii=False, indent=2)
            self.config.update(new_config)
            if new_config['prazo_padrao'] != prazo_anterior:
                self.db.recalcular_prazos(new_config['prazo_padrao'])
            if self.on_save_callback:
                self.on_save_callback(new_config)
            if new_config['cor_tema'] != cor_anterior:
                messagebox.showinfo("Sucesso",
                    "Configurações guardadas com sucesso.\n\n"
                    "⚠️ Reinicie o aplicativo para aplicar o novo esquema de cor.",
                    parent=self)
            else:
                messagebox.showinfo("Sucesso", "Configurações guardadas com sucesso.", parent=self)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao guardar:\n{e}", parent=self)

    def _restaurar_backup(self):
        from database import DB_PATH
        backups_dir = os.path.join(os.path.dirname(DB_PATH), "Backups")
        if not os.path.isdir(backups_dir):
            messagebox.showinfo("Sem Backups", "Nenhum backup encontrado.", parent=self)
            return
        import glob
        ficheiros = sorted(glob.glob(os.path.join(backups_dir, "*.db")),
                           key=os.path.getmtime, reverse=True)
        if not ficheiros:
            messagebox.showinfo("Sem Backups", "Nenhum ficheiro de backup encontrado.", parent=self)
            return

        import tkinter as _tk
        win = ctk.CTkToplevel(self)
        win.title("Restaurar Backup")
        win.geometry("520x360")
        win.grab_set()
        ctk.CTkLabel(win, text="⚠️  Seleccione o backup a restaurar",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(14, 4))
        ctk.CTkLabel(win, text="O ficheiro actual será substituído. O aplicativo deve ser\n"
                               "reiniciado após a restauração.",
                     font=ctk.CTkFont(size=11), text_color="gray").pack()

        lb = _tk.Listbox(win, font=('Segoe UI', 10), selectbackground="#2c6fad",
                         relief='flat', highlightthickness=1, activestyle='none')
        lb.pack(fill="both", expand=True, padx=14, pady=8)
        for f in ficheiros:
            lb.insert("end", os.path.basename(f))
        lb.selection_set(0)

        def _restaurar():
            sel = lb.curselection()
            if not sel:
                return
            fname = lb.get(sel[0])
            src = os.path.join(backups_dir, fname)
            if not messagebox.askyesno("Confirmar",
                    f"Restaurar '{fname}'?\n\nA base de dados actual será substituída.",
                    parent=win):
                return
            try:
                shutil.copy2(src, DB_PATH)
                win.destroy()
                messagebox.showinfo("Sucesso",
                    "Backup restaurado com sucesso.\n\nReinicie o aplicativo para aplicar.",
                    parent=self)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao restaurar:\n{e}", parent=win)

        btn_f = ctk.CTkFrame(win, fg_color="transparent")
        btn_f.pack(pady=(0, 12))
        ctk.CTkButton(btn_f, text="✅ Restaurar", width=130, command=_restaurar,
                      fg_color="#8e44ad").pack(side="left", padx=6)
        ctk.CTkButton(btn_f, text="❌ Cancelar", width=110, command=win.destroy,
                      fg_color="gray50").pack(side="left", padx=6)

    def _exportar_tudo(self):
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="gestao_documentos_completo.xlsx",
            parent=self
        )
        if not filepath:
            return
        busy = BusyDialog(self, "A exportar todos os dados...")
        try:
            ok = self.db.export_all_excel(filepath)
        finally:
            busy.fechar()
        if ok:
            messagebox.showinfo("Sucesso",
                f"Todos os dados exportados para:\n{filepath}\n\n"
                "(4 folhas: Recebidos, Enviados, Reuniões, Contactos)", parent=self)
        else:
            messagebox.showerror("Erro", "Falha ao exportar.", parent=self)

    def _vacuum_db(self):
        if not messagebox.askyesno("Optimizar Base de Dados",
                "Esta operação compacta a base de dados, recuperando espaço e\n"
                "melhorando o desempenho. Pode demorar alguns segundos.\n\n"
                "Continuar?", parent=self):
            return
        busy = BusyDialog(self, "A optimizar base de dados...")
        try:
            self.db.vacuum()
        finally:
            busy.fechar()
        messagebox.showinfo("Concluído", "Base de dados optimizada com sucesso.", parent=self)

    def on_activate(self):
        self._load_current()
