import os
import re
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


class EmailDialog(ctk.CTkToplevel):
    """Janela para enviar um documento por email com anexo."""

    def __init__(self, parent, ficheiro_path="", assunto="", corpo=""):
        super().__init__(parent)
        self.title("✉️ Enviar por Email")
        self.geometry("620x620")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()

        self.ficheiro_path = ficheiro_path
        self._build(assunto, corpo)

    def _build(self, assunto, corpo):
        # Título
        ctk.CTkLabel(self, text="✉️  Enviar Documento por Email",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(16, 8))

        f = ctk.CTkScrollableFrame(self, corner_radius=0)
        f.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        f.grid_columnconfigure(1, weight=1)

        def row_label(text, r):
            ctk.CTkLabel(f, text=text, anchor="e", width=110,
                         font=ctk.CTkFont(size=12)).grid(
                row=r, column=0, padx=(6, 6), pady=6, sticky="e")

        # --- Conta de envio ---
        ctk.CTkLabel(f, text="── Conta de Envio ──",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").grid(row=0, column=0, columnspan=2, pady=(10, 2))

        row_label("Servidor SMTP:", 1)
        self.smtp_var = tk.StringVar(value="smtp.gmail.com")
        ctk.CTkEntry(f, textvariable=self.smtp_var, width=300).grid(
            row=1, column=1, padx=(0, 10), pady=6, sticky="w")

        row_label("Porta:", 2)
        self.porta_var = tk.StringVar(value="587")
        ctk.CTkEntry(f, textvariable=self.porta_var, width=80).grid(
            row=2, column=1, padx=(0, 10), pady=6, sticky="w")

        row_label("Email remetente:", 3)
        self.from_var = tk.StringVar()
        ctk.CTkEntry(f, textvariable=self.from_var,
                     placeholder_text="o_seu_email@gmail.com", width=300).grid(
            row=3, column=1, padx=(0, 10), pady=6, sticky="w")

        row_label("Senha / App Password:", 4)
        self.senha_var = tk.StringVar()
        ctk.CTkEntry(f, textvariable=self.senha_var, show="●", width=300).grid(
            row=4, column=1, padx=(0, 10), pady=6, sticky="w")

        # --- Destinatário ---
        ctk.CTkLabel(f, text="── Destinatário ──",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").grid(row=5, column=0, columnspan=2, pady=(10, 2))

        row_label("Para:", 6)
        self.para_var = tk.StringVar()
        ctk.CTkEntry(f, textvariable=self.para_var,
                     placeholder_text="destinatario@email.com", width=380).grid(
            row=6, column=1, padx=(0, 10), pady=6, sticky="w")

        row_label("CC (opcional):", 7)
        self.cc_var = tk.StringVar()
        ctk.CTkEntry(f, textvariable=self.cc_var,
                     placeholder_text="copia@email.com", width=380).grid(
            row=7, column=1, padx=(0, 10), pady=6, sticky="w")

        # --- Mensagem ---
        ctk.CTkLabel(f, text="── Mensagem ──",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").grid(row=8, column=0, columnspan=2, pady=(10, 2))

        row_label("Assunto:", 9)
        self.assunto_var = tk.StringVar(value=assunto)
        ctk.CTkEntry(f, textvariable=self.assunto_var, width=420).grid(
            row=9, column=1, padx=(0, 10), pady=6, sticky="w")

        row_label("Corpo:", 10)
        self.corpo_text = ctk.CTkTextbox(f, width=420, height=120)
        self.corpo_text.grid(row=10, column=1, padx=(0, 10), pady=6, sticky="w")
        self.corpo_text.insert("1.0", corpo)

        # --- Anexo ---
        ctk.CTkLabel(f, text="── Anexo ──",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").grid(row=11, column=0, columnspan=2, pady=(10, 2))

        row_label("Ficheiro:", 12)
        anexo_frame = ctk.CTkFrame(f, fg_color="transparent")
        anexo_frame.grid(row=12, column=1, padx=(0, 10), pady=6, sticky="w")
        self.anexo_var = tk.StringVar(value=self.ficheiro_path)
        ctk.CTkEntry(anexo_frame, textvariable=self.anexo_var, width=300).pack(
            side="left", padx=(0, 6))
        ctk.CTkButton(anexo_frame, text="📂", width=36,
                      command=self._pick_anexo).pack(side="left")

        # --- Botões ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="📨 Enviar", width=130, command=self._enviar,
                      fg_color="#1F4E79").pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="❌ Cancelar", width=100, command=self.destroy,
                      fg_color="gray50").pack(side="left", padx=8)

        # Nota sobre App Password
        ctk.CTkLabel(self,
                     text="ℹ️  Gmail: use uma 'App Password' em Conta Google → Segurança → Senhas de app",
                     font=ctk.CTkFont(size=10), text_color="gray").pack(pady=(0, 8))

    def _pick_anexo(self):
        path = filedialog.askopenfilename(parent=self)
        if path:
            self.anexo_var.set(path)

    def _enviar(self):
        smtp_host = self.smtp_var.get().strip()
        porta     = self.porta_var.get().strip()
        from_addr = self.from_var.get().strip()
        senha     = self.senha_var.get()
        para_addr = self.para_var.get().strip()
        cc_addr   = self.cc_var.get().strip()
        assunto   = self.assunto_var.get().strip()
        corpo     = self.corpo_text.get("1.0", "end").strip()
        anexo     = self.anexo_var.get().strip()

        # Validações
        if not from_addr:
            messagebox.showwarning("Aviso", "Preencha o email remetente.", parent=self)
            return
        if not para_addr:
            messagebox.showwarning("Aviso", "Preencha o destinatário.", parent=self)
            return
        if not senha:
            messagebox.showwarning("Aviso", "Preencha a senha.", parent=self)
            return

        email_re = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
        if not email_re.match(from_addr):
            messagebox.showerror("Erro", f"Email remetente inválido:\n{from_addr}", parent=self)
            return
        if not email_re.match(para_addr):
            messagebox.showerror("Erro", f"Email do destinatário inválido:\n{para_addr}", parent=self)
            return
        if cc_addr and not email_re.match(cc_addr):
            messagebox.showerror("Erro", f"Email em Cc inválido:\n{cc_addr}", parent=self)
            return

        try:
            porta_int = int(porta)
        except ValueError:
            messagebox.showerror("Erro", "Porta inválida.", parent=self)
            return

        # Construir mensagem
        msg = MIMEMultipart()
        msg["From"]    = from_addr
        msg["To"]      = para_addr
        msg["Subject"] = assunto
        if cc_addr:
            msg["Cc"] = cc_addr

        msg.attach(MIMEText(corpo, "plain", "utf-8"))

        # Anexo
        if anexo and os.path.isfile(anexo):
            nome_ficheiro = os.path.basename(anexo)
            with open(anexo, "rb") as fh:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(fh.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition",
                            f'attachment; filename="{nome_ficheiro}"')
            msg.attach(part)
        elif anexo:
            if not messagebox.askyesno(
                    "Ficheiro não encontrado",
                    f"O ficheiro não existe:\n{anexo}\n\nEnviar sem anexo?",
                    parent=self):
                return

        # Enviar
        destinatarios = [para_addr] + ([cc_addr] if cc_addr else [])
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, porta_int, timeout=15) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(from_addr, senha)
                server.sendmail(from_addr, destinatarios, msg.as_string())

            messagebox.showinfo("Sucesso",
                                f"Email enviado com sucesso para:\n{para_addr}", parent=self)
            self.destroy()

        except smtplib.SMTPAuthenticationError:
            messagebox.showerror("Erro de Autenticação",
                                 "Senha incorrecta ou conta não autorizada.\n"
                                 "Para Gmail use uma 'App Password'.", parent=self)
        except smtplib.SMTPException as e:
            messagebox.showerror("Erro SMTP", f"Falha ao enviar:\n{e}", parent=self)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro inesperado:\n{e}", parent=self)
