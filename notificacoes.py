# notificacoes.py — Avisos automáticos de prazos por email
#
# Verifica os documentos recebidos pendentes (sem data de resposta) e envia
# automaticamente um email ao técnico responsável quando:
#   • falta 1 dia para o fim do prazo de resposta  → aviso "véspera"
#   • o prazo já foi ultrapassado                  → aviso "vencido"
#
# O email do técnico é obtido da lista de Contactos (correspondência por nome,
# ignorando acentos e maiúsculas). Documentos cujo técnico não tem email nos
# Contactos são resumidos num único email enviado para a própria conta SMTP
# configurada, para que o secretariado tome conhecimento.
#
# Cada aviso é enviado apenas uma vez por documento e por tipo (véspera /
# vencido) — o registo fica em avisos_enviados.json na pasta de dados.

import os
import json
import smtplib
import ssl
import unicodedata
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from utils import get_data_dir, dias_uteis, iso_to_display, data_limite

_REGISTO_PATH = os.path.join(get_data_dir(), 'avisos_enviados.json')

# Estados que não geram avisos (documento tratado/arquivado manualmente)
_ESTADOS_EXCLUIDOS = ('Arquivado', 'Arquivo')


# ────────────────────────────────────────────────────────────── registo em disco
def _load_registo():
    try:
        if os.path.isfile(_REGISTO_PATH):
            with open(_REGISTO_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_registo(registo):
    try:
        with open(_REGISTO_PATH, 'w', encoding='utf-8') as f:
            json.dump(registo, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ────────────────────────────────────────────────────────────── nomes / emails
def _normalizar(nome):
    """Remove acentos, pontuação leve e maiúsculas para comparar nomes."""
    nome = (nome or '').strip().casefold()
    nome = unicodedata.normalize('NFD', nome)
    nome = ''.join(ch for ch in nome if unicodedata.category(ch) != 'Mn')
    return ' '.join(nome.replace('.', ' ').split())


def _email_do_tecnico(tecnico, contactos):
    """Procura o email do técnico na lista de contactos.
    Aceita correspondência exacta ou por contenção (ex: 'Luis Guambe'
    encontra 'Eng. Luis Guambe'), desde que não seja ambígua."""
    alvo = _normalizar(tecnico)
    if not alvo:
        return None
    candidatos = []
    for ct in contactos:
        nome = _normalizar(ct.get('nome'))
        email = (ct.get('email') or '').strip()
        if not nome or not email:
            continue
        if nome == alvo:
            return email
        if alvo in nome or nome in alvo:
            candidatos.append(email)
    return candidatos[0] if len(candidatos) == 1 else None


# ────────────────────────────────────────────────────────────── cálculo de prazos
def _dias_decorridos(data_recepcao_iso, usar_dias_uteis):
    """Dias decorridos desde a recepção até hoje (úteis ou corridos)."""
    if usar_dias_uteis:
        return dias_uteis(data_recepcao_iso, None)
    try:
        d1 = datetime.strptime(data_recepcao_iso, '%Y-%m-%d').date()
        return (date.today() - d1).days
    except Exception:
        return None


def apurar_avisos(db, config):
    """Percorre os documentos pendentes e devolve a lista de avisos devidos
    (ainda não enviados). Cada aviso: dict com doc, tipo ('vespera'/'vencido')
    e dias_restantes."""
    prazo = int(config.get('prazo_padrao', 5) or 5)
    usar_uteis = bool(config.get('dias_uteis', False))
    registo = _load_registo()

    docs = db.get_all_recebidos()
    pendentes = [d for d in docs
                 if not (d.get('data_resposta') or '').strip()
                 and d.get('prazo_status') not in _ESTADOS_EXCLUIDOS
                 and (d.get('data_recepcao') or '').strip()]

    avisos = []
    ids_pendentes = set()
    for d in pendentes:
        ids_pendentes.add(str(d['id']))
        # Data-limite: a específica do documento (prazo_data) ou recepção + padrão
        limite = data_limite(d.get('data_recepcao'), d.get('prazo_data'), prazo, usar_uteis)
        if not limite:
            continue
        try:
            restantes = (date.fromisoformat(limite) - date.today()).days
        except Exception:
            continue
        if restantes == 1:
            tipo = 'vespera'
        elif restantes <= 0:
            tipo = 'vencido'
        else:
            continue
        chave = f"{d['id']}:{tipo}"
        if chave in registo:
            continue  # já avisado
        avisos.append({'doc': d, 'tipo': tipo, 'dias_restantes': restantes})

    # Limpeza: remove do registo avisos de documentos já respondidos/arquivados
    obsoletas = [k for k in registo if k.split(':')[0] not in ids_pendentes]
    if obsoletas:
        for k in obsoletas:
            registo.pop(k, None)
        _save_registo(registo)

    return avisos


# ────────────────────────────────────────────────────────────── envio SMTP
def _enviar_email(config, para, assunto, corpo):
    """Envia um email de texto simples com as credenciais das Configurações.
    Lança excepção em caso de falha."""
    host = (config.get('smtp_server') or '').strip()
    porta = int(str(config.get('smtp_port') or '587').strip())
    remetente = (config.get('smtp_email') or '').strip()
    senha = config.get('smtp_password') or ''

    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = para
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo, 'plain', 'utf-8'))

    context = ssl.create_default_context()
    if porta == 465:
        with smtplib.SMTP_SSL(host, porta, context=context, timeout=30) as server:
            server.ehlo()
            server.login(remetente, senha)
            server.sendmail(remetente, [para], msg.as_string())
    else:
        with smtplib.SMTP(host, porta, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(remetente, senha)
            server.sendmail(remetente, [para], msg.as_string())


def _linha_doc(d, tipo, dias_restantes, usar_uteis):
    unidade = 'dia(s) útil(eis)' if usar_uteis else 'dia(s)'
    if tipo == 'vespera':
        estado = "⚠ o prazo vence amanhã (falta 1 dia)"
    else:
        atraso = abs(dias_restantes)
        estado = ("🔴 prazo vence HOJE" if atraso == 0
                  else f"🔴 prazo vencido há {atraso} {unidade}")
    return (f"  • Doc. {d.get('numero', '?')} — {d.get('assunto', '')}\n"
            f"    Proveniência: {d.get('proveniencia') or '—'}\n"
            f"    Recebido em: {iso_to_display(d.get('data_recepcao'))}   |   {estado}")


def _corpo_email(nome_tecnico, avisos, config):
    prazo = config.get('prazo_padrao', 5)
    usar_uteis = bool(config.get('dias_uteis', False))
    vespera = [a for a in avisos if a['tipo'] == 'vespera']
    vencidos = [a for a in avisos if a['tipo'] == 'vencido']

    linhas = [f"Exmo(a). Sr(a). {nome_tecnico},", "",
              "Serve o presente email para notificar sobre o estado dos prazos de "
              "resposta dos documentos sob sua responsabilidade "
              f"(prazo máximo definido: {prazo} dias{' úteis' if usar_uteis else ''}).", ""]

    if vespera:
        linhas.append(f"DOCUMENTOS COM PRAZO A VENCER AMANHÃ ({len(vespera)}):")
        for a in vespera:
            linhas.append(_linha_doc(a['doc'], a['tipo'], a['dias_restantes'], usar_uteis))
        linhas.append("")
    if vencidos:
        linhas.append(f"DOCUMENTOS COM PRAZO VENCIDO ({len(vencidos)}):")
        for a in vencidos:
            linhas.append(_linha_doc(a['doc'], a['tipo'], a['dias_restantes'], usar_uteis))
        linhas.append("")

    linhas += ["Solicita-se que providencie a resposta com a maior brevidade possível.",
               "",
               "Com os melhores cumprimentos,",
               config.get('utilizador', 'Secretariado') or 'Secretariado',
               "Sistema de Gestão de Documentos — DNE | MIREME",
               "",
               "(Mensagem gerada automaticamente. Após registar a Data de Resposta "
               "no sistema, deixará de receber avisos sobre estes documentos.)"]
    return "\n".join(linhas)


# ────────────────────────────────────────────────────────────── ponto de entrada
def smtp_configurado(config):
    return bool((config.get('smtp_server') or '').strip()
                and (config.get('smtp_email') or '').strip()
                and (config.get('smtp_password') or '').strip())


def processar_notificacoes(db, config):
    """Verifica os prazos e envia os emails devidos. Devolve um resumo:
    {'avisos': n, 'emails': n, 'sem_email': [nomes], 'erro': str|None}.
    Pensado para correr numa thread de fundo — não toca na interface."""
    resumo = {'avisos': 0, 'emails': 0, 'sem_email': [], 'erro': None}

    if not smtp_configurado(config):
        resumo['erro'] = 'SMTP não configurado'
        return resumo

    try:
        avisos = apurar_avisos(db, config)
    except Exception as e:
        resumo['erro'] = f'Falha ao apurar prazos: {e}'
        return resumo

    if not avisos:
        return resumo
    resumo['avisos'] = len(avisos)

    contactos = db.get_all_contactos()

    # Agrupa avisos por técnico
    por_tecnico = {}
    for a in avisos:
        tecnico = (a['doc'].get('tecnico') or '').strip()
        por_tecnico.setdefault(tecnico, []).append(a)

    registo = _load_registo()
    hoje = date.today().isoformat()
    sem_destino = []          # avisos sem email de técnico → resumo interno

    for tecnico, grupo in por_tecnico.items():
        email = _email_do_tecnico(tecnico, contactos) if tecnico else None
        if not email:
            sem_destino.extend(grupo)
            if tecnico:
                resumo['sem_email'].append(tecnico)
            continue
        assunto = "⏰ Aviso de Prazos — Documentos Pendentes (DNE/MIREME)"
        corpo = _corpo_email(tecnico, grupo, config)
        try:
            _enviar_email(config, email, assunto, corpo)
            resumo['emails'] += 1
            for a in grupo:
                registo[f"{a['doc']['id']}:{a['tipo']}"] = hoje
        except Exception as e:
            resumo['erro'] = f'Falha ao enviar para {email}: {e}'

    # Documentos sem email de técnico: um único resumo para a conta configurada
    if sem_destino:
        proprio = (config.get('smtp_email') or '').strip()
        corpo = _corpo_email('Secretariado (documentos sem email de técnico nos Contactos)',
                             sem_destino, config)
        try:
            _enviar_email(config, proprio, "⏰ Aviso de Prazos — Documentos sem técnico associado", corpo)
            resumo['emails'] += 1
            for a in sem_destino:
                registo[f"{a['doc']['id']}:{a['tipo']}"] = hoje
        except Exception as e:
            resumo['erro'] = f'Falha ao enviar resumo interno: {e}'

    _save_registo(registo)
    return resumo
