# actualizacoes.py — Verificação discreta de novas versões
#
# Ao arrancar, a aplicação consulta (numa thread de fundo) a última Release
# publicada no GitHub e compara com a versão instalada. Se houver uma versão
# mais recente com instalador anexado, o utilizador é avisado e pode abrir
# directamente a página/ligação de transferência.
# Sem internet ou com o repositório indisponível, fica silencioso.

import re
import json
import urllib.request

_REPO = "iazaldejose-collab/gestao-documentos-dne"
_URL_RELEASE_API = f"https://api.github.com/repos/{_REPO}/releases/latest"
# Página de Releases (usada como recurso se a API falhar mas quisermos abrir o site)
URL_RELEASES = f"https://github.com/{_REPO}/releases/latest"
# version.py em bruto — usado apenas como recurso de comparação se a API falhar
_URL_VERSION = (f"https://raw.githubusercontent.com/{_REPO}/master/version.py")


def _versao_de_texto(texto):
    """Extrai (major, minor, patch) dos primeiros 3 números encontrados."""
    nums = re.findall(r'\d+', texto or '')
    if len(nums) < 3:
        return None
    return tuple(int(n) for n in nums[:3])


def obter_info_release(timeout=10):
    """Consulta a última Release publicada no GitHub. Devolve dict com:
      'versao'   -> tuplo (major, minor, patch) da tag da Release
      'pagina'   -> URL da página da Release (html_url)
      'download' -> URL directo do primeiro ficheiro .exe anexado (ou None)
    Devolve None se não for possível obter (sem internet, sem Releases...)."""
    try:
        req = urllib.request.Request(
            _URL_RELEASE_API,
            headers={'User-Agent': 'GestaoDocumentosDNE',
                     'Accept': 'application/vnd.github+json'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read(200000).decode('utf-8', errors='replace'))
        versao = _versao_de_texto(data.get('tag_name') or data.get('name') or '')
        if not versao:
            return None
        download = None
        for a in data.get('assets', []):
            nome = (a.get('name') or '').lower()
            if nome.endswith('.exe'):
                download = a.get('browser_download_url')
                break
        return {'versao': versao,
                'pagina': data.get('html_url') or URL_RELEASES,
                'download': download}
    except Exception:
        return None


def obter_versao_remota(timeout=10):
    """Recurso: lê a versão do version.py publicado no master (sem Release).
    Devolve (major, minor, patch) ou None."""
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


def verificar_actualizacao():
    """Compara a versão instalada com a última Release publicada no GitHub.
    Se houver uma mais recente, devolve dict:
      {'versao': 'V1.0.43', 'pagina': <url>, 'download': <url ou None>}
    Caso contrário (ou sem internet) devolve None."""
    from version import MAJOR, MINOR, PATCH
    atual = (MAJOR, MINOR, PATCH)

    info = obter_info_release()
    if info and info['versao'] > atual:
        m = info['versao']
        return {'versao': f"V{m[0]}.{m[1]}.{m[2]}",
                'pagina': info.get('pagina') or URL_RELEASES,
                'download': info.get('download')}

    # Recurso: se ainda não há Release mas o version.py no master já subiu,
    # avisa mesmo assim, apontando à página de Releases (sem link directo).
    if info is None:
        remota = obter_versao_remota()
        if remota and remota > atual:
            return {'versao': f"V{remota[0]}.{remota[1]}.{remota[2]}",
                    'pagina': URL_RELEASES, 'download': None}
    return None


def ha_versao_nova():
    """Compatibilidade: devolve apenas a string da nova versão, ou None."""
    info = verificar_actualizacao()
    return info['versao'] if info else None
