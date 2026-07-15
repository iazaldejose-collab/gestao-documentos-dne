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


# ── Nº de Documento ───────────────────────────────────────────────────────────
# Nos ofícios do MIREME o nº costuma ser <parte>/SIGLA/<n>/<ano> e a 1ª parte é
# muitas vezes MANUSCRITA (ex.: "Ofício nº  640 /GMNEC/990/2026"), o que mete
# espaços à volta das barras. O fragmento _CODE aceita esses espaços (removidos
# depois por _limpar_numero) e exige pelo menos uma barra, terminando o código
# de forma tão completa quanto possível (incluindo o /ano).
_CODE = r'[\w.\-]+(?:\s*/\s*[\w.\-]+){1,8}'

PATTERNS_NUM = [
    # Ofício/Nota/Circular/Carta nº <código>  (nº pode ser manuscrito/com espaços,
    # "nº" tolerante a OCR: º, °, o, 0, ., ou ausente)
    r'(?:Of[ií]cio|Nota|Circular|Carta)\s+[nN][.ºo°0]?\s*(' + _CODE + r')',
    # N/Ref. <código>
    r'N/Ref[\wªaâ]*\.?\s*[:\-]?\s*(' + _CODE + r')',
    # Our Ref / Réf / Ref (nº) <código>
    r'(?:Our\s+Ref|R[eé]f)\.?\s*[:.\-]?\s*[nN]?[.ºo°0]?\s*(' + _CODE + r')',
    # Código tipo SIGLA/SIGLA/... (ex.: AFREC/L/MS/036.26)
    r'([A-Z]{2,8}\s*/\s*[A-Z0-9]{1,8}(?:\s*/\s*[\w.\-]+){1,6})',
    # Genérico: código com >=2 barras terminando em ano (último recurso)
    r'((?:[\w.\-]+\s*/\s*){2,8}\d{2,4})',
]


def _limpar_numero(num):
    """Normaliza um nº de documento capturado: junta espaços à volta das barras
    e hífenes (típico de números manuscritos), colapsa espaços repetidos e tira
    pontuação nas pontas. Ex.: '640 /GMNEC/ 990/2026' -> '640/GMNEC/990/2026'."""
    if not num:
        return num
    num = re.sub(r'\s*/\s*', '/', num)
    num = re.sub(r'\s*-\s*', '-', num)
    num = re.sub(r'\s{2,}', ' ', num).strip(' .,;:\t')
    return num


def _parece_data(s):
    """True se o texto parece uma data dd/mm/aa(aa) — para não confundir uma data
    manuscrita (ex.: '3/6/26') com um número de documento."""
    return bool(re.fullmatch(r'\d{1,2}/\d{1,2}/\d{2,4}', s or ''))


def _extrair_numero(text):
    """Percorre os padrões e devolve o 1º nº de documento válido (normalizado),
    ignorando correspondências que pareçam apenas uma data."""
    for pat in PATTERNS_NUM:
        for m in re.finditer(pat, text, re.IGNORECASE):
            cand = _limpar_numero(m.group(1))
            if cand and not _parece_data(cand):
                return cand
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Leitura de texto (PDF / DOCX), com OCR de reserva para digitalizados
# ─────────────────────────────────────────────────────────────────────────────

# ── Caminhos comuns onde o instalador do Tesseract OCR coloca o executável
#    no Windows (caso não esteja disponível no PATH do sistema) ────────────────
_TESSERACT_CANDIDATOS = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    os.path.expandvars(r'%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe'),
    os.path.expandvars(r'%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe'),
]


def _configure_tesseract():
    """Configura o pytesseract para encontrar o motor Tesseract OCR
    instalado no Windows, mesmo que não esteja no PATH do sistema.
    Devolve True se o Tesseract estiver disponível e configurado."""
    try:
        import shutil
        import pytesseract

        # Já configurado/encontrado anteriormente
        cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', 'tesseract')
        if cmd and os.path.isfile(cmd):
            return True

        # Disponível no PATH do sistema
        if shutil.which('tesseract'):
            return True

        # Procura nos caminhos de instalação habituais no Windows
        for candidato in _TESSERACT_CANDIDATOS:
            if os.path.isfile(candidato):
                pytesseract.pytesseract.tesseract_cmd = candidato
                return True

        return False
    except Exception:
        return False


