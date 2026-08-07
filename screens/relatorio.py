"""
screens/relatorio.py
Relatório dinâmico: escolha o que vai nas linhas, o que vai nas
colunas e qual valor comparar - tipo uma tabela dinâmica de planilha.

Dimensões disponíveis (tanto para linha quanto para coluna): Mês,
Loja, Setor, Loja + Setor, Funcionário. Dá pra filtrar por loja,
setor e/ou funcionário antes de gerar a tabela, além de escolher
quais meses entram na base de dados.
"""
import customtkinter as ctk
import tkinter as tk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from widgets import (
    Card, fmt_moeda,
    PAPER, INK, INK_SOFT, LINE, TEAL, TEAL_DARK,
    FONT_H1, FONT_H2, FONT_BODY, FONT_SMALL,
)
from logic import calcular_mes_completo, linhas_detalhadas_mes

DIMENSOES = {
    "Mês": lambda r: r["mes"],
    "Loja": lambda r: r["empresa"],
    "Setor": lambda r: r["estabelecimento"],
    "Loja + Setor": lambda r: f"{r['empresa']} · {r['estabelecimento']}",
    "Funcionário": lambda r: r["nome"],
}
SEM_COLUNA = "(Nenhuma — só o total)"

METRICAS = {
    "Valor vendido": "vendido",
    "Valor devoluções": "devolucoes",
    "Valor líquido": "liquido",
    "Comissão": "comissao",
    "Bônus individual": "bonif_individual",
    "Bônus de equipe": "bonif_equipe",
    "Total a receber": "total",
}


def _mes_ordenacao(mes):
    try:
        m, a = mes.split("/")
        return (int(a), int(m))
    except (ValueError, AttributeError):
        return (0, 0)


