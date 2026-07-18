# nuvem.py — Backup na nuvem (Google Drive) por pasta sincronizada
#
# Não usa a API do Google: assume que o utilizador tem o "Google Drive para
# computador" instalado e com sessão iniciada na conta desejada — o que cria
# uma pasta local que o Drive sincroniza com a nuvem. A aplicação apenas
# escreve nessa pasta cópias de segurança (base de dados + anexos) e o Drive
# trata de as enviar para a nuvem. "Escolher a conta" = escolher a pasta dessa
# conta nas Configurações.

import os
import glob
import shutil
from datetime import datetime

from utils import get_data_dir

SUBPASTA = "GestaoDocumentos_Backup"   # subpasta criada dentro da pasta do Drive
MAX_COPIAS_BD = 7                      # nº de cópias datadas da BD a manter


def _dir_backup(pasta_nuvem):
    d = os.path.join(pasta_nuvem, SUBPASTA)
    os.makedirs(d, exist_ok=True)
    return d


def backup_nuvem(db, pasta_nuvem, incluir_anexos=True):
    """Copia a base de dados (cópia consistente) e os anexos para a pasta do
    Drive. Devolve um resumo:
        {'bd': bool, 'anexos': int, 'pasta': str|None, 'erro': str|None}
    Pensado para correr numa thread de fundo — não toca na interface."""
    resumo = {'bd': False, 'anexos': 0, 'pasta': None, 'erro': None}
    pasta_nuvem = (pasta_nuvem or '').strip()
    if not pasta_nuvem:
        resumo['erro'] = 'Pasta de backup na nuvem não definida.'
        return resumo
    if not os.path.isdir(pasta_nuvem):
        resumo['erro'] = ('A pasta indicada não existe ou não está acessível '
                          '(o Google Drive está instalado e com sessão iniciada?):\n'
                          f'{pasta_nuvem}')
        return resumo
    try:
        destino = _dir_backup(pasta_nuvem)
        resumo['pasta'] = destino

        # 1) Base de dados — cópia consistente (API de backup do SQLite), datada
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        bd_dest = os.path.join(destino, f'gestao_documentos_{ts}.db')
        db.backup_para(bd_dest)
        resumo['bd'] = True

        # Rotação: manter apenas as últimas MAX_COPIAS_BD cópias da BD
        antigas = sorted(glob.glob(os.path.join(destino, 'gestao_documentos_*.db')),
                         key=os.path.getmtime, reverse=True)
        for a in antigas[MAX_COPIAS_BD:]:
            try:
                os.remove(a)
            except OSError:
                pass

        # 2) Anexos — espelho incremental (copia só novos/alterados)
        if incluir_anexos:
            origem = os.path.join(get_data_dir(), 'anexos')
            if os.path.isdir(origem):
                destino_anx = os.path.join(destino, 'anexos')
                os.makedirs(destino_anx, exist_ok=True)
                for nome in os.listdir(origem):
                    src = os.path.join(origem, nome)
                    if not os.path.isfile(src):
                        continue
                    dst = os.path.join(destino_anx, nome)
                    try:
                        precisa = (not os.path.exists(dst)
                                   or os.path.getsize(dst) != os.path.getsize(src)
                                   or os.path.getmtime(dst) < os.path.getmtime(src) - 1)
                    except OSError:
                        precisa = True
                    if precisa:
                        shutil.copy2(src, dst)
                        resumo['anexos'] += 1
    except Exception as e:
        resumo['erro'] = str(e)
    return resumo


def resumo_texto(resumo):
    """Converte o resumo num texto curto para mostrar ao utilizador."""
    if resumo.get('erro'):
        return f"⚠️ Backup na nuvem falhou: {resumo['erro']}"
    partes = []
    if resumo.get('bd'):
        partes.append("base de dados")
    if resumo.get('anexos'):
        partes.append(f"{resumo['anexos']} anexo(s)")
    if not partes:
        return "Backup na nuvem: nada a copiar."
    return "☁️ Backup na nuvem concluído: " + " + ".join(partes) + "."
