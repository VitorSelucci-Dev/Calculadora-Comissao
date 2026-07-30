"""
logic.py
Regras de cálculo - funções puras, sem depender de interface gráfica.

MODELO DE DADOS (a partir desta versão):
Cada funcionário tem um setor de ORIGEM (f["empresa"], f["estabelecimento"]).
Os fechamentos passam a ser por MÊS + LOJA + SETOR:
    app.fechamentos[mes][(empresa, estabelecimento)] = {
        "vendas": {funcionario_id: {"vendido": x, "devolucoes": y}},
        "criado_em": "...",
    }
Um funcionário pode aparecer no fechamento de um setor que não é o dele
(um "convidado" - ex: alguém da Oficina que vendeu na Autopeças). Essa
venda conta no total DAQUELE setor (ajuda a bater a meta de lá), mas:
- a bonificação de equipe dele sempre vem do fechamento do SETOR DE
  ORIGEM dele naquele mês (não do setor onde foi convidado);
- a comissão e o nível de meta individual dele consideram a SOMA de
  tudo que ele vendeu no mês, em qualquer setor.
"""


def nivel_atingido(valor, tiers):
    """Recebe um valor líquido e uma lista de níveis
    [{nivel, valor_meta, bonificacao}], devolve o MAIOR nível atingido
    (não é cumulativo) ou None se nenhum nível foi atingido."""
    atingidos = [t for t in tiers if t.get("valor_meta", 0) > 0 and valor >= t["valor_meta"]]
    if not atingidos:
        return None
    return max(atingidos, key=lambda t: t["nivel"])


def obter_tiers_grupo(metas_equipe, empresa, estabelecimento):
    """Devolve os níveis de meta configurados para essa loja+setor,
    ou lista vazia se ainda não foi configurado."""
    for cfg in metas_equipe:
        if cfg["empresa"] == empresa and cfg["estabelecimento"] == estabelecimento:
            return cfg["tiers"]
    return []


def calcular_fechamento_setor(funcionarios, metas_equipe, empresa, estabelecimento, vendas_map):
    """Calcula o fechamento de UM setor específico: soma tudo que foi
    vendido ali (seja por funcionário do setor ou "convidado" de outro),
    compara com a meta daquele setor, e monta uma linha por vendedor
    que aparece nesse fechamento (marcando quem é convidado)."""
    tiers = obter_tiers_grupo(metas_equipe, empresa, estabelecimento)

    total_vendido = sum(float(v.get("vendido", 0) or 0) for v in vendas_map.values())
    total_devolucoes = sum(float(v.get("devolucoes", 0) or 0) for v in vendas_map.values())
    total_liquido = total_vendido - total_devolucoes

    tier = nivel_atingido(total_liquido, tiers)
    nivel = tier["nivel"] if tier else 0
    bonificacao = tier["bonificacao"] if tier else 0.0

    linhas = []
    for funcionario_id, reg in vendas_map.items():
        f = next((x for x in funcionarios if x["id"] == funcionario_id), None)
        if not f:
            continue
        vendido = float(reg.get("vendido", 0) or 0)
        devolucoes = float(reg.get("devolucoes", 0) or 0)
        convidado = (f.get("empresa"), f.get("estabelecimento")) != (empresa, estabelecimento)
        linhas.append({
            "funcionario": f,
            "vendido": vendido,
            "devolucoes": devolucoes,
            "liquido": vendido - devolucoes,
            "convidado": convidado,
        })
    linhas.sort(key=lambda l: (l["convidado"], l["funcionario"]["nome"]))

    return {
        "empresa": empresa,
        "estabelecimento": estabelecimento,
        "tiers": tiers,
        "tem_metas_configuradas": bool(tiers),
        "total_vendido": total_vendido,
        "total_devolucoes": total_devolucoes,
        "total_liquido": total_liquido,
        "nivel": nivel,
        "bonificacao": bonificacao,
        "linhas": linhas,
    }


