import os
import re
import shutil
import sys
import json
import base64
from datetime import datetime, timedelta


# ─────────────────────────────────────────────────────────────────────────────
#  Cifragem de campos sensíveis (senha SMTP) com o DPAPI do Windows
#
#  Usa CryptProtectData/CryptUnprotectData via ctypes — sem dependências
#  externas. A cifragem está ligada à conta de utilizador do Windows: o
#  valor cifrado não pode ser lido por outra conta nem copiado para outro
#  computador. Em caso de falha (ou fora do Windows) degrada de forma segura,
#  devolvendo o texto original, para nunca impedir gravar/abrir a configuração.
# ─────────────────────────────────────────────────────────────────────────────

_ENC_PREFIX = "enc:"


def _dpapi(texto, proteger):
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _to_blob(dados):
        buf = ctypes.create_string_buffer(dados, len(dados))
        return DATA_BLOB(len(dados), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))

    def _from_blob(blob):
        out = ctypes.create_string_buffer(blob.cbData)
        ctypes.memmove(out, blob.pbData, blob.cbData)
        return out.raw

    fn = (ctypes.windll.crypt32.CryptProtectData if proteger
          else ctypes.windll.crypt32.CryptUnprotectData)
    blob_in = _to_blob(texto)
    blob_out = DATA_BLOB()
    ok = fn(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out))
    if not ok:
        raise OSError("Falha no DPAPI (CryptProtectData/CryptUnprotectData)")
    try:
        return _from_blob(blob_out)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def proteger_texto(texto):
    """Cifra uma string e devolve um token 'enc:<base64>'. Se já estiver
    cifrada ou se a cifragem falhar, devolve o valor sem alteração."""
    if not texto or texto.startswith(_ENC_PREFIX):
        return texto
    try:
        cifrado = _dpapi(texto.encode("utf-8"), proteger=True)
        return _ENC_PREFIX + base64.b64encode(cifrado).decode("ascii")
    except Exception:
        return texto


def desproteger_texto(texto):
    """Decifra um token 'enc:<base64>'. Se não estiver cifrado (configurações
    antigas em texto simples) devolve o valor tal como está."""
    if not texto or not texto.startswith(_ENC_PREFIX):
        return texto
    try:
        bruto = base64.b64decode(texto[len(_ENC_PREFIX):])
        return _dpapi(bruto, proteger=False).decode("utf-8")
    except Exception:
        return texto


# Campos da configuração que devem ser cifrados em disco
_CAMPOS_SENSIVEIS = ("smtp_password",)


def gravar_config(config_path, config):
    """Grava a configuração em JSON, cifrando os campos sensíveis (senha SMTP)
    apenas no ficheiro em disco. O dicionário em memória passado como argumento
    não é alterado (continua em texto simples para uso da aplicação)."""
    em_disco = dict(config)
    for campo in _CAMPOS_SENSIVEIS:
        if em_disco.get(campo):
            em_disco[campo] = proteger_texto(em_disco[campo])
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(em_disco, f, ensure_ascii=False, indent=2)


def decifrar_config(config):
    """Decifra, no lugar, os campos sensíveis de um dicionário de configuração
    lido do disco. Devolve o próprio dicionário."""
    for campo in _CAMPOS_SENSIVEIS:
        if config.get(campo):
            config[campo] = desproteger_texto(config[campo])
    return config


# Departamentos fixos para "Ao Departamento" (documentos recebidos) e relatório
DEPARTAMENTOS_RECEBIDOS = [
    "Direcção - DNE",
    "Dep. Estudos e Projectos",
    "Dep de Licenciamento e Fiscalização",
    "Dep. de Planeamento Energético",
    "Dep. Eficiência Energética",
    "Dep de Energias Renováveis",
    "Rep. de Administração e Finanças",
    "Transição Energética",
    "UIPCE",
]


