# actualizacoes.py — Verificação discreta de novas versões
#
# Ao arrancar, a aplicação consulta (numa thread de fundo) o version.py
# publicado no GitHub e compara com a versão instalada. Se houver versão
# mais recente, o utilizador é avisado para solicitar o instalador novo.
# Sem internet ou com o repositório indisponível, fica silencioso.

import re
import urllib.request

_URL_VERSION = ("https://raw.githubusercontent.com/iazaldejose-collab/"
                "gestao-documentos-dne/master/version.py")


def obter_versao_remota(timeout=10):
    """Devolve (major, minor, patch) da versão publicada no GitHub,
    ou None se não for possível obter (sem internet, repo indisponível...)."""
    try:
        req = urllib.request.Request(_URL_VERSION,
                                     headers={'User-Agent': 'GestaoDocumentosDNE'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            texto = r.read(20000).decode('utf-8', errors='replace')
        valores = {}
        for chave in ('MAJOR', 'MINOR', 'PATCH'):
            m = re.search(rf'^{chave}\s*=\s*(\d+)', texto, re.MULTILINE)
            if not m:
                return None
            valores[chave] = int(m.group(1))
        return (valores['MAJOR'], valores['MINOR'], valores['PATCH'])
    except Exception:
        return None


def ha_versao_nova():
    """Compara a versão instalada com a publicada. Devolve a string da nova
    versão (ex: 'V1.0.42') se existir uma mais recente, senão None."""
    from version import MAJOR, MINOR, PATCH
    remota = obter_versao_remota()
    if remota and remota > (MAJOR, MINOR, PATCH):
        return f"V{remota[0]}.{remota[1]}.{remota[2]}"
    return None
