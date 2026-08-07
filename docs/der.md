# Diagrama de Entidade-Relacionamento (DER) — Painel de Comissões

Baseado no schema real do PostgreSQL (ver `database.py`). As tabelas
`funcoes`, `empresas` e `estabelecimentos` funcionam como **listas de
valores válidos**: não têm chave estrangeira física ligando a
`funcionarios` (o campo é só `TEXT`), mas a aplicação sempre valida
contra elas antes de gravar — por isso aparecem ligadas no diagrama
como relação lógica.

## Diagrama

```mermaid
erDiagram
    FUNCOES {
        text nome PK
        boolean tem_metas
    }

    EMPRESAS {
        text nome PK
    }

    ESTABELECIMENTOS {
        text nome PK
    }

    FUNCIONARIOS {
        serial id PK
        text codigo
        text nome
        text funcao FK
        text empresa FK
        text estabelecimento FK
        numeric salario_base
        numeric vale_alimentacao
        numeric comissao_percent
        boolean recebe_bonif_equipe
        boolean enviar_contabil
    }

    METAS_INDIVIDUAIS {
        serial id PK
        integer funcionario_id FK
        integer nivel
        numeric valor_meta
        numeric bonificacao
    }

    METAS_EQUIPE {
        serial id PK
        text empresa FK
        text estabelecimento FK
        integer nivel
        numeric valor_meta
        numeric bonificacao
    }

    FECHAMENTOS {
        serial id PK
        text mes
        text empresa FK
        text estabelecimento FK
        text criado_em
    }

    FECHAMENTO_VENDAS {
        integer fechamento_id PK,FK
        integer funcionario_id PK,FK
        numeric vendido
        numeric devolucoes
    }

    FUNCOES ||--o{ FUNCIONARIOS : "classifica"
    EMPRESAS ||--o{ FUNCIONARIOS : "lota em"
    ESTABELECIMENTOS ||--o{ FUNCIONARIOS : "lota em"
    FUNCIONARIOS ||--o{ METAS_INDIVIDUAIS : "possui níveis"
    EMPRESAS ||--o{ METAS_EQUIPE : "define metas em"
    ESTABELECIMENTOS ||--o{ METAS_EQUIPE : "define metas em"
    EMPRESAS ||--o{ FECHAMENTOS : "fecha mês em"
    ESTABELECIMENTOS ||--o{ FECHAMENTOS : "fecha mês em"
    FECHAMENTOS ||--o{ FECHAMENTO_VENDAS : "registra vendas"
    FUNCIONARIOS ||--o{ FECHAMENTO_VENDAS : "vendeu em"
```

## Descrição das entidades

| Tabela              | Chave primária                    | O que representa                                                                                                                                                                                      |
| ------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `funcoes`           | `nome`                            | Cargos/funções cadastráveis (ex: Vendedor, Caixa). `tem_metas` decide se quem tem essa função ganha comissão e pode ter metas individuais.                                                            |
| `empresas`          | `nome`                            | Lojas/filiais cadastradas.                                                                                                                                                                            |
| `estabelecimentos`  | `nome`                            | Tipos de setor (ex: Oficina, Autopeças).                                                                                                                                                              |
| `funcionarios`      | `id`                              | Cadastro de cada funcionário, incluindo a que empresa/setor ele pertence "de origem" — é esse vínculo que define de onde vem o bônus de equipe dele.                                                  |
| `metas_individuais` | `id`                              | Níveis de meta individual de um funcionário específico (1‑N por funcionário).                                                                                                                         |
| `metas_equipe`      | `id`                              | Níveis de meta coletiva configurados por combinação de loja + setor (`UNIQUE(empresa, estabelecimento, nivel)`).                                                                                      |
| `fechamentos`       | `id`                              | Um fechamento mensal de UM setor específico (`UNIQUE(mes, empresa, estabelecimento)`) — é a unidade de preenchimento em Cálculo Mensal.                                                               |
| `fechamento_vendas` | `(fechamento_id, funcionario_id)` | Quanto cada funcionário vendeu/devolveu dentro de um fechamento de setor específico. Um funcionário pode aparecer em fechamentos de setores diferentes no mesmo mês (o caso do "vendedor convidado"). |

## Regras importantes que não aparecem no diagrama

- **Um funcionário pode ter vendas em `fechamento_vendas` de setores
  diferentes do seu setor de origem** (funcionalidade de "convidado") —
  isso é o que permite alguém da Oficina vender na Autopeças sem
  perder o vínculo de bônus com a Oficina.
- A **folha consolidada do mês** (usada nos relatórios e impressões)
  não é uma tabela — é calculada em tempo real por `logic.py`,
  juntando todos os `fechamentos` + `fechamento_vendas` de um mês com
  os dados de `funcionarios` e `metas_equipe`.
