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


def obter_config_funcao(funcoes, nome_funcao):
    """Devolve o dict de configuração da função (cargo) pelo nome, ou
    None se não encontrar (funcionário com função "solta"/excluída)."""
    for cfg in funcoes:
        if cfg["nome"] == nome_funcao:
            return cfg
    return None


def obter_modo_calculo(estabelecimentos, nome_estabelecimento):
    """Devolve 'padrao' ou 'personalizado' - o modo de cálculo
    configurado para esse setor. 'padrao' se não encontrar."""
    for e in estabelecimentos:
        if e["nome"] == nome_estabelecimento:
            return e.get("modo_calculo", "padrao")
    return "padrao"


def calcular_mes_completo(funcionarios, metas_equipe, fechamentos_mes, funcoes, estabelecimentos):
    """
    fechamentos_mes: dict {(empresa, estabelecimento): {"vendas": {...}, "criado_em": ...}}
    (ou seja, app.fechamentos.get(mes, {}))
    funcoes: app.funcoes - lista de configuração de cada função/cargo,
    incluindo o modelo de comissão (ver database.py).
    estabelecimentos: app.estabelecimentos - lista de setores, cada um
    com seu modo de cálculo ("padrao" ou "personalizado"). É o setor
    de ORIGEM do funcionário que decide se o modelo de comissão da
    função dele vale ou não - num setor "padrao", todo mundo usa o
    cálculo clássico, não importa o que a função diga.

    Retorna a folha consolidada do mês inteiro: o resultado de cada
    setor que teve fechamento, e uma linha por funcionário com o total
    a receber, calculado conforme o MODELO DE COMISSÃO da função dele:

    - "padrao": metas individuais (níveis) + comissão sobre a própria
      produção + bônus de equipe (valor fixo por nível, do setor de
      origem) - é o modelo "Vendedor" de sempre.
    - "nenhum": sem metas nem comissão; só recebe o bônus de equipe
      (valor fixo) se estiver marcado para isso.
    - "gerencia": sem metas individuais; comissão em % sobre o TOTAL
      vendido pela equipe do setor de origem; bônus FIXO (valor
      configurado na função) se a meta geral do setor for atingida.
    - "percentual_equipe": sem metas nem comissão própria; bônus em %
      sobre o total da equipe, só se a meta geral for atingida.
    - "auxiliar_condicional": tem meta individual (só usada pra saber
      se bateu ou não, não gera bônus fixo); recebe uma % sobre a
      PRÓPRIA produção, e essa % muda conforme bateu a meta individual
      e/ou a meta geral do setor. Não recebe bônus de equipe.
    """
    setores = []
    bonif_por_setor = {}
    liquido_equipe_por_setor = {}
    meta_geral_atingida_por_setor = {}
    for (empresa, estabelecimento), registro in fechamentos_mes.items():
        resultado = calcular_fechamento_setor(funcionarios, metas_equipe, empresa, estabelecimento, registro["vendas"])
        setores.append(resultado)
        chave = (empresa, estabelecimento)
        bonif_por_setor[chave] = resultado["bonificacao"]
        liquido_equipe_por_setor[chave] = resultado["total_liquido"]
        meta_geral_atingida_por_setor[chave] = resultado["nivel"] > 0

    linhas = []
    for f in funcionarios:
        total_vendido, total_devolucoes, vendeu = vendas_consolidadas_funcionario(fechamentos_mes, f["id"])
        liquido = total_vendido - total_devolucoes
        tem_metas = bool(f["metas"])

        chave_origem = (f.get("empresa"), f.get("estabelecimento"))
        bonif_grupo_tier = bonif_por_setor.get(chave_origem, 0.0)
        liquido_equipe_origem = liquido_equipe_por_setor.get(chave_origem, 0.0)
        meta_geral_atingida = meta_geral_atingida_por_setor.get(chave_origem, False)

        cfg_funcao = obter_config_funcao(funcoes, f.get("funcao")) or {}
        modo_setor = obter_modo_calculo(estabelecimentos, f.get("estabelecimento"))
        modelo = cfg_funcao.get("modelo_comissao", "padrao") if modo_setor == "personalizado" else "padrao"

        if modelo == "gerencia":
            nivel = None
            bonif_individual = 0.0
            comissao = liquido_equipe_origem * (cfg_funcao.get("comissao_equipe_percent") or 0) / 100
            bonif_equipe = (cfg_funcao.get("bonificacao_fixa") or 0) if meta_geral_atingida else 0.0

        elif modelo == "percentual_equipe":
            nivel = None
            bonif_individual = 0.0
            comissao = 0.0
            bonif_equipe = (liquido_equipe_origem * (cfg_funcao.get("percentual_bonif_equipe") or 0) / 100
                             if meta_geral_atingida else 0.0)

        elif modelo == "auxiliar_condicional":
            tier = nivel_atingido(liquido, f["metas"]) if tem_metas else None
            individual_atingida = tier is not None
            nivel = tier["nivel"] if tier else 0
            if individual_atingida and meta_geral_atingida:
                pct = cfg_funcao.get("pct_individual_e_geral") or 0
            elif individual_atingida and not meta_geral_atingida:
                pct = cfg_funcao.get("pct_somente_individual") or 0
            elif not individual_atingida and meta_geral_atingida:
                pct = cfg_funcao.get("pct_somente_geral") or 0
            else:
                pct = 0
            comissao = liquido * pct / 100
            bonif_individual = 0.0
            bonif_equipe = 0.0

        else:  # "padrao" ou "nenhum" (e qualquer função sem modelo definido, por segurança)
            if tem_metas:
                tier = nivel_atingido(liquido, f["metas"])
                nivel = tier["nivel"] if tier else 0
                bonif_individual = tier["bonificacao"] if tier else 0.0
                comissao = liquido * (f.get("comissao_percent") or 0) / 100
            else:
                nivel = None
                bonif_individual = 0.0
                comissao = 0.0
            bonif_equipe = bonif_grupo_tier if f.get("recebe_bonif_equipe", True) else 0.0

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