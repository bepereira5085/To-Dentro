import logging
import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "http://router.project-osrm.org/route/v1/driving/{coords}"


def obter_coordenadas(street: str, number: str, city: str, state: str, cep: str) -> tuple[float | None, float | None]:
    """
    Busca as coordenadas (latitude, longitude) de um endereço usando a API Nominatim (OpenStreetMap).
    """
    # Constrói queries de busca de forma progressiva (específica para geral)
    queries = []
    
    # 1. Endereço completo com número
    if street and number and city:
        queries.append(f"{street}, {number}, {city}, {state}, Brasil")
    
    # 2. Apenas rua e cidade
    if street and city:
        queries.append(f"{street}, {city}, {state}, Brasil")
        
    # 3. Apenas CEP
    if cep:
        cep_limpo = cep.replace("-", "").strip()
        queries.append(f"{cep_limpo}, Brasil")

    headers = {
        "User-Agent": "ToDentroApp/1.0 (contact: bernardopcandido@gmail.com)"
    }

    for query in queries:
        try:
            params = {
                "q": query,
                "format": "json",
                "limit": 1
            }
            response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    logger.info(f"Geocodificação bem sucedida para '{query}': ({lat}, {lon})")
                    return lat, lon
        except Exception as e:
            logger.error(f"Erro ao geocodificar usando query '{query}': {e}")
            continue

    logger.warning(f"Não foi possível obter coordenadas para: {street}, {number}, {city}, {state}, {cep}")
    return None, None


def obter_tempo_viagem_carro(lat_orig: float, lng_orig: float, lat_dest: float, lng_dest: float) -> int | None:
    """
    Retorna o tempo estimado de viagem de carro (em minutos) entre duas coordenadas usando a API OSRM.
    """
    if not all([lat_orig, lng_orig, lat_dest, lng_dest]):
        return None

    coords_str = f"{lng_orig},{lat_orig};{lng_dest},{lat_dest}"
    url = OSRM_URL.format(coords=coords_str)

    try:
        response = requests.get(url, params={"overview": "false"}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and "routes" in data and len(data["routes"]) > 0:
                duration_sec = data["routes"][0]["duration"]
                duration_min = round(duration_sec / 60.0)
                return duration_min
    except Exception as e:
        logger.error(f"Erro ao obter tempo de viagem da OSRM: {e}")

    return None
