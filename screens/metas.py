"""
screens/metas.py
Tela de Metas & Bonificações de Equipe.

As metas agora são cadastradas por LOJA (empresa) + SETOR
(estabelecimento) - escolha os dois no topo, preencha os níveis
daquela combinação e salve. Cada combinação guarda sua própria
configuração em app.metas_equipe.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from widgets import (
    Card, TierRow,
    PAPER, INK, INK_SOFT, LINE, TEAL, TEAL_DARK, RED,
    FONT_H1, FONT_H2, FONT_BODY, FONT_SMALL,
)


class MetasEquipeScreen(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=PAPER)
        self.app = app
        self.tier_rows = []

        self.grid_columnconfigure(0, weight=1)
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Metas & Bonificações de Equipe", font=FONT_H1,
                     text_color=INK, anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 2))
        ctk.CTkLabel(frame, text="Escolha a loja e o setor para configurar (ou consultar) os níveis de\n"
                                  "meta coletiva daquele grupo específico.",
                     font=FONT_BODY, text_color=INK_SOFT, justify="left", anchor="w").grid(
            row=1, column=0, sticky="w", pady=(0, 18))

        card = Card(frame)
        card.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        card.grid_columnconfigure(0, weight=1)

        seletor = ctk.CTkFrame(card, fg_color="transparent")
        seletor.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        seletor.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(seletor, text="Loja (empresa)", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=0, column=0, sticky="w")
        self.empresa_var = tk.StringVar()
        self.empresa_menu = ctk.CTkOptionMenu(seletor, values=self._nomes_empresas(), variable=self.empresa_var,
                                               command=lambda _: self._carregar_grupo())
        self.empresa_menu.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(2, 0))

        ctk.CTkLabel(seletor, text="Setor (estabelecimento)", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").grid(
            row=0, column=1, sticky="w")
        self.setor_var = tk.StringVar()
        self.setor_menu = ctk.CTkOptionMenu(seletor, values=self._nomes_estabelecimentos(), variable=self.setor_var,
                                             command=lambda _: self._carregar_grupo())
        self.setor_menu.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(2, 0))

        ctk.CTkLabel(card, text="Níveis desse grupo", font=FONT_H2, text_color=INK, anchor="w").grid(
            row=1, column=0, sticky="w", padx=20, pady=(18, 10))

        self.tiers_wrap = ctk.CTkFrame(card, fg_color="transparent")
        self.tiers_wrap.grid(row=2, column=0, sticky="ew", padx=20)
        self.tiers_wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(card, text="Salvar metas deste grupo", fg_color=TEAL, hover_color=TEAL_DARK,
                      command=self.salvar).grid(row=3, column=0, sticky="w", padx=20, pady=(10, 18))

        # ---------------- Resumo dos grupos já configurados ----------------
        resumo_card = Card(frame)
        resumo_card.grid(row=3, column=0, sticky="ew", pady=(0, 18))
        resumo_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(resumo_card, text="Grupos configurados", font=FONT_H2, text_color=INK, anchor="w").grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 8))
        self.resumo_wrap = ctk.CTkFrame(resumo_card, fg_color="transparent")
        self.resumo_wrap.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.resumo_wrap.grid_columnconfigure(0, weight=1)

        info_card = Card(frame)
        info_card.grid(row=4, column=0, sticky="ew")
        ctk.CTkLabel(info_card, text="Como funciona o cálculo", font=FONT_H2, text_color=INK, anchor="w").pack(
            fill="x", padx=20, pady=(16, 6))
        ctk.CTkLabel(info_card,
                     text="Cada loja + setor tem sua própria meta coletiva. O total vendido é somado\n"
                          "só entre os funcionários daquele grupo, e a bonificação de equipe vale só\n"
                          "para quem está nesse mesmo grupo (e com o bônus de equipe habilitado).",
                     font=FONT_BODY, text_color=INK_SOFT, justify="left", anchor="w").pack(
            fill="x", padx=20, pady=(0, 18))

        self._carregar_grupo()
        self.refresh_resumo()

    # ---------------- Listas auxiliares ----------------
    def _nomes_empresas(self):
        return [e["nome"] for e in self.app.empresas] or ["Matriz"]

    def _nomes_estabelecimentos(self):
        return [e["nome"] for e in self.app.estabelecimentos] or ["Geral"]

    def atualizar_listas(self):
        """Chamado quando empresas/estabelecimentos mudam em outra tela."""
        self.empresa_menu.configure(values=self._nomes_empresas())
        self.setor_menu.configure(values=self._nomes_estabelecimentos())
        if not self.empresa_var.get() and self._nomes_empresas():
            self.empresa_var.set(self._nomes_empresas()[0])
        if not self.setor_var.get() and self._nomes_estabelecimentos():
            self.setor_var.set(self._nomes_estabelecimentos()[0])
        self.refresh_resumo()

    # ---------------- Carregar/renderizar níveis do grupo selecionado ----------------
    def _config_atual(self):
        empresa = self.empresa_var.get()
        setor = self.setor_var.get()
        for cfg in self.app.metas_equipe:
            if cfg["empresa"] == empresa and cfg["estabelecimento"] == setor:
                return cfg
        return None

    def _carregar_grupo(self):
        if not self.empresa_var.get() and self._nomes_empresas():
            self.empresa_var.set(self._nomes_empresas()[0])
        if not self.setor_var.get() and self._nomes_estabelecimentos():
            self.setor_var.set(self._nomes_estabelecimentos()[0])

        cfg = self._config_atual()
        tiers = cfg["tiers"] if cfg else [{"valor_meta": 0, "bonificacao": 0} for _ in range(3)]
        self._render_tiers(tiers)

    def _render_tiers(self, dados=None):
        for w in self.tiers_wrap.winfo_children():
            w.destroy()
        self.tier_rows = []
        dados = dados if dados else [{"valor_meta": 0, "bonificacao": 0}]

        for i, d in enumerate(dados):
            row = TierRow(self.tiers_wrap, i + 1, d.get("valor_meta", 0), d.get("bonificacao", 0),
                          label_meta="Meta de equipe", label_bonus="Bônus por vendedor",
                          on_remove=lambda idx=i: self._remove_tier(idx))
            row.pack(fill="x")
            self.tier_rows.append(row)

        ctk.CTkButton(self.tiers_wrap, text="+ Adicionar nível", fg_color="transparent",
                      border_width=1, border_color=LINE, text_color=TEAL_DARK, height=28,
                      command=self._add_tier).pack(anchor="w", pady=(2, 8))

    def _read_tier_data(self):
        return [row.get() for row in self.tier_rows]

    def _add_tier(self):
        dados = self._read_tier_data()
        dados.append({"valor_meta": 0, "bonificacao": 0})
        self._render_tiers(dados)

    def _remove_tier(self, index):
        dados = self._read_tier_data()
        if len(dados) <= 1:
            messagebox.showinfo("Painel de Comissões", "É preciso manter pelo menos um nível de meta.")
            return
        dados.pop(index)
        self._render_tiers(dados)

    # ---------------- Salvar ----------------
    def salvar(self):
        empresa = self.empresa_var.get()
        setor = self.setor_var.get()
        if not empresa or not setor:
            messagebox.showwarning("Painel de Comissões", "Selecione a loja e o setor.")
            return

        tiers = [{"nivel": i + 1, **d} for i, d in enumerate(self._read_tier_data())]
        self.app.db.salvar_metas_equipe(empresa, setor, tiers)
        self.app.metas_equipe = self.app.db.listar_metas_equipe()

        messagebox.showinfo("Painel de Comissões", f"Metas de {empresa} · {setor} salvas.")
        self.refresh_resumo()

    # ---------------- Resumo dos grupos já configurados ----------------
    def refresh_resumo(self):
        for w in self.resumo_wrap.winfo_children():
            w.destroy()

        if not self.app.metas_equipe:
            ctk.CTkLabel(self.resumo_wrap, text="Nenhum grupo configurado ainda.",
                         text_color=INK_SOFT, font=FONT_BODY).pack(pady=10)
            return

        for cfg in self.app.metas_equipe:
            row = ctk.CTkFrame(self.resumo_wrap, fg_color="#FEFEFD", corner_radius=8,
                                border_width=1, border_color=LINE)
            row.pack(fill="x", pady=4)
            row.grid_columnconfigure(0, weight=1)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.grid(row=0, column=0, sticky="w", padx=14, pady=8)
            ctk.CTkLabel(info, text=f"{cfg['empresa']} · {cfg['estabelecimento']}",
                         font=("Segoe UI Semibold", 13), text_color=INK).pack(anchor="w")
            resumo_niveis = "  ·  ".join(
                f"Nível {t['nivel']}: R$ {t['valor_meta']:,.2f}".replace(",", ".") for t in cfg["tiers"]
            ) if cfg["tiers"] else "sem níveis definidos"
            ctk.CTkLabel(info, text=resumo_niveis, font=FONT_SMALL, text_color=INK_SOFT).pack(anchor="w")

            ctk.CTkButton(row, text="Editar", width=64, height=26, fg_color="transparent",
                          border_width=1, border_color=LINE, text_color=INK_SOFT,
                          command=lambda c=cfg: self._selecionar(c)).grid(row=0, column=1, sticky="e", padx=14)

    def _selecionar(self, cfg):
        self.empresa_var.set(cfg["empresa"])
        self.setor_var.set(cfg["estabelecimento"])
        self._render_tiers(cfg["tiers"])