class RelatorioScreen(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=PAPER)
        self.app = app
        self.mes_vars = {}
        self._ultimo_pivot = None
        self._grafico_popup = None

        self.grid_columnconfigure(0, weight=1)
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Relatório Dinâmico", font=FONT_H1, text_color=INK, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 2))
        ctk.CTkLabel(frame, text="Monte a comparação: escolha o que entra nas linhas, nas colunas e qual valor olhar.",
                     font=FONT_BODY, text_color=INK_SOFT, anchor="w").grid(row=1, column=0, sticky="w", pady=(0, 18))

        filtro_card = Card(frame)
        filtro_card.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        filtro_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(filtro_card, text="Meses incluídos na base", font=FONT_H2, text_color=INK, anchor="w").grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 8))
        self.meses_wrap = ctk.CTkFrame(filtro_card, fg_color="transparent")
        self.meses_wrap.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 14))

        dims_row = ctk.CTkFrame(filtro_card, fg_color="transparent")
        dims_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 6))
        dims_row.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(dims_row, text="Linhas", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(row=0, column=0, sticky="w")
        self.linha_var = tk.StringVar(value="Loja + Setor")
        ctk.CTkOptionMenu(dims_row, values=list(DIMENSOES.keys()), variable=self.linha_var).grid(
            row=1, column=0, sticky="ew", padx=(0, 10), pady=(2, 0))

        ctk.CTkLabel(dims_row, text="Colunas", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(row=0, column=1, sticky="w")
        self.coluna_var = tk.StringVar(value="Mês")
        ctk.CTkOptionMenu(dims_row, values=[SEM_COLUNA] + list(DIMENSOES.keys()), variable=self.coluna_var).grid(
            row=1, column=1, sticky="ew", padx=10, pady=(2, 0))

        ctk.CTkLabel(dims_row, text="Valor", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(row=0, column=2, sticky="w")
        self.metrica_var = tk.StringVar(value=list(METRICAS.keys())[0])
        ctk.CTkOptionMenu(dims_row, values=list(METRICAS.keys()), variable=self.metrica_var).grid(
            row=1, column=2, sticky="ew", padx=(10, 0), pady=(2, 0))

        filtros_row = ctk.CTkFrame(filtro_card, fg_color="transparent")
        filtros_row.grid(row=3, column=0, sticky="ew", padx=20, pady=(14, 6))
        filtros_row.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(filtros_row, text="Filtrar loja", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(row=0, column=0, sticky="w")
        self.filtro_loja_var = tk.StringVar(value="Todas")
        self.filtro_loja_menu = ctk.CTkOptionMenu(filtros_row, values=["Todas"], variable=self.filtro_loja_var)
        self.filtro_loja_menu.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(2, 0))

        ctk.CTkLabel(filtros_row, text="Filtrar setor", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(row=0, column=1, sticky="w")
        self.filtro_setor_var = tk.StringVar(value="Todos")
        self.filtro_setor_menu = ctk.CTkOptionMenu(filtros_row, values=["Todos"], variable=self.filtro_setor_var)
        self.filtro_setor_menu.grid(row=1, column=1, sticky="ew", padx=10, pady=(2, 0))

        ctk.CTkLabel(filtros_row, text="Filtrar funcionário", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(row=0, column=2, sticky="w")
        self.filtro_func_var = tk.StringVar(value="Todos")
        self.filtro_func_menu = ctk.CTkOptionMenu(filtros_row, values=["Todos"], variable=self.filtro_func_var)
        self.filtro_func_menu.grid(row=1, column=2, sticky="ew", padx=(10, 0), pady=(2, 0))

        ctk.CTkButton(filtro_card, text="Gerar tabela dinâmica", fg_color=TEAL, hover_color=TEAL_DARK,
                      command=self.gerar).grid(row=4, column=0, sticky="w", padx=20, pady=(16, 18))

        self.result_wrap = ctk.CTkFrame(frame, fg_color="transparent")
        self.result_wrap.grid(row=3, column=0, sticky="ew")
        self.result_wrap.grid_columnconfigure(0, weight=1)

        self.refresh_filtros()

    # ---------------- Preparar filtros (chamar sempre que a tela é aberta) ----------------
    def refresh_filtros(self):
        for w in self.meses_wrap.winfo_children():
            w.destroy()
        self.mes_vars = {}
        meses = sorted(self.app.fechamentos.keys(), key=_mes_ordenacao)
        if not meses:
            ctk.CTkLabel(self.meses_wrap, text="Nenhum fechamento salvo ainda - feche pelo menos um setor em Cálculo Mensal.",
                         text_color=INK_SOFT, font=FONT_BODY).pack(anchor="w")
        for mes in meses:
            var = tk.BooleanVar(value=True)
            ctk.CTkCheckBox(self.meses_wrap, text=mes, variable=var, font=FONT_SMALL).pack(side="left", padx=(0, 14))
            self.mes_vars[mes] = var

        self.filtro_loja_menu.configure(values=["Todas"] + [e["nome"] for e in self.app.empresas])
        self.filtro_setor_menu.configure(values=["Todos"] + [e["nome"] for e in self.app.estabelecimentos])
        self.filtro_func_menu.configure(values=["Todos"] + sorted({f["nome"] for f in self.app.funcionarios}))

    # ---------------- Montar a base de dados (achatada) ----------------
    def _base_dados(self):
        meses = [m for m, v in self.mes_vars.items() if v.get()]
        meses.sort(key=_mes_ordenacao)
        registros = []
        for mes in meses:
            res = calcular_mes_completo(self.app.funcionarios, self.app.metas_equipe, self.app.fechamentos.get(mes, {}), self.app.funcoes, self.app.estabelecimentos)
            registros.extend(linhas_detalhadas_mes(mes, res))

        if self.filtro_loja_var.get() != "Todas":
            registros = [r for r in registros if r["empresa"] == self.filtro_loja_var.get()]
        if self.filtro_setor_var.get() != "Todos":
            registros = [r for r in registros if r["estabelecimento"] == self.filtro_setor_var.get()]
        if self.filtro_func_var.get() != "Todos":
            registros = [r for r in registros if r["nome"] == self.filtro_func_var.get()]
        return registros

    # ---------------- Gerar a tabela dinâmica ----------------
    def gerar(self):
        for w in self.result_wrap.winfo_children():
            w.destroy()

        registros = self._base_dados()
        if not registros:
            ctk.CTkLabel(self.result_wrap, text="Nenhum dado encontrado para os filtros escolhidos.",
                         text_color=INK_SOFT, font=FONT_BODY).grid(row=0, column=0, sticky="w", pady=10)
            return

        linha_dim = self.linha_var.get()
        coluna_dim = self.coluna_var.get()
        metrica_label = self.metrica_var.get()
        metrica_key = METRICAS[metrica_label]

        row_fn = DIMENSOES[linha_dim]
        tem_coluna = coluna_dim != SEM_COLUNA
        col_fn = DIMENSOES[coluna_dim] if tem_coluna else (lambda r: "Total")

        pivot = {}
        row_keys = []
        col_keys = []
        for r in registros:
            rk = row_fn(r)
            ck = col_fn(r)
            if rk not in row_keys:
                row_keys.append(rk)
            if ck not in col_keys:
                col_keys.append(ck)
            pivot[(rk, ck)] = pivot.get((rk, ck), 0) + (r.get(metrica_key) or 0)

        row_keys.sort()
        if tem_coluna and coluna_dim == "Mês":
            col_keys.sort(key=_mes_ordenacao)
        else:
            col_keys.sort()

        self._ultimo_pivot = {
            "row_keys": row_keys, "col_keys": col_keys, "pivot": pivot,
            "linha_dim": linha_dim, "coluna_dim": coluna_dim, "tem_coluna": tem_coluna,
            "metrica_label": metrica_label,
        }

        card = Card(self.result_wrap)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 10))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text=f"{linha_dim} × {coluna_dim if tem_coluna else 'Total'} — {metrica_label}",
                     font=FONT_H2, text_color=INK, anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkButton(head, text="📊 Gráfico", fg_color=TEAL, hover_color=TEAL_DARK, width=110,
                      command=self.abrir_grafico).grid(row=0, column=1, sticky="e")

        tbl = ctk.CTkFrame(card, fg_color="transparent")
        tbl.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 18))

        tbl.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tbl, text=linha_dim.upper(), font=FONT_SMALL, text_color=INK_SOFT).grid(
            row=0, column=0, sticky="w", padx=(0, 16))
        for c, ck in enumerate(col_keys, start=1):
            tbl.grid_columnconfigure(c, weight=1)
            ctk.CTkLabel(tbl, text=str(ck), font=FONT_SMALL, text_color=INK_SOFT).grid(
                row=0, column=c, sticky="e", padx=(0, 16))
        if len(col_keys) > 1:
            tbl.grid_columnconfigure(len(col_keys) + 1, weight=1)
            ctk.CTkLabel(tbl, text="TOTAL", font=("Segoe UI Semibold", 11), text_color=INK).grid(
                row=0, column=len(col_keys) + 1, sticky="e", padx=(0, 16))

        for r, rk in enumerate(row_keys, start=1):
            ctk.CTkLabel(tbl, text=str(rk), font=FONT_BODY, text_color=INK).grid(
                row=r, column=0, sticky="w", pady=4, padx=(0, 16))
            soma_linha = 0
            for c, ck in enumerate(col_keys, start=1):
                valor = pivot.get((rk, ck), 0)
                soma_linha += valor
                ctk.CTkLabel(tbl, text=fmt_moeda(valor), font=FONT_BODY, text_color=INK).grid(
                    row=r, column=c, sticky="e", pady=4, padx=(0, 16))
            if len(col_keys) > 1:
                ctk.CTkLabel(tbl, text=fmt_moeda(soma_linha), font=("Segoe UI Semibold", 12), text_color=TEAL_DARK).grid(
                    row=r, column=len(col_keys) + 1, sticky="e", pady=4, padx=(0, 16))

        # Linha de total por coluna
        r_total = len(row_keys) + 1
        ctk.CTkLabel(tbl, text="TOTAL", font=("Segoe UI Semibold", 12), text_color=INK).grid(
            row=r_total, column=0, sticky="w", pady=(8, 0), padx=(0, 16))
        soma_geral = 0
        for c, ck in enumerate(col_keys, start=1):
            soma_col = sum(pivot.get((rk, ck), 0) for rk in row_keys)
            soma_geral += soma_col
            ctk.CTkLabel(tbl, text=fmt_moeda(soma_col), font=("Segoe UI Semibold", 12), text_color=INK).grid(
                row=r_total, column=c, sticky="e", pady=(8, 0), padx=(0, 16))
        if len(col_keys) > 1:
            ctk.CTkLabel(tbl, text=fmt_moeda(soma_geral), font=("Segoe UI Semibold", 12), text_color=TEAL_DARK).grid(
                row=r_total, column=len(col_keys) + 1, sticky="e", pady=(8, 0), padx=(0, 16))

    # ---------------- Gráfico ----------------
    def abrir_grafico(self):
        dados = self._ultimo_pivot
        if not dados:
            return
        if self._grafico_popup is not None and self._grafico_popup.winfo_exists():
            self._grafico_popup.destroy()

        popup = ctk.CTkToplevel(self)
        popup.title("Gráfico")
        popup.geometry("900x620")
        popup.transient(self.winfo_toplevel())
        self._grafico_popup = popup

        row_keys = dados["row_keys"]
        col_keys = dados["col_keys"]
        pivot = dados["pivot"]
        metrica_label = dados["metrica_label"]
        coluna_dim = dados["coluna_dim"]
        tem_coluna = dados["tem_coluna"]
        linha_dim = dados["linha_dim"]

        ctk.CTkLabel(popup, text=f"{linha_dim} × {coluna_dim if tem_coluna else 'Total'} — {metrica_label}",
                     font=FONT_H2, text_color=INK).pack(anchor="w", padx=16, pady=(14, 4))

        fig = Figure(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111)
        cores = ["#0E9E8C", "#E3A73C", "#12213D", "#C0524A", "#6C8EBF", "#8E6C8F"]

        if not tem_coluna or len(col_keys) <= 1:
            coluna_unica = col_keys[0] if col_keys else "Total"
            valores = [pivot.get((rk, coluna_unica), 0) for rk in row_keys]
            ax.bar([str(rk) for rk in row_keys], valores, color=cores[0])
            ax.set_ylabel(metrica_label)
            ax.set_xticklabels([str(rk) for rk in row_keys], rotation=25, ha="right")

        elif coluna_dim == "Mês":
            for i, rk in enumerate(row_keys):
                valores = [pivot.get((rk, ck), 0) for ck in col_keys]
                ax.plot(col_keys, valores, marker="o", label=str(rk), color=cores[i % len(cores)])
            ax.set_ylabel(metrica_label)
            ax.legend(fontsize=8)

        else:
            largura = 0.8 / max(len(col_keys), 1)
            posicoes = list(range(len(row_keys)))
            for i, ck in enumerate(col_keys):
                valores = [pivot.get((rk, ck), 0) for rk in row_keys]
                offsets = [p + i * largura for p in posicoes]
                ax.bar(offsets, valores, width=largura, label=str(ck), color=cores[i % len(cores)])
            centro = [p + largura * (len(col_keys) - 1) / 2 for p in posicoes]
            ax.set_xticks(centro)
            ax.set_xticklabels([str(rk) for rk in row_keys], rotation=25, ha="right")
            ax.set_ylabel(metrica_label)
            ax.legend(fontsize=8)

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=popup)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=14, pady=(0, 14))