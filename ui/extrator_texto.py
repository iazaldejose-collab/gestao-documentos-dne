# ui/extrator_texto.py — Janela "Extrair Texto" (Documento → Texto)
#
# Converte para texto o documento anexado (PDF, Word ou imagem via OCR) e
# mostra-o numa janela onde o utilizador pode seleccionar/copiar partes,
# copiar tudo ou guardar como .txt. A extracção corre numa thread de fundo
# (o OCR pode demorar alguns segundos por página) sem bloquear a interface.

import os
import threading
from tkinter import messagebox, filedialog
import customtkinter as ctk

from ui.doc_extract import extrair_texto_completo

# Tipos de ficheiro aceites no selector "outro ficheiro"
FILETYPES_TEXTO = [
    ("Documentos e imagens", "*.pdf *.docx *.doc *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp"),
    ("PDF", "*.pdf"),
    ("Word", "*.docx *.doc"),
    ("Imagens", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp"),
    ("Todos os ficheiros", "*.*"),
]


class ExtrairTextoDialog(ctk.CTkToplevel):
    """Extrai e mostra o texto de um ficheiro (PDF/Word/imagem)."""

    def __init__(self, parent, filepath):
        super().__init__(parent)
        self.filepath = filepath
        self.title(f"📄 Extrair Texto — {os.path.basename(filepath)}")
        self.geometry("780x580")
        self.grab_set()

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.lbl_estado = ctk.CTkLabel(
            self, text="⏳ A extrair o texto... (pode demorar alguns segundos "
                       "se for necessário OCR)",
            font=ctk.CTkFont(size=12), text_color="#e67e22")
        self.lbl_estado.grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")

        self.txt = ctk.CTkTextbox(self, wrap="word", font=ctk.CTkFont(size=13))
        self.txt.grid(row=1, column=0, sticky="nsew", padx=14, pady=4)
        self.txt.insert("1.0", "A processar…")
        self.txt.configure(state="disabled")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, pady=(6, 12))
        self.btn_copiar = ctk.CTkButton(btns, text="📋 Copiar Tudo", width=130,
                                        command=self._copiar_tudo,
                                        fg_color="#1F4E79", state="disabled")
        self.btn_copiar.pack(side="left", padx=6)
        self.btn_guardar = ctk.CTkButton(btns, text="💾 Guardar .txt", width=130,
                                         command=self._guardar_txt,
                                         fg_color="#27ae60", state="disabled")
        self.btn_guardar.pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Fechar", width=100, command=self.destroy,
                      fg_color="gray50").pack(side="left", padx=6)

        # Extracção em thread de fundo (OCR pode demorar)
        self._resultado = {}
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()
        self._aguardar(t)

    def _worker(self):
        try:
            texto, erro = extrair_texto_completo(self.filepath)
        except Exception as e:
            texto, erro = None, f"Erro inesperado: {e}"
        self._resultado = {'texto': texto, 'erro': erro}

    def _aguardar(self, t):
        if t.is_alive():
            self.after(300, lambda: self._aguardar(t))
            return
        self._mostrar()

    def _mostrar(self):
        texto = self._resultado.get('texto')
        erro = self._resultado.get('erro')
        try:
            self.txt.configure(state="normal")
            self.txt.delete("1.0", "end")
            if erro:
                self.txt.insert("1.0", f"⚠️ {erro}")
                self.txt.configure(state="disabled")
                self.lbl_estado.configure(text="❌ Não foi possível extrair o texto.",
                                          text_color="#e74c3c")
                return
            self.txt.insert("1.0", texto)
            # Deixa editável para o utilizador poder seleccionar e apagar partes
            n_linhas = texto.count("\n") + 1
            self.lbl_estado.configure(
                text=f"✅ Texto extraído: {len(texto)} caracteres, ~{n_linhas} linhas. "
                     "Seleccione e copie as partes que precisar.",
                text_color="#27ae60")
            self.btn_copiar.configure(state="normal")
            self.btn_guardar.configure(state="normal")
        except Exception:
            pass

    def _copiar_tudo(self):
        try:
            texto = self.txt.get("1.0", "end").strip()
            self.clipboard_clear()
            self.clipboard_append(texto)
            self.lbl_estado.configure(text="📋 Texto copiado para a área de transferência.",
                                      text_color="#27ae60")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao copiar:\n{e}", parent=self)

    def _guardar_txt(self):
        base = os.path.splitext(os.path.basename(self.filepath))[0]
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt")],
            initialfile=f"{base}.txt",
            parent=self)
        if not filepath:
            return
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.txt.get("1.0", "end").strip() + "\n")
            self.lbl_estado.configure(text=f"💾 Guardado em: {filepath}",
                                      text_color="#27ae60")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao guardar:\n{e}", parent=self)


class EscolherFonteDialog(ctk.CTkToplevel):
    """Quando o documento tem mais do que um anexo, pergunta de qual extrair
    o texto (recebido, resposta, ou outro ficheiro do disco)."""

    def __init__(self, parent, opcoes):
        """opcoes: lista de (rótulo, caminho). O 'outro ficheiro' é acrescentado
        automaticamente. self.escolha fica com o caminho, ou '__outro__'."""
        super().__init__(parent)
        self.escolha = None
        self.title("Extrair Texto de…")
        self.geometry("380x210")
        self.grab_set()

        ctk.CTkLabel(self, text="📄 Extrair o texto de que ficheiro?",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(16, 10))
        for rotulo, caminho in opcoes:
            ctk.CTkButton(self, text=rotulo, width=280,
                          command=lambda c=caminho: self._escolher(c),
                          fg_color="#1F4E79").pack(pady=4)
        ctk.CTkButton(self, text="📂 Outro ficheiro…", width=280,
                      command=lambda: self._escolher("__outro__"),
                      fg_color="#5a6e8a").pack(pady=4)
        ctk.CTkButton(self, text="Cancelar", width=120, command=self.destroy,
                      fg_color="gray50").pack(pady=(8, 0))

    def _escolher(self, caminho):
        self.escolha = caminho
        self.destroy()
