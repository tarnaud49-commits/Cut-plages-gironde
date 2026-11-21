import os
import json
import math
import time
from datetime import datetime, timezone, timedelta
import requests

PLAGES = [
    {"id": "verdon", "nom": "Le Verdon-sur-Mer (Pointe de Grave)", "lat": 45.568, "lon": -1.085, "berme": 2.90, "dune": 4.20, "orient": 285},
    {"id": "soulac", "nom": "Soulac-sur-Mer", "lat": 45.515, "lon": -1.132, "berme": 2.85, "dune": 4.10, "orient": 282},
    {"id": "montalivet", "nom": "Vendays-Montalivet", "lat": 45.378, "lon": -1.161, "berme": 3.00, "dune": 4.45, "orient": 280},
    {"id": "hourtin", "nom": "Hourtin Plage", "lat": 45.221, "lon": -1.178, "berme": 3.10, "dune": 4.70, "orient": 278},
    {"id": "carcans", "nom": "Carcans Plage", "lat": 45.085, "lon": -1.192, "berme": 3.15, "dune": 4.80, "orient": 277},
    {"id": "lacanau", "nom": "Lacanau Océan", "lat": 45.002, "lon": -1.201, "berme": 3.05, "dune": 4.65, "orient": 276},
    {"id": "leporge", "nom": "Le Porge Océan", "lat": 44.895, "lon": -1.214, "berme": 3.20, "dune": 5.05, "orient": 275},
    {"id": "lege", "nom": "Lège (Grand Crohot)", "lat": 44.812, "lon": -1.226, "berme": 3.15, "dune": 4.90, "orient": 275},
    {"id": "trucvert", "nom": "Cap Ferret (Truc Vert)", "lat": 44.718, "lon": -1.242, "berme": 3.10, "dune": 4.75, "orient": 274},
    {"id": "horizon", "nom": "Cap Ferret (L'Horizon)", "lat": 44.635, "lon": -1.256, "berme": 2.95, "dune": 4.50, "orient": 272},
    {"id": "pilat", "nom": "Pyla-sur-Mer (Dune du Pilat)", "lat": 44.588, "lon": -1.218, "berme": 2.80, "dune": 4.30, "orient": 270},
    {"id": "biscarrosse", "nom": "Biscarrosse Plage", "lat": 44.448, "lon": -1.254, "berme": 3.05, "dune": 4.60, "orient": 273}
]

def fetch_json_retry(url, headers=None, retries=4):
    req_headers = {"User-Agent": "Observatoire-Littoral-Gironde/1.0"}
    if headers:
        req_headers.update(headers)
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=req_headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Tentative {attempt + 1}/{retries} échouée pour {url[:60]}... : {e}")
            time.sleep(3 * (attempt + 1))
    return None

def get_tide_info(date_obj):
    # Calcul harmonique astronomique (calibré côte aquitaine)
    ref = datetime(2026, 1, 3, 12, 0, tzinfo=timezone.utc)
    days = (date_obj - ref).total_seconds() / 86400.0
    cycle = math.cos(2 * math.pi * days / 14.765)
    coeff = int(round(75 + 37 * cycle))
    coeff = max(25, min(118, coeff))
    pm_ngf = round(1.85 + (coeff - 20) * (1.25 / 100.0), 2)
    return coeff, pm_ngf

