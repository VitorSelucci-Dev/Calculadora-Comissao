"""
widgets.py
Cores, fontes e componentes visuais reutilizados em várias telas.
"""
import customtkinter as ctk
import tkinter as tk
import re

# ---------------- Paleta ----------------
NAVY = "#0D1B33"
NAVY_2 = "#16294B"
NAVY_SOFT = "#1E345C"
PAPER = "#F6F6F3"
CARD = "#FFFFFF"
INK = "#1B2430"
INK_SOFT = "#5B6472"
LINE = "#E4E3DD"
TEAL = "#0E9E8C"
TEAL_DARK = "#0B7E70"
AMBER = "#E3A73C"
RED = "#C0524A"
INK_SOFT_ON_NAVY = "#93A3C2"

# ---------------- Fontes ----------------
FONT_H1 = ("Segoe UI Semibold", 22)
FONT_H2 = ("Segoe UI Semibold", 15)
FONT_BODY = ("Segoe UI", 13)
FONT_SMALL = ("Segoe UI", 11)


def parse_num(texto):
    if texto is None:
        return 0.0
    texto = str(texto).strip()
    if texto == "":
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except (ValueError, TypeError):
        return 0.0


def fmt_moeda(v):
    v = float(v or 0)
    s = f"{v:,.2f}"
    s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {s}"


class Card(ctk.CTkFrame):
    """Cartão branco padrão usado em todas as telas internas."""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=CARD, corner_radius=10,
                          border_width=1, border_color=LINE, **kwargs)


def format_cents_to_brl(cents):
    cents = max(0, int(cents))
    reais = cents // 100
    cent_part = cents % 100
    s = f"{reais:,}".replace(",", ".")
    return f"R$ {s},{cent_part:02d}"


class MoneyEntry(ctk.CTkEntry):
    """Campo de entrada com máscara de dinheiro (R$ 1.234,56 enquanto digita).
    Por baixo, guarda o valor como centavos (inteiro) - use get_value()/set_value()
    para ler ou definir o valor numérico limpo, sem se preocupar com a formatação."""
    def __init__(self, master, initial_value=0, **kwargs):
        self._var = tk.StringVar()
        super().__init__(master, textvariable=self._var, **kwargs)
        self._cents = int(round(float(initial_value or 0) * 100))
        self._refresh()
        self.bind("<Key>", self._on_key)

    def _on_key(self, event):
        keysym = event.keysym
        if keysym in ("Left", "Right", "Home", "End", "Tab",
                      "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return  # deixa o comportamento padrão (não mexe nos dígitos)
        if keysym in ("BackSpace", "Delete"):
            self._cents = self._cents // 10
            self._refresh()
            return "break"
        if event.char and event.char.isdigit():
            if self._cents < 10**11:  # limite bem folgado (bilhões)
                self._cents = self._cents * 10 + int(event.char)
                self._refresh()
            return "break"
        return "break"  # bloqueia letras e símbolos

    def _refresh(self):
        self._var.set(format_cents_to_brl(self._cents))
        self.icursor("end")

    def get_value(self):
        """Valor numérico limpo (float), pronto para usar em cálculos."""
        return self._cents / 100.0

    def set_value(self, value):
        self._cents = int(round(float(value or 0) * 100))
        self._refresh()


class MesEntry(ctk.CTkEntry):
    """Campo de mês de referência com máscara MM/AAAA (ex: 08/2026).
    Só aceita dígitos, insere a barra automaticamente."""
    def __init__(self, master, initial_value="", **kwargs):
        self._var = tk.StringVar()
        super().__init__(master, textvariable=self._var, **kwargs)
        self._digits = re.sub(r"\D", "", str(initial_value or ""))[:6]
        self._refresh()
        self.bind("<Key>", self._on_key)

    def _on_key(self, event):
        keysym = event.keysym
        if keysym in ("Left", "Right", "Home", "End", "Tab",
                      "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return
        if keysym in ("BackSpace", "Delete"):
            self._digits = self._digits[:-1]
            self._refresh()
            return "break"
        if event.char and event.char.isdigit():
            if len(self._digits) < 6:
                self._digits += event.char
                self._refresh()
            return "break"
        return "break"

    def _refresh(self):
        d = self._digits
        texto = d if len(d) <= 2 else f"{d[:2]}/{d[2:]}"
        self._var.set(texto)
        self.icursor("end")

    def get_value(self):
        """Texto atual no formato MM/AAAA (pode estar incompleto)."""
        return self._var.get()

    def set_value(self, value):
        self._digits = re.sub(r"\D", "", str(value or ""))[:6]
        self._refresh()


def mes_valido(texto):
    """True se o texto está no formato MM/AAAA com mês entre 01 e 12."""
    m = re.match(r"^(0[1-9]|1[0-2])/\d{4}$", str(texto or "").strip())
    return bool(m)


class TierRow(ctk.CTkFrame):
    """Uma linha de nível de meta: nível + campo de valor da meta + campo de
    bonificação + (opcional) botão de remover esse nível."""
    def __init__(self, master, nivel, valor_meta=0, bonificacao=0,
                 label_meta="Meta", label_bonus="Bonificação", on_remove=None):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        badge = ctk.CTkLabel(self, text=str(nivel), width=28, height=28, corner_radius=6,
                              fg_color=PAPER, text_color=INK_SOFT, font=("Segoe UI Semibold", 12))
        badge.grid(row=0, column=0, rowspan=2, padx=(0, 10), sticky="n")

        ctk.CTkLabel(self, text=f"{label_meta} nível {nivel} (R$)", font=FONT_SMALL,
                     text_color=INK_SOFT, anchor="w").grid(row=0, column=1, sticky="w", padx=(0, 8))
        ctk.CTkLabel(self, text=f"{label_bonus} nível {nivel} (R$)", font=FONT_SMALL,
                     text_color=INK_SOFT, anchor="w").grid(row=0, column=2, sticky="w")

        self.meta_entry = MoneyEntry(self, initial_value=valor_meta)
        self.meta_entry.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(2, 10))
        self.bonus_entry = MoneyEntry(self, initial_value=bonificacao)
        self.bonus_entry.grid(row=1, column=2, sticky="ew", pady=(2, 10))

        if on_remove is not None:
            ctk.CTkButton(self, text="✕", width=28, height=28, fg_color="transparent",
                          border_width=1, border_color=LINE, text_color=RED,
                          command=on_remove).grid(row=1, column=3, padx=(8, 0), pady=(2, 10))

    def get(self):
        return {"valor_meta": self.meta_entry.get_value(), "bonificacao": self.bonus_entry.get_value()}


def nivel_badge(parent, nivel):
    cor = {0: (INK_SOFT, "#F0F0EB"), 1: (AMBER, "#FBF1DC"),
           2: (AMBER, "#FCE9C7"), 3: ("white", TEAL)}
    fg, bg = cor.get(nivel, cor[0])
    texto = f"Nível {nivel}" if nivel else "Sem nível"
    return ctk.CTkLabel(parent, text=texto, font=("Segoe UI Semibold", 11),
                         text_color=fg, fg_color=bg, corner_radius=6, padx=8, pady=3)