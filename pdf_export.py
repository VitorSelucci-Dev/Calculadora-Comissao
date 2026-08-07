"""
pdf_export.py
Geração do PDF a partir de um fechamento já calculado (ver logic.py).

Tudo sai em UM ÚNICO arquivo PDF (evita o problema de dois PDFs
abrindo em janelas separadas e um "sumir" atrás do outro):
- Página(s) de relatório: cabeçalho com os totais + tabela por
  funcionário, igual à tela de Cálculo Mensal.
- Se solicitado, depois vêm os recibos de vale alimentação, vários
  por folha (compactos, com linha de corte entre eles), só para quem
  tem valor de vale preenchido.

O PDF é salvo numa pasta "relatorios" ao lado do programa (funciona
tanto rodando com "python main.py" quanto já empacotado como .exe).
"""
import os
import sys
import re

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

NAVY = colors.HexColor("#12213D")
INK_SOFT = colors.HexColor("#5B6472")
LINE = colors.HexColor("#E4E3DD")
PAPER = colors.HexColor("#F6F6F3")


def fmt_moeda(v):
    v = float(v or 0)
    s = f"{v:,.2f}"
    s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {s}"


def _pasta_downloads():
    """Pasta de Downloads do usuário atual. Evita salvar dentro da pasta
    de instalação do programa (ex: Program Files), que é protegida e
    exige permissão de administrador para gravar arquivos."""
    # Método robusto no Windows: pergunta pro próprio sistema onde fica
    # a pasta de Downloads (funciona mesmo se o usuário tiver movido ela,
    # ex: pra um OneDrive).
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            FOLDERID_Downloads = GUID(0x374DE290, 0x123F, 0x4565,
                                       (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B))
            caminho_ptr = ctypes.c_wchar_p()
            resultado = ctypes.windll.shell32.SHGetKnownFolderPath(
                ctypes.byref(FOLDERID_Downloads), 0, 0, ctypes.byref(caminho_ptr)
            )
            if resultado == 0 and caminho_ptr.value:
                return caminho_ptr.value
        except Exception:
            pass

    # Alternativa/fallback: pasta "Downloads" dentro da pasta do usuário
    pasta = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.isdir(pasta):
        return pasta

    # Último recurso: pasta ao lado do programa (comportamento antigo)
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
    pasta = os.path.join(base, "relatorios")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _nome_arquivo(mes):
    mes_limpo = re.sub(r"[^0-9A-Za-z]", "-", mes)
    return f"fechamento_{mes_limpo}.pdf"


