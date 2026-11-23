import os
import json
import math
import time
from datetime import datetime, timezone, timedelta
import requests

BEACHES = {
    "verdon": {"nom": "Le Verdon (Pointe de Grave)", "lat": 45.568, "lon": -1.085, "berme": 2.90, "dune": 4.20, "orient": 285, "port": "verdon"},
    "soulac": {"nom": "Soulac-sur-Mer", "lat": 45.515, "lon": -1.132, "berme": 2.85, "dune": 4.10, "orient": 282, "port": "verdon"},
    "amélie": {"nom": "Soulac (L'Amélie)", "lat": 45.485, "lon": -1.142, "berme": 2.85, "dune": 4.15, "orient": 281, "port": "verdon"},
    "montalivet": {"nom": "Vendays-Montalivet", "lat": 45.378, "lon": -1.161, "berme": 3.00, "dune": 4.45, "orient": 280, "port": "verdon"},
    "hourtin": {"nom": "Hourtin Plage", "lat": 45.221, "lon": -1.178, "berme": 3.10, "dune": 4.70, "orient": 278, "port": "ferret"},
    "carcans": {"nom": "Carcans Plage", "lat": 45.085, "lon": -1.192, "berme": 3.15, "dune": 4.80, "orient": 277, "port": "ferret"},
    "lacanau_nord": {"nom": "Lacanau — Plage Nord", "lat": 45.016, "lon": -1.199, "berme": 3.05, "dune": 4.60, "orient": 276, "port": "ferret"},
    "lacanau_centrale": {"nom": "Lacanau — Plage Centrale", "lat": 45.002, "lon": -1.201, "berme": 3.00, "dune": 4.55, "orient": 276, "port": "ferret"},
    "lacanau_sud": {"nom": "Lacanau — Plage Sud", "lat": 44.991, "lon": -1.203, "berme": 3.05, "dune": 4.65, "orient": 276, "port": "ferret"},
    "lacanau_ecureuils": {"nom": "Lacanau — Les Écureuils", "lat": 44.978, "lon": -1.205, "berme": 3.10, "dune": 4.75, "orient": 276, "port": "ferret"},
    "lacanau_supersud": {"nom": "Lacanau — Super Sud", "lat": 44.962, "lon": -1.208, "berme": 3.15, "dune": 4.85, "orient": 275, "port": "ferret"},
    "lacanau_lion": {"nom": "Lacanau — Le Lion", "lat": 44.950, "lon": -1.2095, "berme": 3.16, "dune": 4.90, "orient": 275, "port": "ferret"},
    "lacanau_alexandre": {"nom": "Lacanau — La Alexandre", "lat": 44.938, "lon": -1.211, "berme": 3.18, "dune": 4.95, "orient": 275, "port": "ferret"},
    "porge_gressier": {"nom": "Le Porge — Le Gressier", "lat": 44.915, "lon": -1.212, "berme": 3.20, "dune": 5.00, "orient": 275, "port": "ferret"},
    "porge_centrale": {"nom": "Le Porge — Plage Centrale", "lat": 44.892, "lon": -1.215, "berme": 3.20, "dune": 5.05, "orient": 275, "port": "ferret"},
    "porge_jenny": {"nom": "Le Porge — La Jenny", "lat": 44.862, "lon": -1.219, "berme": 3.18, "dune": 4.95, "orient": 275, "port": "ferret"},
    "grand_crohot": {"nom": "Lège — Le Grand Crohot", "lat": 44.812, "lon": -1.226, "berme": 3.15, "dune": 4.90, "orient": 275, "port": "ferret"},
    "truc_vert": {"nom": "Cap Ferret — Le Truc Vert", "lat": 44.738, "lon": -1.239, "berme": 3.10, "dune": 4.75, "orient": 274, "port": "ferret"},
    "garonne": {"nom": "Cap Ferret — La Garonne", "lat": 44.705, "lon": -1.245, "berme": 3.05, "dune": 4.65, "orient": 274, "port": "ferret"},
    "torchere": {"nom": "Cap Ferret — La Torchère", "lat": 44.675, "lon": -1.251, "berme": 3.00, "dune": 4.55, "orient": 273, "port": "ferret"},
    "horizon": {"nom": "Cap Ferret — L'Horizon", "lat": 44.645, "lon": -1.256, "berme": 2.95, "dune": 4.50, "orient": 272, "port": "ferret"},
    "dunes_ferret": {"nom": "Cap Ferret — Les Dunes", "lat": 44.622, "lon": -1.254, "berme": 2.90, "dune": 4.40, "orient": 272, "port": "ferret"},
    "pointe_ferret": {"nom": "Cap Ferret — La Pointe", "lat": 44.602, "lon": -1.248, "berme": 2.80, "dune": 4.25, "orient": 271, "port": "ferret"},
    "petit_nice": {"nom": "Pyla-sur-Mer — Le Petit Nice", "lat": 44.572, "lon": -1.226, "berme": 2.80, "dune": 4.25, "orient": 270, "port": "arcachon"},
    "la_lagune": {"nom": "Pyla-sur-Mer — La Lagune", "lat": 44.552, "lon": -1.233, "berme": 2.85, "dune": 4.35, "orient": 270, "port": "arcachon"},
    "salie_nord": {"nom": "La Teste — La Salie Nord", "lat": 44.532, "lon": -1.240, "berme": 2.90, "dune": 4.40, "orient": 271, "port": "arcachon"},
    "salie_sud": {"nom": "La Teste — La Salie Sud", "lat": 44.512, "lon": -1.245, "berme": 2.95, "dune": 4.45, "orient": 272, "port": "arcachon"},
    "biscarrosse": {"nom": "Biscarrosse Plage", "lat": 44.448, "lon": -1.254, "berme": 3.05, "dune": 4.60, "orient": 273, "port": "arcachon"}
}
def fetch_json_retry(url, headers=None, retries=3):
    req_headers = {"User-Agent": "Observatoire-Littoral-Gironde/3.0"}
    if headers:
        req_headers.update(headers)
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=req_headers, timeout=25)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Tentative {attempt + 1}/{retries} échouée : {e}")
            time.sleep(1.5 * (attempt + 1))
    return None

