"""
database.py
Persistência em PostgreSQL (banco compartilhado na rede local).

A conexão é configurada em config.json (ver config.py) - cada
computador aponta pro mesmo servidor (o "computador principal" onde
o PostgreSQL está instalado).

Os métodos daqui devolvem exatamente os mesmos formatos de dados que
as telas já usam em memória (listas de dicts, o dict aninhado de
fechamentos etc.) - assim, nenhuma tela precisou mudar quando trocamos
de SQLite pra PostgreSQL; só este arquivo.
"""
import psycopg2
import psycopg2.extras

from config import carregar_config


class Database:
    def __init__(self, config=None):
        cfg = config or carregar_config()
        try:
            self.conn = psycopg2.connect(
                host=cfg["host"], port=cfg["port"], dbname=cfg["dbname"],
                user=cfg["user"], password=cfg["password"],
                client_encoding="UTF8",
            )
        except UnicodeDecodeError:
            # O psycopg2 tenta ler a mensagem de erro do PostgreSQL como
            # UTF-8; se o servidor responder em português (com acento) e
            # a decodificação falhar, isso mascara o erro real de conexão
            # (senha errada, host errado, rede bloqueada, etc.) atrás de
            # um UnicodeDecodeError sem sentido. Melhor avisar isso do
            # que deixar o traceback confuso aparecer pro usuário.
            raise RuntimeError(
                "Não foi possível conectar ao banco de dados (o PostgreSQL respondeu "
                "com uma mensagem de erro que não pôde ser lida corretamente - "
                "provavelmente a conexão falhou por senha incorreta, host/porta errados, "
                "ou a rede/firewall bloqueando o acesso). Confira o config.json e a "
                "conexão com testar_conexao.py."
            )
        self._criar_tabelas()
        self._migrar_schema()
        self._seed_padroes()

    def _cur(self):
        return self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def _criar_tabelas(self):
        cur = self._cur()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS funcoes (
            nome TEXT PRIMARY KEY,
            tem_metas BOOLEAN NOT NULL DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS empresas (
            nome TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS estabelecimentos (
            nome TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS funcionarios (
            id SERIAL PRIMARY KEY,
            codigo TEXT DEFAULT '',
            nome TEXT NOT NULL,
            funcao TEXT NOT NULL,
            empresa TEXT,
            estabelecimento TEXT,
            salario_base NUMERIC NOT NULL DEFAULT 0,
            vale_alimentacao NUMERIC NOT NULL DEFAULT 0,
            comissao_percent NUMERIC NOT NULL DEFAULT 0,
            recebe_bonif_equipe BOOLEAN NOT NULL DEFAULT TRUE,
            enviar_contabil BOOLEAN NOT NULL DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS metas_individuais (
            id SERIAL PRIMARY KEY,
            funcionario_id INTEGER NOT NULL REFERENCES funcionarios(id) ON DELETE CASCADE,
            nivel INTEGER NOT NULL,
            valor_meta NUMERIC NOT NULL DEFAULT 0,
            bonificacao NUMERIC NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS metas_equipe (
            id SERIAL PRIMARY KEY,
            empresa TEXT NOT NULL,
            estabelecimento TEXT NOT NULL,
            nivel INTEGER NOT NULL,
            valor_meta NUMERIC NOT NULL DEFAULT 0,
            bonificacao NUMERIC NOT NULL DEFAULT 0,
            UNIQUE(empresa, estabelecimento, nivel)
        );

        CREATE TABLE IF NOT EXISTS fechamentos (
            id SERIAL PRIMARY KEY,
            mes TEXT NOT NULL,
            empresa TEXT NOT NULL,
            estabelecimento TEXT NOT NULL,
            criado_em TEXT NOT NULL,
            UNIQUE(mes, empresa, estabelecimento)
        );

        CREATE TABLE IF NOT EXISTS fechamento_vendas (
            fechamento_id INTEGER NOT NULL REFERENCES fechamentos(id) ON DELETE CASCADE,
            funcionario_id INTEGER NOT NULL,
            vendido NUMERIC NOT NULL DEFAULT 0,
            devolucoes NUMERIC NOT NULL DEFAULT 0,
            PRIMARY KEY (fechamento_id, funcionario_id)
        );
        """)
        self.conn.commit()
        cur.close()

    def _migrar_schema(self):
        """Adiciona colunas novas em bancos que já existiam antes dessa
        versão (funciona igual em banco novo - as colunas simplesmente
        já nascem prontas). Usa ADD COLUMN IF NOT EXISTS, então é
        seguro rodar toda vez que o programa abre."""
        cur = self._cur()
        cur.execute("""
        ALTER TABLE funcoes ADD COLUMN IF NOT EXISTS modelo_comissao TEXT NOT NULL DEFAULT 'padrao';
        ALTER TABLE funcoes ADD COLUMN IF NOT EXISTS comissao_equipe_percent NUMERIC NOT NULL DEFAULT 0;
        ALTER TABLE funcoes ADD COLUMN IF NOT EXISTS bonificacao_fixa NUMERIC NOT NULL DEFAULT 0;
        ALTER TABLE funcoes ADD COLUMN IF NOT EXISTS percentual_bonif_equipe NUMERIC NOT NULL DEFAULT 0;
        ALTER TABLE funcoes ADD COLUMN IF NOT EXISTS pct_individual_e_geral NUMERIC NOT NULL DEFAULT 0;
        ALTER TABLE funcoes ADD COLUMN IF NOT EXISTS pct_somente_individual NUMERIC NOT NULL DEFAULT 0;
        ALTER TABLE funcoes ADD COLUMN IF NOT EXISTS pct_somente_geral NUMERIC NOT NULL DEFAULT 0;
        ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS modo_calculo TEXT NOT NULL DEFAULT 'padrao';
        """)
        self.conn.commit()
        cur.close()

    def _seed_padroes(self):
        cur = self._cur()
        cur.execute("SELECT COUNT(*) AS c FROM funcoes")
        if cur.fetchone()["c"] == 0:
            cur.execute(
                "INSERT INTO funcoes (nome, tem_metas) VALUES (%s,%s), (%s,%s)",
                ("Vendedor", True, "Outro", False)
            )
        cur.execute("SELECT COUNT(*) AS c FROM empresas")
        if cur.fetchone()["c"] == 0:
            cur.execute("INSERT INTO empresas (nome) VALUES (%s)", ("Matriz",))
        cur.execute("SELECT COUNT(*) AS c FROM estabelecimentos")
        if cur.fetchone()["c"] == 0:
            cur.execute(
                "INSERT INTO estabelecimentos (nome) VALUES (%s), (%s)",
                ("Oficina", "Autopeças")
            )
        self.conn.commit()
        cur.close()

    # ================= Funções (cargos) =================
    def listar_funcoes(self):
        cur = self._cur()
        cur.execute("""
            SELECT nome, tem_metas, modelo_comissao, comissao_equipe_percent, bonificacao_fixa,
                   percentual_bonif_equipe, pct_individual_e_geral, pct_somente_individual, pct_somente_geral
            FROM funcoes ORDER BY nome
        """)
        resultado = []
        for r in cur.fetchall():
            f = dict(r)
            f["tem_metas"] = bool(f["tem_metas"])
            for campo in ("comissao_equipe_percent", "bonificacao_fixa", "percentual_bonif_equipe",
                          "pct_individual_e_geral", "pct_somente_individual", "pct_somente_geral"):
                f[campo] = float(f[campo])
            resultado.append(f)
        cur.close()
        return resultado

    def salvar_funcao(self, nome, tem_metas, modelo_comissao="padrao", comissao_equipe_percent=0,
                       bonificacao_fixa=0, percentual_bonif_equipe=0, pct_individual_e_geral=0,
                       pct_somente_individual=0, pct_somente_geral=0):
        cur = self._cur()
        cur.execute("""
            INSERT INTO funcoes (nome, tem_metas, modelo_comissao, comissao_equipe_percent, bonificacao_fixa,
                                  percentual_bonif_equipe, pct_individual_e_geral, pct_somente_individual, pct_somente_geral)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (nome) DO UPDATE SET
                tem_metas = EXCLUDED.tem_metas,
                modelo_comissao = EXCLUDED.modelo_comissao,
                comissao_equipe_percent = EXCLUDED.comissao_equipe_percent,
                bonificacao_fixa = EXCLUDED.bonificacao_fixa,
                percentual_bonif_equipe = EXCLUDED.percentual_bonif_equipe,
                pct_individual_e_geral = EXCLUDED.pct_individual_e_geral,
                pct_somente_individual = EXCLUDED.pct_somente_individual,
                pct_somente_geral = EXCLUDED.pct_somente_geral
        """, (nome, bool(tem_metas), modelo_comissao, comissao_equipe_percent, bonificacao_fixa,
              percentual_bonif_equipe, pct_individual_e_geral, pct_somente_individual, pct_somente_geral))
        self.conn.commit()
        cur.close()

    def excluir_funcao(self, nome):
        cur = self._cur()
        cur.execute("DELETE FROM funcoes WHERE nome=%s", (nome,))
        self.conn.commit()
        cur.close()

    # ================= Empresas =================
    def listar_empresas(self):
        cur = self._cur()
        cur.execute("SELECT nome FROM empresas ORDER BY nome")
        resultado = [{"nome": r["nome"]} for r in cur.fetchall()]
        cur.close()
        return resultado

    def salvar_empresa(self, nome):
        cur = self._cur()
        cur.execute("INSERT INTO empresas (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING", (nome,))
        self.conn.commit()
        cur.close()

    def excluir_empresa(self, nome):
        cur = self._cur()
        cur.execute("DELETE FROM empresas WHERE nome=%s", (nome,))
        self.conn.commit()
        cur.close()

    # ================= Estabelecimentos (tipos) =================
    def listar_estabelecimentos(self):
        cur = self._cur()
        cur.execute("SELECT nome, modo_calculo FROM estabelecimentos ORDER BY nome")
        resultado = [{"nome": r["nome"], "modo_calculo": r["modo_calculo"]} for r in cur.fetchall()]
        cur.close()
        return resultado

    def salvar_estabelecimento(self, nome, modo_calculo="padrao"):
        cur = self._cur()
        cur.execute("""
            INSERT INTO estabelecimentos (nome, modo_calculo) VALUES (%s,%s)
            ON CONFLICT (nome) DO UPDATE SET modo_calculo = EXCLUDED.modo_calculo
        """, (nome, modo_calculo))
        self.conn.commit()
        cur.close()

    # ================= Funcionários =================
    def listar_funcionarios(self):
        cur = self._cur()
        cur.execute("SELECT * FROM funcionarios ORDER BY nome")
        funcionarios = []
        for r in cur.fetchall():
            f = dict(r)
            f["recebe_bonif_equipe"] = bool(f["recebe_bonif_equipe"])
            f["enviar_contabil"] = bool(f["enviar_contabil"])
            f["salario_base"] = float(f["salario_base"])
            f["vale_alimentacao"] = float(f["vale_alimentacao"])
            f["comissao_percent"] = float(f["comissao_percent"])
            f["metas"] = self._listar_metas_individuais(f["id"])
            funcionarios.append(f)
        cur.close()
        return funcionarios

    def _listar_metas_individuais(self, funcionario_id):
        cur = self._cur()
        cur.execute(
            "SELECT nivel, valor_meta, bonificacao FROM metas_individuais WHERE funcionario_id=%s ORDER BY nivel",
            (funcionario_id,)
        )
        resultado = [{"nivel": r["nivel"], "valor_meta": float(r["valor_meta"]),
                      "bonificacao": float(r["bonificacao"])} for r in cur.fetchall()]
        cur.close()
        return resultado

    def salvar_funcionario(self, dados, funcionario_id=None):
        """dados: dict com codigo, nome, funcao, empresa, estabelecimento,
        salario_base, vale_alimentacao, comissao_percent,
        recebe_bonif_equipe, enviar_contabil, metas: [{nivel,valor_meta,bonificacao}]"""
        cur = self._cur()
        campos = (
            dados.get("codigo", ""), dados["nome"], dados["funcao"],
            dados.get("empresa"), dados.get("estabelecimento"),
            dados["salario_base"], dados["vale_alimentacao"], dados["comissao_percent"],
            bool(dados.get("recebe_bonif_equipe", True)), bool(dados.get("enviar_contabil", True)),
        )
        if funcionario_id:
            cur.execute("""
                UPDATE funcionarios SET codigo=%s, nome=%s, funcao=%s, empresa=%s, estabelecimento=%s,
                       salario_base=%s, vale_alimentacao=%s, comissao_percent=%s,
                       recebe_bonif_equipe=%s, enviar_contabil=%s
                WHERE id=%s
            """, campos + (funcionario_id,))
            fid = funcionario_id
            cur.execute("DELETE FROM metas_individuais WHERE funcionario_id=%s", (fid,))
        else:
            cur.execute("""
                INSERT INTO funcionarios (codigo, nome, funcao, empresa, estabelecimento,
                    salario_base, vale_alimentacao, comissao_percent, recebe_bonif_equipe, enviar_contabil)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, campos)
            fid = cur.fetchone()["id"]

        for m in dados.get("metas", []):
            cur.execute(
                "INSERT INTO metas_individuais (funcionario_id, nivel, valor_meta, bonificacao) VALUES (%s,%s,%s,%s)",
                (fid, m["nivel"], m["valor_meta"], m["bonificacao"])
            )
        self.conn.commit()
        cur.close()
        return fid

    def excluir_funcionario(self, funcionario_id):
        cur = self._cur()
        cur.execute("DELETE FROM funcionarios WHERE id=%s", (funcionario_id,))
        self.conn.commit()
        cur.close()

    # ================= Metas de equipe (por loja+setor) =================
    def listar_metas_equipe(self):
        cur = self._cur()
        cur.execute(
            "SELECT empresa, estabelecimento, nivel, valor_meta, bonificacao FROM metas_equipe "
            "ORDER BY empresa, estabelecimento, nivel"
        )
        agrupado = {}
        for r in cur.fetchall():
            chave = (r["empresa"], r["estabelecimento"])
            agrupado.setdefault(chave, {"empresa": r["empresa"], "estabelecimento": r["estabelecimento"], "tiers": []})
            agrupado[chave]["tiers"].append({
                "nivel": r["nivel"], "valor_meta": float(r["valor_meta"]), "bonificacao": float(r["bonificacao"])
            })
        cur.close()
        return list(agrupado.values())

    def salvar_metas_equipe(self, empresa, estabelecimento, tiers):
        """Substitui por completo os níveis configurados para essa loja+setor."""
        cur = self._cur()
        cur.execute("DELETE FROM metas_equipe WHERE empresa=%s AND estabelecimento=%s", (empresa, estabelecimento))
        for t in tiers:
            cur.execute(
                "INSERT INTO metas_equipe (empresa, estabelecimento, nivel, valor_meta, bonificacao) "
                "VALUES (%s,%s,%s,%s,%s)",
                (empresa, estabelecimento, t["nivel"], t["valor_meta"], t["bonificacao"])
            )
        self.conn.commit()
        cur.close()

    # ================= Fechamentos (por mês + loja + setor) =================
    def listar_fechamentos(self):
        """Devolve o dict aninhado: {mes: {(empresa,estabelecimento): {"vendas":{...}, "criado_em":...}}}"""
        fechamentos = {}
        cur = self._cur()
        cur.execute("SELECT * FROM fechamentos")
        registros = cur.fetchall()
        for r in registros:
            vendas_cur = self._cur()
            vendas_cur.execute(
                "SELECT funcionario_id, vendido, devolucoes FROM fechamento_vendas WHERE fechamento_id=%s",
                (r["id"],)
            )
            vendas = {v["funcionario_id"]: {"vendido": float(v["vendido"]), "devolucoes": float(v["devolucoes"])}
                      for v in vendas_cur.fetchall()}
            vendas_cur.close()
            fechamentos.setdefault(r["mes"], {})[(r["empresa"], r["estabelecimento"])] = {
                "vendas": vendas, "criado_em": r["criado_em"],
            }
        cur.close()
        return fechamentos

    def salvar_fechamento(self, mes, empresa, estabelecimento, vendas_map, criado_em):
        cur = self._cur()
        cur.execute("SELECT id FROM fechamentos WHERE mes=%s AND empresa=%s AND estabelecimento=%s",
                    (mes, empresa, estabelecimento))
        row = cur.fetchone()
        if row:
            fechamento_id = row["id"]
            cur.execute("UPDATE fechamentos SET criado_em=%s WHERE id=%s", (criado_em, fechamento_id))
            cur.execute("DELETE FROM fechamento_vendas WHERE fechamento_id=%s", (fechamento_id,))
        else:
            cur.execute(
                "INSERT INTO fechamentos (mes, empresa, estabelecimento, criado_em) VALUES (%s,%s,%s,%s) RETURNING id",
                (mes, empresa, estabelecimento, criado_em)
            )
            fechamento_id = cur.fetchone()["id"]

        for funcionario_id, v in vendas_map.items():
            cur.execute(
                "INSERT INTO fechamento_vendas (fechamento_id, funcionario_id, vendido, devolucoes) "
                "VALUES (%s,%s,%s,%s)",
                (fechamento_id, funcionario_id, v.get("vendido", 0), v.get("devolucoes", 0))
            )
        self.conn.commit()
        cur.close()
        return fechamento_id

    def excluir_fechamento(self, mes, empresa, estabelecimento):
        cur = self._cur()
        cur.execute("DELETE FROM fechamentos WHERE mes=%s AND empresa=%s AND estabelecimento=%s",
                    (mes, empresa, estabelecimento))
        self.conn.commit()
        cur.close()

    def close(self):
        self.conn.close()