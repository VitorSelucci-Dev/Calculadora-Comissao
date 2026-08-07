# Painel de Comissões

Aplicação desktop para Windows que calcula comissões e bonificações de funcionários com base em metas — individuais e de equipe — por loja e setor, com banco de dados compartilhado em rede local entre vários computadores.

Feito para negócios com mais de uma filial e/ou mais de um setor por loja (ex: uma oficina e uma loja de autopeças na mesma matriz), onde cada setor tem sua própria meta coletiva, mas a folha final soma tudo que cada funcionário vendeu no mês, em qualquer setor.

---

## Índice

- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Como funciona o cálculo](#como-funciona-o-cálculo)
- [Rodando em modo de desenvolvimento](#rodando-em-modo-de-desenvolvimento)
- [Banco de dados compartilhado (PostgreSQL)](#banco-de-dados-compartilhado-postgresql)
- [Gerando o instalador Windows](#gerando-o-instalador-windows)
- [Solução de problemas](#solução-de-problemas)

---

## Funcionalidades

**Funcionários**

- Cadastro com ID, nome, função (customizável — cada função diz se tem metas/comissão ou não), empresa (loja), tipo/estabelecimento (setor), salário base, vale alimentação e comissão sobre vendas
- Metas individuais em níveis (quantos você quiser, adicionar remover livremente), cada nível com sua própria bonificação
- Checkbox **"Recebe bonificação de equipe"** — permite excluir um funcionário específico do bônus coletivo do setor dele
- Checkbox **"Enviar Contábil?"** — controla quem aparece no relatório simplificado de impressão

**Empresas e setores**

- Cadastro de múltiplas empresas/filiais (menu "⚙ Configurações")
- Cadastro de tipos/estabelecimentos (ex: Oficina, Autopeças) — cada combinação de loja + setor tem sua própria meta de equipe

**Metas & Bonificações**

- Configuração de níveis de meta coletiva por **loja + setor** especificamente (não é uma meta única pra empresa toda)

**Cálculo Mensal**

- Preenchimento por **setor**: escolhe loja, setor e mês, e lança o valor vendido (e devoluções) de cada vendedor daquele setor
- Um funcionário pode ser "convidado" no fechamento de outro setor (ex: alguém da Oficina que vendeu na Autopeças) — a venda conta no total daquele setor, mas o bônus de equipe dele continua vindo do setor de origem
- **Folha completa do mês**: consolida todos os setores fechados naquele mês e calcula o total a receber de cada funcionário (a comissão e a meta individual consideram tudo que a pessoa vendeu no mês, em qualquer setor)
- Impressão em PDF: relatório completo, recibos de vale alimentação (compactos, vários por folha) e um relatório simplificado por loja/setor (nome, comissão e bonificações), respeitando quem está marcado para não entrar no contábil

**Relatório**

- Tabela dinâmica: escolha o que vai nas linhas e nas colunas (Mês,
  Loja, Setor, Loja+Setor, Funcionário), qual métrica comparar, e
  filtros de recorte
- Visualização em gráfico (linhas, barras ou barras agrupadas,
  dependendo da comparação escolhida)

**Banco de dados**

- PostgreSQL compartilhado na rede local — vários computadores acessam
  os mesmos dados ao mesmo tempo

---

## Tecnologias

| Camada            | Tecnologia                                                                         |
| ----------------- | ---------------------------------------------------------------------------------- |
| Interface gráfica | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)                    |
| Banco de dados    | PostgreSQL (via `psycopg2`)                                                        |
| Geração de PDF    | [ReportLab](https://www.reportlab.com/)                                            |
| Gráficos          | [Matplotlib](https://matplotlib.org/) (embutido na janela via `FigureCanvasTkAgg`) |
| Empacotamento     | [PyInstaller](https://pyinstaller.org/) (gera o `.exe`)                            |
| Instalador        | [Inno Setup](https://jrsoftware.org/isinfo.php)                                    |

---

## Estrutura do projeto

```
comissoes_step/
├── main.py                  # Janela principal, menu superior, navegação, popup de Configurações (empresas)
├── database.py               # Camada de persistência (PostgreSQL) - único arquivo que fala SQL
├── config.py                  # Lê/cria o config.json com os dados de conexão do banco
├── logic.py                   # Regras de cálculo puras (metas, comissão, bônus) - sem interface
├── widgets.py                  # Cores, fontes e componentes reutilizáveis (Card, MoneyEntry, MesEntry, TierRow...)
├── pdf_export.py               # Geração dos PDFs (relatório completo, simplificado, recibos)
├── screens/
│   ├── home.py                 # Tela inicial
│   ├── funcionarios.py         # Cadastro de funcionários + popups de função/tipo
│   ├── metas.py                 # Metas de equipe por loja+setor
│   ├── calculo.py                # Cálculo Mensal (preenchimento por setor + folha do mês + impressão)
│   └── relatorio.py              # Relatório dinâmico + gráfico
├── requirements.txt
├── config.json.example          # Modelo do config.json (sem senha real) - este SIM vai pro Git
├── config.json                  # Dados reais de conexão de CADA máquina - NUNCA vai pro Git
├── icone.ico                     # Ícone do aplicativo
├── testar_conexao.py             # Script solto para testar a conexão com o banco antes de abrir o programa
├── instalar_servidor.ps1         # Script que automatiza a instalação/configuração do PostgreSQL
└── instalador.iss                # Script do Inno Setup (gera o instalador .exe)
```

**Por que essa separação:** nenhuma tela fala com o banco de dados
diretamente — todas passam por `database.py`. Isso foi o que permitiu
trocar de SQLite pra PostgreSQL no meio do projeto sem precisar tocar
em nenhuma tela.

---

## Como funciona o cálculo

Ver `logic.py` para a implementação exata. Resumo das regras:

1. **Nível de meta** (individual ou de equipe): sempre vale o **maior
   nível atingido**, nunca cumulativo. Ex: se bateu o nível 3, recebe
   só o bônus do nível 3, não a soma dos três.

2. **Meta de equipe é por loja + setor**: o total vendido de um setor
   é a soma de todos que venderam ali naquele mês (incluindo
   "convidados" de outros setores). Cada setor é comparado só com a
   própria meta configurada.

3. **Bônus de equipe é sempre do setor de ORIGEM do funcionário**, não
   de onde ele eventualmente vendeu como convidado — e só é pago pra
   quem estiver com "Recebe bonificação de equipe" marcado.

4. **Comissão e meta individual** consideram a soma de tudo que o
   funcionário vendeu no mês inteiro, em qualquer setor (não só no
   setor de origem).

5. **Total a receber** = salário base + vale alimentação + comissão +
   bônus individual + bônus de equipe.

---

## Rodando em modo de desenvolvimento

Pré-requisitos: Python 3.10+ e acesso a um PostgreSQL (local ou de
rede — ver seção seguinte).

```bash
pip install -r requirements.txt
cp config.json.example config.json   # depois edite com os dados reais
python testar_conexao.py             # confirma que a conexão funciona
python main.py
```

---

## Banco de dados compartilhado (PostgreSQL)

O sistema foi pensado pra rodar em **rede local**: um computador
("servidor") hospeda o PostgreSQL, e todos os outros ("clientes") se
conectam nele pela rede — assim todo mundo vê o mesmo cadastro e o
mesmo histórico.

### Configuração (`config.json`)

Cada computador tem seu próprio `config.json` (fora do Git):

```json
{
  "host": "192.168.X.X",
  "port": 5432,
  "dbname": "comissoes",
  "user": "comissoes_app",
  "password": "sua_senha"
}
```

- No **servidor**: `host` pode ser `"localhost"`
- Nos **clientes**: `host` é o **IP do servidor** na rede local (não
  o IP do próprio cliente!)

### Configuração manual do servidor (referência)

O `instalar_servidor.ps1` faz tudo isso automaticamente durante a
instalação, mas caso precise fazer manualmente:

```sql
CREATE DATABASE comissoes;
CREATE USER comissoes_app WITH PASSWORD 'sua_senha';
GRANT ALL PRIVILEGES ON DATABASE comissoes TO comissoes_app;
\c comissoes
ALTER SCHEMA public OWNER TO comissoes_app;
ALTER SYSTEM SET lc_messages = 'C';
SELECT pg_reload_conf();
```

`postgresql.conf`: `listen_addresses = '*'`

`pg_hba.conf` (troque pela faixa real da sua rede):

```
host    comissoes    comissoes_app    192.168.X.0/24    scram-sha-256
```

Reinicie o serviço do PostgreSQL depois de editar esses dois arquivos.

### Testando a conexão

Antes de abrir o programa, sempre vale rodar:

```bash
python testar_conexao.py
```

Ele lê o `config.json` e tenta conectar, mostrando um checklist claro
se algo falhar (host errado, firewall, serviço parado, etc.).

---

## Gerando o instalador Windows

**1. Gerar o `.exe` do programa:**

```bat
python -m PyInstaller --noconfirm --onefile --windowed --icon=icone.ico --name "PainelDeComissoes" main.py
```

**2. Montar a pasta antes de compilar o instalador:**

```
projeto\
├── dist\PainelDeComissoes.exe
├── redist\postgresql-installer.exe   ← baixar de postgresql.org e renomear
├── icone.ico
├── instalar_servidor.ps1
├── instalador.iss
```

**3. Compilar:** abra `instalador.iss` no Inno Setup → `Build → Compile`
(F9). O instalador final sai em `Output\PainelDeComissoes_Setup.exe`.

**O que o instalador faz:** pergunta se o computador é o "servidor
principal" (instala e configura o PostgreSQL sozinho, com detecção
automática da faixa de rede) ou se vai "usar um servidor existente"
(só pede o IP do servidor e escreve o `config.json`).

**Importante:** o `redist\postgresql-installer.exe` (~350MB) **nunca**
deve ir pro Git — está no `.gitignore` por ultrapassar o limite de
tamanho de arquivo do GitHub.

---

## Solução de problemas

**"pyinstaller não é reconhecido"** → use `python -m PyInstaller ...`
em vez de `pyinstaller ...` diretamente.

**Erro de conexão com o banco (timeout)** → geralmente é firewall.
Teste com `Test-NetConnection -ComputerName <IP> -Port 5432` no
cliente antes de mais nada.

**"Connection refused"** → o serviço do PostgreSQL não está rodando,
ou a porta está errada. Confira com `sc query postgresql-x64-XX` no
servidor.

**"permissão negada para esquema public"** → falta rodar
`ALTER SCHEMA public OWNER TO comissoes_app;` no banco `comissoes`
(necessário a partir do PostgreSQL 15).

**`UnicodeDecodeError` ao conectar** → o PostgreSQL respondeu com uma
mensagem de erro em português (com acento) que o driver não conseguiu
ler, mascarando o erro real. Rode `ALTER SYSTEM SET lc_messages='C';
SELECT pg_reload_conf();` no servidor pra sempre ver o erro real daqui
pra frente. As causas mais comuns por trás disso: senha errada, ou o
IP do cliente não está liberado no `pg_hba.conf` (confira o log do
Postgres em `...\data\log\` pra confirmar).

**Serviço do PostgreSQL não inicia** → confira o Visualizador de
Eventos do Windows (`eventvwr.msc` → Logs do Windows → Aplicativo) —
o log do próprio Postgres às vezes fica vazio quando o problema
acontece antes dele conseguir escrever nele.

**`config.json` não deixa salvar** → o programa foi instalado em
"Arquivos de Programas" (pasta protegida). Abra o Bloco de Notas
como Administrador antes de editar o arquivo.
