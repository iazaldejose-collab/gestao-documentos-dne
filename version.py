# version.py — Controlo de versão do Sistema de Gestão de Documentos DNE/MIREME
# Actualizar PATCH a cada correcção/melhoria
# Actualizar MINOR a cada conjunto de novas funcionalidades
# Actualizar MAJOR a cada versão com mudanças estruturais (após V1.0.10 -> V2.0.0)

MAJOR = 1
MINOR = 0
PATCH = 15

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
]

