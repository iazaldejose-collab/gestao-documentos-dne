import os
from datetime import datetime
import customtkinter as ctk

try:
    from version import VERSION, HISTORICO, historico_recente_primeiro
except ImportError:
    VERSION = "V1.0.8"
    HISTORICO = []
    def historico_recente_primeiro():
        return list(reversed(HISTORICO))
from tkinter import messagebox

from database import Database
from utils import get_meeting_datetimes, gravar_config
from ui.recebidos import RecebidosFrame
from ui.confidenciais import ConfidenciaisFrame, DesbloquearDialog
from ui.enviados import EnviadosFrame
from ui.reunioes import ReunioesFrame
from ui.relatorio import RelatorioFrame
from ui.contactos import ContactosFrame
from ui.configuracoes import ConfiguracoesFrame
from ui.widgets import setup_context_menu


# Paletas de cores da aparência — aplicadas directamente aos elementos
# principais (header, barra lateral, botões de destaque), já que muitos
# widgets usam cores fixas e não respondem apenas ao set_default_color_theme.
PALETTES = {
    'blue':    {'primary': '#1F4E79', 'primary2': '#0d2b4e',
                'accent': '#2c6fad', 'accent_dark': '#1a4d7d',
                'sidebar': '#1a3a5c', 'sidebar2': '#111c2d'},
    'green':   {'primary': '#1B5E3A', 'primary2': '#0c2e1c',
                'accent': '#27ae60', 'accent_dark': '#1d8348',
                'sidebar': '#1d4a33', 'sidebar2': '#0f2419'},
    'purple':  {'primary': '#5B2C83', 'primary2': '#2d1640',
                'accent': '#8E44AD', 'accent_dark': '#6c3483',
                'sidebar': '#3d1f5c', 'sidebar2': '#1f0f30'},
    'sunset':  {'primary': '#B33939', 'primary2': '#591c1c',
                'accent': '#E67E22', 'accent_dark': '#cb6e1c',
                'sidebar': '#7d2424', 'sidebar2': '#3e1212'},
    'rainbow': {'primary': '#6A1B9A', 'primary2': '#2c0f47',
                'accent': '#E91E63', 'accent_dark': '#AD1457',
                'sidebar': '#283593', 'sidebar2': '#141a4a'},
}

# Sequência de cores do arco-íris usada para dar um efeito de gradiente
# aos botões de navegação quando o esquema "rainbow" está activo.
RAINBOW_HUES = ["#E53935", "#FB8C00", "#FDD835", "#43A047", "#1E88E5", "#8E24AA"]