def vendas_consolidadas_funcionario(fechamentos_mes, funcionario_id):
    """Soma o vendido/devoluções desse funcionário em TODOS os setores
    daquele mês (fechamentos_mes = app.fechamentos.get(mes, {})).
    Devolve (total_vendido, total_devolucoes, apareceu_em_algum_setor)."""
    total_vendido = 0.0
    total_devolucoes = 0.0
    apareceu = False
    for registro in fechamentos_mes.values():
        reg = registro["vendas"].get(funcionario_id)
        if reg:
            apareceu = True
            total_vendido += float(reg.get("vendido", 0) or 0)
            total_devolucoes += float(reg.get("devolucoes", 0) or 0)
    return total_vendido, total_devolucoes, apareceu


def calcular_mes_completo(funcionarios, metas_equipe, fechamentos_mes):
    """
    fechamentos_mes: dict {(empresa, estabelecimento): {"vendas": {...}, "criado_em": ...}}
    (ou seja, app.fechamentos.get(mes, {}))

    Retorna a folha consolidada do mês inteiro: o resultado de cada
    setor que teve fechamento, e uma linha por funcionário com o total
    a receber (metas/comissão pelo total vendido no mês inteiro,
    bônus de equipe pelo setor de origem).
    """
    setores = []
    bonif_por_setor = {}
    for (empresa, estabelecimento), registro in fechamentos_mes.items():
        resultado = calcular_fechamento_setor(funcionarios, metas_equipe, empresa, estabelecimento, registro["vendas"])
        setores.append(resultado)
        bonif_por_setor[(empresa, estabelecimento)] = resultado["bonificacao"]

    linhas = []
    for f in funcionarios:
        total_vendido, total_devolucoes, vendeu = vendas_consolidadas_funcionario(fechamentos_mes, f["id"])
        liquido = total_vendido - total_devolucoes
        tem_metas = bool(f["metas"])

        if tem_metas:
            tier = nivel_atingido(liquido, f["metas"])
            nivel = tier["nivel"] if tier else 0
            bonif_individual = tier["bonificacao"] if tier else 0.0
            comissao = liquido * (f.get("comissao_percent") or 0) / 100
        else:
            nivel = None
            bonif_individual = 0.0
            comissao = 0.0

        chave_origem = (f.get("empresa"), f.get("estabelecimento"))
        bonif_grupo = bonif_por_setor.get(chave_origem, 0.0)
        bonif_equipe = bonif_grupo if f.get("recebe_bonif_equipe", True) else 0.0

        total = f["salario_base"] + f["vale_alimentacao"] + comissao + bonif_individual + bonif_equipe

        linhas.append({
            "funcionario": f,
            "tem_metas": tem_metas,
            "tem_venda": vendeu,
            "vendido": total_vendido if vendeu else None,
            "devolucoes": total_devolucoes if vendeu else None,
            "liquido": liquido if vendeu else None,
            "nivel": nivel,
            "bonif_individual": bonif_individual,
            "comissao": comissao,
            "bonif_equipe": bonif_equipe,
            "total": total,
        })

    linhas.sort(key=lambda l: 0 if l["tem_metas"] else 1)
    total_folha = sum(l["total"] for l in linhas)
    total_vale_alimentacao = sum(f["vale_alimentacao"] for f in funcionarios)

    return {
        "setores": setores,
        "linhas": linhas,
        "total_folha": total_folha,
        "total_vale_alimentacao": total_vale_alimentacao,
    }


def linhas_detalhadas_mes(mes, res):
    """A partir do resultado de calcular_mes_completo, devolve uma lista
    de dicts "achatados" (um por funcionário) prontos para relatórios
    dinâmicos: mes, nome, empresa, estabelecimento e todos os valores."""
    linhas = []
    for l in res["linhas"]:
        f = l["funcionario"]
        linhas.append({
            "mes": mes,
            "funcionario_id": f["id"],
            "nome": f["nome"],
            "empresa": f.get("empresa") or "—",
            "estabelecimento": f.get("estabelecimento") or "—",
            "vendido": l["vendido"] or 0,
            "devolucoes": l["devolucoes"] or 0,
            "liquido": l["liquido"] or 0,
            "comissao": l["comissao"] or 0,
            "bonif_individual": l["bonif_individual"] or 0,
            "bonif_equipe": l["bonif_equipe"] or 0,
            "total": l["total"] or 0,
        })
    return linhas