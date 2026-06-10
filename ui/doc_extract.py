"""
doc_extract.py — Extracção automática de dados a partir de ficheiros
PDF / Word (.docx, .doc) anexados, para o Sistema de Gestão de
Documentos DNE/MIREME.

Funções principais:
    extrair_dados_recebido(filepath)  -> dict (numero, proveniencia,
                                          remetente_nome, remetente_cargo,
                                          assunto, ...)
    extrair_dados_enviado(filepath)   -> dict (numero, assunto,
                                          destinatario_nome, ...)

Ambas devolvem '_erro' (problema técnico ao ler o ficheiro) ou
'_formato' (ficheiro lido mas sem texto reconhecível — ex: digitalizado
ou manuscrito sem OCR disponível) quando não conseguem extrair dados.
"""
import os
import re


# ── Padrões comuns de Nº de Documento (Ofício, Nota, Ref.ª, etc.) ──────────────
PATTERNS_NUM = [
    r'(Ofí?cio\s+[nN][°º.]\s*[\w./\-]+(?:/\d{4})?)',
    r'(N/Ref[aâ]?\s*[\w°º./\-]+(?:/\d{4})?)',
    r'(Our\s+Ref\.?\s*[nN][°º.]?\s*[\w./\-]+)',
    r'(Nota\s+[nN][°º.]\s*[\w./\-]+(?:/\d{4})?)',
    r'(Ref\.?\s*[nN][°º.]?\s*[\w./\-]+(?:/\d{4})?)',
    r'(\d{2,4}/[A-Z]{2,8}/[\w./\-]+/\d{4})',
    r'([A-Z]{2,8}/[A-Z]{2,8}/[\w./\-]+/\d{4})',
]


# ─────────────────────────────────────────────────────────────────────────────
#  Leitura de texto (PDF / DOCX), com OCR de reserva para digitalizados
# ─────────────────────────────────────────────────────────────────────────────

def _ocr_pdf(filepath, max_pages=2):
    """Tenta reconhecer texto em PDFs digitalizados ou manuscritos via OCR
    (Tesseract, através do pytesseract). Devolve "" se o OCR não estiver
    disponível no sistema (pacote pytesseract e/ou motor Tesseract não
    instalados) ou se nada for reconhecido.

    Nota: o reconhecimento de letra manuscrita é limitado — funciona melhor
    com letra bem legível e maiúsculas. Para melhores resultados recomenda-se
    digitalizar a, pelo menos, 200-300 dpi.
    """
    try:
        import pytesseract
        import fitz
        from PIL import Image
        import io

        doc = fitz.open(filepath)
        textos = []
        for i in range(min(max_pages, len(doc))):
            pix = doc[i].get_pixmap(matrix=fitz.Matrix(3, 3))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            try:
                textos.append(pytesseract.image_to_string(img, lang='por'))
            except Exception:
                try:
                    textos.append(pytesseract.image_to_string(img))
                except Exception:
                    pass
        doc.close()
        return "\n".join(textos)
    except Exception:
        return ""


def _extrair_texto(filepath, max_pages=4):
    """Devolve (texto, erro). 'erro' é None se a leitura foi bem sucedida,
    ou um dict com '_erro' (problema técnico) ou '_formato' (sem texto)."""
    if not filepath or not os.path.exists(filepath):
        return None, {'_erro': 'Ficheiro não encontrado.'}

    ext = os.path.splitext(filepath)[1].lower()
    text = ""
    lib_erro = None

    # ── Leitura do texto ──────────────────────────────────────────────────────
    if ext == '.pdf':
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages[:max_pages])
        except ImportError:
            lib_erro = "pdfplumber"
        except Exception:
            pass

        if not text.strip():
            try:
                import fitz
                doc = fitz.open(filepath)
                text = "\n".join(doc[i].get_text() for i in range(min(max_pages, len(doc))))
                doc.close()
            except ImportError:
                lib_erro = "PyMuPDF"
            except Exception:
                pass

        # ── PDF digitalizado/manuscrito sem texto: tenta OCR ─────────────────
        if not text.strip():
            text = _ocr_pdf(filepath, max_pages=2)

    elif ext in ('.docx', '.doc'):
        # Lê DOCX sem python-docx — usa apenas zipfile + xml (built-in no Python)
        try:
            import zipfile
            import xml.etree.ElementTree as ET

            W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

            with zipfile.ZipFile(filepath, 'r') as z:
                with z.open('word/document.xml') as f:
                    root = ET.parse(f).getroot()

                partes = []
                for para in root.iter(f'{{{W}}}p'):
                    linha = ''.join(
                        t.text for t in para.iter(f'{{{W}}}t') if t.text
                    ).strip()
                    if linha:
                        partes.append(linha)

                text = '\n'.join(partes[:120])
        except zipfile.BadZipFile:
            return None, {'_erro': 'Ficheiro .docx inválido ou corrompido.'}
        except KeyError:
            return None, {'_erro': 'Estrutura do ficheiro Word não reconhecida.'}
        except Exception as e:
            return None, {'_erro': f'Erro ao ler o ficheiro Word: {e}'}
    else:
        return None, {'_erro': f'Formato "{ext}" não suportado. Use PDF ou DOCX.'}

    if lib_erro and not text.strip():
        # fitz também não disponível — tenta leitura básica com pdfminer se instalado
        try:
            from pdfminer.high_level import extract_text as pm_extract
            text = pm_extract(filepath)
        except Exception:
            return None, {'_erro': 'Não foi possível ler o PDF. Ficheiro pode ser digitalizado (imagem).'}

    if not text:
        text = ""

    if not text.strip():
        return None, {'_formato': 'O ficheiro não contém texto reconhecível '
                                   '(pode ser digitalizado ou manuscrito e o OCR '
                                   'não conseguiu ler).'}

    return text, None


