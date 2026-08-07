"""
screens/funcionarios.py
Tela de cadastro e listagem de funcionários.

- As "funções" (cargos) são customizáveis: cada uma diz se possui ou não
  metas individuais + comissão. Ficam em app.funcoes. Um botão "+" ao lado
  do campo Função abre um popup separado para cadastrar novas funções.
- Salário base e vale alimentação usam campo com máscara de dinheiro
  (MoneyEntry): o texto exibido já vem formatado (R$ 1.234,56) mas o
  valor guardado por trás é sempre um número limpo.
- Os níveis de meta individual podem ser adicionados ou removidos
  livremente (não são mais fixos em 3).

Os dados ficam em app.funcionarios (lista em memória, por enquanto -
o próximo passo do projeto é trocar isso por um banco SQLite).
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from widgets import (
    Card, TierRow, MoneyEntry, parse_num, fmt_moeda,
    PAPER, INK, INK_SOFT, LINE, TEAL, TEAL_DARK, RED, AMBER,
    FONT_H1, FONT_H2, FONT_BODY, FONT_SMALL,
)


class FuncionariosScreen(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=PAPER)
        self.app = app
        self.editing_id = None
        self.emp_tier_rows = []
        self._funcao_popup = None

        self.grid_columnconfigure(0, weight=1)
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Funcionários", font=FONT_H1, text_color=INK, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 2))
        ctk.CTkLabel(frame, text="Cadastre a equipe: função, salário base, vale alimentação e,\n"
                                  "para funções com metas, comissão e níveis individuais.",
                     font=FONT_BODY, text_color=INK_SOFT, justify="left", anchor="w").grid(
            row=1, column=0, sticky="w", pady=(0, 18))

        # ---------------- Formulário de funcionário ----------------
        form = Card(frame)
        form.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        form.grid_columnconfigure((0, 1, 2), weight=1)

        self.emp_title_lbl = ctk.CTkLabel(form, text="Novo funcionário", font=FONT_H2, text_color=INK, anchor="w")
        self.emp_title_lbl.grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(14, 4))

        ctk.CTkLabel(form, text="ID", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=1, column=0, sticky="w", padx=20)
        self.emp_id_var = tk.StringVar()
        vcmd = (form.register(lambda s: s == "" or s.isdigit()), "%P")
        ctk.CTkEntry(form, textvariable=self.emp_id_var, validate="key", validatecommand=vcmd).grid(
            row=2, column=0, sticky="ew", padx=(20, 10), pady=(2, 10))

        ctk.CTkLabel(form, text="Nome", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=1, column=1, sticky="w")
        self.emp_nome_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self.emp_nome_var).grid(row=2, column=1, sticky="ew", padx=10, pady=(2, 10))

        ctk.CTkLabel(form, text="Função", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=1, column=2, sticky="w", padx=(0, 20))
        funcao_row = ctk.CTkFrame(form, fg_color="transparent")
        funcao_row.grid(row=2, column=2, sticky="ew", padx=(10, 20), pady=(2, 10))
        funcao_row.grid_columnconfigure(0, weight=1)

        self.emp_funcao_var = tk.StringVar(value="Vendedor")
        self.funcao_menu = ctk.CTkOptionMenu(funcao_row, values=self._nomes_funcoes(), variable=self.emp_funcao_var,
                                              command=lambda _: self._toggle_emp_funcao())
        self.funcao_menu.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(funcao_row, text="+", width=30, height=28, fg_color=TEAL, hover_color=TEAL_DARK,
                      command=self.abrir_popup_funcao).grid(row=0, column=1, padx=(6, 0))

        ctk.CTkLabel(form, text="Salário base", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=3, column=0, sticky="w", padx=20)
        self.emp_salario_entry = MoneyEntry(form)
        self.emp_salario_entry.grid(row=4, column=0, sticky="ew", padx=(20, 10), pady=(2, 10))

        ctk.CTkLabel(form, text="Vale alimentação", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=3, column=1, sticky="w")
        self.emp_va_entry = MoneyEntry(form)
        self.emp_va_entry.grid(row=4, column=1, sticky="ew", padx=10, pady=(2, 10))

        self.emp_comissao_wrap = ctk.CTkFrame(form, fg_color="transparent")
        self.emp_comissao_wrap.grid(row=3, column=2, rowspan=2, sticky="new", padx=(0, 20))
        ctk.CTkLabel(self.emp_comissao_wrap, text="Comissão sobre vendas (%)", font=FONT_SMALL,
                     text_color=INK_SOFT, anchor="w").pack(fill="x", pady=(0, 2))
        self.emp_comissao_var = tk.StringVar()
        ctk.CTkEntry(self.emp_comissao_wrap, textvariable=self.emp_comissao_var).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text="Empresa", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=5, column=0, sticky="w", padx=20)
        empresa_row = ctk.CTkFrame(form, fg_color="transparent")
        empresa_row.grid(row=6, column=0, sticky="ew", padx=(20, 10), pady=(2, 10))
        empresa_row.grid_columnconfigure(0, weight=1)

        self.emp_empresa_var = tk.StringVar(value=(self._nomes_empresas()[0] if self._nomes_empresas() else ""))
        self.empresa_menu = ctk.CTkOptionMenu(empresa_row, values=self._nomes_empresas(), variable=self.emp_empresa_var)
        self.empresa_menu.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(empresa_row, text="+", width=30, height=28, fg_color=TEAL, hover_color=TEAL_DARK,
                      command=self.app.abrir_configuracoes).grid(row=0, column=1, padx=(6, 0))

        ctk.CTkLabel(form, text="Tipo / Estabelecimento", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=5, column=1, sticky="w")
        tipo_row = ctk.CTkFrame(form, fg_color="transparent")
        tipo_row.grid(row=6, column=1, sticky="ew", padx=10, pady=(2, 10))
        tipo_row.grid_columnconfigure(0, weight=1)

        self.emp_estabelecimento_var = tk.StringVar(value=(self._nomes_estabelecimentos()[0] if self._nomes_estabelecimentos() else ""))
        self.estabelecimento_menu = ctk.CTkOptionMenu(tipo_row, values=self._nomes_estabelecimentos(),
                                                       variable=self.emp_estabelecimento_var)
        self.estabelecimento_menu.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(tipo_row, text="+", width=30, height=28, fg_color=TEAL, hover_color=TEAL_DARK,
                      command=self.abrir_popup_estabelecimento).grid(row=0, column=1, padx=(6, 0))

        ctk.CTkLabel(form, text="Opções", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=5, column=2, sticky="w", padx=(0, 20))
        checks_row = ctk.CTkFrame(form, fg_color="transparent")
        checks_row.grid(row=6, column=2, sticky="ew", padx=(10, 20), pady=(2, 10))

        self.emp_bonif_equipe_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(checks_row, text="Recebe bonificação de equipe", variable=self.emp_bonif_equipe_var,
                        font=FONT_SMALL).pack(side="left", padx=(0, 16))

        self.emp_contabil_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(checks_row, text="Enviar Contábil?", variable=self.emp_contabil_var,
                        font=FONT_SMALL).pack(side="left")

        self.emp_tiers_wrap = ctk.CTkFrame(form, fg_color="transparent")
        self.emp_tiers_wrap.grid(row=7, column=0, columnspan=3, sticky="ew", padx=20, pady=(6, 6))
        self.emp_tiers_wrap.grid_columnconfigure(0, weight=1)
        self._render_emp_tiers()

        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.grid(row=8, column=0, columnspan=3, sticky="w", padx=20, pady=(6, 18))
        ctk.CTkButton(btn_row, text="Salvar funcionário", fg_color=TEAL, hover_color=TEAL_DARK,
                      command=self.salvar_funcionario).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Cancelar edição", fg_color="transparent", border_width=1,
                      border_color=LINE, text_color=INK_SOFT,
                      command=self.cancelar_edicao_funcionario).pack(side="left")

        list_card = Card(frame)
        list_card.grid(row=3, column=0, sticky="ew")
        list_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(list_card, text="Equipe cadastrada", font=FONT_H2, text_color=INK, anchor="w").grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 8))
        self.emp_list_wrap = ctk.CTkFrame(list_card, fg_color="transparent")
        self.emp_list_wrap.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.emp_list_wrap.grid_columnconfigure(0, weight=1)

        self._toggle_emp_funcao()
        self.refresh_funcionarios()

    # ---------------- Funções (cargos) ----------------
    def _nomes_funcoes(self):
        return [f["nome"] for f in self.app.funcoes] or ["Outro"]

    def _funcao_tem_metas(self, nome):
        f = next((x for x in self.app.funcoes if x["nome"] == nome), None)
        return bool(f["tem_metas"]) if f else False

    def _modelo_funcao(self, nome):
        f = next((x for x in self.app.funcoes if x["nome"] == nome), None)
        return f.get("modelo_comissao", "padrao") if f else "padrao"

    MODELOS_COMISSAO = {
        "Padrão (metas individuais + comissão própria + bônus fixo de equipe)": "padrao",
        "Sem comissão nem metas": "nenhum",
        "Gerência (comissão sobre a equipe + bônus fixo se bater a meta)": "gerencia",
        "Percentual da equipe (bônus % sobre o total da equipe)": "percentual_equipe",
        "Auxiliar condicional (% sobre a própria produção, conforme metas)": "auxiliar_condicional",
    }
    MODELOS_LABEL = {v: k for k, v in MODELOS_COMISSAO.items()}

    def abrir_popup_funcao(self):
        if self._funcao_popup is not None and self._funcao_popup.winfo_exists():
            self._funcao_popup.focus()
            return

        popup = ctk.CTkToplevel(self)
        popup.title("Função")
        popup.geometry("560x680")
        popup.minsize(480, 420)
        popup.resizable(True, True)
        popup.transient(self.winfo_toplevel())
        self._funcao_popup = popup

        conteudo = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        conteudo.pack(fill="both", expand=True)

        ctk.CTkLabel(conteudo, text="Funções cadastradas", font=FONT_H2, text_color=INK).pack(
            anchor="w", padx=20, pady=(20, 8))
        ctk.CTkLabel(conteudo, text="Clique numa função pra editar o modelo de comissão dela.",
                     font=FONT_SMALL, text_color=INK_SOFT, anchor="w").pack(fill="x", padx=20, pady=(0, 8))

        lista_wrap = ctk.CTkScrollableFrame(conteudo, fg_color="transparent", height=140)
        lista_wrap.pack(fill="x", padx=20)

        nome_var = tk.StringVar()
        modelo_var = tk.StringVar(value=list(self.MODELOS_COMISSAO.keys())[0])
        comissao_equipe_var = tk.StringVar(value="0")
        percentual_bonif_var = tk.StringVar(value="0")
        pct_ambos_var = tk.StringVar(value="0")
        pct_individual_var = tk.StringVar(value="0")
        pct_geral_var = tk.StringVar(value="0")

        def render_lista():
            for w in lista_wrap.winfo_children():
                w.destroy()
            for f in self.app.funcoes:
                modelo = f.get("modelo_comissao", "padrao")
                personalizado = modelo not in ("padrao", "nenhum")
                cor_bg = "#FBF1DC" if personalizado else ("#E4F6F3" if f["tem_metas"] else "#EEEEE9")
                cor_fg = AMBER if personalizado else (TEAL_DARK if f["tem_metas"] else INK_SOFT)
                texto = f"{f['nome']}  ·  {self.MODELOS_LABEL.get(modelo, modelo).split(' (')[0]}"

                linha = ctk.CTkFrame(lista_wrap, fg_color=cor_bg, corner_radius=6)
                linha.pack(fill="x", pady=2)
                linha.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(linha, text=texto, font=FONT_SMALL, text_color=cor_fg, anchor="w").grid(
                    row=0, column=0, sticky="w", padx=8, pady=6)
                ctk.CTkButton(linha, text="Editar", width=50, height=22, fg_color="transparent",
                              border_width=1, border_color=LINE, text_color=INK_SOFT, font=FONT_SMALL,
                              command=lambda ff=f: carregar(ff)).grid(row=0, column=1, padx=(0, 4), pady=4)
                ctk.CTkButton(linha, text="Excluir", width=54, height=22, fg_color="transparent",
                              border_width=1, border_color="#E9C9C6", text_color=RED, font=FONT_SMALL,
                              command=lambda ff=f: excluir(ff)).grid(row=0, column=2, padx=(0, 6), pady=4)

        def excluir(f):
            em_uso = sum(1 for func in self.app.funcionarios if func.get("funcao") == f["nome"])
            aviso = f"\n\n{em_uso} funcionário(s) usam essa função e ficarão sem função válida." if em_uso else ""
            if not messagebox.askyesno("Painel de Comissões",
                                        f"Excluir a função \"{f['nome']}\"?{aviso}", parent=popup):
                return
            self.app.db.excluir_funcao(f["nome"])
            self.app.funcoes = self.app.db.listar_funcoes()
            render_lista()
            self.funcao_menu.configure(values=self._nomes_funcoes())
            self._toggle_emp_funcao()

        def carregar(f):
            titulo_form.configure(text=f"Editando: {f['nome']}")
            nome_var.set(f["nome"])
            modelo_var.set(self.MODELOS_LABEL.get(f.get("modelo_comissao", "padrao")))
            comissao_equipe_var.set(str(f.get("comissao_equipe_percent", 0)))
            bonif_fixa_entry.set_value(f.get("bonificacao_fixa", 0))
            percentual_bonif_var.set(str(f.get("percentual_bonif_equipe", 0)))
            pct_ambos_var.set(str(f.get("pct_individual_e_geral", 0)))
            pct_individual_var.set(str(f.get("pct_somente_individual", 0)))
            pct_geral_var.set(str(f.get("pct_somente_geral", 0)))
            render_campos()

        render_lista()

        titulo_form = ctk.CTkLabel(conteudo, text="Nova função", font=FONT_H2, text_color=INK, anchor="w")
        titulo_form.pack(fill="x", padx=20, pady=(14, 4))

        ctk.CTkLabel(conteudo, text="Nome da função", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").pack(
            fill="x", padx=20, pady=(2, 2))
        ctk.CTkEntry(conteudo, textvariable=nome_var, placeholder_text="Ex: Supervisor").pack(fill="x", padx=20)

        ctk.CTkLabel(conteudo, text="Modelo de comissão", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").pack(
            fill="x", padx=20, pady=(12, 2))
        ctk.CTkOptionMenu(conteudo, values=list(self.MODELOS_COMISSAO.keys()), variable=modelo_var,
                          command=lambda _: render_campos()).pack(fill="x", padx=20)

        campos_wrap = ctk.CTkFrame(conteudo, fg_color="transparent")
        campos_wrap.pack(fill="x", padx=20, pady=(10, 0))

        bonif_fixa_entry = MoneyEntry(conteudo)  # criado uma vez, reposicionado dentro de campos_wrap quando necessário

        def campo(parent, texto, var):
            ctk.CTkLabel(parent, text=texto, font=FONT_SMALL, text_color=INK_SOFT, anchor="w").pack(
                fill="x", pady=(6, 2))
            ctk.CTkEntry(parent, textvariable=var).pack(fill="x")

        def render_campos():
            for w in campos_wrap.winfo_children():
                w.pack_forget()
            bonif_fixa_entry.pack_forget()
            modelo = self.MODELOS_COMISSAO.get(modelo_var.get(), "padrao")

            if modelo == "gerencia":
                campo(campos_wrap, "Comissão sobre o total da equipe (%)", comissao_equipe_var)
                ctk.CTkLabel(campos_wrap, text="Bonificação fixa se a meta geral for atingida (R$)",
                             font=FONT_SMALL, text_color=INK_SOFT, anchor="w").pack(fill="x", pady=(6, 2))
                bonif_fixa_entry.pack(in_=campos_wrap, fill="x")
            elif modelo == "percentual_equipe":
                campo(campos_wrap, "Percentual sobre o total da equipe, se bater a meta geral (%)", percentual_bonif_var)
            elif modelo == "auxiliar_condicional":
                ctk.CTkLabel(campos_wrap, text="Percentuais sobre a própria produção, conforme o que for batido:",
                             font=FONT_SMALL, text_color=INK_SOFT, anchor="w", wraplength=400).pack(fill="x", pady=(4, 2))
                campo(campos_wrap, "% se bater a meta individual E a meta geral", pct_ambos_var)
                campo(campos_wrap, "% se bater só a meta individual", pct_individual_var)
                campo(campos_wrap, "% se bater só a meta geral", pct_geral_var)
            else:
                ctk.CTkLabel(campos_wrap, text="Esse modelo não precisa de campos extras.",
                             font=FONT_SMALL, text_color=INK_SOFT, anchor="w").pack(fill="x", pady=(4, 2))

        render_campos()

        def limpar_formulario():
            titulo_form.configure(text="Nova função")
            nome_var.set("")
            modelo_var.set(list(self.MODELOS_COMISSAO.keys())[0])
            comissao_equipe_var.set("0")
            bonif_fixa_entry.set_value(0)
            percentual_bonif_var.set("0")
            pct_ambos_var.set("0")
            pct_individual_var.set("0")
            pct_geral_var.set("0")
            render_campos()

        def salvar():
            nome = nome_var.get().strip()
            if not nome:
                messagebox.showwarning("Painel de Comissões", "Informe o nome da função.", parent=popup)
                return
            modelo = self.MODELOS_COMISSAO.get(modelo_var.get(), "padrao")
            tem_metas = modelo in ("padrao", "auxiliar_condicional")
            self.app.db.salvar_funcao(
                nome, tem_metas, modelo_comissao=modelo,
                comissao_equipe_percent=parse_num(comissao_equipe_var.get()),
                bonificacao_fixa=bonif_fixa_entry.get_value(),
                percentual_bonif_equipe=parse_num(percentual_bonif_var.get()),
                pct_individual_e_geral=parse_num(pct_ambos_var.get()),
                pct_somente_individual=parse_num(pct_individual_var.get()),
                pct_somente_geral=parse_num(pct_geral_var.get()),
            )
            self.app.funcoes = self.app.db.listar_funcoes()
            limpar_formulario()
            render_lista()
            self.funcao_menu.configure(values=self._nomes_funcoes())
            self._toggle_emp_funcao()

        ctk.CTkButton(conteudo, text="Salvar função", fg_color=TEAL, hover_color=TEAL_DARK,
                      command=salvar).pack(fill="x", padx=20, pady=(16, 4))
        ctk.CTkButton(conteudo, text="Cancelar edição", fg_color="transparent", border_width=1,
                      border_color=LINE, text_color=INK_SOFT,
                      command=limpar_formulario).pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkButton(conteudo, text="Fechar", fg_color="transparent", border_width=1,
                      border_color=LINE, text_color=INK_SOFT,
                      command=popup.destroy).pack(fill="x", padx=20, pady=(0, 20))

        popup.after(50, lambda: popup.grab_set())

    # ---------------- Empresas ----------------
    def _nomes_empresas(self):
        return [e["nome"] for e in self.app.empresas] or ["Matriz"]

    def atualizar_lista_empresas(self):
        """Chamado pelo main.py quando a lista de empresas muda no popup de Configurações."""
        self.empresa_menu.configure(values=self._nomes_empresas())
        if not self.emp_empresa_var.get() and self._nomes_empresas():
            self.emp_empresa_var.set(self._nomes_empresas()[0])

    # ---------------- Tipo / Estabelecimento ----------------
    def _nomes_estabelecimentos(self):
        return [e["nome"] for e in self.app.estabelecimentos] or ["Geral"]

    def abrir_popup_estabelecimento(self):
        if getattr(self, "_estabelecimento_popup", None) is not None and self._estabelecimento_popup.winfo_exists():
            self._estabelecimento_popup.focus()
            return

        popup = ctk.CTkToplevel(self)
        popup.title("Tipo / estabelecimento")
        popup.geometry("460x560")
        popup.minsize(400, 380)
        popup.resizable(True, True)
        popup.transient(self.winfo_toplevel())
        self._estabelecimento_popup = popup

        conteudo = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        conteudo.pack(fill="both", expand=True)

        ctk.CTkLabel(conteudo, text="Tipos cadastrados", font=FONT_H2, text_color=INK).pack(
            anchor="w", padx=20, pady=(20, 8))
        ctk.CTkLabel(conteudo, text="Ex: Oficina, Autopeças. Clique num tipo pra editar o modo de cálculo dele.",
                     font=FONT_SMALL, text_color=INK_SOFT, anchor="w", justify="left").pack(
            fill="x", padx=20, pady=(0, 8))

        lista_wrap = ctk.CTkScrollableFrame(conteudo, fg_color="transparent", height=140)
        lista_wrap.pack(fill="x", padx=20)

        nome_var = tk.StringVar()
        modo_var = tk.StringVar(value="Padrão")

        def render_lista():
            for w in lista_wrap.winfo_children():
                w.destroy()
            for e in self.app.estabelecimentos:
                personalizado = e.get("modo_calculo") == "personalizado"
                cor_bg = "#FBF1DC" if personalizado else "#E4F6F3"
                cor_fg = AMBER if personalizado else TEAL_DARK
                texto = f"{e['nome']}  ·  {'Personalizado' if personalizado else 'Padrão'}"
                chip = ctk.CTkLabel(lista_wrap, text=texto, font=FONT_SMALL, text_color=cor_fg,
                                     fg_color=cor_bg, corner_radius=6, anchor="w", cursor="hand2")
                chip.pack(fill="x", pady=2, ipady=3, ipadx=6)
                chip.bind("<Button-1>", lambda ev, est=e: carregar(est))

        def carregar(est):
            nome_var.set(est["nome"])
            modo_var.set("Personalizado" if est.get("modo_calculo") == "personalizado" else "Padrão")

        render_lista()

        ctk.CTkLabel(conteudo, text="Nome do tipo", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").pack(
            fill="x", padx=20, pady=(16, 2))
        ctk.CTkEntry(conteudo, textvariable=nome_var, placeholder_text="Ex: Estoque").pack(fill="x", padx=20)

        ctk.CTkLabel(conteudo, text="Modo de cálculo", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").pack(
            fill="x", padx=20, pady=(14, 4))
        modo_row = ctk.CTkFrame(conteudo, fg_color="transparent")
        modo_row.pack(fill="x", padx=20)
        ctk.CTkRadioButton(modo_row, text="Padrão (metas individuais + comissão + bônus fixo de equipe)",
                           variable=modo_var, value="Padrão").pack(anchor="w", pady=(0, 4))
        ctk.CTkRadioButton(modo_row, text="Personalizado (usa o modelo de comissão configurado em cada função)",
                           variable=modo_var, value="Personalizado").pack(anchor="w")

        def salvar():
            nome = nome_var.get().strip()
            if not nome:
                messagebox.showwarning("Painel de Comissões", "Informe o nome do tipo.", parent=popup)
                return
            modo = "personalizado" if modo_var.get() == "Personalizado" else "padrao"
            self.app.db.salvar_estabelecimento(nome, modo)
            self.app.estabelecimentos = self.app.db.listar_estabelecimentos()
            nome_var.set("")
            modo_var.set("Padrão")
            render_lista()
            self.estabelecimento_menu.configure(values=self._nomes_estabelecimentos())
            tela_metas = self.app.sections.get("metas")
            if tela_metas is not None and hasattr(tela_metas, "atualizar_listas"):
                tela_metas.atualizar_listas()

        ctk.CTkButton(conteudo, text="Salvar tipo", fg_color=TEAL, hover_color=TEAL_DARK,
                      command=salvar).pack(fill="x", padx=20, pady=(14, 8))
        ctk.CTkButton(conteudo, text="Fechar", fg_color="transparent", border_width=1,
                      border_color=LINE, text_color=INK_SOFT,
                      command=popup.destroy).pack(fill="x", padx=20, pady=(0, 20))

        popup.after(50, lambda: popup.grab_set())
    def _render_emp_tiers(self, metas=None):
        for w in self.emp_tiers_wrap.winfo_children():
            w.destroy()
        self.emp_tier_rows = []
        metas = metas if metas is not None else [{"valor_meta": 0, "bonificacao": 0} for _ in range(3)]
        if not metas:
            metas = [{"valor_meta": 0, "bonificacao": 0}]

        ctk.CTkLabel(self.emp_tiers_wrap, text="Metas individuais e bonificação por nível",
                     font=FONT_SMALL, text_color=INK_SOFT, anchor="w").pack(fill="x", pady=(4, 6))
        for i, m in enumerate(metas):
            row = TierRow(self.emp_tiers_wrap, i + 1, m["valor_meta"], m["bonificacao"],
                          on_remove=lambda idx=i: self._remove_tier(idx))
            row.pack(fill="x")
            self.emp_tier_rows.append(row)

        ctk.CTkButton(self.emp_tiers_wrap, text="+ Adicionar nível", fg_color="transparent",
                      border_width=1, border_color=LINE, text_color=TEAL_DARK, height=28,
                      command=self._add_tier).pack(anchor="w", pady=(2, 8))

    def _read_tier_data(self):
        return [row.get() for row in self.emp_tier_rows]

    def _add_tier(self):
        dados = self._read_tier_data()
        dados.append({"valor_meta": 0, "bonificacao": 0})
        self._render_emp_tiers(dados)

    def _remove_tier(self, index):
        dados = self._read_tier_data()
        if len(dados) <= 1:
            messagebox.showinfo("Painel de Comissões", "É preciso manter pelo menos um nível de meta.")
            return
        dados.pop(index)
        self._render_emp_tiers(dados)

    def _toggle_emp_funcao(self):
        if self._funcao_tem_metas(self.emp_funcao_var.get()):
            self.emp_tiers_wrap.grid()
        else:
            self.emp_tiers_wrap.grid_remove()

        # A comissão por percentual individual só faz sentido no modelo
        # "padrão" - os outros modelos (gerência, % da equipe, auxiliar
        # condicional) calculam a comissão de outro jeito, configurado
        # na função, não aqui no funcionário.
        if self._modelo_funcao(self.emp_funcao_var.get()) == "padrao":
            self.emp_comissao_wrap.grid()
        else:
            self.emp_comissao_wrap.grid_remove()

    # ---------------- CRUD ----------------
    def cancelar_edicao_funcionario(self):
        self.editing_id = None
        self.emp_title_lbl.configure(text="Novo funcionário")
        self.emp_nome_var.set("")
        if self._nomes_funcoes():
            self.emp_funcao_var.set(self._nomes_funcoes()[0])
        self.emp_salario_entry.set_value(0)
        self.emp_va_entry.set_value(0)
        self.emp_comissao_var.set("")
        self.emp_id_var.set("")
        if self._nomes_empresas():
            self.emp_empresa_var.set(self._nomes_empresas()[0])
        if self._nomes_estabelecimentos():
            self.emp_estabelecimento_var.set(self._nomes_estabelecimentos()[0])
        self.emp_bonif_equipe_var.set(True)
        self.emp_contabil_var.set(True)
        self._render_emp_tiers()
        self._toggle_emp_funcao()

    def salvar_funcionario(self):
        nome = self.emp_nome_var.get().strip()
        if not nome:
            messagebox.showwarning("Painel de Comissões", "Informe o nome do funcionário.")
            return
        try:
            funcao = self.emp_funcao_var.get()
            tem_metas = self._funcao_tem_metas(funcao)
            modelo = self._modelo_funcao(funcao)
            dados = {
                "codigo": self.emp_id_var.get().strip(),
                "nome": nome,
                "funcao": funcao,
                "empresa": self.emp_empresa_var.get(),
                "estabelecimento": self.emp_estabelecimento_var.get(),
                "salario_base": self.emp_salario_entry.get_value(),
                "vale_alimentacao": self.emp_va_entry.get_value(),
                "comissao_percent": parse_num(self.emp_comissao_var.get()) if modelo == "padrao" else 0,
                "metas": [{"nivel": i + 1, **row.get()} for i, row in enumerate(self.emp_tier_rows)] if tem_metas else [],
                "recebe_bonif_equipe": self.emp_bonif_equipe_var.get(),
                "enviar_contabil": self.emp_contabil_var.get(),
            }
            self.app.db.salvar_funcionario(dados, self.editing_id)
            self.app.funcionarios = self.app.db.listar_funcionarios()
        except Exception as e:
            messagebox.showerror("Painel de Comissões", f"Não foi possível salvar: {e}")
            return

        self.cancelar_edicao_funcionario()
        self.refresh_funcionarios()

    def editar_funcionario(self, funcionario_id):
        f = next((x for x in self.app.funcionarios if x["id"] == funcionario_id), None)
        if not f:
            return
        self.editing_id = funcionario_id
        self.emp_title_lbl.configure(text=f"Editando: {f['nome']}")
        self.emp_nome_var.set(f["nome"])
        self.emp_funcao_var.set(f["funcao"])
        self.emp_salario_entry.set_value(f["salario_base"])
        self.emp_va_entry.set_value(f["vale_alimentacao"])
        self.emp_comissao_var.set(str(f["comissao_percent"]))
        self.emp_id_var.set(f.get("codigo", ""))
        self.emp_empresa_var.set(f.get("empresa", self._nomes_empresas()[0] if self._nomes_empresas() else ""))
        self.emp_estabelecimento_var.set(f.get("estabelecimento", self._nomes_estabelecimentos()[0] if self._nomes_estabelecimentos() else ""))
        self.emp_bonif_equipe_var.set(f.get("recebe_bonif_equipe", True))
        self.emp_contabil_var.set(f.get("enviar_contabil", True))
        self._render_emp_tiers([{"valor_meta": m["valor_meta"], "bonificacao": m["bonificacao"]} for m in f["metas"]] if f["metas"] else None)
        self._toggle_emp_funcao()

    def excluir_funcionario(self, funcionario_id, nome):
        if messagebox.askyesno("Painel de Comissões", f"Remover {nome} do cadastro?"):
            self.app.db.excluir_funcionario(funcionario_id)
            self.app.funcionarios = self.app.db.listar_funcionarios()
            self.refresh_funcionarios()

    # ---------------- Lista ----------------
    def refresh_funcionarios(self):
        for w in self.emp_list_wrap.winfo_children():
            w.destroy()
        if not self.app.funcionarios:
            ctk.CTkLabel(self.emp_list_wrap, text="Nenhum funcionário cadastrado ainda.",
                         text_color=INK_SOFT, font=FONT_BODY).pack(pady=20)
            return
        for f in sorted(self.app.funcionarios, key=lambda x: 0 if x["metas"] else 1):
            row = ctk.CTkFrame(self.emp_list_wrap, fg_color="#FEFEFD", corner_radius=8,
                                border_width=1, border_color=LINE)
            row.pack(fill="x", pady=5)
            row.grid_columnconfigure(0, weight=1)

            top = ctk.CTkFrame(row, fg_color="transparent")
            top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
            top.grid_columnconfigure(0, weight=1)

            info = ctk.CTkFrame(top, fg_color="transparent")
            info.grid(row=0, column=0, sticky="w")
            nome_linha = f["nome"] + (f"   ·  ID {f['codigo']}" if f.get("codigo") else "")
            ctk.CTkLabel(info, text=nome_linha, font=("Segoe UI Semibold", 14), text_color=INK).pack(anchor="w")
            detalhe = (f"{f['funcao']}  ·  {f.get('empresa','—')}  ·  {f.get('estabelecimento','—')}  ·  "
                       f"Salário base {fmt_moeda(f['salario_base'])}  ·  VA {fmt_moeda(f['vale_alimentacao'])}")
            if f["metas"]:
                detalhe += f"  ·  Comissão {f['comissao_percent']}%"
            if not f.get("recebe_bonif_equipe", True):
                detalhe += "  ·  Não recebe bônus de equipe"
            if not f.get("enviar_contabil", True):
                detalhe += "  ·  Não enviado ao contábil"
            ctk.CTkLabel(info, text=detalhe, font=FONT_SMALL, text_color=INK_SOFT).pack(anchor="w")

            actions = ctk.CTkFrame(top, fg_color="transparent")
            actions.grid(row=0, column=1, sticky="e")
            ctk.CTkButton(actions, text="Editar", width=64, height=26, fg_color="transparent",
                          border_width=1, border_color=LINE, text_color=INK_SOFT,
                          command=lambda fid=f["id"]: self.editar_funcionario(fid)).pack(side="left", padx=4)
            ctk.CTkButton(actions, text="Remover", width=72, height=26, fg_color="transparent",
                          border_width=1, border_color="#E9C9C6", text_color=RED,
                          command=lambda fid=f["id"], n=f["nome"]: self.excluir_funcionario(fid, n)).pack(side="left")

            if f["metas"]:
                chips = ctk.CTkFrame(row, fg_color="transparent")
                chips.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
                texto = "   ".join(
                    f"Nível {m['nivel']}: {fmt_moeda(m['valor_meta'])} → bônus {fmt_moeda(m['bonificacao'])}"
                    for m in f["metas"]
                )
                ctk.CTkLabel(chips, text=texto, font=FONT_SMALL, text_color=INK_SOFT).pack(anchor="w")