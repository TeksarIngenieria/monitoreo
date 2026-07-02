import os
import json
import requests
from datetime import datetime, timedelta

# Levantamos las credenciales seguras desde los Secrets de GitHub
APP_ID = os.environ.get("DEYE_APP_ID")
APP_SECRET = os.environ.get("DEYE_APP_SECRET")
EMAIL = os.environ.get("DEYE_EMAIL")
PASSWORD = os.environ.get("DEYE_PASSWORD")

def obtener_token():
    url = "https://api-eu.deyecloud.com/v1.0/oauth/token"
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET,
        "email": EMAIL,
        "password": PASSWORD,
        "grant_type": "password"
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        return response.json().get("data", {}).get("access_token")
    except Exception as e:
        print(f"Error al obtener token: {e}")
        return None

def obtener_plantas(token):
    url = "https://api-eu.deyecloud.com/v1.0/account/plants"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json().get("data", {}).get("list", [])
    except Exception as e:
        print(f"Error al obtener plantas: {e}")
        return []

def main():
    print("Iniciando actualización de datos desde GitHub Actions...")
    
    if not all([APP_ID, APP_SECRET, EMAIL, PASSWORD]):
        print("ERROR: Faltan configurar algunos Secrets en GitHub.")
        return

    token = obtener_token()
    if not token:
        print("ERROR: No se pudo autenticar con Deye Cloud.")
        return

    plantas = obtener_plantas(token)
    print(f"OK - Conectado. Se encontraron {len(plantas)} plantas.")

    # Estructura final para el JSON
    data_final = {
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_plantas": len(plantas),
        "plantas": plantas
    }

    # Guardamos el archivo que leerá el index.html
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data_final, f, indent=4, ensure_ascii=False)

    print(f"OK - data.json generado con {len(plantas)} plantas.")

if __name__ == "__main__":
    main()
