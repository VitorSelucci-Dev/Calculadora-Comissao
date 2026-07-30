"""
screens/calculo.py
Tela de Cálculo Mensal, com 3 partes:

- Lista (tela padrão ao entrar): agrupada por MÊS, mostrando os
  setores já preenchidos naquele mês (Editar/Excluir cada um) e um
  botão para ver a folha completa consolidada do mês.
- Formulário: escolha Loja + Setor + Mês, preencha o valor vendido
  pelos vendedores daquele setor. Dá pra "convidar" um funcionário de
  outro setor que vendeu ali também (conta no total do setor, mas a
  bonificação de equipe dele continua vindo do setor de origem).
- Folha do mês: consolida todos os setores preenchidos naquele mês e
  mostra o total a receber de cada funcionário (aqui entra o botão
  de Imprimir).

Os dados ficam em app.fechamentos (ver logic.py para o formato).
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

from widgets import (
    Card, MoneyEntry, MesEntry, mes_valido, nivel_badge, fmt_moeda,
    PAPER, INK, INK_SOFT, LINE, TEAL, TEAL_DARK, AMBER, RED,
    FONT_H1, FONT_H2, FONT_BODY, FONT_SMALL,
)
from logic import calcular_fechamento_setor, calcular_mes_completo
from pdf_export import gerar_pdf_relatorio, gerar_pdf_simplificado


def _mes_ordenacao(mes):
    try:
        m, a = mes.split("/")
        return (int(a), int(m))
    except (ValueError, AttributeError):
        return (0, 0)


class StatBox(ctk.CTkFrame):
    def __init__(self, master, label, value="—", accent=INK, **kwargs):
        super().__init__(master, fg_color="#FFFFFF", corner_radius=10,
                          border_width=1, border_color=LINE, **kwargs)
        ctk.CTkLabel(self, text=label.upper(), font=FONT_SMALL, text_color=INK_SOFT,
                     anchor="w").pack(fill="x", padx=16, pady=(14, 2))
        ctk.CTkLabel(self, text=value, font=("Segoe UI Semibold", 20),
                     text_color=accent, anchor="w").pack(fill="x", padx=16, pady=(0, 14))


class CalculoScreen(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=PAPER)
        self.app = app
        self._venda_entries = {}     # funcionario_id -> (entry_vendido, entry_devolucoes)
        self._editing_original_key = None   # (mes, empresa, estabelecimento) quando editando

        self.grid_columnconfigure(0, weight=1)

        # ---------------- Tela de lista (agrupada por mês) ----------------
        self.list_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.list_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.list_frame, text="Cálculo Mensal", font=FONT_H1, text_color=INK, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 2))
        ctk.CTkLabel(self.list_frame, text="Fechamentos por loja e setor, agrupados por mês.",
                     font=FONT_BODY, text_color=INK_SOFT, anchor="w").grid(row=1, column=0, sticky="w", pady=(0, 14))

        ctk.CTkButton(self.list_frame, text="+ Novo fechamento de setor", fg_color=TEAL, hover_color=TEAL_DARK,
                      command=self.novo_fechamento).grid(row=2, column=0, sticky="w", pady=(0, 18))

        self.saved_list_wrap = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        self.saved_list_wrap.grid(row=3, column=0, sticky="ew")
        self.saved_list_wrap.grid_columnconfigure(0, weight=1)

        # ---------------- Tela de formulário (preencher 1 setor) ----------------
        self.form_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form_frame.grid_columnconfigure(0, weight=1)
        self._build_form()

        # ---------------- Tela de folha completa do mês ----------------
        self.month_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.month_frame.grid_columnconfigure(0, weight=1)

        self.mostrar_lista()

    # ================= FORMULÁRIO (preencher 1 setor) =================
    def _build_form(self):
        top_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(top_row, text="← Voltar para a lista", fg_color="transparent", border_width=1,
                      border_color=LINE, text_color=INK_SOFT, width=160,
                      command=self.voltar_para_lista).grid(row=0, column=0, sticky="w")

        self.form_title_lbl = ctk.CTkLabel(self.form_frame, text="Novo fechamento de setor", font=FONT_H1,
                                            text_color=INK, anchor="w")
        self.form_title_lbl.grid(row=1, column=0, sticky="w", pady=(14, 2))
        ctk.CTkLabel(self.form_frame, text="Escolha a loja, o setor e o mês, depois preencha o valor vendido.",
                     font=FONT_BODY, text_color=INK_SOFT, anchor="w").grid(row=2, column=0, sticky="w", pady=(0, 18))

        top_card = Card(self.form_frame)
        top_card.grid(row=3, column=0, sticky="ew", pady=(0, 18))
        top_card.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(top_card, text="Loja", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 2))
        self.empresa_var = tk.StringVar()
        self.empresa_menu = ctk.CTkOptionMenu(top_card, values=self._nomes_empresas(), variable=self.empresa_var)
        self.empresa_menu.grid(row=1, column=0, sticky="ew", padx=(20, 10), pady=(0, 16))

        ctk.CTkLabel(top_card, text="Setor", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=0, column=1, sticky="w", pady=(16, 2))
        self.setor_var = tk.StringVar()
        self.setor_menu = ctk.CTkOptionMenu(top_card, values=self._nomes_estabelecimentos(), variable=self.setor_var)
        self.setor_menu.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 16))

        ctk.CTkLabel(top_card, text="Mês (MM/AAAA)", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=0, column=2, sticky="w", padx=(0, 20), pady=(16, 2))
        self.mes_entry = MesEntry(top_card, placeholder_text="Ex: 08/2026")
        self.mes_entry.grid(row=1, column=2, sticky="ew", padx=(10, 20), pady=(0, 10))
        ctk.CTkButton(top_card, text="Carregar / Calcular", fg_color=TEAL, hover_color=TEAL_DARK,
                      command=self.calcular).grid(row=2, column=2, sticky="e", padx=(10, 20), pady=(0, 16))

        self.result_wrap = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.result_wrap.grid(row=4, column=0, sticky="ew")
        self.result_wrap.grid_columnconfigure(0, weight=1)

    def _nomes_empresas(self):
        return [e["nome"] for e in self.app.empresas] or ["Matriz"]

    def _nomes_estabelecimentos(self):
        return [e["nome"] for e in self.app.estabelecimentos] or ["Geral"]

    def _travar_seletor(self, travado):
        estado = "disabled" if travado else "normal"
        self.empresa_menu.configure(state=estado)
        self.setor_menu.configure(state=estado)
        self.mes_entry.configure(state=estado)

    # ---------------- Navegação entre as 3 telas ----------------
    def mostrar_lista(self):
        self.form_frame.grid_remove()
        self.month_frame.grid_remove()
        self.list_frame.grid(row=0, column=0, sticky="nsew")
        self.refresh_lista()

    def mostrar_formulario(self):
        self.list_frame.grid_remove()
        self.month_frame.grid_remove()
        self.form_frame.grid(row=0, column=0, sticky="nsew")

    def mostrar_mes(self, mes):
        self.list_frame.grid_remove()
        self.form_frame.grid_remove()
        self.month_frame.grid(row=0, column=0, sticky="nsew")
        self._render_mes_completo(mes)

    def voltar_para_lista(self):
        self.mostrar_lista()

    def novo_fechamento(self):
        self._editing_original_key = None
        self.form_title_lbl.configure(text="Novo fechamento de setor")
        self._travar_seletor(False)
        self.empresa_menu.configure(values=self._nomes_empresas())
        self.setor_menu.configure(values=self._nomes_estabelecimentos())
        if self._nomes_empresas():
            self.empresa_var.set(self._nomes_empresas()[0])
        if self._nomes_estabelecimentos():
            self.setor_var.set(self._nomes_estabelecimentos()[0])
        self.mes_entry.set_value("")
        for w in self.result_wrap.winfo_children():
            w.destroy()
        self.mostrar_formulario()

    # ---------------- Lista agrupada por mês ----------------
    def refresh_lista(self):
        for w in self.saved_list_wrap.winfo_children():
            w.destroy()

        if not self.app.fechamentos:
            ctk.CTkLabel(self.saved_list_wrap, text="Nenhum fechamento salvo ainda.",
                         text_color=INK_SOFT, font=FONT_BODY).pack(pady=20)
            return

        meses = sorted(self.app.fechamentos.keys(), key=_mes_ordenacao, reverse=True)
        for mes in meses:
            setores = self.app.fechamentos[mes]
            mes_card = Card(self.saved_list_wrap)
            mes_card.pack(fill="x", pady=6)
            mes_card.grid_columnconfigure(0, weight=1)

            head = ctk.CTkFrame(mes_card, fg_color="transparent")
            head.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 6))
            head.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(head, text=mes, font=("Segoe UI Semibold", 15), text_color=INK).grid(
                row=0, column=0, sticky="w")
            ctk.CTkButton(head, text="Ver folha completa do mês", fg_color=TEAL, hover_color=TEAL_DARK,
                          height=28, command=lambda m=mes: self.mostrar_mes(m)).grid(row=0, column=1, sticky="e")

            self._render_setores_do_mes(mes_card, mes, setores)

    def _render_setores_do_mes(self, mes_card, mes, setores):
        wrap = ctk.CTkFrame(mes_card, fg_color="transparent")
        wrap.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 14))
        wrap.grid_columnconfigure(0, weight=1)

        for i, ((empresa, estabelecimento), registro) in enumerate(setores.items()):
            res_setor = calcular_fechamento_setor(self.app.funcionarios, self.app.metas_equipe,
                                                   empresa, estabelecimento, registro["vendas"])
            row = ctk.CTkFrame(wrap, fg_color="#FEFEFD", corner_radius=8, border_width=1, border_color=LINE)
            row.grid(row=i, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(0, weight=1)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.grid(row=0, column=0, sticky="w", padx=14, pady=8)
            ctk.CTkLabel(info, text=f"{empresa} · {estabelecimento}", font=("Segoe UI Semibold", 13),
                         text_color=INK).pack(anchor="w")
            nivel_txt = f"Nível {res_setor['nivel']}" if res_setor["tem_metas_configuradas"] else "sem meta configurada"
            ctk.CTkLabel(info, text=f"Líquido {fmt_moeda(res_setor['total_liquido'])}  ·  {nivel_txt}  ·  "
                                     f"bônus {fmt_moeda(res_setor['bonificacao'])}",
                         font=FONT_SMALL, text_color=INK_SOFT).pack(anchor="w")

            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.grid(row=0, column=1, sticky="e", padx=14)
            ctk.CTkButton(actions, text="Editar", width=64, height=26, fg_color="transparent",
                          border_width=1, border_color=LINE, text_color=INK_SOFT,
                          command=lambda m=mes, e=empresa, s=estabelecimento: self.editar_setor(m, e, s)).pack(side="left", padx=4)
            ctk.CTkButton(actions, text="Excluir", width=72, height=26, fg_color="transparent",
                          border_width=1, border_color="#E9C9C6", text_color=RED,
                          command=lambda m=mes, e=empresa, s=estabelecimento: self.excluir_setor(m, e, s)).pack(side="left")

    def editar_setor(self, mes, empresa, estabelecimento):
        registro = self.app.fechamentos.get(mes, {}).get((empresa, estabelecimento))
        if not registro:
            return
        self._editing_original_key = (mes, empresa, estabelecimento)
        self.form_title_lbl.configure(text=f"Editando: {mes} — {empresa} · {estabelecimento}")
        self.empresa_menu.configure(values=self._nomes_empresas())
        self.setor_menu.configure(values=self._nomes_estabelecimentos())
        self.empresa_var.set(empresa)
        self.setor_var.set(estabelecimento)
        self.mes_entry.set_value(mes)
        self._travar_seletor(True)
        self.mostrar_formulario()
        self._render_result(mes, empresa, estabelecimento, dict(registro["vendas"]))

    def excluir_setor(self, mes, empresa, estabelecimento):
        if messagebox.askyesno("Painel de Comissões", f"Excluir o fechamento de {empresa} · {estabelecimento} em {mes}?"):
            self.app.db.excluir_fechamento(mes, empresa, estabelecimento)
            self.app.fechamentos = self.app.db.listar_fechamentos()
            self.refresh_lista()

    # ---------------- Cálculo / preenchimento de um setor ----------------
    def calcular(self):
        empresa = self.empresa_var.get()
        estabelecimento = self.setor_var.get()
        mes = self.mes_entry.get_value().strip()
        if not mes_valido(mes):
            messagebox.showwarning("Painel de Comissões", "Informe o mês no formato MM/AAAA (ex: 08/2026).")
            return
        registro = self.app.fechamentos.get(mes, {}).get((empresa, estabelecimento))
        vendas_map = {fid: dict(v) for fid, v in registro["vendas"].items()} if registro else {}
        self._render_result(mes, empresa, estabelecimento, vendas_map)

    def _render_result(self, mes, empresa, estabelecimento, vendas_map):
        for w in self.result_wrap.winfo_children():
            w.destroy()

        # Vendedores do setor sempre entram no cálculo (mesmo com valor zerado).
        for f in self.app.funcionarios:
            if f["metas"] and f["empresa"] == empresa and f["estabelecimento"] == estabelecimento and f["id"] not in vendas_map:
                vendas_map[f["id"]] = {"vendido": 0, "devolucoes": 0}

        res = calcular_fechamento_setor(self.app.funcionarios, self.app.metas_equipe, empresa, estabelecimento, vendas_map)

        stats = ctk.CTkFrame(self.result_wrap, fg_color="transparent")
        stats.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        for i in range(5):
            stats.grid_columnconfigure(i, weight=1)
        StatBox(stats, "Vendido", fmt_moeda(res["total_vendido"])).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        StatBox(stats, "Devoluções", fmt_moeda(res["total_devolucoes"])).grid(row=0, column=1, sticky="ew", padx=8)
        StatBox(stats, "Líquido", fmt_moeda(res["total_liquido"]), accent=TEAL_DARK).grid(row=0, column=2, sticky="ew", padx=8)
        nivel_txt = (f"Nível {res['nivel']}" if res["nivel"] else "—") if res["tem_metas_configuradas"] else "sem meta"
        StatBox(stats, "Nível atingido", nivel_txt, accent=TEAL_DARK).grid(row=0, column=3, sticky="ew", padx=8)
        StatBox(stats, "Bônus por pessoa", fmt_moeda(res["bonificacao"]), accent=AMBER).grid(row=0, column=4, sticky="ew", padx=(8, 0))

        tbl_card = Card(self.result_wrap)
        tbl_card.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        tbl_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tbl_card, text="Vendedores deste setor", font=FONT_H2, text_color=INK, anchor="w").grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 10))

        headers = ["Funcionário", "Valor vendido", "Valor devoluções", "Valor líquido", ""]
        tbl = ctk.CTkFrame(tbl_card, fg_color="transparent")
        tbl.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        for c, h in enumerate(headers):
            tbl.grid_columnconfigure(c, weight=1)
            ctk.CTkLabel(tbl, text=h.upper(), font=FONT_SMALL, text_color=INK_SOFT).grid(
                row=0, column=c, sticky="w", pady=(0, 6), padx=(0, 8))

        self._venda_entries = {}
        if not res["linhas"]:
            ctk.CTkLabel(tbl, text="Nenhum vendedor neste setor ainda - adicione um abaixo.",
                         text_color=INK_SOFT).grid(row=1, column=0, columnspan=5, sticky="w")

        for r, l in enumerate(res["linhas"], start=1):
            f = l["funcionario"]
            nome_txt = f["nome"] + ("  (convidado)" if l["convidado"] else "")
            ctk.CTkLabel(tbl, text=nome_txt, font=FONT_BODY,
                         text_color=INK_SOFT if l["convidado"] else INK).grid(row=r, column=0, sticky="w", pady=4)

            entry_v = MoneyEntry(tbl, initial_value=l["vendido"], width=105)
            entry_v.grid(row=r, column=1, sticky="w", pady=4, padx=(0, 4))
            entry_d = MoneyEntry(tbl, initial_value=l["devolucoes"], width=105)
            entry_d.grid(row=r, column=2, sticky="w", pady=4, padx=(0, 4))
            for entry in (entry_v, entry_d):
                entry.bind("<FocusOut>", lambda e, m=mes, em=empresa, es=estabelecimento: self._recalcular(m, em, es))
                entry.bind("<Return>", lambda e, m=mes, em=empresa, es=estabelecimento: self._recalcular(m, em, es))
            self._venda_entries[f["id"]] = (entry_v, entry_d)

            ctk.CTkLabel(tbl, text=fmt_moeda(l["liquido"]), font=("Segoe UI Semibold", 12), text_color=INK).grid(
                row=r, column=3, sticky="w", pady=4)
            ctk.CTkButton(tbl, text="✕", width=26, height=26, fg_color="transparent", border_width=1,
                          border_color=LINE, text_color=RED,
                          command=lambda fid=f["id"], m=mes, em=empresa, es=estabelecimento: self._remover_vendedor(fid, m, em, es)).grid(
                row=r, column=4, sticky="w", pady=4)

        # ---------------- Adicionar vendedor (do próprio setor ou convidado) ----------------
        add_row = ctk.CTkFrame(tbl_card, fg_color="transparent")
        add_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 18))
        ja_incluidos = set(self._venda_entries.keys())
        disponiveis = [f for f in self.app.funcionarios if f["id"] not in ja_incluidos]
        if disponiveis:
            self._novo_vendedor_var = tk.StringVar(value=disponiveis[0]["nome"])
            self._novo_vendedor_map = {f["nome"]: f["id"] for f in disponiveis}
            ctk.CTkOptionMenu(add_row, values=list(self._novo_vendedor_map.keys()),
                              variable=self._novo_vendedor_var, width=220).pack(side="left", padx=(0, 8))
            ctk.CTkButton(add_row, text="+ Adicionar vendedor a este fechamento", fg_color="transparent",
                          border_width=1, border_color=LINE, text_color=TEAL_DARK,
                          command=lambda m=mes, em=empresa, es=estabelecimento: self._adicionar_vendedor(m, em, es)).pack(side="left")
        else:
            ctk.CTkLabel(add_row, text="Todos os funcionários já estão neste fechamento.",
                         font=FONT_SMALL, text_color=INK_SOFT).pack(anchor="w")

        btn_row = ctk.CTkFrame(self.result_wrap, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="w", pady=(0, 20))
        ctk.CTkButton(btn_row, text="Salvar fechamento deste setor", fg_color=TEAL, hover_color=TEAL_DARK,
                      command=lambda: self.salvar(mes, empresa, estabelecimento)).pack(side="left")

    def _ler_vendas_atuais(self):
        return {fid: {"vendido": ev.get_value(), "devolucoes": ed.get_value()}
                for fid, (ev, ed) in self._venda_entries.items()}

    def _recalcular(self, mes, empresa, estabelecimento):
        vendas_map = self._ler_vendas_atuais()
        self._render_result(mes, empresa, estabelecimento, vendas_map)

    def _adicionar_vendedor(self, mes, empresa, estabelecimento):
        nome = self._novo_vendedor_var.get()
        funcionario_id = self._novo_vendedor_map.get(nome)
        if funcionario_id is None:
            return
        vendas_map = self._ler_vendas_atuais()
        vendas_map[funcionario_id] = {"vendido": 0, "devolucoes": 0}
        self._render_result(mes, empresa, estabelecimento, vendas_map)

    def _remover_vendedor(self, funcionario_id, mes, empresa, estabelecimento):
        vendas_map = self._ler_vendas_atuais()
        vendas_map.pop(funcionario_id, None)
        self._render_result(mes, empresa, estabelecimento, vendas_map)

    def salvar(self, mes, empresa, estabelecimento):
        vendas_map = self._ler_vendas_atuais()

        if self._editing_original_key and self._editing_original_key != (mes, empresa, estabelecimento):
            mes_antigo, emp_antiga, set_antigo = self._editing_original_key
            self.app.db.excluir_fechamento(mes_antigo, emp_antiga, set_antigo)

        criado_em = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.app.db.salvar_fechamento(mes, empresa, estabelecimento, vendas_map, criado_em)
        self.app.fechamentos = self.app.db.listar_fechamentos()
        self.mostrar_lista()

    # ================= FOLHA COMPLETA DO MÊS =================
    def _render_mes_completo(self, mes):
        for w in self.month_frame.winfo_children():
            w.destroy()

        top_row = ctk.CTkFrame(self.month_frame, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(top_row, text="← Voltar para a lista", fg_color="transparent", border_width=1,
                      border_color=LINE, text_color=INK_SOFT, width=160,
                      command=self.voltar_para_lista).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(self.month_frame, text=f"Folha completa — {mes}", font=FONT_H1, text_color=INK, anchor="w").grid(
            row=1, column=0, sticky="w", pady=(14, 2))
        ctk.CTkLabel(self.month_frame, text="Consolidado de todos os setores preenchidos neste mês.",
                     font=FONT_BODY, text_color=INK_SOFT, anchor="w").grid(row=2, column=0, sticky="w", pady=(0, 18))

        fechamentos_mes = self.app.fechamentos.get(mes, {})
        res = calcular_mes_completo(self.app.funcionarios, self.app.metas_equipe, fechamentos_mes)

        setor_card = Card(self.month_frame)
        setor_card.grid(row=3, column=0, sticky="ew", pady=(0, 16))
        setor_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(setor_card, text="Resumo por loja / setor", font=FONT_H2, text_color=INK, anchor="w").grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 10))
        setor_tbl = ctk.CTkFrame(setor_card, fg_color="transparent")
        setor_tbl.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))
        headers_s = ["Loja", "Setor", "Vendido", "Devoluções", "Líquido", "Nível", "Bônus/pessoa"]
        for c, h in enumerate(headers_s):
            setor_tbl.grid_columnconfigure(c, weight=1)
            ctk.CTkLabel(setor_tbl, text=h.upper(), font=FONT_SMALL, text_color=INK_SOFT).grid(
                row=0, column=c, sticky="w", padx=(0, 10), pady=(0, 6))
        for r, s in enumerate(res["setores"], start=1):
            ctk.CTkLabel(setor_tbl, text=s["empresa"], font=FONT_BODY, text_color=INK).grid(row=r, column=0, sticky="w", pady=3)
            ctk.CTkLabel(setor_tbl, text=s["estabelecimento"], font=FONT_BODY, text_color=INK).grid(row=r, column=1, sticky="w", pady=3)
            ctk.CTkLabel(setor_tbl, text=fmt_moeda(s["total_vendido"]), font=FONT_BODY, text_color=INK).grid(row=r, column=2, sticky="w", pady=3)
            ctk.CTkLabel(setor_tbl, text=fmt_moeda(s["total_devolucoes"]), font=FONT_BODY, text_color=INK).grid(row=r, column=3, sticky="w", pady=3)
            ctk.CTkLabel(setor_tbl, text=fmt_moeda(s["total_liquido"]), font=("Segoe UI Semibold", 12), text_color=TEAL_DARK).grid(row=r, column=4, sticky="w", pady=3)
            if s["tem_metas_configuradas"]:
                nivel_badge(setor_tbl, s["nivel"]).grid(row=r, column=5, sticky="w", pady=3)
                ctk.CTkLabel(setor_tbl, text=fmt_moeda(s["bonificacao"]), font=FONT_BODY, text_color=AMBER).grid(row=r, column=6, sticky="w", pady=3)
            else:
                ctk.CTkLabel(setor_tbl, text="—", text_color=INK_SOFT).grid(row=r, column=5, sticky="w", pady=3)
                ctk.CTkLabel(setor_tbl, text="Sem meta configurada", font=FONT_SMALL, text_color=INK_SOFT).grid(row=r, column=6, sticky="w", pady=3)

        stats2 = ctk.CTkFrame(self.month_frame, fg_color="transparent")
        stats2.grid(row=4, column=0, sticky="ew", pady=(0, 16))
        for i in range(2):
            stats2.grid_columnconfigure(i, weight=1)
        StatBox(stats2, "Total vale alimentação", fmt_moeda(res["total_vale_alimentacao"])).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        StatBox(stats2, "Folha total do mês", fmt_moeda(res["total_folha"])).grid(row=0, column=1, sticky="ew", padx=(8, 0))

        func_card = Card(self.month_frame)
        func_card.grid(row=5, column=0, sticky="ew", pady=(0, 16))
        func_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(func_card, text="Funcionários", font=FONT_H2, text_color=INK, anchor="w").grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 10))
        func_tbl = ctk.CTkFrame(func_card, fg_color="transparent")
        func_tbl.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))
        headers_f = ["Funcionário", "Vendido (mês)", "Devoluções", "Líquido", "Nível", "Bônus ind.",
                     "Comissão", "Vale", "Bônus equipe", "Total"]
        for c, h in enumerate(headers_f):
            func_tbl.grid_columnconfigure(c, weight=1)
            ctk.CTkLabel(func_tbl, text=h.upper(), font=FONT_SMALL, text_color=INK_SOFT).grid(
                row=0, column=c, sticky="w", padx=(0, 8), pady=(0, 6))
        for r, l in enumerate(res["linhas"], start=1):
            f = l["funcionario"]
            ctk.CTkLabel(func_tbl, text=f["nome"], font=FONT_BODY, text_color=INK).grid(row=r, column=0, sticky="w", pady=4)
            tem_valores = l["tem_metas"] or l["tem_venda"]
            ctk.CTkLabel(func_tbl, text=fmt_moeda(l["vendido"]) if tem_valores else "—", font=FONT_BODY, text_color=INK).grid(row=r, column=1, sticky="w", pady=4)
            ctk.CTkLabel(func_tbl, text=fmt_moeda(l["devolucoes"]) if tem_valores else "—", font=FONT_BODY, text_color=INK).grid(row=r, column=2, sticky="w", pady=4)
            ctk.CTkLabel(func_tbl, text=fmt_moeda(l["liquido"]) if tem_valores else "—", font=FONT_BODY, text_color=INK).grid(row=r, column=3, sticky="w", pady=4)
            if l["tem_metas"]:
                nivel_badge(func_tbl, l["nivel"]).grid(row=r, column=4, sticky="w", pady=4)
                ctk.CTkLabel(func_tbl, text=fmt_moeda(l["bonif_individual"]), font=FONT_BODY, text_color=INK).grid(row=r, column=5, sticky="w", pady=4)
                ctk.CTkLabel(func_tbl, text=fmt_moeda(l["comissao"]), font=FONT_BODY, text_color=INK).grid(row=r, column=6, sticky="w", pady=4)
            else:
                for col in (4, 5, 6):
                    ctk.CTkLabel(func_tbl, text="—", font=FONT_BODY, text_color=INK_SOFT).grid(row=r, column=col, sticky="w", pady=4)
            ctk.CTkLabel(func_tbl, text=fmt_moeda(f["vale_alimentacao"]), font=FONT_BODY, text_color=INK).grid(row=r, column=7, sticky="w", pady=4)
            ctk.CTkLabel(func_tbl, text=fmt_moeda(l["bonif_equipe"]), font=FONT_BODY, text_color=INK).grid(row=r, column=8, sticky="w", pady=4)
            ctk.CTkLabel(func_tbl, text=fmt_moeda(l["total"]), font=("Segoe UI Semibold", 13), text_color=INK).grid(row=r, column=9, sticky="w", pady=4)

        btn_row = ctk.CTkFrame(self.month_frame, fg_color="transparent")
        btn_row.grid(row=6, column=0, sticky="w", pady=(0, 20))
        ctk.CTkButton(btn_row, text="Imprimir", fg_color=TEAL, hover_color=TEAL_DARK,
                      command=lambda: self.imprimir_mes(mes, res)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Imprimir Simplificado", fg_color="transparent", border_width=1,
                      border_color=LINE, text_color=INK_SOFT,
                      command=lambda: self.imprimir_simplificado(mes, res)).pack(side="left")

    def imprimir_simplificado(self, mes, res):
        try:
            caminho = gerar_pdf_simplificado(mes, res)
            self._abrir_arquivo(caminho)
        except Exception as e:
            messagebox.showerror("Painel de Comissões", f"Não foi possível gerar o PDF: {e}")

    def imprimir_mes(self, mes, res):
        quer_recibos = messagebox.askyesno("Painel de Comissões", "Deseja imprimir recibos também?")
        try:
            caminho = gerar_pdf_relatorio(mes, res, incluir_recibos=quer_recibos)
            self._abrir_arquivo(caminho)
        except Exception as e:
            messagebox.showerror("Painel de Comissões", f"Não foi possível gerar o PDF: {e}")

    def _abrir_arquivo(self, caminho):
        import os
        try:
            os.startfile(caminho)
        except AttributeError:
            messagebox.showinfo("Painel de Comissões", f"PDF salvo em:\n{caminho}")
        except Exception as e:
            messagebox.showinfo("Painel de Comissões", f"PDF salvo em:\n{caminho}\n\n(não foi possível abrir automaticamente: {e})")