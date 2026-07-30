"""
main.py
Janela principal do Painel de Comissões: menu superior, área de
conteúdo e navegação entre telas. A lógica de cada tela vive em
screens/, e os componentes/cores compartilhados em widgets.py.
"""
import customtkinter as ctk
import tkinter as tk
import os
import sys

from widgets import NAVY, NAVY_SOFT, PAPER, INK_SOFT_ON_NAVY
from database import Database
from screens.home import HomeScreen
from screens.funcionarios import FuncionariosScreen
from screens.metas import MetasEquipeScreen
from screens.calculo import CalculoScreen
from screens.relatorio import RelatorioScreen

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def _caminho_icone():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base, "icone.ico")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Painel de Comissões")
        try:
            self.iconbitmap(_caminho_icone())
        except Exception:
            pass  # se o ícone não for encontrado, o programa continua normalmente
        self.geometry("1150x750")
        self.minsize(950, 640)
        self.configure(fg_color=PAPER)

        # Banco de dados (SQLite, comissoes.db ao lado do programa) -
        # tudo abaixo é carregado dele e mantido em memória enquanto o
        # programa está aberto; cada tela salva de volta no banco a
        # cada alteração.
        self.db = Database()
        self.funcoes = self.db.listar_funcoes()
        self.empresas = self.db.listar_empresas()
        self.estabelecimentos = self.db.listar_estabelecimentos()
        self.funcionarios = self.db.listar_funcionarios()
        self.metas_equipe = self.db.listar_metas_equipe()
        self.fechamentos = self.db.listar_fechamentos()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_content_area()
        self.show_section("inicio")

    def _build_topbar(self):
        topbar = ctk.CTkFrame(self, fg_color=NAVY, corner_radius=0, height=56)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(topbar, text="Painel de Comissões", font=("Segoe UI Semibold", 15),
                     text_color="white").grid(row=0, column=0, padx=24, pady=14, sticky="w")

        nav_wrap = ctk.CTkFrame(topbar, fg_color="transparent")
        nav_wrap.grid(row=0, column=1, sticky="e", padx=16)

        ctk.CTkButton(topbar, text="⚙ Configurações", fg_color="transparent", border_width=1,
                      border_color=NAVY_SOFT, text_color=INK_SOFT_ON_NAVY, hover_color=NAVY_SOFT,
                      corner_radius=6, height=32, font=("Segoe UI", 13),
                      command=self.abrir_configuracoes).grid(row=0, column=2, sticky="e", padx=(0, 24))

        self.nav_buttons = {}
        opcoes = [
            ("inicio", "Início"), ("funcionarios", "Funcionários"),
            ("metas", "Metas & Bonificações"), ("calculo", "Cálculo Mensal"),
            ("relatorio", "Relatório"),
        ]
        for key, label in opcoes:
            btn = ctk.CTkButton(nav_wrap, text=label, fg_color="transparent",
                                 hover_color=NAVY_SOFT, text_color=INK_SOFT_ON_NAVY,
                                 corner_radius=6, height=32, font=("Segoe UI", 13),
                                 command=lambda k=key: self.show_section(k))
            btn.pack(side="left", padx=2)
            self.nav_buttons[key] = btn

    def _build_content_area(self):
        self.content = ctk.CTkFrame(self, fg_color=PAPER, corner_radius=0)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.sections = {
            "inicio": HomeScreen(self.content, self),
            "funcionarios": FuncionariosScreen(self.content, self),
            "metas": MetasEquipeScreen(self.content, self),
            "calculo": CalculoScreen(self.content, self),
            "relatorio": RelatorioScreen(self.content, self),
        }

    def abrir_configuracoes(self):
        if getattr(self, "_config_popup", None) is not None and self._config_popup.winfo_exists():
            self._config_popup.focus()
            return

        popup = ctk.CTkToplevel(self)
        popup.title("Configurações")
        popup.geometry("420x420")
        popup.resizable(False, False)
        popup.transient(self)
        self._config_popup = popup

        from widgets import FONT_H2, FONT_SMALL, TEAL, TEAL_DARK, INK, INK_SOFT, LINE

        ctk.CTkLabel(popup, text="Empresas cadastradas", font=FONT_H2, text_color=INK).pack(
            anchor="w", padx=20, pady=(20, 8))
        ctk.CTkLabel(popup, text="Cadastre as filiais/empresas que vão usar o mesmo sistema.",
                     font=FONT_SMALL, text_color=INK_SOFT, anchor="w", justify="left").pack(
            fill="x", padx=20, pady=(0, 10))

        lista_wrap = ctk.CTkFrame(popup, fg_color="transparent")
        lista_wrap.pack(fill="x", padx=20)

        def render_lista():
            for w in lista_wrap.winfo_children():
                w.destroy()
            for emp in self.empresas:
                linha = ctk.CTkFrame(lista_wrap, fg_color="#F6F6F3", corner_radius=6)
                linha.pack(fill="x", pady=2)
                ctk.CTkLabel(linha, text=emp["nome"], font=FONT_SMALL, text_color=INK, anchor="w").pack(
                    side="left", padx=10, pady=6)
                ctk.CTkButton(linha, text="Remover", width=64, height=22, fg_color="transparent",
                              border_width=1, border_color=LINE, text_color=INK_SOFT,
                              command=lambda e=emp: remover(e)).pack(side="right", padx=6, pady=4)

        def remover(emp):
            if len(self.empresas) <= 1:
                from tkinter import messagebox
                messagebox.showinfo("Painel de Comissões", "É preciso manter ao menos uma empresa cadastrada.", parent=popup)
                return
            self.db.excluir_empresa(emp["nome"])
            self.empresas = self.db.listar_empresas()
            render_lista()
            self._atualizar_dropdowns_empresa()

        render_lista()

        ctk.CTkLabel(popup, text="Nome da nova empresa", font=FONT_SMALL, text_color=INK_SOFT, anchor="w").pack(
            fill="x", padx=20, pady=(18, 2))
        nome_var = tk.StringVar()
        ctk.CTkEntry(popup, textvariable=nome_var, placeholder_text="Ex: Filial Centro").pack(fill="x", padx=20)

        from tkinter import messagebox

        def adicionar():
            nome = nome_var.get().strip()
            if not nome:
                messagebox.showwarning("Painel de Comissões", "Informe o nome da empresa.", parent=popup)
                return
            if any(e["nome"].lower() == nome.lower() for e in self.empresas):
                messagebox.showwarning("Painel de Comissões", "Já existe uma empresa com esse nome.", parent=popup)
                return
            self.db.salvar_empresa(nome)
            self.empresas = self.db.listar_empresas()
            nome_var.set("")
            render_lista()
            self._atualizar_dropdowns_empresa()

        ctk.CTkButton(popup, text="Adicionar empresa", fg_color=TEAL, hover_color=TEAL_DARK,
                      command=adicionar).pack(fill="x", padx=20, pady=(14, 8))
        ctk.CTkButton(popup, text="Fechar", fg_color="transparent", border_width=1,
                      border_color=LINE, text_color=INK_SOFT, command=popup.destroy).pack(
            fill="x", padx=20, pady=(0, 20))

        popup.after(50, lambda: popup.grab_set())

    def _atualizar_dropdowns_empresa(self):
        """Avisa as telas de Funcionários e Metas pra atualizar seus dropdowns,
        caso a lista de empresas/tipos tenha mudado enquanto já estavam abertas."""
        tela_func = self.sections.get("funcionarios")
        if tela_func is not None and hasattr(tela_func, "atualizar_lista_empresas"):
            tela_func.atualizar_lista_empresas()
        tela_metas = self.sections.get("metas")
        if tela_metas is not None and hasattr(tela_metas, "atualizar_listas"):
            tela_metas.atualizar_listas()

    def show_section(self, key):
        for frame in self.sections.values():
            frame.grid_remove()
        self.sections[key].grid(row=0, column=0, sticky="nsew")
        if key == "relatorio" and hasattr(self.sections[key], "refresh_filtros"):
            self.sections[key].refresh_filtros()
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=NAVY_SOFT, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=INK_SOFT_ON_NAVY)


    def on_close(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()