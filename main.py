import sys
import os
import json
import customtkinter as ctk
from ui.app import App

if getattr(sys, 'frozen', False):
    CONFIG_PATH = os.path.join(os.path.dirname(sys.executable), 'config.json')
else:
    CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')


def load_config():
    defaults = {
        "utilizador": "Utilizador",
        "pasta_arquivo": "",
        "prazo_padrao": 5,
        "tema": "dark"
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                defaults.update(cfg)
        except Exception:
            pass
    return defaults


def main():
    try:
        config = load_config()
        tema = config.get("tema", "dark")
        ctk.set_appearance_mode(tema)
        cor_tema = config.get("cor_tema", "blue")
        # CTk só aceita estes 3 temas embutidos para set_default_color_theme;
        # as nossas paletas extra (purple, sunset, rainbow...) são aplicadas
        # directamente pela App através de self.palette (ver ui/app.py)
        ctk.set_default_color_theme(cor_tema if cor_tema in ("blue", "green", "dark-blue") else "blue")
        app = App(config, CONFIG_PATH)
        app.mainloop()
    except Exception as e:
        import traceback
        log_path = os.path.join(os.path.dirname(CONFIG_PATH), 'erro.log')
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(traceback.format_exc())
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk(); root.withdraw()
            messagebox.showerror("Erro Fatal", f"Erro ao iniciar:\n{e}\n\nDetalhes em: {log_path}")
            root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    main()
