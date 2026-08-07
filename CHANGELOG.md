# Changelog — Painel de Comissões

Todas as mudanças notáveis do projeto ficam documentadas aqui. O
formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e o projeto usa [Versionamento Semântico](https://semver.org/lang/pt-BR/)
(`MAJOR.MINOR.PATCH`).

## [2.0.0] — 2026-07

### Adicionado

- **Modelos de comissão configuráveis por função**: além do modelo
  clássico ("Padrão"), agora dá pra configurar Gerência (comissão
  sobre o total da equipe + bônus fixo), Percentual da equipe (bônus
  % sobre o total, se bater a meta) e Auxiliar condicional
  (percentual sobre a própria produção, variando conforme bateu meta
  individual e/ou geral)
- **Modo de cálculo por setor** ("Padrão" ou "Personalizado") — o
  setor decide se usa o cálculo clássico ou os modelos configurados
  por função; o mesmo cargo pode se comportar diferente em setores
  diferentes
- Impressão (relatório completo e simplificado) agora organizada por
  setor, mostrando só quem é daquele setor, com uma nota separada
  para quem apareceu como "vendedor convidado"
- Documentação técnica: casos de uso, DER e arquitetura em `docs/`

### Alterado

- Migração de schema automática no banco (`_migrar_schema`) — roda
  sozinha ao abrir o programa, sem precisar mexer no PostgreSQL na mão

## [1.0.0] — 2026-07

Versão inicial completa do sistema.

### Adicionado

- Cadastro de funcionários com ID, função (customizável), empresa,
  tipo/estabelecimento, salário, vale alimentação, comissão e metas
  individuais em níveis
- Cadastro de múltiplas empresas (filiais) e tipos/estabelecimentos
  (setores)
- Metas de equipe configuráveis por loja + setor
- Cálculo mensal por setor, com suporte a "vendedor convidado" (venda
  em setor diferente do de origem)
- Folha consolidada do mês, somando tudo que cada funcionário vendeu
  em qualquer setor
- Geração de PDF: relatório completo, relatório simplificado (com
  checkbox "Enviar Contábil?") e recibos de vale alimentação
- Relatório dinâmico (tipo tabela dinâmica) com gráficos
- Banco de dados PostgreSQL compartilhado em rede local entre vários
  computadores
- Instalador Windows (Inno Setup) com configuração automática do
  servidor PostgreSQL