def get_data_dir():
    """Pasta persistente para os dados do utilizador (BD, configuração, backups).

    Em modo executável fica em %LOCALAPPDATA%\\GestaoDocumentosDNE, fora da
    pasta de instalação — assim sobrevive a reinstalações/reconstruções do
    executável (que apagam a pasta dist\\GestaoDocumentos_DNE). Em modo de
    desenvolvimento usa a pasta do projecto, como antes."""
    if getattr(sys, 'frozen', False):
        base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
        data_dir = os.path.join(base, 'GestaoDocumentosDNE')
    else:
        data_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def migrar_dados_antigos(data_dir, old_dir):
    """Migração única: copia gestao_documentos.db, config.json e Backups/ da
    pasta antiga (junto ao executável) para a pasta persistente, caso ainda
    não existam lá."""
    if not old_dir or os.path.normcase(old_dir) == os.path.normcase(data_dir):
        return
    for nome in ('gestao_documentos.db', 'config.json'):
        destino = os.path.join(data_dir, nome)
        origem = os.path.join(old_dir, nome)
        if not os.path.exists(destino) and os.path.exists(origem):
            try:
                shutil.copy2(origem, destino)
            except Exception:
                pass

    origem_backups = os.path.join(old_dir, 'Backups')
    destino_backups = os.path.join(data_dir, 'Backups')
    if os.path.isdir(origem_backups) and not os.path.isdir(destino_backups):
        try:
            shutil.copytree(origem_backups, destino_backups)
        except Exception:
            pass

def iso_to_display(iso_str):
    """Converte data ISO (AAAA-MM-DD) para exibição (DD/MM/AAAA)."""
    if not iso_str:
        return ""
    try:
        return datetime.strptime(iso_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return iso_str


def display_to_iso(disp):
    """Converte data de exibição (DD/MM/AAAA) para ISO (AAAA-MM-DD)."""
    if not disp:
        return ""
    try:
        return datetime.strptime(disp, "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        return disp


_HORA_LOCAL_RE = re.compile(r'(\d{1,2}:\d{2})\s*(?:[-aà]+\s*(\d{1,2}:\d{2}))?\s*(.*)')


def parse_hora_local(hora_local):
    """Extrai (hora_inicio, hora_fim, local) do campo combinado 'hora_local',
    ex: '07:30 - 09:00  Sala de Reuniões' -> ('07:30', '09:00', 'Sala de Reuniões')."""
    hora_local = (hora_local or '').strip()
    m = _HORA_LOCAL_RE.match(hora_local)
    if m and m.group(1):
        hora_inicio = m.group(1).strip()
        hora_fim = (m.group(2) or '').strip()
        local = (m.group(3) or '').strip(' -—,')
        return hora_inicio, hora_fim, local
    return '', '', hora_local


def parse_clipboard_fields(texto, todos_labels):
    """Analisa texto no formato gerado por _copiar_tudo() e devolve
    um dicionário {label: valor} onde o valor pode ser multi-linha."""
    resultado = {}
    campo_atual = None
    buffer = []
    for linha in texto.splitlines():
        matched = None
        for label in todos_labels:
            if linha.startswith(label + ':'):
                matched = label
                break
        if matched is not None:
            if campo_atual is not None:
                resultado[campo_atual] = '\n'.join(buffer).strip()
            campo_atual = matched
            buffer = [linha[len(matched) + 1:].strip()]
        elif campo_atual is not None:
            buffer.append(linha)
    if campo_atual is not None:
        resultado[campo_atual] = '\n'.join(buffer).strip()
    return resultado


def dias_uteis(d1_iso, d2_iso):
    """Conta dias úteis (seg–sex) entre duas datas ISO. d2 pode ser None (usa hoje)."""
    try:
        d1 = datetime.strptime(d1_iso, "%Y-%m-%d").date()
        if d2_iso:
            d2 = datetime.strptime(d2_iso, "%Y-%m-%d").date()
        else:
            from datetime import date as _date
            d2 = _date.today()
        count = 0
        current = d1
        while current < d2:
            if current.weekday() < 5:  # 0=seg … 4=sex
                count += 1
            current += timedelta(days=1)
        return count
    except Exception:
        return None


def get_meeting_datetimes(data_reuniao_iso, hora_local):
    """Devolve (inicio, fim) como datetime para uma reunião, ou (None, None)
    se a data não for válida. Se a hora não estiver definida, assume
    00:00 (início) e 23:59 (fim) desse dia."""
    if not data_reuniao_iso:
        return None, None
    try:
        d = datetime.strptime(data_reuniao_iso, "%Y-%m-%d").date()
    except Exception:
        return None, None

    hora_inicio, hora_fim, _ = parse_hora_local(hora_local)

    inicio = datetime(d.year, d.month, d.day, 0, 0)
    if hora_inicio:
        try:
            h, mi = map(int, hora_inicio.split(":"))
            inicio = datetime(d.year, d.month, d.day, h, mi)
        except Exception:
            pass

    fim = datetime(d.year, d.month, d.day, 23, 59)
    if hora_fim:
        try:
            h, mi = map(int, hora_fim.split(":"))
            fim = datetime(d.year, d.month, d.day, h, mi)
        except Exception:
            pass

    return inicio, fim
