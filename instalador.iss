; instalador.iss
; Script do Inno Setup para o Painel de Comissoes.
;
; ESTRUTURA DE PASTAS ESPERADA (ao lado deste arquivo, antes de compilar):
;   dist\PainelDeComissoes.exe        <- gerado pelo PyInstaller (ver README.md)
;   redist\postgresql-installer.exe   <- baixe em postgresql.org/download/windows
;                                        e renomeie pra esse nome exato
;   instalar_servidor.ps1             <- já está pronto, é só deixar do lado
;
; Depois de compilar (Build > Compile, ou F9), o instalador final sai em
; Output\PainelDeComissoes_Setup.exe
;
; IMPORTANTE: eu não tenho como compilar/testar este script aqui (preciso
; de Windows + Inno Setup instalado) - revise com calma e teste numa
; máquina real antes de distribuir. Ajustes pequenos de caminho/nome de
; serviço podem ser necessários dependendo da versão do PostgreSQL.

#define MyAppName "Painel de Comissoes"
#define MyAppVersion "2.0.0"
#define MyAppExeName "PainelDeComissoes.exe"

[Setup]
AppId={{B8F1E2A4-6C3D-4F5A-9B7E-COMISSOES001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=PainelDeComissoes_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "icone.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "instalar_servidor.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "redist\postgresql-installer.exe"; DestDir: "{app}\redist"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icone.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icone.ico"

[Code]
var
  PaginaTipoInstalacao: TInputOptionWizardPage;
  PaginaServidor: TInputQueryWizardPage;
  PaginaCliente: TInputQueryWizardPage;

function EhServidor(): Boolean;
begin
  Result := PaginaTipoInstalacao.SelectedValueIndex = 0;
end;

function EhAtualizacao(): Boolean;
begin
  Result := PaginaTipoInstalacao.SelectedValueIndex = 2;
end;

procedure InitializeWizard();
begin
  { Pergunta se este computador é o servidor principal, um cliente novo,
    ou se é só pra atualizar uma instalação que já existe aqui }
  PaginaTipoInstalacao := CreateInputOptionPage(wpSelectDir,
    'Tipo de instalação', 'O que você quer fazer?',
    'Escolha uma opção:' + #13#10 +
    '- "Computador principal" instala e configura o banco de dados (PostgreSQL) aqui.' + #13#10 +
    '- "Usar servidor existente" só instala o programa, conectando num banco que já ' +
    'está rodando em outro computador da rede.' + #13#10 +
    '- "Atualizar" só troca os arquivos do programa - NÃO mexe no banco de dados nem ' +
    'no arquivo de configuração (config.json) que já existem aqui. Use essa opção ' +
    'sempre que for só instalar uma versão nova em cima de uma que já funciona.',
    False, False);
  PaginaTipoInstalacao.Add('Este é o computador principal (servidor do banco de dados)');
  PaginaTipoInstalacao.Add('Este computador vai usar um servidor existente na rede');
  PaginaTipoInstalacao.Add('Atualizar uma instalação existente (não mexe no banco de dados)');

  { Se já existe um config.json na pasta de instalação detectada, é bem
    provável que a pessoa só queira atualizar - deixa essa opção pré-selecionada }
  if FileExists(ExpandConstant('{app}') + '\config.json') then
    PaginaTipoInstalacao.SelectedValueIndex := 2
  else
    PaginaTipoInstalacao.SelectedValueIndex := 0;

  { Página exibida só se for o servidor: pede a senha do banco }
  PaginaServidor := CreateInputQueryPage(PaginaTipoInstalacao.ID,
    'Configuração do banco de dados', 'Defina a senha do banco de dados',
    'Essa senha vai ser usada pelo PostgreSQL (inclusive pelo usuário administrador ' +
    '"postgres") e por este programa. Anote ela - os outros computadores da rede vão ' +
    'precisar dela também. Se este computador já tiver um PostgreSQL instalado antes, ' +
    'use a MESMA senha que já foi definida para o usuário "postgres" nele.');
  PaginaServidor.Add('Senha do banco de dados:', True);

  { Página exibida só se NÃO for o servidor: pede o IP e a senha }
  PaginaCliente := CreateInputQueryPage(PaginaTipoInstalacao.ID,
    'Conectar num servidor existente', 'Informe os dados do computador principal',
    'Peça essas informações pra quem configurou o computador principal.');
  PaginaCliente.Add('IP do computador principal (ex: 192.168.0.105):', False);
  PaginaCliente.Add('Senha do banco de dados:', True);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if EhAtualizacao() and ((PageID = PaginaServidor.ID) or (PageID = PaginaCliente.ID)) then
    Result := True
  else if PageID = PaginaServidor.ID then
    Result := not EhServidor()
  else if PageID = PaginaCliente.ID then
    Result := EhServidor();
end;

function ObterIPLocalPadrao(): String;
begin
  { Deixa em branco - a pessoa preenche o IP do servidor manualmente }
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  SenhaBanco, IPServidor, ComandoPS, ConfigJson: String;
begin
  if CurStep = ssPostInstall then
  begin
    if EhAtualizacao() then
    begin
      { Só os arquivos do programa foram trocados pela seção [Files].
        Não mexe no config.json nem no banco de dados. }
      MsgBox('Atualização concluída. Seus dados e configurações de conexão foram mantidos.',
             mbInformation, MB_OK);
    end
    else if EhServidor() then
    begin
      SenhaBanco := PaginaServidor.Values[0];

      WizardForm.StatusLabel.Caption := 'Configurando o servidor de banco de dados (pode levar alguns minutos)...';

      ComandoPS := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}') + '\instalar_servidor.ps1" ' +
        '-PgInstalador "' + ExpandConstant('{app}') + '\redist\postgresql-installer.exe" ' +
        '-SenhaBanco "' + SenhaBanco + '" ' +
        '-PastaApp "' + ExpandConstant('{app}') + '"';

      if not Exec('powershell.exe', ComandoPS, '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
        MsgBox('Não foi possível rodar o script de configuração do servidor. ' +
               'Você pode rodá-lo manualmente depois: ' + ExpandConstant('{app}') + '\instalar_servidor.ps1',
               mbError, MB_OK)
      else if ResultCode <> 0 then
        MsgBox('O script de configuração do servidor terminou com um aviso/erro (código ' + IntToStr(ResultCode) + '). ' +
               'Confira a janela do PowerShell que abriu, ou rode manualmente depois.',
               mbInformation, MB_OK);
    end
    else
    begin
      IPServidor := PaginaCliente.Values[0];
      SenhaBanco := PaginaCliente.Values[1];

      ConfigJson := '{' + #13#10 +
        '  "host": "' + IPServidor + '",' + #13#10 +
        '  "port": 5432,' + #13#10 +
        '  "dbname": "comissoes",' + #13#10 +
        '  "user": "comissoes_app",' + #13#10 +
        '  "password": "' + SenhaBanco + '"' + #13#10 +
        '}';
      SaveStringToFile(ExpandConstant('{app}') + '\config.json', ConfigJson, False);
    end;
  end;
end;

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir o Painel de Comissões agora"; Flags: nowait postinstall skipifsilent
