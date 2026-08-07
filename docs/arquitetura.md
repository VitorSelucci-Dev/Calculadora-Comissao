# Arquitetura — Painel de Comissões

## Topologia de implantação (rede local)

Um computador da rede local hospeda o banco de dados; os demais se
conectam nele pela rede. Não existe servidor de aplicação — cada
computador roda uma cópia completa do programa, e todos compartilham
o mesmo PostgreSQL.

```mermaid
graph TB
    subgraph Servidor["Computador Principal (Servidor)"]
        App1[Painel de Comissões .exe]
        PG[(PostgreSQL<br/>banco: comissoes)]
        App1 -->|"localhost:5432"| PG
    end

    subgraph Cliente1["Computador Cliente 1"]
        App2[Painel de Comissões .exe]
    end

    subgraph Cliente2["Computador Cliente 2"]
        App3[Painel de Comissões .exe]
    end

    App2 -->|"TCP 5432<br/>rede local"| PG
    App3 -->|"TCP 5432<br/>rede local"| PG

    style PG fill:#12213D,color:#fff
```

Cada computador guarda localmente um `config.json` com o endereço do
servidor (`host`, `port`, `dbname`, `user`, `password`) — ver
`config.py`. No servidor, `host` é `localhost`; nos clientes, é o IP
do servidor na rede.

## Camadas da aplicação

```mermaid
graph TB
    subgraph Interface["Interface (screens/)"]
        home[home.py]
        func[funcionarios.py]
        metas[metas.py]
        calc[calculo.py]
        rel[relatorio.py]
    end

    main[main.py<br/>janela principal, navegação, estado compartilhado]
    widgets[widgets.py<br/>componentes visuais reutilizáveis]
    logic[logic.py<br/>regras de cálculo puras]
    pdf[pdf_export.py<br/>geração de PDF]
    db[database.py<br/>única camada que fala SQL]
    config[config.py<br/>configuração de conexão]
    pg[(PostgreSQL)]

    main --> Interface
    Interface --> widgets
    Interface --> logic
    Interface --> db
    calc --> pdf
    pdf --> logic
    db --> config
    db --> pg

    style db fill:#0E9E8C,color:#fff
    style logic fill:#E3A73C,color:#000
```

**Princípio central do projeto:** nenhuma tela executa SQL
diretamente — tudo passa por `database.py`. Foi essa separação que
permitiu trocar a persistência de SQLite para PostgreSQL no meio do
desenvolvimento sem alterar nenhuma tela. Da mesma forma, `logic.py`
não conhece a interface gráfica — só recebe dados e devolve números,
o que permite testar as regras de cálculo isoladamente (via script,
sem abrir a janela).

## Fluxo de empacotamento

```mermaid
graph LR
    src[Código-fonte Python] -->|PyInstaller| exe[PainelDeComissoes.exe]
    exe --> iss[instalador.iss<br/>Inno Setup]
    pg_installer[postgresql-installer.exe] --> iss
    ps1[instalar_servidor.ps1] --> iss
    icone[icone.ico] --> iss
    iss -->|compila| setup[PainelDeComissoes_Setup.exe]
```

Ver `README.md` para o passo a passo completo de geração do
instalador.
