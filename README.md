# Painel de Comissões

Aplicação desktop para cálculo de comissões e bonificações de
funcionários, com base em metas individuais e de equipe.

## Funcionalidades

- Cadastro de funcionários: função, salário base, vale alimentação
  e comissão sobre vendas (para vendedores)
- Metas individuais por vendedor, em 3 níveis, cada um com uma
  bonificação própria
- Metas de equipe (soma das vendas do time), com bonificação paga
  a cada vendedor quando o nível é atingido
- Cálculo automático do fechamento mensal: salário + vale
  alimentação + comissão + bonificações
- Histórico de fechamentos salvos, consultável a qualquer momento

## Tecnologias

- Python
- CustomTkinter (interface gráfica)
- SQLite (persistência local dos dados)

## Como rodar

\`\`\`bash
pip install -r requirements.txt
python main.py
\`\`\`
