# seguranca.py — Senha da secção Confidenciais
#
# A senha é guardada como HASH (PBKDF2-HMAC-SHA256 com sal aleatório), nunca em
# texto simples. O formato do token guardado no config.json é:
#     pbkdf2$<iteracoes>$<sal_hex>$<hash_hex>
# Assim, mesmo quem abra o ficheiro de configuração não consegue ler a senha.
#
# Regras: a senha tem de combinar LETRAS e NÚMEROS, com no mínimo 6 caracteres.
# Recuperação: gera-se um código numérico temporário, enviado por email.

import hashlib
import hmac
import secrets

_ITERACOES = 200_000
_MIN_LEN = 6


def validar_password(senha):
    """Devolve None se a senha for válida, ou uma mensagem de erro (str) caso
    contrário. Regra: mínimo 6 caracteres, com pelo menos uma letra e um número."""
    senha = senha or ""
    if len(senha) < _MIN_LEN:
        return f"A senha deve ter pelo menos {_MIN_LEN} caracteres."
    if not any(c.isalpha() for c in senha):
        return "A senha deve conter pelo menos uma letra."
    if not any(c.isdigit() for c in senha):
        return "A senha deve conter pelo menos um número."
    if any(c.isspace() for c in senha):
        return "A senha não pode conter espaços."
    return None


def hash_password(senha):
    """Devolve o token 'pbkdf2$iter$sal$hash' para guardar no config."""
    sal = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', senha.encode('utf-8'), sal, _ITERACOES)
    return f"pbkdf2${_ITERACOES}${sal.hex()}${dk.hex()}"


def verificar_password(senha, token):
    """Verifica a senha contra o token guardado. Devolve True/False.
    Comparação em tempo constante (hmac.compare_digest)."""
    try:
        esquema, iteracoes, sal_hex, hash_hex = (token or "").split('$')
        if esquema != 'pbkdf2':
            return False
        dk = hashlib.pbkdf2_hmac('sha256', (senha or "").encode('utf-8'),
                                 bytes.fromhex(sal_hex), int(iteracoes))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def tem_password(config):
    """True se já existe uma senha de confidenciais definida."""
    return bool((config or {}).get('confidencial_hash'))


def gerar_codigo_reposicao(n=6):
    """Gera um código numérico de reposição (por defeito 6 dígitos)."""
    return ''.join(secrets.choice('0123456789') for _ in range(n))