class App(ctk.CTk):
    def __init__(self, config, config_path):
        super().__init__()
        self.config_data = config
        self.config_path = config_path
        self.db = Database()

        self.cor_tema = config.get('cor_tema', 'blue')
        self.palette = PALETTES.get(self.cor_tema, PALETTES['blue'])

        self.title("Sistema de Gestão de Documentos — DNE | MIREME 2026")
        self.minsize(1280, 800)
        self.geometry("1400x860")

        setup_context_menu(self)

        self._build_layout()
        self._build_header()
        self._build_sidebar()
        self._build_main_area()
        self._build_statusbar()

        self._start_clock()
        self.after(500, self._check_alertas_startup)
        self.after(700, self._update_reunioes_badge)
        self.after(800, self._update_atraso_badge)
        self.after(1200, self._backup_startup)
        self.after(2000, self._check_auto_theme)
        self.after(3500, self._notificacoes_prazos)
        self.after(5000, self._verificar_actualizacoes)

        self.bind_all("<Control-n>", self._shortcut_novo)
        self.bind_all("<Control-f>", self._shortcut_buscar)
        self.bind_all("<Control-e>", self._shortcut_exportar)
        self.bind_all("<F5>",        self._shortcut_refresh)
        self.bind_all("<Escape>",    self._shortcut_esc)
        self.bind_all("<F1>",        self._show_ajuda)

        # Navegação rápida entre secções
        _secoes = ["recebidos", "enviados", "reunioes", "relatorio", "contactos", "configuracoes"]
        for i, sec in enumerate(_secoes, 1):
            self.bind_all(f"<Control-{i}>", lambda e, s=sec: self._show_frame(s))

        # Zoom com Ctrl+scroll do rato
        self._zoom_scale = 1.0   # escala inicial (100%)
        self.bind_all("<Control-MouseWheel>", self._on_zoom)    # Windows
        self.bind_all("<Control-Button-4>",   self._on_zoom)    # Linux scroll up
        self.bind_all("<Control-Button-5>",   self._on_zoom)    # Linux scroll down
        self.bind_all("<Control-0>",          self._zoom_reset) # repor zoom

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Estado da área Confidencial (desbloqueada apenas na sessão actual)
        self._confid_unlocked = False

        last = config.get('last_section', 'recebidos')
        # Nunca restaurar directamente para Confidenciais (exigiria senha ao arrancar)
        if last not in self.frames or last == 'confidenciais':
            last = 'recebidos'
        self._show_frame(last)

    # ── Fecho do aplicativo ───────────────────────────────────────────────────
    def _on_close(self):
        try:
            alertas = self.db.check_alertas()
            pendentes = len(alertas.get('docs_pendentes', []))
            reunioes  = len(alertas.get('reunioes_proximas', []))
            extras = []
            if pendentes:
                extras.append(f"📋 {pendentes} documento(s) pendente(s) sem resposta")
            if reunioes:
                extras.append(f"📅 {reunioes} reunião(ões) nos próximos 3 dias")
            msg = "Tem a certeza que deseja sair do aplicativo?"
            if extras:
                msg += "\n\n⚠️ Atenção:\n" + "\n".join(extras)
        except Exception:
            msg = "Tem a certeza que deseja sair do aplicativo?"
        if not messagebox.askyesno("Confirmar Saída", msg, parent=self):
            return
        self._save_config()   # grava a última secção activa (e restantes definições)
        self._auto_backup_db()
        self.destroy()

    # ── Notificações automáticas de prazos por email ─────────────────────────
    def _notificacoes_prazos(self):
        """Verifica os prazos dos documentos pendentes e envia avisos por email
        aos técnicos (1 dia antes de vencer e quando vencido). Corre numa thread
        de fundo para nunca bloquear a interface; repete a cada 6 horas
        enquanto a aplicação estiver aberta."""
        # reagenda sempre a próxima verificação (6 h), mesmo que esta falhe
        self.after(6 * 3600 * 1000, self._notificacoes_prazos)

        if not self.config_data.get('notificacoes_email', True):
            return
        try:
            from notificacoes import smtp_configurado
            if not smtp_configurado(self.config_data):
                return  # sem SMTP configurado, nada a fazer (silencioso)
        except Exception:
            return

        import threading
        resultado = {}

        def worker():
            try:
                from notificacoes import processar_notificacoes
                resultado.update(processar_notificacoes(self.db, self.config_data))
            except Exception as e:
                resultado['erro'] = str(e)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        def verificar_fim():
            if t.is_alive():
                self.after(1000, verificar_fim)
                return
            emails = resultado.get('emails', 0)
            erro = resultado.get('erro')
            if emails:
                self._statusbar_hold_until = datetime.now().timestamp() + 10
                try:
                    self.lbl_status_left.configure(
                        text=f"  📧 {emails} email(s) de aviso de prazo enviados aos técnicos")
                except Exception:
                    pass
            elif erro and 'SMTP não configurado' not in erro:
                self._statusbar_hold_until = datetime.now().timestamp() + 10
                try:
                    self.lbl_status_left.configure(
                        text=f"  ⚠️ Avisos de prazo: {erro[:90]}")
                except Exception:
                    pass

        self.after(1500, verificar_fim)

    # ── Verificação de novas versões (GitHub) ────────────────────────────────
    def _verificar_actualizacoes(self):
        """Verifica numa thread de fundo se há uma versão mais recente
        publicada no GitHub. Silencioso sem internet ou em caso de erro."""
        import threading

        def worker():
            try:
                from actualizacoes import verificar_actualizacao
                info = verificar_actualizacao()
            except Exception:
                info = None
            if info:
                # Volta à thread da interface antes de mexer em widgets
                try:
                    self.after(0, lambda: self._avisar_nova_versao(info))
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def _avisar_nova_versao(self, info):
        """Mostra o aviso de nova versão: mensagem na barra de estado e,
        uma única vez por versão, uma caixa de diálogo com opção de transferir
        directamente o instalador."""
        nova = info.get('versao') if isinstance(info, dict) else info
        pagina = info.get('pagina') if isinstance(info, dict) else None
        download = info.get('download') if isinstance(info, dict) else None

        self._statusbar_hold_until = datetime.now().timestamp() + 30
        try:
            self.lbl_status_left.configure(
                text=f"  🔔 Nova versão {nova} disponível (instalada: {VERSION}) — "
                     "abra o menu para transferir o instalador")
        except Exception:
            pass

        if self.config_data.get('versao_avisada') == nova:
            return
        self.config_data['versao_avisada'] = nova
        self._save_config()

        destino = download or pagina
        if destino:
            abrir = messagebox.askyesno(
                "Nova versão disponível",
                f"Está disponível a versão {nova} do Sistema de Gestão de "
                f"Documentos (esta máquina tem a {VERSION}).\n\n"
                "Deseja abrir a página de transferência do instalador agora?\n\n"
                "(Depois de transferir, feche a aplicação e execute o instalador "
                "para actualizar — os seus dados são preservados.)",
                parent=self)
            if abrir:
                import webbrowser
                try:
                    webbrowser.open(destino)
                except Exception:
                    pass
        else:
            messagebox.showinfo(
                "Nova versão disponível",
                f"Está disponível a versão {nova} do Sistema de Gestão de "
                f"Documentos (esta máquina tem a {VERSION}).\n\n"
                "Solicite o instalador actualizado ao responsável (DNE/MIREME) "
                "e execute-o para actualizar — os seus dados são preservados.",
                parent=self)

    def _check_auto_theme(self):
        if self.config_data.get('tema_auto', False):
            hora = datetime.now().hour
            novo = "dark" if hora >= 18 or hora < 8 else "light"
            actual = ctk.get_appearance_mode().lower()
            if novo != actual:
                ctk.set_appearance_mode(novo)
                self.btn_tema.configure(text="☀️" if novo == "light" else "🌙")
        self.after(300000, self._check_auto_theme)  # verifica a cada 5 min

    def _backup_startup(self):
        """Cria backup ao iniciar se ainda não existir um backup automático de hoje."""
        try:
            import glob
            from database import DB_PATH
            backups_dir = os.path.join(os.path.dirname(DB_PATH), "Backups")
            hoje = datetime.now().strftime("%Y%m%d")
            existentes = glob.glob(os.path.join(backups_dir, f"auto_backup_{hoje}*.db"))
            if not existentes:
                self._auto_backup_db()
        except Exception:
            pass

    def _auto_backup_db(self):
        """Cria uma cópia de segurança automática da base de dados ao fechar
        o aplicativo, mantendo apenas as 5 mais recentes na pasta Backups/."""
        try:
            import glob
            from database import DB_PATH
            if not os.path.exists(DB_PATH):
                return
            backups_dir = os.path.join(os.path.dirname(DB_PATH), "Backups")
            os.makedirs(backups_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(backups_dir, f"auto_backup_{ts}.db")
            # API de backup do SQLite: cópia consistente mesmo com a BD em uso
            self.db.backup_para(dest)

            # Mantém apenas os 5 backups automáticos mais recentes
            existentes = sorted(glob.glob(os.path.join(backups_dir, "auto_backup_*.db")),
                                key=os.path.getmtime, reverse=True)
            for antigo in existentes[5:]:
                try:
                    os.remove(antigo)
                except OSError:
                    pass
        except Exception:
            pass

    def _build_layout(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def _build_header(self):
        p = self.palette
        self.header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color=(p['primary'], p['primary2']))
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.header.grid_propagate(False)
        self.header.grid_columnconfigure(1, weight=1)

        left_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        left_frame.grid(row=0, column=0, padx=10, pady=6, sticky="w")
        self.lbl_brasao = ctk.CTkLabel(left_frame, text="", width=0)
        self.lbl_brasao.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(left_frame, text="DNE | MIREME — Sistema de Gestão de Documentos",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color="white").pack(side="left")
        self._atualizar_brasao()

        self.lbl_clock = ctk.CTkLabel(self.header, text="", font=ctk.CTkFont(size=13), text_color="#adc8e6")
        self.lbl_clock.grid(row=0, column=1, pady=10)

        right_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        right_frame.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        # Avatar (foto de perfil) + nome — clicáveis para abrir Configurações
        self.lbl_avatar = ctk.CTkLabel(right_frame, text="👤", width=34, height=34,
                                       font=ctk.CTkFont(size=18), text_color="#adc8e6",
                                       cursor="hand2")
        self.lbl_avatar.pack(side="left", padx=(0, 6))
        self.lbl_user = ctk.CTkLabel(right_frame,
                                     text=self.config_data.get('utilizador', 'Utilizador'),
                                     font=ctk.CTkFont(size=12), text_color="#adc8e6",
                                     cursor="hand2")
        self.lbl_user.pack(side="left", padx=(0, 10))
        for _w in (self.lbl_avatar, self.lbl_user):
            _w.bind("<Button-1>", lambda e: self._show_frame('configuracoes'))
        self._atualizar_avatar()

        # Botão para bloquear os Confidenciais — só visível quando desbloqueado
        self.btn_bloquear = ctk.CTkButton(right_frame, text="🔒 Bloquear", width=100, height=28,
                                          command=self._bloquear_confidenciais,
                                          fg_color="#8e44ad", hover_color="#763a92")
        # (não é empacotado agora; aparece via _atualizar_botao_bloquear)

        self.btn_tema = ctk.CTkButton(right_frame, text="🌙", width=36, height=28,
                                      command=self._toggle_tema, fg_color=p['accent'], hover_color=p['accent_dark'])
        self.btn_tema.pack(side="left", padx=(0, 4))

        ctk.CTkButton(right_frame, text="❓", width=32, height=28,
                      command=self._show_ajuda, fg_color="#555", hover_color="#333").pack(side="left")

    def _build_sidebar(self):
        p = self.palette
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=(p['sidebar'], p['sidebar2']))
        self.sidebar.grid(row=1, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        nav_items = [
            ("recebidos", "📥  Recebidos"),
            ("confidenciais", "🔒  Confidenciais"),
            ("enviados", "📤  Enviados"),
            ("reunioes", "📅  Reuniões"),
            ("relatorio", "📊  Relatório"),
            ("contactos", "👥  Contactos"),
            ("configuracoes", "⚙️  Configurações"),
        ]

        self.nav_buttons = {}
        self._nav_labels = {key: label for key, label in nav_items}
        for i, (key, label) in enumerate(nav_items):
            txt_color = RAINBOW_HUES[i % len(RAINBOW_HUES)] if self.cor_tema == 'rainbow' else ("white", "white")
            btn = ctk.CTkButton(self.sidebar, text=label, anchor="w",
                                width=180, height=44,
                                font=ctk.CTkFont(size=13, weight="bold" if self.cor_tema == 'rainbow' else "normal"),
                                fg_color="transparent",
                                hover_color=(p['accent'], p['accent_dark']),
                                text_color=txt_color,
                                corner_radius=6,
                                command=lambda k=key: self._show_frame(k))
            btn.pack(padx=10, pady=(8 if i == 0 else 2, 2))
            self.nav_buttons[key] = btn

        self.lbl_notif = ctk.CTkLabel(self.sidebar, text="", font=ctk.CTkFont(size=11),
                                      text_color="#ff9900", cursor="hand2")
        self.lbl_notif.pack(padx=10, pady=(20, 5))
        self.lbl_notif.bind("<Button-1>", lambda e: self._show_alertas())
        self._alertas_cache = {}

    def _build_main_area(self):
        self.main_container = ctk.CTkFrame(self, corner_radius=0)
        self.main_container.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        self.frames["recebidos"] = RecebidosFrame(self.main_container, self.db, self.config_data)
        self.frames["confidenciais"] = ConfidenciaisFrame(self.main_container, self.db, self.config_data)
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
                                             text=f"{VERSION}  |  DNE/MIREME  |  © Iazalde Jose Jeremias  ",
                                             font=ctk.CTkFont(size=11),
                                             text_color=("#444", "#aaa"),
                                             cursor="hand2")
        self.lbl_status_right.grid(row=0, column=2, padx=5, sticky="e")
        self.lbl_status_right.bind("<Button-1>", self._show_versoes)

    # ── Confidenciais: desbloqueio / bloqueio ────────────────────────────────
    def _desbloquear_confidenciais(self):
        """Pede a senha (ou orienta a defini-la). Devolve True se ficou
        desbloqueado nesta sessão."""
        import seguranca
        if not seguranca.tem_password(self.config_data):
            ir = messagebox.askyesno(
                "Confidenciais sem senha",
                "Ainda não definiu uma senha para a área Confidencial.\n\n"
                "Deseja abrir as Configurações para a definir agora?",
                parent=self)
            if ir:
                self._show_frame('configuracoes')
            return False
        dlg = DesbloquearDialog(self, self.config_data, self.config_path)
        self.wait_window(dlg)
        if getattr(dlg, 'sucesso', False):
            self._confid_unlocked = True
            self._atualizar_botao_bloquear()
            return True
        return False

    def _bloquear_confidenciais(self):
        """Bloqueia de novo a área Confidencial (pedirá senha na próxima vez)."""
        self._confid_unlocked = False
        self._atualizar_botao_bloquear()
        if self.current_frame_key == 'confidenciais':
            self._show_frame('recebidos')

    def _atualizar_botao_bloquear(self):
        try:
            if getattr(self, '_confid_unlocked', False):
                self.btn_bloquear.pack(side="left", padx=(0, 8))
            else:
                self.btn_bloquear.pack_forget()
        except Exception:
            pass

    def _show_frame(self, key):
        # A secção Confidenciais exige desbloqueio por senha antes de abrir
        if key == 'confidenciais' and not getattr(self, '_confid_unlocked', False):
            if not self._desbloquear_confidenciais():
                return  # cancelado ou senha errada — não muda de secção

        if self.current_frame_key == key:
            return
        self.current_frame_key = key
        frame = self.frames[key]
        frame.tkraise()

        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=(self.palette['accent'], self.palette['accent_dark']))
            else:
                btn.configure(fg_color="transparent")

        if hasattr(frame, 'on_activate'):
            frame.on_activate()

        self._update_statusbar()
        # Guardado apenas em memória; é escrito em disco ao fechar a aplicação
        # (evita cifrar e reescrever o config.json a cada mudança de secção)
        self.config_data['last_section'] = key

    def _update_statusbar(self):
        try:
            stats = self.db.get_relatorio_stats()
            recebidos  = stats.get('total_recebidos', 0)
            respondidos = stats.get('total_respondidos', 0)
            fora_prazo = stats.get('total_fora_prazo', 0)
            fora_txt = f"  ⚠️ {fora_prazo} fora do prazo  |" if fora_prazo else ""
            self._statusbar_prefix = (
                f"  📥 {recebidos} recebidos  |  ✅ {respondidos} respondidos  |{fora_txt}")
            self._render_statusbar_left(force=True)
        except Exception:
            pass

    def _render_statusbar_left(self, force=False):
        """Actualiza os contadores + hora no rodapé, mantendo a hora
        sincronizada com o relógio do cabeçalho (é chamado a cada segundo).
        'force' ignora a retenção temporária usada por mensagens passageiras
        como o indicador de zoom."""
        if not force and getattr(self, '_statusbar_hold_until', 0) > datetime.now().timestamp():
            return
        prefix = getattr(self, '_statusbar_prefix', None)
        if prefix is None:
            return
        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        try:
            self.lbl_status_left.configure(text=f"{prefix}  🕐 {now}")
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
            self._render_statusbar_left()  # mantém a hora do rodapé em sincronia
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
            msgs = self._refresh_alertas()
            if msgs:
                messagebox.showinfo("Alertas do Sistema", "\n".join(msgs), parent=self)
        except Exception:
            pass

    def _refresh_alertas(self):
        """Recalcula os alertas, actualiza a etiqueta da barra lateral e
        devolve a lista de mensagens (vazia se não houver alertas)."""
        alertas = self.db.check_alertas()
        pendentes = alertas.get('docs_pendentes', [])
        reunioes = alertas.get('reunioes_proximas', [])
        self._alertas_cache = {'pendentes': pendentes, 'reunioes': reunioes}
        msgs = []
        if pendentes:
            msgs.append(f"📋 {len(pendentes)} documento(s) pendente(s) sem resposta.")
        if reunioes:
            msgs.append(f"📅 {len(reunioes)} reunião(ões) nos próximos 3 dias.")
        total = len(pendentes) + len(reunioes)
        self.lbl_notif.configure(text=f"⚠️ {total} alerta(s)" if total else "")
        return msgs

    def refresh_indicators(self):
        """Actualiza todos os indicadores globais (alertas, crachás da barra
        lateral e rodapé) sem reiniciar a aplicação. Chamado pelos ecrãs
        sempre que os dados mudam ou o utilizador clica em Actualizar."""
        for fn in (self._refresh_alertas, self._refresh_reunioes_badge,
                   self._refresh_atraso_badge, self._update_statusbar):
            try:
                fn()
            except Exception:
                pass

    def _refresh_reunioes_badge(self):
        """Mostra na barra lateral quantas reuniões de hoje ainda estão por
        acontecer ou em curso."""
        hoje = datetime.now().date().isoformat()
        agora = datetime.now()
        reunioes_hoje = self.db.get_all_reunioes(filters={'data_reuniao': hoje})
        count = 0
        for r in reunioes_hoje:
            _, fim = get_meeting_datetimes(r.get('data_reuniao', ''), r.get('hora_local', ''))
            if fim and agora <= fim:
                count += 1

        base = self._nav_labels['reunioes']
        texto = f"{base}   🔴 {count}" if count else base
        self.nav_buttons['reunioes'].configure(text=texto)

    def _update_reunioes_badge(self):
        try:
            self._refresh_reunioes_badge()
        except Exception:
            pass
        self.after(60000, self._update_reunioes_badge)

    def _refresh_atraso_badge(self):
        """Mostra na barra lateral quantos documentos estão fora do prazo."""
        stats = self.db.get_relatorio_stats()
        fora = stats.get('total_fora_prazo', 0)
        base = self._nav_labels['recebidos']
        self.nav_buttons['recebidos'].configure(
            text=f"{base}   🔴 {fora}" if fora > 0 else base)

    def _update_atraso_badge(self):
        try:
            self._refresh_atraso_badge()
        except Exception:
            pass
        self.after(300000, self._update_atraso_badge)  # actualiza a cada 5 min

    def _show_alertas(self):
        cache = getattr(self, '_alertas_cache', {})
        pendentes = cache.get('pendentes', [])
        reunioes = cache.get('reunioes', [])
        if not pendentes and not reunioes:
            messagebox.showinfo("Alertas do Sistema", "Sem alertas no momento. ✅", parent=self)
            return

        win = ctk.CTkToplevel(self)
        win.title("Alertas do Sistema")
        win.geometry("560x440")
        win.grab_set()

        ctk.CTkLabel(win, text="⚠️ Alertas do Sistema",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 5))

        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(fill="both", expand=True, padx=15, pady=10)

        if pendentes:
            ctk.CTkLabel(scroll, text=f"📋 Documentos pendentes sem resposta ({len(pendentes)})",
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=(self.palette["primary"], self.palette["accent"])).pack(anchor="w", pady=(5, 4))
            for d in pendentes:
                txt = f"• {d.get('numero', '')} — {d.get('assunto', '')[:60]}"
                ctk.CTkLabel(scroll, text=txt, anchor="w", justify="left",
                             wraplength=480).pack(anchor="w", padx=10, pady=1)

        if reunioes:
            ctk.CTkLabel(scroll, text=f"📅 Reuniões nos próximos 3 dias ({len(reunioes)})",
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=(self.palette["primary"], self.palette["accent"])).pack(anchor="w", pady=(15, 4))
            for r in reunioes:
                txt = f"• {r.get('data_reuniao', '')} — {r.get('assunto', '')[:60]}"
                ctk.CTkLabel(scroll, text=txt, anchor="w", justify="left",
                             wraplength=480).pack(anchor="w", padx=10, pady=1)

        ctk.CTkButton(win, text="Fechar", width=120, command=win.destroy,
                      fg_color=self.palette["primary"]).pack(pady=(0, 15))

    def _atualizar_avatar(self):
        """Actualiza o avatar do cabeçalho a partir da foto de perfil nas
        configurações (ou mostra o emoji 👤 se não houver foto)."""
        try:
            from ui.widgets import carregar_foto_circular
            img = carregar_foto_circular(self.config_data.get('utilizador_foto'), 30)
        except Exception:
            img = None
        self._avatar_img = img  # manter referência (evita ser recolhido)
        if img:
            self.lbl_avatar.configure(image=img, text="")
        else:
            self.lbl_avatar.configure(image=None, text="👤")

    def _atualizar_brasao(self):
        """Mostra o brasão/logótipo no cabeçalho, antes do título (ou nada)."""
        try:
            from ui.widgets import carregar_imagem_altura
            img = carregar_imagem_altura(self.config_data.get('brasao'), 40)
        except Exception:
            img = None
        self._brasao_img = img  # manter referência
        if img:
            self.lbl_brasao.configure(image=img, text="")
        else:
            self.lbl_brasao.configure(image=None, text="")

    def _on_config_saved(self, new_config):
        self.config_data.update(new_config)
        self.lbl_user.configure(text=self.config_data.get('utilizador', 'Utilizador'))
        self._atualizar_avatar()
        self._atualizar_brasao()

    def _save_config(self):
        try:
            gravar_config(self.config_path, self.config_data)
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
        """Limpa a pesquisa da secção actual (Escape)."""
        if not self.current_frame_key:
            return
        frame = self.frames[self.current_frame_key]
        if hasattr(frame, 'search_var') and frame.search_var.get():
            frame.search_var.set("")
            if hasattr(frame, 'refresh'):
                frame.refresh()

    # ── Zoom (Ctrl + scroll) ──────────────────────────────────────────────────
    def _on_zoom(self, event):
        """Aumenta ou diminui o zoom da janela com Ctrl+scroll."""
        # Windows usa event.delta (+120 / -120); Linux usa event.num (4/5)
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            self._zoom_scale = min(round(self._zoom_scale + 0.1, 1), 2.0)
        else:
            self._zoom_scale = max(round(self._zoom_scale - 0.1, 1), 0.6)

        # CustomTkinter tem o seu próprio sistema de escala
        ctk.set_widget_scaling(self._zoom_scale)
        ctk.set_window_scaling(self._zoom_scale)

        pct = int(round(self._zoom_scale * 100))
        # Segura a mensagem de zoom no rodapé por alguns segundos, para que
        # o relógio (que corre a cada segundo) não a apague de imediato.
        self._statusbar_hold_until = datetime.now().timestamp() + 4
        try:
            self.lbl_status_left.configure(
                text=f"  Zoom: {pct}%  |  Ctrl+scroll para ajustar  |  Ctrl+0 para repor")
        except Exception:
            pass

    def _show_versoes(self, event=None):
        """Janela com histórico de versões — clique na versão no rodapé."""
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Histórico de Versões — {VERSION}")
        dlg.geometry("620x460")
        dlg.grab_set()
        dlg.resizable(False, False)

        # Cabeçalho
        hdr = ctk.CTkFrame(dlg, corner_radius=0, fg_color=(self.palette["primary"], self.palette["primary2"]))
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="📋  Histórico de Versões",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="white").pack(side="left", padx=16, pady=12)
        ctk.CTkLabel(hdr, text=f"Versão actual: {VERSION}",
                     font=ctk.CTkFont(size=12),
                     text_color="#adc8e6").pack(side="right", padx=16)

        # Lista de versões
        scroll = ctk.CTkScrollableFrame(dlg)
        scroll.pack(fill="both", expand=True, padx=12, pady=8)

        for i, (ver, data, descricao) in enumerate(historico_recente_primeiro()):
            is_current = (ver == VERSION)
            bg = ("#dbeafe", "#1e3a5f") if is_current else (
                 "#f0f4f8" if i % 2 == 0 else "white",
                 "#2a2a3a" if i % 2 == 0 else "#222230")

            row = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=8)
            row.pack(fill="x", pady=3)

            left = ctk.CTkFrame(row, fg_color="transparent", width=90)
            left.pack(side="left", padx=(10, 0), pady=8)
            left.pack_propagate(False)

            ctk.CTkLabel(left, text=ver,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=(self.palette["primary"] if is_current else ("#444", "#ccc"))).pack()
            ctk.CTkLabel(left, text=data,
                         font=ctk.CTkFont(size=9),
                         text_color="gray").pack()

            if is_current:
                ctk.CTkLabel(left, text="● ACTUAL",
                             font=ctk.CTkFont(size=8, weight="bold"),
                             text_color="#27ae60").pack()

            ctk.CTkLabel(row, text=descricao,
                         font=ctk.CTkFont(size=11),
                         anchor="w", justify="left",
                         wraplength=470).pack(side="left", padx=10, pady=8, fill="x", expand=True)

        # Rodapé
        ctk.CTkLabel(dlg, text="Clique na versão no rodapé da janela principal para ver este histórico.",
                     font=ctk.CTkFont(size=10), text_color="gray").pack(pady=(0, 4))
        ctk.CTkButton(dlg, text="Fechar", command=dlg.destroy,
                      fg_color=self.palette["primary"], width=100).pack(pady=(0, 10))

    def _show_ajuda(self, event=None):
        """Diálogo com todos os atalhos de teclado."""
        import customtkinter as ctk2
        dlg = ctk2.CTkToplevel(self)
        dlg.title("Ajuda — Atalhos de Teclado")
        dlg.geometry("420x480")
        dlg.grab_set()
        dlg.resizable(False, False)

        ctk2.CTkLabel(dlg, text="⌨️  Atalhos de Teclado",
                      font=ctk2.CTkFont(size=15, weight="bold")).pack(pady=(16, 8))

        atalhos = [
            ("Ctrl + N",       "Novo documento / entrada"),
            ("Ctrl + F",       "Pesquisar / Focar campo de pesquisa"),
            ("Ctrl + E",       "Exportar para Excel"),
            ("Ctrl + S",       "Guardar formulário aberto"),
            ("F5",             "Actualizar lista"),
            ("F1",             "Esta janela de ajuda"),
            ("── Navegação ──", ""),
            ("Ctrl + 1",       "Ir para Recebidos"),
            ("Ctrl + 2",       "Ir para Enviados"),
            ("Ctrl + 3",       "Ir para Reuniões"),
            ("Ctrl + 4",       "Ir para Relatório"),
            ("Ctrl + 5",       "Ir para Contactos"),
            ("Ctrl + 6",       "Ir para Configurações"),
            ("── Tabela ──", ""),
            ("Enter",          "Editar linha seleccionada"),
            ("Delete",         "Eliminar linha seleccionada"),
            ("Escape",         "Limpar pesquisa"),
            ("Duplo Clique",   "Editar documento seleccionado"),
            ("Clique no Cabeçalho", "Ordenar coluna (segundo clique inverte)"),
            ("Botão Direito",  "Menu de contexto (copiar / colar)"),
            ("── Zoom ──", ""),
            ("Ctrl + Scroll ↑","Aumentar zoom"),
            ("Ctrl + Scroll ↓","Diminuir zoom"),
            ("Ctrl + 0",       "Repor zoom a 100%"),
        ]

        frame = ctk2.CTkScrollableFrame(dlg)
        frame.pack(fill="both", expand=True, padx=16, pady=8)

        row_count = 0
        for atalho, descricao in atalhos:
            if atalho.startswith("──"):
                ctk2.CTkLabel(frame, text=atalho,
                              font=ctk2.CTkFont(size=10, weight="bold"),
                              text_color="gray").pack(anchor="w", padx=10, pady=(8, 2))
                continue
            bg = ("#f0f4f8", "#2a2a3a") if row_count % 2 == 0 else ("white", "#222230")
            row_count += 1
            row = ctk2.CTkFrame(frame, fg_color=bg, corner_radius=6, height=32)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)
            ctk2.CTkLabel(row, text=atalho, font=ctk2.CTkFont(size=11, weight="bold"),
                          width=150, anchor="w",
                          text_color=(self.palette["primary"], self.palette["accent"])).pack(side="left", padx=10)
            ctk2.CTkLabel(row, text=descricao, font=ctk2.CTkFont(size=11),
                          anchor="w").pack(side="left", padx=4)

        ctk2.CTkButton(dlg, text="Fechar", command=dlg.destroy,
                       fg_color=self.palette["primary"]).pack(pady=12)

    def _zoom_reset(self, event=None):
        """Repõe o zoom para 100%."""
        self._zoom_scale = 1.0
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
        self._statusbar_hold_until = datetime.now().timestamp() + 2
        try:
            self.lbl_status_left.configure(text="  Zoom: 100%")
            self.after(2000, self._update_statusbar)
        except Exception:
            pass
