# ui/confidenciais.py — Secção Confidenciais
#
# Reutiliza 100% o ecrã de Recebidos, mas apontado à tabela SEPARADA de
# documentos confidenciais, através de um proxy que reencaminha as chamadas
# específicas de "recebido" para os métodos "confidencial" da base de dados.
# Inclui os diálogos de desbloqueio (senha) e de recuperação (código por email).

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

import seguranca
from ui.recebidos import RecebidosFrame


class _ConfidencialDB:
    """Proxy da base de dados: as operações de 'recebido' passam a actuar sobre
    a tabela confidencial; tudo o resto é reencaminhado para a BD real."""

    # Sinaliza aos formulários que estão a operar sobre dados confidenciais
    # (ex.: guardar os anexos numa pasta isolada, fora do backup na nuvem).
    CONFIDENCIAL = True

    def __init__(self, db):
        self._db = db

    def get_all_recebidos(self, filters=None):
        return self._db.get_all_confidenciais(filters)

    def get_recebido(self, id):
        return self._db.get_confidencial(id)

    def insert_recebido(self, data):
        return self._db.insert_confidencial(data)

    def update_recebido(self, id, data):
        return self._db.update_confidencial(id, data)

    def delete_recebido(self, id):
        return self._db.delete_confidencial(id)

    def export_recebidos_excel(self, filepath, filters=None):
        return self._db.export_confidenciais_excel(filepath, filters)

    def suggest_next_numero(self, tabela='recebidos'):
        return self._db.suggest_next_numero('confidenciais')

    def find_numero_duplicado(self, tabela, numero, excluir_id=None):
        return self._db.find_numero_duplicado('confidenciais', numero, excluir_id)

    def __getattr__(self, name):
        # Qualquer outro método (contactos, autocomplete, recalcular_prazos...)
        # é servido pela base de dados real, sem alteração.
        return getattr(self._db, name)


class ConfidenciaisFrame(RecebidosFrame):
    """Ecrã de Confidenciais — idêntico a Recebidos, sobre a tabela separada."""

    TIPO_FICHA = "CONFIDENCIAL"
    NOME_EXPORT = "documentos_confidenciais.xlsx"

    def __init__(self, parent, db, config):
        super().__init__(parent, _ConfidencialDB(db), config)


class DesbloquearDialog(ctk.CTkToplevel):
    """Pede a senha para abrir os Confidenciais. Permite recuperar a senha por
    email (código de reposição). Define self.sucesso=True se desbloqueado."""

    def __init__(self, parent, config, config_path):
        super().__init__(parent)
        self.config = config
        self.config_path = config_path
        self.sucesso = False
        self.title("Confidenciais — Senha")
        self.geometry("420x220")
        self.grab_set()

        ctk.CTkLabel(self, text="🔒 Área Confidencial",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(18, 4))
        ctk.CTkLabel(self, text="Introduza a senha para aceder.",
                     font=ctk.CTkFont(size=11), text_color="gray").pack(pady=(0, 10))

        self._var = tk.StringVar()
        entry = ctk.CTkEntry(self, textvariable=self._var, width=260, show="*")
        entry.pack(pady=4)
        entry.bind("<Return>", lambda e: self._verificar())
        entry.focus_set()

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=14)
        ctk.CTkButton(btns, text="🔓 Entrar", width=120, command=self._verificar,
                      fg_color="#8e44ad").pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Cancelar", width=100, command=self.destroy,
                      fg_color="gray50").pack(side="left", padx=6)

        ctk.CTkButton(self, text="Esqueci a senha", width=140, fg_color="transparent",
                      text_color=("#1F4E79", "#5ba3d9"), hover=False,
                      command=self._recuperar).pack()

    def _verificar(self):
        if seguranca.verificar_password(self._var.get(),
                                        self.config.get('confidencial_hash', '')):
            self.sucesso = True
            self.destroy()
        else:
            messagebox.showerror("Senha incorrecta", "A senha introduzida está errada.", parent=self)
            self._var.set("")

    def _recuperar(self):
        RecuperarSenhaDialog(self, self.config, self.config_path)


