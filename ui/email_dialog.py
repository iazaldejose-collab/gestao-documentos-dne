import os
import json
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


_HIST_FILE = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                          "GestaoDocumentosDNE", "email_historico.json")


def _load_historico():
    try:
        if os.path.isfile(_HIST_FILE):
            with open(_HIST_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh)
    except Exception:
        pass
    return []


def _save_historico(email):
    email = email.lower().strip()
    if not email:
        return
    hist = _load_historico()
    if email in hist:
        hist.remove(email)
    hist.insert(0, email)
    try:
        with open(_HIST_FILE, "w", encoding="utf-8") as fh:
            json.dump(hist[:50], fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


class EmailDialog(ctk.CTkToplevel):
    """Janela para enviar um documento por email com anexo."""

    def __init__(self, parent, config=None, ficheiro_path="", assunto="", corpo=""):
        super().__init__(parent)
        self.title("✉️ Enviar por Email")
        self.geometry("620x640")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()

        self.ficheiro_path = ficheiro_path
        self._config = config or {}
        self._historico = _load_historico()
        self._popup = None
        self._popup_lb = None
        self._build(assunto, corpo)

    def _build(self, assunto, corpo):
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
        self.smtp_var = tk.StringVar(value=self._config.get('smtp_server', 'smtp.gmail.com'))
        ctk.CTkEntry(f, textvariable=self.smtp_var, width=300).grid(
            row=1, column=1, padx=(0, 10), pady=6, sticky="w")

        row_label("Porta:", 2)
        porta_frame = ctk.CTkFrame(f, fg_color="transparent")
        porta_frame.grid(row=2, column=1, padx=(0, 10), pady=6, sticky="w")
        self.porta_var = tk.StringVar(value=str(self._config.get('smtp_port', '587')))
        ctk.CTkEntry(porta_frame, textvariable=self.porta_var, width=80).pack(side="left")
        ctk.CTkLabel(porta_frame, text="  465 = SSL directo  |  587 = STARTTLS",
                     font=ctk.CTkFont(size=10), text_color="gray").pack(side="left", padx=(8, 0))

        row_label("Email remetente:", 3)
        self.from_var = tk.StringVar(value=self._config.get('smtp_email', ''))
        ctk.CTkEntry(f, textvariable=self.from_var,
                     placeholder_text="o_seu_email@gmail.com", width=300).grid(
            row=3, column=1, padx=(0, 10), pady=6, sticky="w")

        row_label("Senha / App Password:", 4)
        self.senha_var = tk.StringVar(value=self._config.get('smtp_password', ''))
        ctk.CTkEntry(f, textvariable=self.senha_var, show="●", width=300).grid(
            row=4, column=1, padx=(0, 10), pady=6, sticky="w")

        # --- Destinatário ---
        ctk.CTkLabel(f, text="── Destinatário ──",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").grid(row=5, column=0, columnspan=2, pady=(10, 2))

        row_label("Para:", 6)
        self.para_var = tk.StringVar()
        para_entry = ctk.CTkEntry(f, textvariable=self.para_var,
                                  placeholder_text="destinatario@email.com", width=380)
        para_entry.grid(row=6, column=1, padx=(0, 10), pady=6, sticky="w")
        self._bind_autocomplete(para_entry, self.para_var)

        row_label("CC (opcional):", 7)
        self.cc_var = tk.StringVar()
        cc_entry = ctk.CTkEntry(f, textvariable=self.cc_var,
                                placeholder_text="copia@email.com", width=380)
        cc_entry.grid(row=7, column=1, padx=(0, 10), pady=6, sticky="w")
        self._bind_autocomplete(cc_entry, self.cc_var)

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

        ctk.CTkLabel(self,
                     text="ℹ️  Gmail: use uma 'App Password' em Conta Google → Segurança → Senhas de app",
                     font=ctk.CTkFont(size=10), text_color="gray").pack(pady=(0, 8))

        self.bind("<Configure>", lambda e: self._hide_popup())

    # ------------------------------------------------------------------ autocomplete
    def _bind_autocomplete(self, ctk_entry, var):
        var.trace_add("write", lambda *_: self.after(50, lambda: self._update_popup(ctk_entry, var)))
        try:
            inner = ctk_entry._entry
            inner.bind("<FocusOut>", lambda e: self.after(200, self._hide_popup))
            inner.bind("<Escape>",   lambda e: self._hide_popup())
            inner.bind("<Down>",     lambda e: self._focus_popup())
        except Exception:
            pass

    def _update_popup(self, ctk_entry, var):
        typed = var.get().strip().lower()
        if not typed or not self._historico:
            self._hide_popup()
            return
        matches = [e for e in self._historico if typed in e.lower()]
        if matches:
            self._show_popup(ctk_entry, var, matches)
        else:
            self._hide_popup()

    def _show_popup(self, ctk_entry, var, matches):
        self._hide_popup()
        try:
            x = ctk_entry.winfo_rootx()
            y = ctk_entry.winfo_rooty() + ctk_entry.winfo_height()
        except Exception:
            return

        popup = tk.Toplevel(self)
        popup.wm_overrideredirect(True)
        popup.geometry(f"+{x}+{y}")
        popup.lift()

        lb = tk.Listbox(popup, height=min(len(matches), 7), width=46,
                        font=('Segoe UI', 10), relief='solid', borderwidth=1,
                        bg='#2b2b2b', fg='white',
                        selectbackground='#1F4E79', selectforeground='white',
                        activestyle='none')
        lb.pack(fill='both')
        for m in matches:
            lb.insert('end', m)

        def select(evt=None):
            sel = lb.curselection()
            if sel:
                var.set(lb.get(sel[0]))
            self._hide_popup()

        lb.bind('<ButtonRelease-1>', select)
        lb.bind('<Return>', select)

        self._popup = popup
        self._popup_lb = lb

    def _focus_popup(self):
        if self._popup and self._popup_lb:
            self._popup_lb.focus_set()
            if self._popup_lb.size() > 0:
                self._popup_lb.selection_set(0)
                self._popup_lb.activate(0)

    def _hide_popup(self, *_):
        if self._popup:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None
            self._popup_lb = None

    # ------------------------------------------------------------------ acções
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

        msg = MIMEMultipart()
        msg["From"]    = from_addr
        msg["To"]      = para_addr
        msg["Subject"] = assunto
        if cc_addr:
            msg["Cc"] = cc_addr

        msg.attach(MIMEText(corpo, "plain", "utf-8"))

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

        destinatarios = [para_addr] + ([cc_addr] if cc_addr else [])
        try:
            context = ssl.create_default_context()
            if porta_int == 465:
                # SSL directo (porta 465)
                with smtplib.SMTP_SSL(smtp_host, porta_int, context=context, timeout=30) as server:
                    server.ehlo()
                    server.login(from_addr, senha)
                    server.sendmail(from_addr, destinatarios, msg.as_string())
            else:
                # STARTTLS (porta 587 ou outra)
                with smtplib.SMTP(smtp_host, porta_int, timeout=30) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.login(from_addr, senha)
                    server.sendmail(from_addr, destinatarios, msg.as_string())

            _save_historico(para_addr)
            if cc_addr:
                _save_historico(cc_addr)

            messagebox.showinfo("Sucesso",
                                f"Email enviado com sucesso para:\n{para_addr}", parent=self)
            self.destroy()

        except smtplib.SMTPAuthenticationError:
            messagebox.showerror("Erro de Autenticação",
                                 "Senha incorrecta ou conta não autorizada.\n\n"
                                 "Para Gmail:\n"
                                 "1. Active a verificação em 2 passos na sua conta Google\n"
                                 "2. Vá a: Conta Google → Segurança → Senhas de app\n"
                                 "3. Crie uma senha de app e use-a aqui (não a senha normal)", parent=self)
        except smtplib.SMTPException as e:
            messagebox.showerror("Erro SMTP", f"Falha ao enviar:\n{e}", parent=self)
        except OSError as e:
            if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                messagebox.showerror("Ligação Bloqueada",
                                     f"Não foi possível ligar ao servidor ({smtp_host}:{porta_int}).\n\n"
                                     "Causas mais comuns em redes corporativas:\n"
                                     "• A firewall bloqueia a porta SMTP\n"
                                     "• Sem acesso à Internet nesta rede\n\n"
                                     "Sugestões:\n"
                                     "• Tente a porta 465 (SSL directo) em vez de 587\n"
                                     "• Verifique com o responsável de TI se as portas\n"
                                     "  465 e 587 estão abertas para tráfego de saída", parent=self)
            else:
                messagebox.showerror("Erro de Rede", f"Erro de ligação:\n{e}", parent=self)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro inesperado:\n{e}", parent=self)
