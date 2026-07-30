"""
screens/placeholder.py
Tela genérica de "ainda não construído", usada pelas telas que
ainda vamos montar (Metas & Bonificações, Cálculo Mensal, Relatório).
Cada uma vira seu próprio arquivo quando chegar a vez de construí-la.
"""
import customtkinter as ctk
from widgets import PAPER, INK_SOFT, FONT_H1


class PlaceholderScreen(ctk.CTkFrame):
    def __init__(self, master, app, titulo):
        super().__init__(master, fg_color=PAPER)
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=40, pady=30)
        ctk.CTkLabel(inner, text=titulo, font=FONT_H1).pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(inner, text="(conteúdo desta tela ainda será construído)",
                     text_color=INK_SOFT).pack(anchor="w")