# ─────────────────────────────────────────────────────────────────────────────
#  Documentos Recebidos
# ─────────────────────────────────────────────────────────────────────────────

def extrair_dados_recebido(filepath):
    """Tenta extrair Nº Documento, Proveniência, Remetente e Assunto de um
    ficheiro PDF/DOCX (incluindo PDFs digitalizados/manuscritos via OCR,
    quando disponível)."""
    text, erro = _extrair_texto(filepath)
    if erro:
        return erro

    result = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # ── Nº Documento ──────────────────────────────────────────────────────────
    for pat in PATTERNS_NUM:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result['numero'] = m.group(1).strip()
            break

    # ── Assunto ────────────────────────────────────────────────────────────────
    m = re.search(
        r'(?:Assunto|Subject|Re|Ref(?:erência)?)\s*[:\-]\s*(.+?)(?:\n|$)',
        text, re.IGNORECASE
    )
    if m:
        result['assunto'] = m.group(1).strip()
    else:
        for ln in lines[1:10]:
            if len(ln.split()) >= 4 and not re.match(r'^[\d/\-]', ln):
                result['assunto'] = ln
                break

    # ── Proveniência ──────────────────────────────────────────────────────────
    header = "\n".join(lines[:20])
    siglas = (
        r'\b(MIREME|EDM|MPD|GEPR|ARENE|MOPHRH|MEF|MF|INE|BM|FIPAG|CFM|LAM|ADN|'
        r'INEFP|INAM|INAP|IPEME|FUNAE|CFJJ|PGR|SERNAP|MITADER|MADER|MCTES|'
        r'MAEFP|MGCAS|MINT|MINJUSDH|MINEDH|MISAU|MITSS|MICM|MTC|INSS|IGEPE|'
        r'CTA|CIP|DNGRH|ANE|ANAC|ICV|IPAJ|CNA|CMAM|INAGE|'
        r'MIREME-DPC|MIREME-DNE|MIREME-GM|MPD-GM|MF-GM|EDM-CA)\b'
    )
    m = re.search(siglas, header, re.IGNORECASE)
    if m:
        result['proveniencia'] = m.group(1).upper()
    elif 'numero' in result:
        m2 = re.search(r'[/\-]([A-Z]{2,8})[/\-]', result['numero'])
        if m2:
            result['proveniencia'] = m2.group(1)

    if 'proveniencia' not in result and lines:
        primeira = lines[0]
        if len(primeira) < 80 and not re.search(r'[0-9@]', primeira):
            result['proveniencia'] = primeira

    # ── Remetente (nome e cargo) ──────────────────────────────────────────────
    cargo_keywords = (
        r'(Ministro[a]?|Director[a]?(?:\s+(?:Nacional|Geral|Adjunto[a]?))?|'
        r'Presidente|Secretário[a]?|Secretário[a]?[-\s]Geral|PCA|CEO|'
        r'Administrador[a]?|Vereador[a]?|Governador[a]?|'
        r'Alto\s+Comissário|Cônsul|Embaixador[a]?|Coordenador[a]?)'
    )
    tail_lines = lines[-30:]
    tail_text = "\n".join(tail_lines)

    m_cargo = re.search(cargo_keywords, tail_text, re.IGNORECASE)
    if m_cargo:
        result['remetente_cargo'] = m_cargo.group(1).strip()
        idx = next((i for i, ln in enumerate(tail_lines)
                    if m_cargo.group(1).lower() in ln.lower()), None)
        if idx is not None:
            for delta in (-1, -2, 1, 2):
                ci = idx + delta
                if 0 <= ci < len(tail_lines):
                    candidate = tail_lines[ci].strip()
                    if (len(candidate.split()) >= 2
                            and not re.search(cargo_keywords, candidate, re.IGNORECASE)
                            and not re.search(r'[0-9@/]', candidate)
                            and len(candidate) < 60):
                        result['remetente_nome'] = candidate
                        break

    if not result:
        result['_formato'] = 'Ficheiro lido mas sem dados no formato de carta oficial.'

    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Documentos Enviados
# ─────────────────────────────────────────────────────────────────────────────

def extrair_dados_enviado(filepath):
    """Tenta extrair Nº Documento, Assunto e Destinatário (via "Att.") de um
    ficheiro PDF/DOCX a enviar (incluindo digitalizados/manuscritos via OCR,
    quando disponível)."""
    text, erro = _extrair_texto(filepath)
    if erro:
        return erro

    result = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # ── Nº Documento ──────────────────────────────────────────────────────────
    for pat in PATTERNS_NUM:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result['numero'] = m.group(1).strip()
            break

    # ── Assunto ────────────────────────────────────────────────────────────────
    m = re.search(
        r'(?:Assunto|Subject|Re|Ref(?:erência)?)\s*[:\-]\s*(.+?)(?:\n|$)',
        text, re.IGNORECASE
    )
    if m:
        result['assunto'] = m.group(1).strip()
    else:
        for ln in lines[1:10]:
            if len(ln.split()) >= 4 and not re.match(r'^[\d/\-]', ln):
                result['assunto'] = ln
                break

    # ── Destinatário (via "Att.") ─────────────────────────────────────────────
    # Exige "Att" seguido de "." ":" "-" ou espaço, para não confundir com
    # palavras como "Atenção"/"Attention".
    m = re.search(r'\bAtt\.?(?:[:\-]|\s)+(.+?)(?:\n|$)', text, re.IGNORECASE)
    if m:
        nome = m.group(1).strip(' :.-\t')
        if nome and 0 < len(nome) < 80:
            result['destinatario_nome'] = nome

    if not result:
        result['_formato'] = 'Ficheiro lido mas sem dados reconhecíveis.'

    return result
