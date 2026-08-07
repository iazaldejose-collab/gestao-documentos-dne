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
#
# Também envia lembretes de REUNIÕES agendadas: um email ao organizador
# (email obtido dos Contactos) na véspera da reunião e no próprio dia.
# Cada lembrete é enviado uma única vez — registo em avisos_reunioes.json.

import os
import json
import smtplib
import ssl
import unicodedata
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from utils import (get_data_dir, dias_uteis, iso_to_display, data_limite,
                   parse_hora_local, get_meeting_datetimes, parece_cifrado)

_REGISTO_PATH = os.path.join(get_data_dir(), 'avisos_enviados.json')
_REGISTO_REUNIOES_PATH = os.path.join(get_data_dir(), 'avisos_reunioes.json')

# Estados que não geram avisos (documento tratado/arquivado manualmente)
_ESTADOS_EXCLUIDOS = ('Arquivado', 'Arquivo')


# ────────────────────────────────────────────────────────────── registo em disco
def _load_registo(path=_REGISTO_PATH):
    try:
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_registo(registo, path=_REGISTO_PATH):
    try:
        with open(path, 'w', encoding='utf-8') as f:
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

    if parece_cifrado(senha):
        raise RuntimeError(
            "A senha de email guardada não pôde ser decifrada nesta conta Windows "
            "ou neste computador. Reintroduza-a em Configurações → Email (SMTP).")

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


# ────────────────────────────────────────────────────────────── reuniões
def apurar_avisos_reunioes(db):
    """Percorre as reuniões agendadas e devolve os lembretes devidos (ainda
    não enviados). Cada lembrete: dict com reuniao e tipo ('vespera'/'hoje').
    Reuniões canceladas ou já terminadas não geram lembrete."""
    registo = _load_registo(_REGISTO_REUNIOES_PATH)
    hoje = date.today()
    avisos = []
    ids_activos = set()

    for r in db.get_all_reunioes():
        if int(r.get('cancelada', 0) or 0):
            continue
        dr = (r.get('data_reuniao') or '').strip()
        try:
            d = date.fromisoformat(dr)
        except Exception:
            continue
        dias = (d - hoje).days
        if dias == 1:
            tipo = 'vespera'
        elif dias == 0:
            # No próprio dia, só lembra reuniões que ainda não terminaram
            _, fim = get_meeting_datetimes(dr, r.get('hora_local', ''))
            if fim is not None and datetime.now() > fim:
                continue
            tipo = 'hoje'
        else:
            continue
        ids_activos.add(str(r['id']))
        chave = f"{r['id']}:{tipo}"
        if chave in registo:
            continue  # já lembrado
        avisos.append({'reuniao': r, 'tipo': tipo})

    # Limpeza: remove do registo lembretes de reuniões já passadas/canceladas
    obsoletas = [k for k in registo if k.split(':')[0] not in ids_activos]
    if obsoletas:
        for k in obsoletas:
            registo.pop(k, None)
        _save_registo(registo, _REGISTO_REUNIOES_PATH)

    return avisos


def _linha_reuniao(a):
    r = a['reuniao']
    hora_inicio, hora_fim, local = parse_hora_local(r.get('hora_local', ''))
    quando = "AMANHÃ" if a['tipo'] == 'vespera' else "HOJE"
    hora_txt = f" às {hora_inicio}" if hora_inicio else ""
    if hora_inicio and hora_fim:
        hora_txt = f" das {hora_inicio} às {hora_fim}"
    linhas = [f"  • {quando}, {iso_to_display(r.get('data_reuniao'))}{hora_txt} — "
              f"{r.get('assunto', '')}"]
    if local:
        linhas.append(f"    Local: {local}")
    if (r.get('num_doc') or '').strip():
        linhas.append(f"    Nº Doc: {r['num_doc']}")
    if (r.get('link_convocatoria') or '').strip():
        linhas.append(f"    Link: {r['link_convocatoria']}")
    return "\n".join(linhas)


def _corpo_email_reunioes(nome, avisos, config):
    hoje_avisos = [a for a in avisos if a['tipo'] == 'hoje']
    vespera = [a for a in avisos if a['tipo'] == 'vespera']

    linhas = [f"Exmo(a). Sr(a). {nome},", "",
              "Serve o presente email para lembrar as reuniões agendadas "
              "sob sua organização:", ""]
    if hoje_avisos:
        linhas.append(f"REUNIÕES DE HOJE ({len(hoje_avisos)}):")
        linhas += [_linha_reuniao(a) for a in hoje_avisos]
        linhas.append("")
    if vespera:
        linhas.append(f"REUNIÕES DE AMANHÃ ({len(vespera)}):")
        linhas += [_linha_reuniao(a) for a in vespera]
        linhas.append("")

    linhas += ["Com os melhores cumprimentos,",
               config.get('utilizador', 'Secretariado') or 'Secretariado',
               "Sistema de Gestão de Documentos — DNE | MIREME",
               "",
               "(Mensagem gerada automaticamente. Cada lembrete é enviado "
               "uma única vez por reunião.)"]
    return "\n".join(linhas)


def _processar_reunioes(db, config, resumo):
    """Envia os lembretes de reuniões devidos e actualiza o resumo partilhado.
    Chamado por processar_notificacoes — assume SMTP já validado."""
    try:
        avisos = apurar_avisos_reunioes(db)
    except Exception as e:
        if not resumo['erro']:
            resumo['erro'] = f'Falha ao apurar reuniões: {e}'
        return

    if not avisos:
        return
    resumo['avisos'] += len(avisos)

    contactos = db.get_all_contactos()

    # Agrupa lembretes por organizador
    por_organizador = {}
    for a in avisos:
        org = (a['reuniao'].get('organizador') or '').strip()
        por_organizador.setdefault(org, []).append(a)

    registo = _load_registo(_REGISTO_REUNIOES_PATH)
    hoje = date.today().isoformat()
    sem_destino = []          # lembretes sem email do organizador → resumo interno

    for org, grupo in por_organizador.items():
        email = _email_do_tecnico(org, contactos) if org else None
        if not email:
            sem_destino.extend(grupo)
            if org and org not in resumo['sem_email']:
                resumo['sem_email'].append(org)
            continue
        assunto = "📅 Lembrete de Reuniões Agendadas (DNE/MIREME)"
        corpo = _corpo_email_reunioes(org, grupo, config)
        try:
            _enviar_email(config, email, assunto, corpo)
            resumo['emails'] += 1
            for a in grupo:
                registo[f"{a['reuniao']['id']}:{a['tipo']}"] = hoje
        except Exception as e:
            resumo['erro'] = f'Falha ao enviar para {email}: {e}'

    # Reuniões sem email do organizador: resumo único para a conta configurada
    if sem_destino:
        proprio = (config.get('smtp_email') or '').strip()
        corpo = _corpo_email_reunioes(
            'Secretariado (reuniões sem email do organizador nos Contactos)',
            sem_destino, config)
        try:
            _enviar_email(config, proprio,
                          "📅 Lembrete de Reuniões — sem organizador associado", corpo)
            resumo['emails'] += 1
            for a in sem_destino:
                registo[f"{a['reuniao']['id']}:{a['tipo']}"] = hoje
        except Exception as e:
            resumo['erro'] = f'Falha ao enviar resumo interno de reuniões: {e}'

    _save_registo(registo, _REGISTO_REUNIOES_PATH)


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
        avisos = []

    if not avisos:
        _processar_reunioes(db, config, resumo)
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

    # Lembretes de reuniões (véspera e próprio dia)
    _processar_reunioes(db, config, resumo)
    return resumo