def _tessdata_dir_extra():
    """Devolve o caminho de uma pasta 'tessdata' adicional fornecida com a
    aplicação (contendo, por exemplo, 'por.traineddata'), caso exista. Isto
    permite usar o reconhecimento em Português mesmo que a instalação do
    Tesseract no computador só tenha o pacote de idioma Inglês."""
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        candidatos = [
            os.path.join(base, '..', 'assets', 'tessdata'),
            os.path.join(base, '..', '..', 'assets', 'tessdata'),
            os.path.join(base, 'tessdata'),
        ]
        for c in candidatos:
            c = os.path.abspath(c)
            if os.path.isfile(os.path.join(c, 'por.traineddata')):
                return c
    except Exception:
        pass
    return None


def _preprocess_ocr(img):
    """Prepara a imagem de uma página para melhorar a precisão do OCR:
    escala de cinza, aumento de contraste, binarização (limiar de Otsu) e
    ampliação de páginas pequenas. Devolve a imagem tratada (ou a original
    em caso de qualquer problema)."""
    try:
        from PIL import Image, ImageOps, ImageFilter

        g = img.convert('L')                     # escala de cinza
        g = ImageOps.autocontrast(g, cutoff=1)   # estica o contraste

        # Ampliar páginas de baixa resolução (o Tesseract prefere ~300 dpi)
        if g.width < 1700:
            fator = 1700 / g.width
            g = g.resize((int(g.width * fator), int(g.height * fator)),
                         Image.LANCZOS)

        g = g.filter(ImageFilter.MedianFilter(size=3))  # reduz ruído do scan

        # Limiar de Otsu (calculado a partir do histograma, sem numpy)
        hist = g.histogram()
        total = sum(hist)
        if total:
            soma_total = sum(i * hist[i] for i in range(256))
            soma_b = 0.0
            peso_b = 0.0
            maximo = 0.0
            limiar = 160
            for i in range(256):
                peso_b += hist[i]
                if peso_b == 0:
                    continue
                peso_f = total - peso_b
                if peso_f == 0:
                    break
                soma_b += i * hist[i]
                media_b = soma_b / peso_b
                media_f = (soma_total - soma_b) / peso_f
                entre = peso_b * peso_f * (media_b - media_f) ** 2
                if entre > maximo:
                    maximo = entre
                    limiar = i
            g = g.point(lambda p, t=limiar: 255 if p > t else 0)
        return g
    except Exception:
        return img


def _ocr_pdf(filepath, max_pages=2):
    """Tenta reconhecer texto em PDFs digitalizados ou manuscritos via OCR
    (Tesseract, através do pytesseract). Devolve "" se o OCR não estiver
    disponível no sistema (pacote pytesseract e/ou motor Tesseract não
    instalados) ou se nada for reconhecido.

    A imagem de cada página é pré-tratada (escala de cinza, contraste,
    binarização Otsu e ampliação) e reconhecida com o motor LSTM do Tesseract
    (--oem 1). Tenta o modo de página uniforme (--psm 6) e, se não aparecerem
    dígitos (típico do nº de documento), tenta ainda o modo de texto disperso
    (--psm 11), combinando os resultados.

    Nota: o reconhecimento de letra manuscrita é limitado — funciona melhor
    com letra bem legível e maiúsculas. Para melhores resultados recomenda-se
    digitalizar a, pelo menos, 300 dpi.
    """
    try:
        import pytesseract
    except ImportError:
        return "__ocr_erro__:pytesseract não disponível no executável"
    try:
        import fitz
    except ImportError:
        return "__ocr_erro__:PyMuPDF não disponível no executável"
    try:
        from PIL import Image
        import io
    except ImportError:
        return "__ocr_erro__:Pillow (PIL) não disponível no executável"

    if not _configure_tesseract():
        return "__ocr_erro__:Motor Tesseract OCR não encontrado. Instale o Tesseract em https://github.com/UB-Mannheim/tesseract/wiki"

    tessdata_extra = _tessdata_dir_extra()
    prefix_anterior = os.environ.get('TESSDATA_PREFIX')
    if tessdata_extra:
        os.environ['TESSDATA_PREFIX'] = tessdata_extra

    def _reconhecer(imagem, config):
        """image_to_string com fallback para inglês se 'por' não existir."""
        try:
            return pytesseract.image_to_string(imagem, lang='por', config=config)
        except Exception:
            try:
                return pytesseract.image_to_string(imagem, config=config)
            except Exception:
                return ""

    try:
        doc = fitz.open(filepath)
        textos = []
        for i in range(min(max_pages, len(doc))):
            # Renderiza a ~288 dpi (matriz 4x sobre os 72 dpi base)
            pix = doc[i].get_pixmap(matrix=fitz.Matrix(4, 4))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img = _preprocess_ocr(img)

            txt = _reconhecer(img, '--oem 1 --psm 6')
            # Se não saíram dígitos, o nº de documento pode estar disperso no
            # cabeçalho — tenta o modo de texto disperso e junta o que apanhar.
            if not re.search(r'\d', txt or ''):
                txt2 = _reconhecer(img, '--oem 1 --psm 11')
                if txt2:
                    txt = (txt or "") + "\n" + txt2
            if txt:
                textos.append(txt)
        doc.close()
        if not any(t.strip() for t in textos):
            return "__ocr_erro__:Falha no reconhecimento de texto (nada legível)."
        return "\n".join(textos)
    except Exception as e:
        return f"__ocr_erro__:Erro ao processar PDF para OCR: {e}"
    finally:
        if tessdata_extra:
            if prefix_anterior is None:
                os.environ.pop('TESSDATA_PREFIX', None)
            else:
                os.environ['TESSDATA_PREFIX'] = prefix_anterior


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
            ocr_result = _ocr_pdf(filepath, max_pages=2)
            if ocr_result.startswith("__ocr_erro__:"):
                return None, {'_erro': ocr_result.replace("__ocr_erro__:", "OCR: ")}
            text = ocr_result

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


