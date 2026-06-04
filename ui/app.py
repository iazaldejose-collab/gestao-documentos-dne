import json
import os
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from database import Database
from ui.recebidos import RecebidosFrame
from ui.enviados import EnviadosFrame
from ui.reunioes import ReunioesFrame
from ui.relatorio import RelatorioFrame
from ui.contactos import ContactosFrame
from ui.configuracoes import ConfiguracoesFrame


class App(ctk.CTk):
    def __init__(self, config, config_path):
        super().__init__()
        self.config_data = config
        self.config_path = config_path
        self.db = Database()

        self.title("Sistema de Gestão de Documentos — DNE | MIREME 2026")
        self.minsize(1280, 800)
        self.geometry("1400x860")

        self._build_layout()
        self._build_header()
        self._build_sidebar()
        self._build_main_area()
        self._build_statusbar()

        self._start_clock()
        self.after(500, self._check_alertas_startup)

        self.bind_all("<Control-n>", self._shortcut_novo)
        self.bind_all("<Control-f>", self._shortcut_buscar)
        self.bind_all("<Control-e>", self._shortcut_exportar)
        self.bind_all("<F5>", self._shortcut_refresh)
        self.bind_all("<Escape>", self._shortcut_esc)

        self._show_frame("recebidos")

    def _build_layout(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def _build_header(self):
        self.header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color=("#1F4E79", "#0d2b4e"))
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.header.grid_propagate(False)
        self.header.grid_columnconfigure(1, weight=1)

        lbl_inst = ctk.CTkLabel(self.header, text="  DNE | MIREME — Sistema de Gestão de Documentos",
                                font=ctk.CTkFont(size=16, weight="bold"), text_color="white")
        lbl_inst.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.lbl_clock = ctk.CTkLabel(self.header, text="", font=ctk.CTkFont(size=13), text_color="#adc8e6")
        self.lbl_clock.grid(row=0, column=1, pady=10)

        right_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        right_frame.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        self.lbl_user = ctk.CTkLabel(right_frame,
                                     text=f"👤 {self.config_data.get('utilizador', 'Utilizador')}",
                                     font=ctk.CTkFont(size=12), text_color="#adc8e6")
        self.lbl_user.pack(side="left", padx=(0, 10))

        self.btn_tema = ctk.CTkButton(right_frame, text="🌙", width=36, height=28,
                                      command=self._toggle_tema, fg_color="#2c6fad", hover_color="#1a4d7d")
        self.btn_tema.pack(side="left")

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=("#1a3a5c", "#111c2d"))
        self.sidebar.grid(row=1, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        nav_items = [
            ("recebidos", "📥  Recebidos"),
            ("enviados", "📤  Enviados"),
            ("reunioes", "📅  Reuniões"),
            ("relatorio", "📊  Relatório"),
            ("contactos", "👥  Contactos"),
            ("configuracoes", "⚙️  Configurações"),
        ]

        self.nav_buttons = {}
        for i, (key, label) in enumerate(nav_items):
            btn = ctk.CTkButton(self.sidebar, text=label, anchor="w",
                                width=180, height=44,
                                font=ctk.CTkFont(size=13),
                                fg_color="transparent",
                                hover_color=("#2c6fad", "#1a4d7d"),
                                text_color=("white", "white"),
                                corner_radius=6,
                                command=lambda k=key: self._show_frame(k))
            btn.pack(padx=10, pady=(8 if i == 0 else 2, 2))
            self.nav_buttons[key] = btn

        self.lbl_notif = ctk.CTkLabel(self.sidebar, text="", font=ctk.CTkFont(size=11),
                                      text_color="#ff9900")
        self.lbl_notif.pack(padx=10, pady=(20, 5))

    def _build_main_area(self):
        self.main_container = ctk.CTkFrame(self, corner_radius=0)
        self.main_container.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        self.frames["recebidos"] = RecebidosFrame(self.main_container, self.db, self.config_data)
        self.frames["enviados"] = EnviadosFrame(self.main_container, self.db, self.config_data)
        self.frames["reunioes"] = ReunioesFrame(self.main_container, self.db, self.config_data)
        self.frames["relatorio"] = RelatorioFrame(self.main_container, self.db, self.config_data)
        self.frames["contactos"] = ContactosFrame(self.main_container, self.db, self.config_data)
        self.frames["configuracoes"] = ConfiguracoesFrame(self.main_container, self.db,
                                                          self.config_data, self.config_path,
                                                          self._on_config_saved)

        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

        self.current_frame_key = None

    def _build_statusbar(self):
        self.statusbar = ctk.CTkFrame(self, height=28, corner_radius=0,
                                      fg_color=("#e8ecf0", "#1a1a2e"))
        self.statusbar.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.statusbar.grid_propagate(False)
        self.statusbar.grid_columnconfigure(1, weight=1)

        self.lbl_status_left = ctk.CTkLabel(self.statusbar, text="  Pronto",
                                            font=ctk.CTkFont(size=11),
                                            text_color=("#444", "#aaa"))
        self.lbl_status_left.grid(row=0, column=0, padx=5)

        self.lbl_status_right = ctk.CTkLabel(self.statusbar,
                                             text="v1.0.0  |  DNE/MIREME  |  Iazalde Jose Jeremias  ",
                                             font=ctk.CTkFont(size=11),
                                             text_color=("#444", "#aaa"))
        self.lbl_status_right.grid(row=0, column=2, padx=5, sticky="e")

    def _show_frame(self, key):
        if self.current_frame_key == key:
            return
        self.current_frame_key = key
        frame = self.frames[key]
        frame.tkraise()

        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=("#2c6fad", "#1a4d7d"))
            else:
                btn.configure(fg_color="transparent")

        if hasattr(frame, 'on_activate'):
            frame.on_activate()

        self._update_statusbar()

    def _update_statusbar(self):
        try:
            stats = self.db.get_relatorio_stats()
            total = stats.get('total_recebidos', 0)
            now = datetime.now().strftime('%d/%m/%Y %H:%M')
            self.lbl_status_left.configure(
                text=f"  Recebidos este ano: {total}  |  Última actualização: {now}")
        except Exception:
            pass

    def _start_clock(self):
        DIAS_PT = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
                   "Sexta-feira", "Sábado", "Domingo"]
        MESES_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

        def tick():
            now = datetime.now()
            dia_semana = DIAS_PT[now.weekday()]
            mes = MESES_PT[now.month]
            texto = f"{dia_semana}, {now.day:02d} de {mes} de {now.year}   {now.strftime('%H:%M:%S')}"
            self.lbl_clock.configure(text=texto)
            self.after(1000, tick)
        tick()

    def _toggle_tema(self):
        current = ctk.get_appearance_mode().lower()
        new_tema = "light" if current == "dark" else "dark"
        ctk.set_appearance_mode(new_tema)
        self.btn_tema.configure(text="☀️" if new_tema == "light" else "🌙")
        self.config_data['tema'] = new_tema
        self._save_config()

    def _check_alertas_startup(self):
        try:
            alertas = self.db.check_alertas()
            pendentes = alertas.get('docs_pendentes', [])
            reunioes = alertas.get('reunioes_proximas', [])
            msgs = []
            if pendentes:
                msgs.append(f"📋 {len(pendentes)} documento(s) pendente(s) sem resposta.")
            if reunioes:
                msgs.append(f"📅 {len(reunioes)} reunião(ões) nos próximos 3 dias.")
            if msgs:
                self.lbl_notif.configure(text=f"⚠️ {len(pendentes)+len(reunioes)} alerta(s)")
                msg = "\n".join(msgs)
                messagebox.showinfo("Alertas do Sistema", msg, parent=self)
        except Exception:
            pass

    def _on_config_saved(self, new_config):
        self.config_data.update(new_config)
        self.lbl_user.configure(text=f"👤 {self.config_data.get('utilizador', 'Utilizador')}")

    def _save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # Keyboard shortcuts
    def _shortcut_novo(self, event=None):
        if self.current_frame_key and hasattr(self.frames[self.current_frame_key], 'open_new'):
            self.frames[self.current_frame_key].open_new()

    def _shortcut_buscar(self, event=None):
        if self.current_frame_key and hasattr(self.frames[self.current_frame_key], 'focus_search'):
            self.frames[self.current_frame_key].focus_search()

    def _shortcut_exportar(self, event=None):
        if self.current_frame_key and hasattr(self.frames[self.current_frame_key], 'exportar'):
            self.frames[self.current_frame_key].exportar()

    def _shortcut_refresh(self, event=None):
        if self.current_frame_key and hasattr(self.frames[self.current_frame_key], 'refresh'):
            self.frames[self.current_frame_key].refresh()

    def _shortcut_esc(self, event=None):
        pass