def _elementos_relatorio(mes, res, styles):
    titulo_style = ParagraphStyle("Titulo", parent=styles["Heading1"], fontSize=18, textColor=NAVY)
    subtitulo_style = ParagraphStyle("Subtitulo", parent=styles["Normal"], fontSize=11,
                                      textColor=INK_SOFT, spaceAfter=14)

    elementos = [
        Paragraph("Painel de Comissões", titulo_style),
        Paragraph(f"Fechamento mensal — {mes}", subtitulo_style),
    ]

    cabecalho_grupo = ["Loja", "Setor", "Vendido", "Devoluções", "Líquido", "Nível", "Bônus/pessoa"]
    linhas_grupo = [cabecalho_grupo]
    for g in res["setores"]:
        nivel_txt = f"Nível {g['nivel']}" if g["tem_metas_configuradas"] and g["nivel"] else (
            "—" if g["tem_metas_configuradas"] else "sem meta")
        bonif_txt = fmt_moeda(g["bonificacao"]) if g["tem_metas_configuradas"] else "—"
        linhas_grupo.append([
            g["empresa"] or "—", g["estabelecimento"] or "—",
            fmt_moeda(g["total_vendido"]), fmt_moeda(g["total_devolucoes"]),
            fmt_moeda(g["total_liquido"]), nivel_txt, bonif_txt,
        ])

    tabela_grupos = Table(linhas_grupo, colWidths=[3.2 * cm, 3.2 * cm, 2.6 * cm, 2.6 * cm, 2.6 * cm, 2.2 * cm, 2.6 * cm])
    tabela_grupos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elementos.append(Paragraph("Resumo por loja / setor", styles["Heading2"]))
    elementos.append(Spacer(1, 6))
    elementos.append(tabela_grupos)
    elementos.append(Spacer(1, 14))

    dados_totais = [
        ["Total vale alimentação", fmt_moeda(res["total_vale_alimentacao"])],
        ["Folha total do mês", fmt_moeda(res["total_folha"])],
    ]
    tabela_totais = Table(dados_totais, colWidths=[9 * cm, 6 * cm])
    tabela_totais.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), INK_SOFT),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, LINE),
    ]))
    elementos.append(tabela_totais)
    elementos.append(Spacer(1, 18))

    elementos.append(Paragraph("Funcionários", styles["Heading2"]))
    elementos.append(Spacer(1, 6))

    subheading_style = ParagraphStyle("Subheading", parent=styles["Heading3"], fontSize=11,
                                       textColor=NAVY, spaceBefore=10, spaceAfter=4)
    nota_style = ParagraphStyle("Nota", parent=styles["Normal"], fontSize=8.5,
                                 textColor=INK_SOFT, spaceAfter=6)

    cabecalho = ["Funcionário", "Vendido", "Devoluções", "Líquido", "Nível",
                 "Bônus ind.", "Comissão", "Vale", "Bônus equipe", "Total"]
    larguras_funcionarios = [5.0 * cm, 2.6 * cm, 2.6 * cm, 2.6 * cm, 1.7 * cm,
                              2.4 * cm, 2.4 * cm, 2.1 * cm, 2.5 * cm, 2.5 * cm]

    # Só entram setores que tiveram fechamento neste mês - e, dentro de
    # cada um, só os funcionários cujo setor DE ORIGEM é aquele (quem
    # apareceu como "convidado" ali fica só numa nota, já que o total a
    # receber dele já está contabilizado no setor de origem dele).
    for setor_res in res["setores"]:
        empresa, estabelecimento = setor_res["empresa"], setor_res["estabelecimento"]
        elementos.append(Paragraph(f"{empresa} - {estabelecimento}", subheading_style))

        linhas_do_setor = [l for l in res["linhas"]
                            if (l["funcionario"].get("empresa") or "—") == empresa
                            and (l["funcionario"].get("estabelecimento") or "—") == estabelecimento]

        linhas_tabela = [cabecalho]
        for l in linhas_do_setor:
            f = l["funcionario"]
            tem_valores = l["tem_metas"] or l["tem_venda"]
            vendido = fmt_moeda(l["vendido"]) if tem_valores else "—"
            devol = fmt_moeda(l["devolucoes"]) if tem_valores else "—"
            liquido = fmt_moeda(l["liquido"]) if tem_valores else "—"
            nivel = f"Nível {l['nivel']}" if (l["tem_metas"] and l["nivel"]) else "—"
            bonif_ind = fmt_moeda(l["bonif_individual"]) if l["tem_metas"] else "—"
            comissao = fmt_moeda(l["comissao"])
            linhas_tabela.append([
                f["nome"], vendido, devol, liquido, nivel, bonif_ind, comissao,
                fmt_moeda(f["vale_alimentacao"]), fmt_moeda(l["bonif_equipe"]), fmt_moeda(l["total"]),
            ])

        if len(linhas_tabela) == 1:
            elementos.append(Paragraph("Nenhum funcionário cadastrado neste setor.", nota_style))
            continue

        tabela = Table(linhas_tabela, colWidths=larguras_funcionarios, repeatRows=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabela)

        convidados = [l for l in setor_res["linhas"] if l["convidado"]]
        if convidados:
            nomes = ", ".join(c["funcionario"]["nome"] for c in convidados)
            elementos.append(Paragraph(
                f"Também venderam aqui como convidados (valores já somados no setor de origem de cada um): {nomes}",
                nota_style))

    return elementos


def _tabela_recibos(mes, funcionarios_com_va, styles):
    texto_style = ParagraphStyle("ReciboTexto", parent=styles["Normal"], fontSize=10, leading=14)
    linhas = []
    for f in funcionarios_com_va:
        conteudo = Paragraph(
            f"<b>Recibo de Vale Alimentação</b> &nbsp;·&nbsp; Mês: <b>{mes}</b><br/>"
            f"Funcionário: <b>{f['nome']}</b> &nbsp;&nbsp;&nbsp; Valor: <b>{fmt_moeda(f['vale_alimentacao'])}</b><br/>"
            f"Assinatura: _______________________________________________",
            texto_style,
        )
        linhas.append([conteudo])

    tabela = Table(linhas, colWidths=[26.5 * cm], rowHeights=[4.3 * cm] * len(linhas))
    estilo = [
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]
    if len(linhas) > 1:
        estilo.append(("LINEBELOW", (0, 0), (0, -2), 0.6, LINE))
    tabela.setStyle(TableStyle(estilo))
    return tabela


