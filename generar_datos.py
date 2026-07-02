import hashlib
import json
import os
import datetime
import time
import requests

# Credenciales desde los Secrets de GitHub
APP_ID     = os.environ.get("DEYE_APP_ID")
APP_SECRET = os.environ.get("DEYE_APP_SECRET")
EMAIL      = os.environ.get("DEYE_EMAIL")
PASSWORD   = os.environ.get("DEYE_PASSWORD")

BASE_URL = "https://us1-developer.deyecloud.com"


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def obtener_token():
    url = BASE_URL + "/v1.0/account/token?appId=" + APP_ID
    payload = {"appSecret": APP_SECRET, "email": EMAIL, "password": sha256(PASSWORD)}
    r = requests.post(url, json=payload, timeout=20)
    data = r.json()
    if not data.get("success"):
        raise RuntimeError("Token error: " + str(data))
    return data["accessToken"]


def post(token, path, body, reintentos=2):
    headers = {"Authorization": "Bearer " + token}
    for intento in range(reintentos + 1):
        try:
            r = requests.post(BASE_URL + path, headers=headers, json=body, timeout=30)
            return r.json()
        except Exception as e:
            if intento == reintentos:
                return {"success": False, "error": str(e)}
            time.sleep(2)


def listar_plantas(token):
    d = post(token, "/v1.0/station/list", {"page": 1, "size": 200})
    return d.get("stationList", [])


def energia_periodo(token, sid, granularity, start, end):
    d = post(token, "/v1.0/station/history",
             {"stationId": sid, "granularity": granularity, "startAt": start, "endAt": end})
    items = d.get("stationDataItems", []) or []
    tot = {"generation": 0.0, "consumption": 0.0, "grid": 0.0,
           "purchase": 0.0, "charge": 0.0, "discharge": 0.0}
    for it in items:
        tot["generation"]  += (it.get("generationValue")  or 0)
        tot["consumption"] += (it.get("consumptionValue") or 0)
        tot["grid"]        += (it.get("gridValue")        or 0)
        tot["purchase"]    += (it.get("purchaseValue")    or 0)
        tot["charge"]      += (it.get("chargeValue")      or 0)
        tot["discharge"]   += (it.get("dischargeValue")   or 0)
    return {k: round(v, 1) for k, v in tot.items()}


def contar_alertas(token, sid, desde_ts, hasta_ts):
    d = post(token, "/v1.0/station/alertList",
             {"stationId": sid, "page": 1, "size": 100,
              "startTimestamp": desde_ts, "endTimestamp": hasta_ts})
    total = d.get("total", 0) or 0
    items = d.get("stationAlertItems", []) or []
    principal = ""
    if items:
        items_ord = sorted(items, key=lambda x: x.get("alertStartTime", 0), reverse=True)
        principal = (items_ord[0].get("alertName", "") or "").replace("_", " ")
    return total, principal


def main():
    print("Iniciando actualizacion de datos desde GitHub Actions...")
    if not all([APP_ID, APP_SECRET, EMAIL, PASSWORD]):
        print("ERROR: Faltan configurar algunos Secrets en GitHub.")
        return

    token = obtener_token()
    plantas = listar_plantas(token)
    print("Plantas encontradas:", len(plantas))

    hoy = datetime.date.today()
    manana = hoy + datetime.timedelta(days=1)
    dia_start = hoy.strftime("%Y-%m-%d")
    dia_end = manana.strftime("%Y-%m-%d")
    mes_start = hoy.strftime("%Y-%m")
    mes_end = hoy.strftime("%Y-%m")
    anio_start = hoy.strftime("%Y")
    anio_end = hoy.strftime("%Y")

    ahora_ts = int(time.time())
    hace3_ts = ahora_ts - 3 * 86400

    resultado = []
    for i, p in enumerate(plantas, 1):
        sid = p.get("id")
        nombre = p.get("name", "")
        print("  [%d/%d] %s..." % (i, len(plantas), nombre))

        latest = post(token, "/v1.0/station/latest", {"stationId": sid})
        dia = energia_periodo(token, sid, 2, dia_start, dia_end)
        mes = energia_periodo(token, sid, 3, mes_start, mes_end)
        anio = energia_periodo(token, sid, 4, anio_start, anio_end)
        alertas, alerta_principal = contar_alertas(token, sid, hace3_ts, ahora_ts)

        resultado.append({
            "id": sid,
            "nombre": nombre,
            "kwp": p.get("installedCapacity"),
            "tipo": p.get("gridInterconnectionType"),
            "estado": p.get("connectionStatus"),
            "potenciaActual": latest.get("generationPower"),
            "consumoActual": latest.get("consumptionPower"),
            "bateriaSOC": latest.get("batterySOC"),
            "dia": dia,
            "mes": mes,
            "anio": anio,
            "alertas3d": alertas,
            "alertaPrincipal": alerta_principal,
        })
        time.sleep(0.3)

    salida = {
        "actualizado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "totalPlantas": len(resultado),
        "plantas": resultado,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print("OK - data.json generado con", len(resultado), "plantas")


if __name__ == "__main__":
    main()
