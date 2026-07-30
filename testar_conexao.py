"""
testar_conexao.py
Roda este arquivo sozinho (python testar_conexao.py) pra confirmar
que este computador consegue se conectar no PostgreSQL, ANTES de
abrir o programa inteiro. Ajuda a isolar problema de rede/senha de
problema no programa em si.
"""
from config import carregar_config

print("Lendo config.json...")
cfg = carregar_config()
print(f"  host={cfg['host']}  port={cfg['port']}  dbname={cfg['dbname']}  user={cfg['user']}")

print("\nTentando conectar...")
try:
    import psycopg2
    conn = psycopg2.connect(
        host=cfg["host"], port=cfg["port"], dbname=cfg["dbname"],
        user=cfg["user"], password=cfg["password"],
        connect_timeout=5,
        client_encoding="UTF8",
    )
    cur = conn.cursor()
    cur.execute("SELECT version();")
    versao = cur.fetchone()[0]
    conn.close()
    print("\n✅ Conectou com sucesso!")
    print(f"Versão do PostgreSQL no servidor: {versao}")
except ModuleNotFoundError:
    print("\n❌ Falta instalar a biblioteca: pip install psycopg2-binary")
except UnicodeDecodeError:
    print("\n❌ A conexão falhou e o PostgreSQL respondeu com uma mensagem de erro")
    print("   que não pôde ser lida (provavelmente em português, com acento).")
    print("   Isso quase sempre significa: senha errada, host/porta errados,")
    print("   ou o usuário/banco não existe no servidor. Confira esses dados.")
except Exception as e:
    print(f"\n❌ Não foi possível conectar: {e}")
    print("\nChecklist:")
    print("  1. O PostgreSQL está rodando no computador principal?")
    print("  2. O host/porta em config.json estão corretos (IP do computador principal)?")
    print("  3. O PostgreSQL está configurado para aceitar conexões da rede")
    print("     (postgresql.conf: listen_addresses='*' / pg_hba.conf liberado pra rede local)?")
    print("  4. O Firewall do Windows na máquina principal libera a porta 5432?")
    print("  5. Usuário/senha em config.json estão certos?")