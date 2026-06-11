import re
from datetime import datetime

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
