import os
import json
import math
import time
from datetime import datetime, timezone, timedelta
import requests

BEACHES = {
    "verdon": {"nom": "Le Verdon (Pointe de Grave)", "lat": 45.568, "lon": -1.085, "berme": 2.90, "dune": 4.20, "orient": 285},
    "soulac": {"nom": "Soulac-sur-Mer", "lat": 45.515, "lon": -1.132, "berme": 2.85, "dune": 4.10, "orient": 282},
    "amélie": {"nom": "Soulac (L'Amélie)", "lat": 45.485, "lon": -1.142, "berme": 2.85, "dune": 4.15, "orient": 281},
    "montalivet": {"nom": "Vendays-Montalivet", "lat": 45.378, "lon": -1.161, "berme": 3.00, "dune": 4.45, "orient": 280},
    "hourtin": {"nom": "Hourtin Plage", "lat": 45.221, "lon": -1.178, "berme": 3.10, "dune": 4.70, "orient": 278},
    "carcans": {"nom": "Carcans Plage", "lat": 45.085, "lon": -1.192, "berme": 3.15, "dune": 4.80, "orient": 277},
    "lacanau_lion": {"nom": "Lacanau — Le Lion", "lat": 45.035, "lon": -1.196, "berme": 3.10, "dune": 4.70, "orient": 276},
    "lacanau_nord": {"nom": "Lacanau — Plage Nord", "lat": 45.016, "lon": -1.199, "berme": 3.05, "dune": 4.60, "orient": 276},
    "lacanau_centrale": {"nom": "Lacanau — Plage Centrale", "lat": 45.002, "lon": -1.201, "berme": 3.00, "dune": 4.55, "orient": 276},
    "lacanau_sud": {"nom": "Lacanau — Plage Sud", "lat": 44.991, "lon": -1.203, "berme": 3.05, "dune": 4.65, "orient": 276},
    "lacanau_ecureuils": {"nom": "Lacanau — Les Écureuils", "lat": 44.978, "lon": -1.205, "berme": 3.10, "dune": 4.75, "orient": 276},
    "lacanau_supersud": {"nom": "Lacanau — Super Sud", "lat": 44.962, "lon": -1.208, "berme": 3.15, "dune": 4.85, "orient": 275},
    "lacanau_alexandre": {"nom": "Lacanau — La Alexandre", "lat": 44.938, "lon": -1.211, "berme": 3.18, "dune": 4.95, "orient": 275},
    "porge_gressier": {"nom": "Le Porge — Le Gressier", "lat": 44.915, "lon": -1.212, "berme": 3.20, "dune": 5.00, "orient": 275},
    "porge_centrale": {"nom": "Le Porge — Plage Centrale", "lat": 44.892, "lon": -1.215, "berme": 3.20, "dune": 5.05, "orient": 275},
    "porge_jenny": {"nom": "Le Porge — La Jenny", "lat": 44.862, "lon": -1.219, "berme": 3.18, "dune": 4.95, "orient": 275},
    "grand_crohot": {"nom": "Lège — Le Grand Crohot", "lat": 44.812, "lon": -1.226, "berme": 3.15, "dune": 4.90, "orient": 275},
    "truc_vert": {"nom": "Cap Ferret — Le Truc Vert", "lat": 44.738, "lon": -1.239, "berme": 3.10, "dune": 4.75, "orient": 274},
    "garonne": {"nom": "Cap Ferret — La Garonne", "lat": 44.705, "lon": -1.245, "berme": 3.05, "dune": 4.65, "orient": 274},
    "torchere": {"nom": "Cap Ferret — La Torchère", "lat": 44.675, "lon": -1.251, "berme": 3.00, "dune": 4.55, "orient": 273},
    "horizon": {"nom": "Cap Ferret — L'Horizon", "lat": 44.645, "lon": -1.256, "berme": 2.95, "dune": 4.50, "orient": 272},
    "dunes_ferret": {"nom": "Cap Ferret — Les Dunes", "lat": 44.622, "lon": -1.254, "berme": 2.90, "dune": 4.40, "orient": 272},
    "pointe_ferret": {"nom": "Cap Ferret — La Pointe", "lat": 44.602, "lon": -1.248, "berme": 2.80, "dune": 4.25, "orient": 271},
    "petit_nice": {"nom": "Pyla-sur-Mer — Le Petit Nice", "lat": 44.572, "lon": -1.226, "berme": 2.80, "dune": 4.25, "orient": 270},
    "la_lagune": {"nom": "Pyla-sur-Mer — La Lagune", "lat": 44.552, "lon": -1.233, "berme": 2.85, "dune": 4.35, "orient": 270},
    "salie_nord": {"nom": "La Teste — La Salie Nord", "lat": 44.532, "lon": -1.240, "berme": 2.90, "dune": 4.40, "orient": 271},
    "salie_sud": {"nom": "La Teste — La Salie Sud", "lat": 44.512, "lon": -1.245, "berme": 2.95, "dune": 4.45, "orient": 272},
    "biscarrosse": {"nom": "Biscarrosse Plage", "lat": 44.448, "lon": -1.254, "berme": 3.05, "dune": 4.60, "orient": 273}
}
def fetch_json_retry(url, headers=None, retries=3):
    req_headers = {"User-Agent": "Observatoire-Littoral-Gironde/2.0"}
    if headers:
        req_headers.update(headers)
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=req_headers, timeout=25)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Tentative {attempt + 1}/{retries} échouée : {e}")
            time.sleep(2 * (attempt + 1))
    return None

