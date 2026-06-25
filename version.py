# version.py — Controlo de versão do Sistema de Gestão de Documentos DNE/MIREME
# Actualizar PATCH a cada correcção/melhoria
# Actualizar MINOR a cada conjunto de novas funcionalidades
# Actualizar MAJOR a cada versão com mudanças estruturais (após V1.0.10 -> V2.0.0)

MAJOR = 1
MINOR = 0
PATCH = 31

VERSION = f"V{MAJOR}.{MINOR}.{PATCH}"
VERSION_FULL = f"Versão {MAJOR}.{MINOR}.{PATCH}"

HISTORICO = [
    ("V1.0.0", "2026-06-03", "Versão inicial — Recebidos, Enviados, Reuniões, Contactos, Relatório, Configurações"),
    ("V1.0.1", "2026-06-04", "ComboBox Despacho (Directores), Endereçado A e Técnico dos Contactos"),
    ("V1.0.2", "2026-06-04", "Zoom Ctrl+scroll (primeira implementação)"),
    ("V1.0.3", "2026-06-05", "Zoom corrigido com ctk.set_widget_scaling + Ctrl+0 para repor"),
    ("V1.0.4", "2026-06-05", "Extracção automática de dados ao anexar PDF/DOCX"),
    ("V1.0.5", "2026-06-05", "Correcção bundling python-docx no executável"),
    ("V1.0.6", "2026-06-05", "Correcção erro astropy — spec file com exclusões + UPX desactivado"),
    ("V1.0.7", "2026-06-06", "Melhorias globais: calendário, abrir ficheiro, imprimir, menu contexto, filtro datas, SMTP, ajuda F1"),
    ("V1.0.8", "2026-06-06", "Correcção erro argumento tooltip_text no CTkButton"),
    ("V1.0.9", "2026-06-06", "Leitura DOCX sem python-docx — usa zipfile+xml built-in, resolve erro biblioteca nao disponivel"),
    ("V1.0.10", "2026-06-10", "Campo 'Endereçado A' renomeado para 'Ao Departamento' com lista fixa de departamentos"),
    ("V1.0.11", "2026-06-11", "Removida reposição automática de documentos recebidos de exemplo ao iniciar com a lista vazia"),
    ("V1.0.12", "2026-06-11", "Reuniões: colunas Hora e Local separadas, cores de status (verde/vermelho/amarelo), "
                              "ocultação de alertas de reuniões já encerradas e horário de agendamento restrito a 07:30-18:00"),
    ("V1.0.13", "2026-06-12", "Dados (base de dados, configuração e backups) movidos para a pasta persistente "
                              "%LOCALAPPDATA%\\GestaoDocumentosDNE, fora da pasta de instalação — passam a sobreviver "
                              "a futuras reconstruções/reinstalações do programa"),
    ("V1.0.14", "2026-06-12", "Configurações: novos botões para abrir a pasta de dados e a pasta de backups, "
                              "indicação do local onde os dados são guardados, e número de versão correcto nos créditos"),
    ("V1.0.15", "2026-06-12", "Relatório: novo botão 'Exportar PDF' que gera um relatório oficial em PDF com "
                              "indicadores, desempenho por departamento, gráfico e principais remetentes"),
    ("V1.0.16", "2026-06-12", "Barra lateral: indicador junto a 'Reuniões' com o número de reuniões "
                              "de hoje ainda por realizar ou em curso, actualizado automaticamente"),
    ("V1.0.17", "2026-06-12", "Correcção do nome 'Dep. de Planeamento Energético' (estava mal escrito) "
                              "na lista de departamentos e nos registos existentes; confirmação de "
                              "eliminação passa a mostrar o nome/assunto em Enviados, Reuniões e Contactos; "
                              "aviso ao guardar um nº de documento já existente em Recebidos e Enviados; "
                              "novo filtro 'Preparado Por' em Enviados"),
    ("V1.0.18", "2026-06-12", "Limpeza interna de código (funções de data centralizadas, remoção de "
                              "importação não usada) e validação do formato dos emails antes de enviar"),
    ("V1.0.19", "2026-06-15", "Menu de contexto (botão direito) com Cortar/Copiar/Colar/Seleccionar Tudo "
                              "em todos os campos de texto da aplicação"),
    ("V1.0.20", "2026-06-15", "Aviso de alterações não guardadas ao fechar um formulário, atalho "
                              "Ctrl+S para guardar e validação para impedir Data de Resposta anterior "
                              "à Data de Recepção em Documentos Recebidos"),
    ("V1.0.21", "2026-06-15", "Relatório: tabela de Desempenho por Departamento com cores "
                              "indicativas da Taxa de Cumprimento (verde/laranja/vermelho) e novo "
                              "gráfico de ranking de cumprimento por departamento com linha de meta (80%)"),
    ("V1.0.22", "2026-06-16", "Janela Enviar por Email: pré-preenchimento automático de servidor SMTP, "
                              "email remetente e senha a partir das Configurações; histórico de destinatários "
                              "com autocomplete — os endereços usados anteriormente são sugeridos ao digitar"),
    ("V1.0.23", "2026-06-16", "Imprimir: o botão Imprimir abre uma janela de selecção de impressora "
                              "que lista todas as impressoras disponíveis na rede, permitindo escolher "
                              "a destino antes de enviar o documento"),
    ("V1.0.24", "2026-06-16", "Correcção da extracção automática de dados de PDF: "
                              "bibliotecas pdfplumber e PyMuPDF agora incluídas no executável; "
                              "padrões de Nº Documento alargados para formatos AFREC/AFD/internacionais "
                              "(ex: AFREC/L/MS/036.26); siglas de proveniência e cargos de remetente "
                              "internacionais adicionados"),
    ("V1.0.25", "2026-06-16", "Correcção do OCR: PIL (Pillow) e pytesseract agora correctamente "
                              "incluídos no executável via collect_all; erros de OCR passam a ser "
                              "mostrados ao utilizador em vez de falharem silenciosamente"),
    ("V1.0.26", "2026-06-17", "Melhorias gerais: atalhos Ctrl+1-6 para navegação rápida entre secções; "
                              "backup automático ao iniciar (protege contra falhas/crashes); "
                              "badge de documentos Fora do Prazo na barra lateral; "
                              "barra de estado com Recebidos, Respondidos e Fora do Prazo; "
                              "memória da última secção activa — reabre onde ficou ao fechar"),
    ("V1.0.27", "2026-06-18", "Reuniões: nova opção 'Cancelada' no formulário de edição — "
                              "reunião cancelada fica a cinzento na tabela; "
                              "botão 'Copiar Tudo' nos formulários de Reuniões, Documentos Recebidos "
                              "e Documentos Enviados para copiar todo o conteúdo com um clique"),
    ("V1.0.28", "2026-06-18", "Botão 'Colar Tudo' nos três formulários: analisa o conteúdo copiado "
                              "e preenche automaticamente todos os campos; "
                              "novo gráfico interactivo de Desempenho por Departamento no Relatório "
                              "com selector de tipo (Barras Agrupadas, Barras Empilhadas, "
                              "Pizza, Rosca, Radar)"),
    ("V1.0.29", "2026-06-19", "Correcção dos gráficos no executável: DLLs de que o Pillow depende "
                              "(tiff.dll, openjp2.dll, zlib.dll, freetype.dll, lcms2.dll, libwebp.dll) "
                              "passam a ser incluídas no bundle — resolve o erro "
                              "'DLL load failed while importing _imaging'"),
    ("V1.0.31", "2026-06-21", "14 melhorias: sugestão automática de Nº Documento; botão Duplicar "
                              "em Recebidos e Enviados; duplo clique no calendário cria reunião; "
                              "pesquisa inclui campo Observação; cor laranja para documentos a "
                              "vencer; templates de assunto (💡); gráfico de evolução mensal e "
                              "tabela de desempenho por técnico no Relatório; Restaurar Backup, "
                              "Exportar Tudo (4 folhas), Optimizar BD e opção de dias úteis nas "
                              "Configurações; aviso de pendentes ao fechar; tema automático por hora"),
    ("V1.0.30", "2026-06-21", "Autocomplete nos formulários de Documentos Recebidos e Enviados: "
                              "Proveniência, Nome do Remetente, Cargo do Remetente (Recebidos) e "
                              "Nome do Destinatário, Cargo do Destinatário, Instituição (Enviados) "
                              "sugerem automaticamente valores previamente introduzidos à medida "
                              "que o utilizador digita — navegação com ↓/↑, selecção com Enter ou clique"),
]