# Extensões de imagem aceites pelo conversor Imagem → Texto (OCR)
_IMG_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.webp', '.gif')


def _ocr_imagem(filepath):
    """Reconhece o texto de um ficheiro de IMAGEM (digitalização/fotografia)
    via OCR, com o mesmo pré-tratamento usado para PDFs digitalizados.
    Devolve o texto, ou '__ocr_erro__:<motivo>' em caso de falha."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "__ocr_erro__:OCR não disponível no executável (pytesseract/Pillow)"

    if not _configure_tesseract():
        return ("__ocr_erro__:Motor Tesseract OCR não encontrado. Instale o "
                "Tesseract em https://github.com/UB-Mannheim/tesseract/wiki")

    tessdata_extra = _tessdata_dir_extra()
    prefix_anterior = os.environ.get('TESSDATA_PREFIX')
    if tessdata_extra:
        os.environ['TESSDATA_PREFIX'] = tessdata_extra

    def _reconhecer(imagem, config):
        try:
            return pytesseract.image_to_string(imagem, lang='por', config=config)
        except Exception:
            try:
                return pytesseract.image_to_string(imagem, config=config)
            except Exception:
                return ""

    try:
        img = Image.open(filepath)
        img = _preprocess_ocr(img)
        txt = _reconhecer(img, '--oem 1 --psm 6')
        if not (txt or '').strip():
            # Texto disperso (cabeçalhos, carimbos) — tenta o modo esparso
            txt = _reconhecer(img, '--oem 1 --psm 11')
        if not (txt or '').strip():
            return "__ocr_erro__:Falha no reconhecimento (nada legível na imagem)."
        return txt
    except Exception as e:
        return f"__ocr_erro__:Erro ao processar a imagem: {e}"
    finally:
        if tessdata_extra:
            if prefix_anterior is None:
                os.environ.pop('TESSDATA_PREFIX', None)
            else:
                os.environ['TESSDATA_PREFIX'] = prefix_anterior


def extrair_texto_completo(filepath, max_pages=20, ocr_max_pages=6):
    """Conversor Documento → Texto para uso do utilizador (janela Extrair Texto).

    Suporta PDF (texto nativo; OCR automático se for digitalizado), Word
    (.docx) e IMAGENS (jpg, png, tif, bmp, webp — via OCR). Ao contrário de
    _extrair_texto (usado no preenchimento automático de campos), lê mais
    páginas, para devolver o conteúdo completo do documento.

    Devolve (texto, erro): 'erro' é None em caso de sucesso, senão uma
    mensagem legível para mostrar ao utilizador."""
    if not filepath or not os.path.exists(filepath):
        return None, "Ficheiro não encontrado."

    ext = os.path.splitext(filepath)[1].lower()

    # ── Imagem → Texto (OCR directo) ─────────────────────────────────────────
    if ext in _IMG_EXTS:
        r = _ocr_imagem(filepath)
        if r.startswith("__ocr_erro__:"):
            return None, r.replace("__ocr_erro__:", "OCR: ")
        return r, None

    # ── PDF → Texto (nativo, com OCR de recurso) ─────────────────────────────
    if ext == '.pdf':
        text = ""
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages[:max_pages])
        except Exception:
            pass
        if not text.strip():
            try:
                import fitz
                doc = fitz.open(filepath)
                text = "\n".join(doc[i].get_text() for i in range(min(max_pages, len(doc))))
                doc.close()
            except Exception:
                pass
        if not text.strip():
            r = _ocr_pdf(filepath, max_pages=ocr_max_pages)
            if r.startswith("__ocr_erro__:"):
                return None, r.replace("__ocr_erro__:", "OCR: ")
            text = r
        if not (text or '').strip():
            return None, ("O ficheiro não contém texto reconhecível "
                          "(pode ser digitalizado e o OCR não conseguiu ler).")
        return text, None

    # ── Word (.docx) → Texto ─────────────────────────────────────────────────
    if ext in ('.docx', '.doc'):
        texto, erro = _extrair_texto(filepath, max_pages=max_pages)
        if erro:
            return None, erro.get('_erro') or erro.get('_formato') or "Falha na leitura."
        return texto, None

    return None, (f'Formato "{ext}" não suportado. '
                  'Use PDF, Word (.docx) ou imagem (JPG, PNG, TIF).')


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
    numero = _extrair_numero(text)
    if numero:
        result['numero'] = numero

    # ── Assunto ────────────────────────────────────────────────────────────────
    m = re.search(
        r'(?:Assunto|Subject|Objet|Re(?:f(?:erência)?)?)\s*[:\-]\s*(.+?)(?:\n|$)',
        text, re.IGNORECASE
    )
    if m:
        resultado_assunto = m.group(1).strip()
        # evitar capturar o próprio número de ref como assunto
        if len(resultado_assunto.split()) >= 2:
            result['assunto'] = resultado_assunto
    if 'assunto' not in result:
        for ln in lines[1:15]:
            if (len(ln.split()) >= 4
                    and not re.match(r'^[\d/\-]', ln)
                    and not re.search(r'[A-Z]{2,}/[A-Z]', ln)):
                result['assunto'] = ln
                break

    # ── Proveniência ──────────────────────────────────────────────────────────
    header = "\n".join(lines[:20])
    siglas = (
        r'\b(MIREME|EDM|MPD|GEPR|ARENE|MOPHRH|MEF|MF|INE|BM|FIPAG|CFM|LAM|ADN|'
        r'INEFP|INAM|INAP|IPEME|FUNAE|CFJJ|PGR|SERNAP|MITADER|MADER|MCTES|'
        r'MAEFP|MGCAS|MINT|MINJUSDH|MINEDH|MISAU|MITSS|MICM|MTC|INSS|IGEPE|'
        r'CTA|CIP|DNGRH|ANE|ANAC|ICV|IPAJ|CNA|CMAM|INAGE|'
        r'AFREC|AFD|BAfD|GIZ|USAID|UNDP|PNUD|SADC|UA|SAPP|ZESCO|SNEL|'
        r'WB|ADB|AfDB|IFC|IMF|FMI|EU|UE|DFID|FCDO|JICA|KfW|'
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
        r'Alto\s+Comissário|Cônsul|Embaixador[a]?|Coordenador[a]?|'
        r'Chairman|Director\s*General|Executive\s*Director|Head\s*of|'
        r'Manager|Program\s*Manager|Country\s*Director|Representative)'
    )
    # Procura no final do documento (assinatura) e também no início (cabeçalho)
    tail_lines = lines[-30:]
    tail_text = "\n".join(tail_lines)
    full_search_text = tail_text  # prioridade: rodapé

    m_cargo = re.search(cargo_keywords, full_search_text, re.IGNORECASE)
    # Se não encontrou no rodapé, tenta no cabeçalho (documentos internacionais)
    if not m_cargo:
        head_text = "\n".join(lines[:20])
        m_cargo = re.search(cargo_keywords, head_text, re.IGNORECASE)
        if m_cargo:
            search_lines = lines[:20]
        else:
            search_lines = tail_lines
    else:
        search_lines = tail_lines

    if m_cargo:
        result['remetente_cargo'] = m_cargo.group(1).strip()
        idx = next((i for i, ln in enumerate(search_lines)
                    if m_cargo.group(1).lower() in ln.lower()), None)
        if idx is not None:
            for delta in (-1, -2, 1, 2):
                ci = idx + delta
                if 0 <= ci < len(search_lines):
                    candidate = search_lines[ci].strip()
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
    numero = _extrair_numero(text)
    if numero:
        result['numero'] = numero

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