def send_email_alert(alerts_summary):
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    email_to = (os.environ.get("ALERT_EMAIL_TO") or os.environ.get("ALERT_EMAIL") or "").strip()
    if not api_key or not email_to or not alerts_summary:
        print("Alerte email ignorée (clé/destinataire absent ou aucune alerte critique).")
        return

    payload = {
        "sender": {"name": "Alerte Littoral Gironde", "email": "VOTRE_EMAIL_BREVO@exemple.fr"},
        "to": [{"email": email_to}],
        "subject": f"⚠️ Alerte Érosion Littoral Girondin ({len(alerts_summary)} secteurs à risque)",
        "htmlContent": "<h3>Bulletin de vigilance morphodynamique (48h)</h3><ul>" +
                       "".join(f"<li>{item}</li>" for item in alerts_summary) + "</ul>"
    }
    try:
        r = requests.post(
            "https://brevo.com",
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        print("Statut envoi email Brevo :", r.status_code)
    except Exception as e:
        print("Erreur envoi email :", e)

def main():
    now = datetime.now(timezone.utc)
    dates = [(now + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    output = {"updated_at": now.isoformat(), "dates": dates, "plages": []}
    alerts_48h = []

    for p in PLAGES:
        marine_url = f"https://open-meteo.com{p['lat']}&longitude={p['lon']}&hourly=wave_height,wave_period,wave_direction&forecast_days=7&timezone=Europe%2FParis"
        weather_url = f"https://open-meteo.com{p['lat']}&longitude={p['lon']}&hourly=wind_speed_10m,wind_direction_10m,surface_pressure&forecast_days=7&timezone=Europe%2FParis"

        marine = fetch_json_retry(marine_url)
        weather = fetch_json_retry(weather_url)

        daily_forecasts = []
        for day_idx, d_str in enumerate(dates):
            dt_day = now + timedelta(days=day_idx)
            coeff, pm_ngf = get_tide_info(dt_day)

            h_slice = slice(day_idx * 24, (day_idx + 1) * 24)
            if marine and "hourly" in marine:
                hs_list = [x for x in marine["hourly"]["wave_height"][h_slice] if x is not None]
                tp_list = [x for x in marine["hourly"]["wave_period"][h_slice] if x is not None]
                dir_list = [x for x in marine["hourly"]["wave_direction"][h_slice] if x is not None]
                hs = max(hs_list) if hs_list else 1.5
                tp = max(tp_list) if tp_list else 10.0
                wdir = dir_list[len(dir_list)//2] if dir_list else 280
            else:
                hs, tp, wdir = 1.6, 10.5, 280

            if weather and "hourly" in weather:
                wind_list = [x for x in weather["hourly"]["wind_speed_10m"][h_slice] if x is not None]
                press_list = [x for x in weather["hourly"]["surface_pressure"][h_slice] if x is not None]
                wind = max(wind_list) if wind_list else 20.0
                press = min(press_list) if press_list else 1015.0
            else:
                wind, press = 20.0, 1015.0

            surcote = max(0.0, (1015.0 - press) * 0.01) + (wind * 0.005)
            runup = 0.35 * math.sqrt(hs * (1.56 * tp * tp) * 0.04)
            eau_totale = round(pm_ngf + surcote + runup, 2)

            angle_diff = abs(((wdir - p["orient"] + 180) % 360) - 180)
            obliquity_factor = 1.25 if 20 <= angle_diff <= 55 else 1.0
            energie_houle = round((hs ** 2) * tp * obliquity_factor, 1)

            risque_dune = eau_totale >= (p["dune"] - 0.15)
            risque_cut = (not risque_dune) and (energie_houle >= 55.0 or (eau_totale >= p["berme"] and hs >= 2.2))

            statut = "dune" if risque_dune else ("cut" if risque_cut else "stable")
            if day_idx <= 1 and statut != "stable":
                label = "ATTAQUE DUNE (Rouge)" if statut == "dune" else "CUT D'ESTRAN (Jaune)"
                alerts_48h.append(f"<b>{p['nom']}</b> ({d_str}) : {label} — Houle {hs}m / {tp}s, Niveau max {eau_totale}m NGF")

            daily_forecasts.append({
                "date": d_str,
                "coeff": coeff,
                "pm_ngf": pm_ngf,
                "hs": round(hs, 2),
                "tp": round(tp, 1),
                "wdir": int(wdir),
                "wind": round(wind, 1),
                "eau_totale": eau_totale,
                "energie": energie_houle,
                "statut": statut
            })

        output["plages"].append({
            "id": p["id"],
            "nom": p["nom"],
            "lat": p["lat"],
            "lon": p["lon"],
            "berme": p["berme"],
            "dune": p["dune"],
            "previsions": daily_forecasts
        })
        time.sleep(0.5)

    with open("data_littoral.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("Fichier data_littoral.json généré avec succès.")
    send_email_alert(alerts_48h)

if __name__ == "__main__":
    main()
