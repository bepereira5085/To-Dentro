"""
Serviço de CEP — integração com ViaCEP e lógica de proximidade por prefixo.
"""
import requests


_VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"


def buscar_endereco_por_cep(cep: str) -> dict | None:
    """
    Consulta a API ViaCEP e retorna dados do endereço.

    Returns:
        dict com chaves: cep, logradouro, bairro, cidade, uf, estado
        ou None se o CEP for inválido ou não encontrado.
    """
    cep_limpo = cep.replace("-", "").replace(".", "").strip()
    if len(cep_limpo) != 8 or not cep_limpo.isdigit():
        return None

    try:
        response = requests.get(
            _VIACEP_URL.format(cep=cep_limpo),
            timeout=5,
        )
        if response.status_code != 200:
            return None

        data = response.json()
        if data.get("erro"):
            return None

        return {
            "cep": data.get("cep", "").replace("-", ""),
            "logradouro": data.get("logradouro", ""),
            "bairro": data.get("bairro", ""),
            "cidade": data.get("localidade", ""),
            "uf": data.get("uf", ""),
            "estado": _uf_para_estado(data.get("uf", "")),
        }
    except (requests.RequestException, ValueError):
        return None


def calcular_proximidade_cep(cep_usuario: str, cep_evento: str) -> int:
    """
    Calcula score de proximidade entre dois CEPs por correspondência de prefixo.

    Score:
        5 — mesmos 5 primeiros dígitos (mesma área da cidade)
        4 — mesmos 4 primeiros dígitos
        3 — mesmos 3 primeiros dígitos (mesma região)
        2 — mesmos 2 primeiros dígitos (mesmo estado/macrorregião)
        1 — primeiro dígito igual
        0 — nenhuma correspondência
    """
    if not cep_usuario or not cep_evento:
        return 0

    cu = cep_usuario.replace("-", "").strip()
    ce = cep_evento.replace("-", "").strip()

    if len(cu) != 8 or len(ce) != 8:
        return 0

    score = 0
    for i in range(1, 6):
        if cu[:i] == ce[:i]:
            score = i
        else:
            break
    return score


def obter_cep_usuario(user) -> str | None:
    """
    Obtém o CEP do endereço principal do usuário.

    Returns:
        CEP como string (8 dígitos sem formatação) ou None.
    """
    if not user or not user.is_authenticated:
        return None

    if not user.addresses:
        return None

    user_address = user.addresses[0]
    address = user_address.address if hasattr(user_address, "address") else None
    if address and address.cep:
        return address.cep
    return None


def _uf_para_estado(uf: str) -> str:
    """Converte sigla UF para nome completo do estado."""
    estados = {
        "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
        "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
        "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
        "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
        "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco",
        "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
        "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
        "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe",
        "TO": "Tocantins",
    }
    return estados.get(uf.upper(), uf)
