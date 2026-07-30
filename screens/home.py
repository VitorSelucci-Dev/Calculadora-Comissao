"""
screens/home.py
Tela inicial: fundo azul escuro, título de destaque e cartões de atalho.
"""
import customtkinter as ctk
from widgets import NAVY, NAVY_2, NAVY_SOFT, TEAL, AMBER, INK_SOFT_ON_NAVY


class HomeScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=NAVY, corner_radius=0)
        self.app = app

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.place(relx=0.5, rely=0.38, anchor="center")
        ctk.CTkLabel(wrap, text="Calculadora de Comissão", font=("Segoe UI Semibold", 42),
                     text_color="white").pack()
        ctk.CTkLabel(wrap, text="Cadastros, metas, bonificações e fechamento mensal em um só lugar",
                     font=("Segoe UI", 14), text_color=INK_SOFT_ON_NAVY).pack(pady=(8, 0))

        cards_wrap = ctk.CTkFrame(self, fg_color="transparent")
        cards_wrap.place(relx=0.5, rely=0.68, anchor="center")

        atalhos = [
            ("funcionarios", "Funcionários", "Cadastro da equipe", TEAL),
            ("metas", "Metas & Bonificações", "Níveis de meta da equipe", AMBER),
            ("calculo", "Cálculo Mensal", "Fechamento do mês", TEAL),
            ("relatorio", "Relatório", "Histórico salvo", AMBER),
        ]
        for i, (key, titulo, sub, cor) in enumerate(atalhos):
            card = ctk.CTkFrame(cards_wrap, fg_color=NAVY_2, corner_radius=10,
                                 border_width=1, border_color=NAVY_SOFT, width=210, height=110)
            card.grid(row=0, column=i, padx=10)
            card.grid_propagate(False)

            strip = ctk.CTkFrame(card, fg_color=cor, width=36, height=4, corner_radius=2)
            strip.place(x=20, y=20)

            ctk.CTkLabel(card, text=titulo, font=("Segoe UI Semibold", 14),
                         text_color="white", anchor="w").place(x=20, y=38)
            ctk.CTkLabel(card, text=sub, font=("Segoe UI", 11.5),
                         text_color=INK_SOFT_ON_NAVY, anchor="w").place(x=20, y=64)

            for widget in (card, strip):
                widget.bind("<Button-1>", lambda e, k=key: self.app.show_section(k))
            card.configure(cursor="hand2")