def gerar_pdf_relatorio(mes, res, incluir_recibos=False):
    """Gera o PDF do fechamento (e, opcionalmente, os recibos de vale
    alimentação logo em seguida, no MESMO arquivo) e devolve o caminho."""
    caminho = os.path.join(_pasta_downloads(), _nome_arquivo(mes))

    doc = SimpleDocTemplate(caminho, pagesize=landscape(A4), topMargin=1.2 * cm, bottomMargin=1.2 * cm,
                             leftMargin=1.2 * cm, rightMargin=1.2 * cm)
    styles = getSampleStyleSheet()

    elementos = _elementos_relatorio(mes, res, styles)

    if incluir_recibos:
        elementos.append(PageBreak())
        elementos.append(Paragraph("Recibos de Vale Alimentação", styles["Heading2"]))
        elementos.append(Spacer(1, 10))

        funcionarios_com_va = [l["funcionario"] for l in res["linhas"] if (l["funcionario"]["vale_alimentacao"] or 0) > 0]
        if funcionarios_com_va:
            elementos.append(_tabela_recibos(mes, funcionarios_com_va, styles))
        else:
            texto_style = ParagraphStyle("Texto", parent=styles["Normal"], fontSize=11)
            elementos.append(Paragraph("Nenhum funcionário com vale alimentação preenchido neste mês.", texto_style))

    doc.build(elementos)
    return caminho


def _nome_arquivo_simplificado(mes):
    mes_limpo = re.sub(r"[^0-9A-Za-z]", "-", mes)
    return f"simplificado_{mes_limpo}.pdf"


def gerar_pdf_simplificado(mes, res):
    """Gera o PDF simplificado: um cabeçalho por Loja - Setor, listando
    só os funcionários marcados para 'Enviar Contábil', com Nome,
    Comissão e Bonificações (individual + equipe somadas). Devolve o
    caminho do arquivo."""
    caminho = os.path.join(_pasta_downloads(), _nome_arquivo_simplificado(mes))

    doc = SimpleDocTemplate(caminho, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                             leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle("Titulo", parent=styles["Heading1"], fontSize=18, textColor=NAVY)
    subtitulo_style = ParagraphStyle("Subtitulo", parent=styles["Normal"], fontSize=11,
                                      textColor=INK_SOFT, spaceAfter=6)
    cabecalho_grupo_style = ParagraphStyle("CabecalhoGrupo", parent=styles["Heading2"], fontSize=13,
                                            textColor=NAVY, spaceBefore=14, spaceAfter=6)
    texto_style = ParagraphStyle("Texto", parent=styles["Normal"], fontSize=10.5)

    elementos = [
        Paragraph("Painel de Comissões", titulo_style),
        Paragraph(f"Relatório simplificado — {mes}", subtitulo_style),
    ]

    setores_do_mes = {(s["empresa"], s["estabelecimento"]) for s in res["setores"]}

    grupos = {}
    for l in res["linhas"]:
        f = l["funcionario"]
        chave = (f.get("empresa") or "—", f.get("estabelecimento") or "—")
        if chave not in setores_do_mes:
            continue
        grupos.setdefault(chave, []).append(l)

    if not grupos:
        elementos.append(Paragraph("Nenhum funcionário cadastrado.", texto_style))

    for (empresa, estabelecimento), linhas_grupo in sorted(grupos.items()):
        elementos.append(Paragraph(f"{empresa} - {estabelecimento}", cabecalho_grupo_style))

        linhas_visiveis = [l for l in linhas_grupo if l["funcionario"].get("enviar_contabil", True)]
        if not linhas_visiveis:
            elementos.append(Paragraph("Nenhum funcionário para exibir neste grupo.", texto_style))
            continue

        cabecalho = ["Nome", "Comissão", "Bonificações"]
        linhas_tabela = [cabecalho]
        for l in linhas_visiveis:
            bonificacoes = (l["bonif_individual"] or 0) + (l["bonif_equipe"] or 0)
            linhas_tabela.append([l["funcionario"]["nome"], fmt_moeda(l["comissao"]), fmt_moeda(bonificacoes)])

        tabela = Table(linhas_tabela, colWidths=[8 * cm, 4 * cm, 4 * cm])
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabela)

    doc.build(elementos)
    return caminho