def get_accurate_tide(dt_utc):
    nm_ref = datetime(2026, 1, 18, 19, 52, tzinfo=timezone.utc)
    per_ref = datetime(2026, 1, 1, 21, 44, tzinfo=timezone.utc)
    syn = 29.530588853
    anom = 27.55454988

    days_nm = (dt_utc - nm_ref).total_seconds() / 86400.0
    phase_syn = 2.0 * math.pi * ((days_nm - 1.5) / (syn / 2.0))

    days_per = (dt_utc - per_ref).total_seconds() / 86400.0
    phase_anom = 2.0 * math.pi * ((days_per - 1.5) / anom)

    doy = dt_utc.timetuple().tm_yday
    decl_factor = math.cos(2.0 * math.pi * (doy - 80) / 182.625)

    amp = 32.0 + 7.5 * math.cos(phase_anom) + 5.5 * decl_factor
    coeff = int(round(71.0 + amp * math.cos(phase_syn)))
    coeff = max(20, min(120, coeff))

    pm_ngf = round(1.80 + (coeff - 20) * (1.30 / 100.0), 2)
    return coeff, pm_ngf

def send_email_alert(alerts_list):
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    email_to = (os.environ.get("ALERT_EMAIL_TO") or os.environ.get("ALERT_EMAIL") or "").strip()
    if not api_key or not email_to or not alerts_list:
        print("Aucune alerte e-mail envoyée.")
        return

    payload = {
        "sender": {"name": "Alerte Littoral Gironde", "email": "VOTRE_EMAIL_BREVO@exemple.fr"},
        "to": [{"email": email_to}],
        "subject": f"⚠️ Vigilance Érosion Gironde ({len(alerts_list)} secteurs en alerte sous 48h)",
        "htmlContent": "<h3>Bulletin de vigilance morphodynamique (48h)</h3><ul>" +
                       "".join(f"<li>{item}</li>" for item in alerts_list) + "</ul>"
    }
    try:
        r = requests.post(
            "https://brevo.com",
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        print("Statut envoi Brevo :", r.status_code)
    except Exception as e:
        print("Erreur envoi e-mail :", e)

def main():
    now = datetime.now(timezone.utc)
    dates = [(now + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    zones_coords = {}
    for key, info in BEACHES.items():
        z_key = f"{round(info['lat'], 1)}_{round(info['lon'], 1)}"
        if z_key not in zones_coords:
            zones_coords[z_key] = {"lat": info["lat"], "lon": info["lon"], "marine": None, "weather": None}

    for z_key, z_data in zones_coords.items():
        m_url = f"https://open-meteo.com{z_data['lat']}&longitude={z_data['lon']}&hourly=wave_height,wave_period,wave_direction&forecast_days=7&timezone=Europe%2FParis"
        w_url = f"https://open-meteo.com{z_data['lat']}&longitude={z_data['lon']}&hourly=wind_speed_10m,wind_direction_10m,surface_pressure&forecast_days=7&timezone=Europe%2FParis"
        z_data["marine"] = fetch_json_retry(m_url)
        z_data["weather"] = fetch_json_retry(w_url)
        time.sleep(0.3)

    beaches_output = {}
    alerts_48h = []

    for key, info in BEACHES.items():
        z_key = f"{round(info['lat'], 1)}_{round(info['lon'], 1)}"
        marine = zones_coords[z_key]["marine"]
        weather = zones_coords[z_key]["weather"]
        daily_list = []

        for day_idx, d_str in enumerate(dates):
            dt_day = now + timedelta(days=day_idx, hours=12)
            coeff, pm_ngf = get_accurate_tide(dt_day)
            h_slice = slice(day_idx * 24, (day_idx + 1) * 24)

            if marine and "hourly" in marine:
                hs_vals = [x for x in marine["hourly"]["wave_height"][h_slice] if x is not None]
                tp_vals = [x for x in marine["hourly"]["wave_period"][h_slice] if x is not None]
                wd_vals = [x for x in marine["hourly"]["wave_direction"][h_slice] if x is not None]
                hs = max(hs_vals) if hs_vals else 1.5
                tp = max(tp_vals) if tp_vals else 10.0
                wave_dir = int(wd_vals[len(wd_vals) // 2]) if wd_vals else 280
            else:
                hs, tp, wave_dir = 1.6, 10.5, 280

            if weather and "hourly" in weather:
                wind_vals = [x for x in weather["hourly"]["wind_speed_10m"][h_slice] if x is not None]
                wdir_vals = [x for x in weather["hourly"]["wind_direction_10m"][h_slice] if x is not None]
                press_vals = [x for x in weather["hourly"]["surface_pressure"][h_slice] if x is not None]
                wind = max(wind_vals) if wind_vals else 20.0
                wind_dir = int(wdir_vals[len(wdir_vals) // 2]) if wdir_vals else 270
                press = min(press_vals) if press_vals else 1015.0
            else:
                wind, wind_dir, press = 20.0, 270, 1015.0

            wind_angle_rad = math.radians(((wind_dir - info["orient"] + 180) % 360) - 180)
            onshore_wind = wind * math.cos(wind_angle_rad)

            surcote_baro = max(0.0, (1015.0 - press) * 0.01)
            wind_setup = max(-0.08, onshore_wind * 0.0045)
            runup = 0.34 * math.sqrt(hs * (1.56 * (tp ** 2)) * 0.042)
            total_water = round(pm_ngf + surcote_baro + wind_setup + runup, 2)

            wave_obliquity = abs(((wave_dir - info["orient"] + 180) % 360) - 180)
            obliquity_factor = 1.22 if 18 <= wave_obliquity <= 55 else 1.0
            wind_cut_factor = 1.0 + max(-0.12, min(0.28, onshore_wind * 0.0045))
            effective_power = int(round((hs ** 2) * tp * obliquity_factor * wind_cut_factor))

            dune_attack = total_water >= (info["dune"] - 0.12)
            cut_estran = (not dune_attack) and (effective_power >= 58 or (total_water >= info["berme"] and hs >= 2.25))
            status = "dune" if dune_attack else ("cut" if cut_estran else "safe")

            if day_idx <= 1 and status != "safe":
                label = "ATTAQUE DUNE (Rouge)" if status == "dune" else "CUT D'ESTRAN (Bleu)"
                alerts_48h.append(f"<b>{info['nom']}</b> ({d_str}) : {label} — Houle {hs}m/{tp}s, Vent {wind}km/h, Coeff {coeff}, Eau max +{total_water}m NGF")

            daily_list.append({
                "date": d_str,
                "hs": round(hs, 2),
                "tp": round(tp, 1),
                "waveDir": wave_dir,
                "wind": round(wind, 1),
                "windDir": wind_dir,
                "coeff": coeff,
                "totalWater": total_water,
                "effectivePower": effective_power,
                "duneAttack": dune_attack,
                "cutEstran": cut_estran,
                "status": status
            })

        beaches_output[key] = daily_list

    output = {
        "updated_at": now.strftime("%d/%m/%Y %H:%M UTC"),
        "beaches": beaches_output
    }
    with open("data_littoral.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("Mise à jour terminée pour", len(beaches_output), "plages.")
    send_email_alert(alerts_48h)

if __name__ == "__main__":
    main()