def get_accurate_tide(dt_utc, port="ferret"):
    y, m = dt_utc.year, dt_utc.month
    d = dt_utc.day + (dt_utc.hour + dt_utc.minute / 60.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    A = y // 100
    B = 2 - A + (A // 4)
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5 - 1.22

    T = (jd - 2451545.0) / 36525.0
    D = math.radians((297.8501921 + 445267.1114034 * T) % 360)
    M = math.radians((357.5291092 + 35999.0502909 * T) % 360)
    Mp = math.radians((134.9633964 + 477198.8675055 * T) % 360)
    F = math.radians((93.2720950 + 483202.0175233 * T) % 360)

    ratio = 1.0 + 0.16 * math.cos(Mp) + 0.04 * math.cos(M) + 0.09 * math.cos(2 * F)
    coeff = int(round(71.5 + 21.8 * ratio * math.cos(2 * D)))
    coeff = max(20, min(120, coeff))

    if port == "verdon":
        hauteur_zh = 3.25 + (coeff - 20) * (2.05 / 100.0)
        pm_ngf = round(hauteur_zh - 2.75, 2)
    elif port == "arcachon":
        hauteur_zh = 2.68 + (coeff - 20) * (1.62 / 100.0)
        pm_ngf = round(hauteur_zh - 2.10, 2)
    else:
        hauteur_zh = 2.65 + (coeff - 20) * (1.58 / 100.0)
        pm_ngf = round(hauteur_zh - 2.15, 2)
    return coeff, pm_ngf
    
def get_tide_times(dt_utc, port="ferret"):
    ref_utc = datetime(2026, 11, 21, 0, 0, tzinfo=timezone.utc)
    days_elapsed = (dt_utc.replace(hour=0, minute=0, second=0, microsecond=0) - ref_utc).total_seconds() / 86400.0
    port_offset_min = 25 if port == "verdon" else (15 if port == "arcachon" else 0)
    base_pm1_min = 117.0 + (days_elapsed * 48.8) + port_offset_min
    step_min = 372.2
    pm_list, bm_list = [], []
    for k in range(-2, 6):
        t_min = base_pm1_min + k * step_min
        if 0 <= t_min < 1440:
            h, m = int(t_min // 60), int(round(t_min % 60))
            if m == 60:
                h += 1
                m = 0
            label = f"{h:02d}h{m:02d}"
            if k % 2 == 0:
                pm_list.append(label)
            else:
                bm_list.append(label)
    return " / ".join(pm_list) or "--", " / ".join(bm_list) or "--"

def send_email_alert(alerts_list):
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    email_to = (os.environ.get("ALERT_EMAIL_TO") or os.environ.get("ALERT_EMAIL") or "").strip()
    if not api_key or not email_to or not alerts_list:
        print("Aucune alerte e-mail envoyée.")
        return

    payload = {
        "sender": {"name": "Alerte Littoral Gironde", "email": "tarnaud49@gmail.com"},
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
    beaches_output = {}
    alerts_48h = []

    for key, info in BEACHES.items():
        m_url = f"https://open-meteo.com{info['lat']}&longitude={info['lon']}&hourly=wave_height,wave_period,wave_direction&forecast_days=7&timezone=Europe%2FParis"
        w_url = f"https://open-meteo.com{info['lat']}&longitude={info['lon']}&hourly=wind_speed_10m,wind_direction_10m,surface_pressure&forecast_days=7&timezone=Europe%2FParis"
        marine = fetch_json_retry(m_url)
        weather = fetch_json_retry(w_url)
        daily_list = []

        for day_idx, d_str in enumerate(dates):
            dt_day = now + timedelta(days=day_idx, hours=12)
            coeff, pm_ngf = get_accurate_tide(dt_day, info["port"])
            pm_times, bm_times = get_tide_times(dt_day, info["port"])
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
                "pmTimes": pm_times,
                "bmTimes": bm_times,
                "totalWater": total_water,
                "effectivePower": effective_power,
                "duneAttack": dune_attack,
                "cutEstran": cut_estran,
                "status": status
            })

        beaches_output[key] = daily_list
        time.sleep(0.25)

    output = {
        "updated_at": now.strftime("%d/%m/%Y %H:%M UTC"),
        "beaches": beaches_output
    }
    with open("data_littoral.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("Mise à jour individuelle terminée pour", len(beaches_output), "plages.")
    send_email_alert(alerts_48h)

if __name__ == "__main__":
    main()