class RecuperarSenhaDialog(ctk.CTkToplevel):
    """Recuperação por email: envia um código para o email das Configurações e,
    com esse código, permite definir uma nova senha."""

    def __init__(self, parent, config, config_path):
        super().__init__(parent)
        self.config = config
        self.config_path = config_path
        self._codigo_enviado = None
        self.title("Recuperar Senha")
        self.geometry("460x400")
        self.grab_set()

        ctk.CTkLabel(self, text="🔑 Recuperar Senha",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(16, 2))
        email = (self.config.get('smtp_email') or '').strip()
        alvo = email or "(email não configurado)"
        ctk.CTkLabel(self, text=f"Será enviado um código para:\n{alvo}",
                     font=ctk.CTkFont(size=11), text_color="gray",
                     justify="center").pack(pady=(0, 8))

        ctk.CTkButton(self, text="📨 Enviar código por email", width=220,
                      command=self._enviar_codigo, fg_color="#1F4E79").pack(pady=6)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(padx=20, pady=10, fill="x")
        self._vars = {}
        for i, (lbl, key) in enumerate([("Código recebido:", "codigo"),
                                        ("Nova senha:", "nova"),
                                        ("Confirmar:", "confirmar")]):
            ctk.CTkLabel(form, text=lbl, anchor="e", width=120).grid(
                row=i, column=0, padx=(0, 8), pady=6, sticky="e")
            self._vars[key] = tk.StringVar()
            show = "" if key == "codigo" else "*"
            ctk.CTkEntry(form, textvariable=self._vars[key], width=220, show=show).grid(
                row=i, column=1, pady=6, sticky="w")

        ctk.CTkLabel(self, text="Requer o email (SMTP) configurado nas Configurações.",
                     font=ctk.CTkFont(size=10), text_color="gray").pack(pady=(0, 4))
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=8)
        ctk.CTkButton(btns, text="💾 Definir nova senha", width=170,
                      command=self._redefinir, fg_color="#27ae60").pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Fechar", width=100, command=self.destroy,
                      fg_color="gray50").pack(side="left", padx=6)

    def _enviar_codigo(self):
        try:
            from notificacoes import smtp_configurado, _enviar_email
        except Exception:
            messagebox.showerror("Erro", "Módulo de email indisponível.", parent=self)
            return
        if not smtp_configurado(self.config):
            messagebox.showwarning(
                "Email não configurado",
                "Configure o email (SMTP) nas Configurações para poder receber o "
                "código de recuperação.", parent=self)
            return
        codigo = seguranca.gerar_codigo_reposicao()
        email = (self.config.get('smtp_email') or '').strip()
        corpo = ("Recebeu este email porque foi pedida a recuperação da senha da "
                 "área Confidencial do Sistema de Gestão de Documentos.\n\n"
                 f"O seu código de reposição é:  {codigo}\n\n"
                 "Introduza-o na aplicação e defina uma nova senha. Se não foi você "
                 "a pedir, ignore este email e a senha permanece inalterada.")
        try:
            _enviar_email(self.config, email,
                          "🔑 Código de recuperação — Confidenciais", corpo)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao enviar o email:\n{e}", parent=self)
            return
        self._codigo_enviado = codigo
        messagebox.showinfo("Código enviado",
                            f"Foi enviado um código para {email}.\n"
                            "Verifique a caixa de entrada (e o spam).", parent=self)

    def _redefinir(self):
        if not self._codigo_enviado:
            messagebox.showwarning("Aviso", "Primeiro envie o código por email.", parent=self)
            return
        if self._vars['codigo'].get().strip() != self._codigo_enviado:
            messagebox.showerror("Erro", "O código introduzido está incorrecto.", parent=self)
            return
        nova = self._vars['nova'].get()
        if nova != self._vars['confirmar'].get():
            messagebox.showerror("Erro", "A nova senha e a confirmação não coincidem.", parent=self)
            return
        erro = seguranca.validar_password(nova)
        if erro:
            messagebox.showerror("Senha inválida", erro, parent=self)
            return
        try:
            from utils import gravar_config
            self.config['confidencial_hash'] = seguranca.hash_password(nova)
            gravar_config(self.config_path, self.config)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao guardar a senha:\n{e}", parent=self)
            return
        messagebox.showinfo("Sucesso",
                            "Senha redefinida com sucesso. Já pode entrar com a nova senha.",
                            parent=self)
        self.destroy()
