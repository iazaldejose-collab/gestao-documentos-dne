; ============================================================================
;  Script de instalacao — Sistema de Gestao de Documentos DNE / MIREME
;  Empacota a build ONEDIR (pasta ..\dist\GestaoDocumentos_DNE\ gerada pelo
;  spec da RAIZ GestaoDocumentos_DNE.spec, que inclui as DLLs do Pillow, OCR
;  e todos os dados). Gera um setup.exe unico, pronto a distribuir.
;  Compilar: ISCC.exe instalador.iss  (a partir da pasta GestaoDocumentos\)
; ============================================================================

#define AppName "Sistema de Gestao de Documentos DNE"
#define AppVersion "1.0.44"
#define AppPublisher "Iazalde Jose Jeremias - DNE/MIREME"
#define AppExeName "GestaoDocumentos_DNE.exe"

[Setup]
AppId={{7C3A6F41-9D2E-4B8A-A1F0-DNE2026MIREME}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=mailto:iazaldejose@gmail.com
DefaultDirName={autopf}\GestaoDocumentosDNE
DefaultGroupName=Gestao de Documentos DNE
DisableProgramGroupPage=yes
; Instalacao por utilizador — nao exige privilegios de administrador
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=Installer
OutputBaseFilename=GestaoDocumentosDNE_Setup_v{#AppVersion}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
WizardStyle=modern
; lzma2/normal: bom equilibrio entre tamanho e tempo de compilacao (a pasta
; onedir tem ~633 MB; /max demora demasiado)
Compression=lzma2/normal
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Pasta onedir COMPLETA e verificada (exe + _internal com DLLs Pillow, OCR,
; matplotlib) — gerada pelo spec da RAIZ GestaoDocumentos_DNE.spec
Source: "..\dist\GestaoDocumentos_DNE\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; Guia de instalacao ao lado do programa
Source: "Guia_Instalacao_e_Configuracao.docx"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Menu Iniciar — icone vem do proprio executavel
Name: "{group}\Gestao de Documentos DNE"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Guia de Instalacao e Configuracao"; Filename: "{app}\Guia_Instalacao_e_Configuracao.docx"
Name: "{group}\Desinstalar Gestao de Documentos DNE"; Filename: "{uninstallexe}"
; Ambiente de trabalho (opcional, via Tasks)
Name: "{autodesktop}\Gestao de Documentos DNE"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,Gestao de Documentos DNE}"; Flags: nowait postinstall skipifsilent
