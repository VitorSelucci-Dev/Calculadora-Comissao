"""
config.py
Configuração de conexão com o banco de dados PostgreSQL compartilhado.

Guarda tudo em config.json, ao lado do main.py (ou do .exe). Cada
computador tem seu próprio config.json, apontando pro mesmo servidor
(o "computador principal" onde o PostgreSQL está instalado). Assim,
não precisa mexer em nenhum código pra apontar pra outro servidor -
só editar esse arquivo.
"""
import json
import os
import sys

PADRAO = {
    "host": "localhost",
    "port": 5432,
    "dbname": "comissoes",
    "user": "comissoes_app",
    "password": "troque_esta_senha",
}


def _caminho_config():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base, "config.json")


def carregar_config():
    """Lê o config.json. Se ainda não existir, cria um com valores
    padrão (apontando pra localhost) pra você editar depois.

    Tenta ler como UTF-8 primeiro; se falhar (ex: o arquivo foi escrito
    pelo instalador em ANSI/Windows-1252, o que acontece quando a senha
    tem acento), tenta de novo como CP1252 antes de desistir."""
    caminho = _caminho_config()
    if not os.path.exists(caminho):
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(PADRAO, f, indent=2, ensure_ascii=False)
        return dict(PADRAO)

    with open(caminho, "rb") as f:
        bruto = f.read()
    try:
        texto = bruto.decode("utf-8")
    except UnicodeDecodeError:
        texto = bruto.decode("cp1252")

    cfg = json.loads(texto)
    completo = dict(PADRAO)
    completo.update(cfg)
    return completo