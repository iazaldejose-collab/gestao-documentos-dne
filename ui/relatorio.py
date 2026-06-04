import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class RelatorioFrame(ctk.CTkFrame):
    def __init__(self, parent, db, config):
        super().__init__(parent, corner_radius=0)
        self.db = db
        self.config = config
        self._canvas_widget = None
        self._fig = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_toolbar()
        self._build_body()

    def _build_toolbar(self):
        tb = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color=("gray90", "gray20"))
        tb.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(tb, text="📊  Relatório e Dashboard",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=15)

        btn_frame = ctk.CTkFrame(tb, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)
        ctk.CTkButton(btn_frame, text="🔄 Actualizar", width=110, command=self.refresh,
                      fg_color="#1F4E79").pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="📤 Exportar Excel", width=130, command=self.exportar,
                      fg_color="#27ae60").pack(side="left", padx=4)

    def _build_body(self):
        self.scroll = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.scroll.grid(row=1, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)
        self.refresh()

    def refresh(self, *args):
        # Clear existing content
        for w in self.scroll.winfo_children():
            w.destroy()
        if self._fig is not None:
            try:
                plt.close(self._fig)
            except Exception:
                pass
            self._fig = None
        self._canvas_widget = None

        try:
            self._build_kpis()
            self._build_dept_table()
            if HAS_MATPLOTLIB:
                self._build_chart()
            self._build_remetentes()
        except Exception as e:
            ctk.CTkLabel(self.scroll, text=f"Erro ao carregar relatório: {e}",
                         text_color="red").pack(pady=20)

    def _build_kpis(self):
        stats = self.db.get_relatorio_stats()
        section = ctk.CTkFrame(self.scroll, corner_radius=8)
        section.pack(fill="x", padx=15, pady=(15, 8))

        ctk.CTkLabel(section, text="Indicadores Chave de Desempenho",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        cards_frame = ctk.CTkFrame(section, fg_color="transparent")
        cards_frame.pack(fill="x", padx=10, pady=(0, 10))

        kpis = [
            ("📥 Recebidos\n(Este Ano)", str(stats['total_recebidos']), "#1F4E79"),
            ("✅ Respondidos", str(stats['total_respondidos']), "#27ae60"),
            ("📈 Taxa Cumprimento", f"{stats['taxa_cumprimento']}%",
             "#27ae60" if stats['taxa_cumprimento'] >= 80 else "#e67e22"),
            ("⚠️ Fora do Prazo", str(stats['total_fora_prazo']), "#c0392b"),
            ("📅 Reuniões\n(Este Mês)", str(stats['reunioes_mes']), "#8e44ad"),
            ("📤 Enviados\n(Este Ano)", str(stats['total_enviados']), "#2c6fad"),
        ]

        for label, value, color in kpis:
            card = ctk.CTkFrame(cards_frame, width=150, height=90, corner_radius=10,
                                fg_color=color)
            card.pack(side="left", padx=6, pady=4)
            card.pack_propagate(False)
            ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=26, weight="bold"),
                         text_color="white").pack(expand=True)
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=10),
                         text_color="white", wraplength=140, justify="center").pack(pady=(0, 6))

    def _build_dept_table(self):
        depts = self.db.get_relatorio_departamentos()
        section = ctk.CTkFrame(self.scroll, corner_radius=8)
        section.pack(fill="x", padx=15, pady=8)

        ctk.CTkLabel(section, text="Desempenho por Departamento",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        table_frame = ctk.CTkFrame(section, fg_color="transparent")
        table_frame.pack(fill="x", padx=10, pady=(0, 10))

        style = ttk.Style()
        style.configure("Dept.Treeview", rowheight=24, font=('Segoe UI', 10))
        style.configure("Dept.Treeview.Heading", font=('Segoe UI', 10, 'bold'),
                        background="#1F4E79", foreground="white")

        cols = ("dept", "total", "dentro", "fora", "taxa")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                            style="Dept.Treeview", height=6)
        col_cfg = [("dept", "Departamento", 260), ("total", "Total", 70),
                   ("dentro", "Dentro Prazo", 100), ("fora", "Fora Prazo", 100), ("taxa", "Taxa (%)", 80)]
        for col, heading, width in col_cfg:
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=40)
        for d in depts:
            tree.insert("", "end", values=(
                d['departamento'], d['total'], d['dentro_prazo'], d['fora_prazo'],
                f"{d['taxa']}%"
            ))
        tree.pack(fill="x")

    def _build_chart(self):
        depts = self.db.get_relatorio_departamentos()
        if not depts:
            return

        section = ctk.CTkFrame(self.scroll, corner_radius=8)
        section.pack(fill="x", padx=15, pady=8)
        ctk.CTkLabel(section, text="Gráfico: Dentro vs Fora do Prazo por Departamento",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        try:
            labels = [d['departamento'].replace("Dep. ", "").replace("Rep. ", "") for d in depts]
            dentro = [d['dentro_prazo'] for d in depts]
            fora = [d['fora_prazo'] for d in depts]

            self._fig, ax = plt.subplots(figsize=(9, 3.5))
            x = range(len(labels))
            width = 0.35
            bars1 = ax.bar([i - width / 2 for i in x], dentro, width, label='Dentro do Prazo', color='#27ae60')
            bars2 = ax.bar([i + width / 2 for i in x], fora, width, label='Fora do Prazo', color='#c0392b')
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=20, ha='right', fontsize=8)
            ax.set_ylabel('Documentos')
            ax.set_title('Cumprimento por Departamento')
            ax.legend()
            self._fig.tight_layout()

            canvas = FigureCanvasTkAgg(self._fig, master=section)
            self._canvas_widget = canvas.get_tk_widget()
            self._canvas_widget.pack(fill="x", padx=10, pady=(0, 10))
            canvas.draw()
        except Exception as e:
            ctk.CTkLabel(section, text=f"Gráfico indisponível: {e}").pack(pady=10)

    def _build_remetentes(self):
        remetentes = self.db.get_remetentes_frequentes()
        section = ctk.CTkFrame(self.scroll, corner_radius=8)
        section.pack(fill="x", padx=15, pady=(8, 15))
        ctk.CTkLabel(section, text="Principais Remetentes",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        style = ttk.Style()
        style.configure("Rem.Treeview", rowheight=24, font=('Segoe UI', 10))
        style.configure("Rem.Treeview.Heading", font=('Segoe UI', 10, 'bold'),
                        background="#1F4E79", foreground="white")

        cols = ("proveniencia", "total")
        tree = ttk.Treeview(section, columns=cols, show="headings",
                            style="Rem.Treeview", height=min(len(remetentes), 8))
        tree.heading("proveniencia", text="Proveniência / Instituição")
        tree.column("proveniencia", width=300)
        tree.heading("total", text="Total Documentos")
        tree.column("total", width=130)
        for r in remetentes:
            tree.insert("", "end", values=(r['proveniencia'], r['total']))
        tree.pack(fill="x", padx=10, pady=(0, 10))

    def exportar(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="relatorio_dne.xlsx",
            parent=self
        )
        if not filepath:
            return
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Relatório"
            ws.append(["RELATÓRIO DE GESTÃO DE DOCUMENTOS — DNE/MIREME"])
            ws["A1"].font = Font(bold=True, size=14)
            ws.append([])

            stats = self.db.get_relatorio_stats()
            ws.append(["Indicador", "Valor"])
            for cell in ws[ws.max_row]:
                cell.font = Font(bold=True)
            kpis = [
                ("Total Recebidos (Este Ano)", stats['total_recebidos']),
                ("Total Respondidos", stats['total_respondidos']),
                ("Taxa de Cumprimento (%)", f"{stats['taxa_cumprimento']}%"),
                ("Total Fora do Prazo", stats['total_fora_prazo']),
                ("Reuniões Este Mês", stats['reunioes_mes']),
                ("Total Enviados (Este Ano)", stats['total_enviados']),
            ]
            for k, v in kpis:
                ws.append([k, v])
            ws.append([])

            ws.append(["Desempenho por Departamento"])
            ws[ws.cell(ws.max_row, 1).coordinate].font = Font(bold=True)
            ws.append(["Departamento", "Total", "Dentro Prazo", "Fora Prazo", "Taxa (%)"])
            depts = self.db.get_relatorio_departamentos()
            for d in depts:
                ws.append([d['departamento'], d['total'], d['dentro_prazo'],
                            d['fora_prazo'], f"{d['taxa']}%"])

            wb.save(filepath)
            messagebox.showinfo("Sucesso", f"Relatório exportado para:\n{filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar:\n{e}", parent=self)

    def on_activate(self):
        self.refresh()
