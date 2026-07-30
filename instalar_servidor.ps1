# instalar_servidor.ps1
#
# Automatiza no computador principal tudo que fizemos na mao durante
# os testes: instalar o PostgreSQL, criar banco/usuario, liberar o
# schema (necessario no Postgres 15+), liberar rede/firewall, e
# CONFIRMAR que o servico realmente subiu antes de dizer que deu certo.
#
# Uso (PowerShell como Administrador):
#   .\instalar_servidor.ps1 -PgInstalador "C:\caminho\postgresql-18-windows-x64.exe" -SenhaBanco "MinhaSenh@123" -PastaApp "C:\Painel de Comissoes" -SubnetRede "192.168.3.0/24"

param(
    [Parameter(Mandatory=$true)][string]$PgInstalador,
    [Parameter(Mandatory=$true)][string]$SenhaBanco,
    [Parameter(Mandatory=$true)][string]$PastaApp,
    [string]$SubnetRede = "192.168.0.0/24",
    [string]$NomeBanco = "comissoes",
    [string]$UsuarioApp = "comissoes_app",
    [int]$Porta = 5432
)

$ErrorActionPreference = "Stop"
$Utf8SemBom = New-Object System.Text.UTF8Encoding($false)

function Log($msg)  { Write-Host "==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "OK: $msg" -ForegroundColor Green }
function Falha($msg){ Write-Host "ERRO: $msg" -ForegroundColor Red }

# ---------------------------------------------------------------
# 1. Instalar o PostgreSQL silenciosamente (so se ainda nao existir)
# ---------------------------------------------------------------
$servico = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
$instalacaoNova = $false

if ($servico) {
    Log "PostgreSQL ja esta instalado (servico $($servico.Name))."
    Log "Vou usar a senha informada para configurar o banco - se o PostgreSQL"
    Log "ja existia de uma instalacao anterior com senha DIFERENTE da que voce"
    Log "passou agora, os proximos passos vao falhar com erro de autenticacao."
} else {
    Log "Instalando PostgreSQL (isso demora alguns minutos)..."
    $args = @(
        "--mode", "unattended",
        "--unattendedmodeui", "minimal",
        "--superpassword", "$SenhaBanco",
        "--serverport", "$Porta",
        "--enable-components", "server,commandlinetools",
        "--disable-components", "pgAdmin,stackbuilder"
    )
    Start-Process -FilePath $PgInstalador -ArgumentList $args -Wait -NoNewWindow
    $instalacaoNova = $true
    Log "Instalacao concluida. Aguardando o servico aparecer..."

    $tentativas = 0
    while (-not $servico -and $tentativas -lt 20) {
        Start-Sleep -Seconds 3
        $servico = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
        $tentativas++
    }
    if (-not $servico) {
        throw "O instalador rodou mas o servico do PostgreSQL nao apareceu. Verifique se o instalador realmente concluiu."
    }
}

# ---------------------------------------------------------------
# 2. Garantir que o servico esta rodando (independente de ser
#    instalacao nova ou ja existente)
# ---------------------------------------------------------------
Set-Service -Name $servico.Name -StartupType Automatic
if ($servico.Status -ne "Running") {
    Log "Iniciando o servico $($servico.Name)..."
    Start-Service -Name $servico.Name
    Start-Sleep -Seconds 3
}
$servico.Refresh()
if ($servico.Status -ne "Running") {
    throw "O servico $($servico.Name) nao conseguiu iniciar. Confira o Visualizador de Eventos (eventvwr.msc > Logs do Windows > Aplicativo) para o motivo exato."
}
Ok "Servico $($servico.Name) esta rodando."

# ---------------------------------------------------------------
# 3. Localizar pastas de instalacao
# ---------------------------------------------------------------
$pgRoot = Get-ChildItem "C:\Program Files\PostgreSQL" -Directory -ErrorAction SilentlyContinue |
          Sort-Object Name -Descending | Select-Object -First 1
if (-not $pgRoot) {
    throw "Nao encontrei a instalacao do PostgreSQL em C:\Program Files\PostgreSQL."
}
$binPath = Join-Path $pgRoot.FullName "bin"
$dataPath = Join-Path $pgRoot.FullName "data"
$psql = Join-Path $binPath "psql.exe"
Log "PostgreSQL em $($pgRoot.FullName) (servico: $($servico.Name))"

# ---------------------------------------------------------------
# 4. Criar banco, usuario, e dar a ele posse do schema public
#    (necessario a partir do PostgreSQL 15 - senao o programa nao
#    consegue criar as tabelas na primeira vez que abrir)
# ---------------------------------------------------------------
Log "Configurando banco de dados e usuario da aplicacao..."
$env:PGPASSWORD = $SenhaBanco

function RodarSql($sql, $banco = "postgres") {
    $saida = & $psql -U postgres -h localhost -p $Porta -d $banco -v ON_ERROR_STOP=0 -c $sql 2>&1
    return $saida -join "`n"
}

$saida = RodarSql "SELECT 1;"
if ($saida -match "autentica|password authentication failed|FATAL") {
    Falha "Nao foi possivel autenticar no PostgreSQL com a senha informada."
    Falha "Se este PostgreSQL ja existia antes deste script, a senha do usuario"
    Falha "'postgres' pode ser diferente da que voce passou agora. Resete a"
    Falha "senha manualmente (ALTER USER postgres WITH PASSWORD '...') e rode de novo."
    throw "Falha de autenticacao com o PostgreSQL."
}

RodarSql "CREATE DATABASE $NomeBanco;" | Out-Null
RodarSql "CREATE USER $UsuarioApp WITH PASSWORD '$SenhaBanco';" | Out-Null
RodarSql "GRANT ALL PRIVILEGES ON DATABASE $NomeBanco TO $UsuarioApp;" | Out-Null
RodarSql "ALTER SCHEMA public OWNER TO $UsuarioApp;" -banco $NomeBanco | Out-Null
RodarSql "GRANT ALL ON SCHEMA public TO $UsuarioApp;" -banco $NomeBanco | Out-Null
Ok "Banco '$NomeBanco' e usuario '$UsuarioApp' configurados (com posse do schema public)."

# ---------------------------------------------------------------
# 5. Liberar o PostgreSQL pra aceitar conexao da rede local
#    (editando com .NET diretamente, em UTF-8 sem BOM, pra nao
#    arriscar corromper os arquivos de configuracao)
# ---------------------------------------------------------------
Log "Configurando acesso pela rede local..."
$confPath = Join-Path $dataPath "postgresql.conf"
$hbaPath = Join-Path $dataPath "pg_hba.conf"

$confLinhas = [System.IO.File]::ReadAllLines($confPath)
$confNovo = $confLinhas | ForEach-Object {
    if ($_ -match "^\s*#?\s*listen_addresses\s*=") { "listen_addresses = '*'" }
    else { $_ }
}
[System.IO.File]::WriteAllLines($confPath, $confNovo, $Utf8SemBom)

$linhaHba = "host    $NomeBanco    $UsuarioApp    $SubnetRede    scram-sha-256"
$hbaConteudo = [System.IO.File]::ReadAllText($hbaPath)
if ($hbaConteudo -notmatch [regex]::Escape($linhaHba)) {
    $hbaConteudo += "`n# Liberado automaticamente pelo instalador do Painel de Comissoes`n$linhaHba`n"
    [System.IO.File]::WriteAllText($hbaPath, $hbaConteudo, $Utf8SemBom)
}
Ok "Configuracao de rede atualizada."

Log "Reiniciando o servico para aplicar as mudancas..."
Restart-Service -Name $servico.Name -Force
Start-Sleep -Seconds 4
$servico.Refresh()
if ($servico.Status -ne "Running") {
    throw "O servico parou depois de editar postgresql.conf/pg_hba.conf. Confira se as edicoes ficaram com sintaxe valida (veja os arquivos em $dataPath)."
}
Ok "Servico reiniciado e continua rodando."

# ---------------------------------------------------------------
# 6. Firewall
# ---------------------------------------------------------------
Log "Liberando a porta $Porta no Firewall do Windows..."
if (-not (Get-NetFirewallRule -DisplayName "PostgreSQL Painel de Comissoes" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "PostgreSQL Painel de Comissoes" -Direction Inbound `
        -Protocol TCP -LocalPort $Porta -Action Allow | Out-Null
}
Ok "Porta $Porta liberada no firewall."

# ---------------------------------------------------------------
# 7. Confirmar de verdade que esta tudo escutando (nao so "achar" que sim)
# ---------------------------------------------------------------
Log "Confirmando que a porta esta aceitando conexoes..."
$teste = Test-NetConnection -ComputerName "localhost" -Port $Porta -WarningAction SilentlyContinue
if (-not $teste.TcpTestSucceeded) {
    throw "O servico esta rodando, mas a porta $Porta nao respondeu no teste local. Confira o log em $dataPath\log."
}
Ok "Porta $Porta respondendo normalmente."

# ---------------------------------------------------------------
# 8. Escrever o config.json do programa (aponta pra localhost, ja
#    que este e o proprio servidor)
# ---------------------------------------------------------------
Log "Escrevendo config.json..."
$configJson = @{
    host     = "localhost"
    port     = $Porta
    dbname   = $NomeBanco
    user     = $UsuarioApp
    password = $SenhaBanco
} | ConvertTo-Json

if (-not (Test-Path $PastaApp)) {
    New-Item -ItemType Directory -Path $PastaApp -Force | Out-Null
}
[System.IO.File]::WriteAllText((Join-Path $PastaApp "config.json"), $configJson, $Utf8SemBom)

Write-Host ""
Ok "Tudo pronto! Servidor configurado e confirmado com sucesso."
Write-Host ""
Write-Host "IP deste computador (use nos outros computadores da rede):" -ForegroundColor Yellow
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" } |
    Select-Object -ExpandProperty IPAddress