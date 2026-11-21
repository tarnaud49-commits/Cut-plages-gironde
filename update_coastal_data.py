import json
import math
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone

BEACHES = [
    {"id": "verdon", "name": "Le Verdon-sur-Mer (Pointe de Grave)", "lat": 45.547, "lon": -1.077, "berm": 3.15, "dune": 4.30},
    {"id": "soulac", "name": "Soulac-sur-Mer (Plage Centrale)", "lat": 45.514, "lon": -1.132, "berm": 3.05, "dune": 4.10},
    {"id": "amélie", "name": "L'Amélie (Soulac Sud)", "lat": 45.483, "lon": -1.148, "berm": 3.10, "dune": 4.20},
    {"id": "montalivet", "name": "Vendays-Montalivet", "lat": 45.376, "lon": -1.179, "berm": 3.25, "dune": 4.45},
    {"id": "hourtin", "name": "Hourtin Plage", "lat": 45.221, "lon": -1.198, "berm": 3.40, "dune": 4.75},
    {"id": "carcans", "name": "Carcans Plage", "lat": 45.083, "lon": -1.206, "berm": 3.45, "dune": 4.85},
    {"id": "lacanau", "name": "Lacanau Océan", "lat": 45.002, "lon": -1.209, "berm": 3.40, "dune": 4.65},
    {"id": "leporge", "name": "Le Porge Océan", "lat": 44.885, "lon": -1.219, "berm": 3.55, "dune": 5.05},
    {"id": "trucvert", "name": "Lège-Cap-Ferret (Truc Vert)", "lat": 44.738, "lon": -1.249, "berm": 3.50, "dune": 4.95},
    {"id": "horizon", "name": "Cap Ferret (Plage de l'Horizon)", "lat": 44.639, "lon": -1.258, "berm": 3.35, "dune": 4.60},
    {"id": "pilat", "name": "Pyla-sur-Mer (La Corniche)", "lat": 44.588, "lon": -1.219, "berm": 3.20, "dune": 4.35},
    {"id": "biscarrosse", "name": "Biscarrosse Plage", "lat": 44.447, "lon": -1.256, "berm": 3.45, "dune": 4.80},
]

def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "GirondeErosionMonitor/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_tide_coeff(date_str):
    shom_key = os.getenv("SHOM_API_KEY", "").strip()
    if shom_key:
        try:
            url = f"https://services.data.shom.fr/maregraphie/service/tide/coeff?port=CORDOUAN&date={date_str}"
            data = fetch_json(url, headers={"apikey": shom_key})
            if isinstance(data, dict) and "coeff" in data:
                return int(data["coeff"])
        except Exception as e:
            print(f"Repli harmonique SHOM pour {date_str}: {e}")

    d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    ref = datetime(2026, 1, 3, tzinfo=timezone.utc)
    days = (d - ref).total_seconds() / 86400.0
    phase = (2 * math.pi * days) / 14.765
    return round(72 + 38 * math.cos(phase))

def evaluate_beach_day(beach, day_raw):
    hs = day_raw["hs"]
    tp = day_raw["tp"]
    wave_dir = day_raw["waveDir"]
    wind = day_raw["wind"]
    wind_dir = day_raw["windDir"]
    coeff = day_raw["coeff"]

    tide_height = 2.15 + (coeff - 70) * 0.015
    wind_surge = (wind - 30) * 0.012 if (wind > 30 and 210 <= wind_dir <= 330) else 0.05
    runup = 0.38 * hs * math.sqrt(tp / 10.0)
    total_water = round(tide_height + wind_surge + runup, 2)

    wave_power = (hs ** 2) * tp
    oblique_factor = 1.15 if (wave_dir >= 285 or wave_dir <= 245) else 1.0
    effective_power = round(wave_power * oblique_factor)

    dune_attack = total_water >= beach["dune"]
    cut_estran = (not dune_attack) and (effective_power >= 75 or (total_water >= beach["berm"] and hs >= 2.2))
    status = "dune" if dune_attack else ("cut" if cut_estran else "safe")

    return {
        "date": day_raw["date"],
        "hs": round(hs, 2),
        "tp": round(tp, 1),
        "waveDir": round(wave_dir),
        "wind": round(wind, 1),
        "windDir": round(wind_dir),
        "coeff": coeff,
        "totalWater": total_water,
        "effectivePower": effective_power,
        "duneAttack": dune_attack,
        "cutEstran": cut_estran,
        "status": status
    }

def send_alerts(alerts_today_or_tomorrow):
    if not alerts_today_or_tomorrow:
        print("Aucune alerte érosion majeure détectée à J ou J+1.")
        return

    lines = ["⚠️ VIGILANCE ÉROSION LITTORALE (Gironde - Biscarrosse)", ""]
    for item in alerts_today_or_tomorrow:
        icon = "🔴 ATTAQUE PIED DE DUNE" if item["status"] == "dune" else "🟡 CUT D'ESTRAN"
        lines.append(f"- {item['date']} | {item['beach']} : {icon} (Niv. +{item['totalWater']}m NGF, Houle {item['hs']}m/{item['tp']}s, Coeff {item['coeff']})")

    message = "\n".join(lines)
    print(message)

    # 1. Envoi E-mail via API Brevo (Sendinblue) si configuré
    brevo_key = os.getenv("BREVO_API_KEY", "").strip()
    alert_email = os.getenv("ALERT_EMAIL", "").strip()
    if brevo_key and alert_email:
        payload = json.dumps({
            "sender": {"name": "Vigilance Littoral", "email": alert_email},
            "to": [{"email": alert_email}],
            "subject": "⚠️ Alerte Érosion Côtière - Littoral Girondin",
            "textContent": message
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=payload,
            headers={"api-key": brevo_key, "Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(req, timeout=15)
            print("Alerte e-mail envoyée via Brevo.")
        except Exception as e:
            print(f"Erreur envoi e-mail Brevo : {e}")

    # 2. Envoi SMS via Twilio si configuré
    tw_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    tw_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    tw_from = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    tw_to = os.getenv("ALERT_PHONE_NUMBER", "").strip()
    if tw_sid and tw_token and tw_from and tw_to:
        sms_body = f"Vigilance Littoral: {len(alerts_today_or_tomorrow)} secteur(s) en alerte érosion (Cut/Dune) sous 48h. Consultez la carte."
        data = urllib.parse.urlencode({"From": tw_from, "To": tw_to, "Body": sms_body}).encode("utf-8")
        req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{tw_sid}/Messages.json", data=data)
        import base64
        auth = base64.b64encode(f"{tw_sid}:{tw_token}".encode("utf-8")).decode("utf-8")
        req.add_header("Authorization", f"Basic {auth}")
        try:
            urllib.request.urlopen(req, timeout=15)
            print("Alerte SMS envoyée via Twilio.")
        except Exception as e:
            print(f"Erreur envoi SMS Twilio : {e}")

def main():
    lats = ",".join(str(b["lat"]) for b in BEACHES)
    lons = ",".join(str(b["lon"]) for b in BEACHES)

    marine_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lats}&longitude={lons}&daily=wave_height_max,wave_period_max,wave_direction_dominant&timezone=Europe%2FParis&forecast_days=7"
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lats}&longitude={lons}&daily=wind_speed_10m_max,wind_direction_10m_dominant&timezone=Europe%2FParis&forecast_days=7"

    marine_data = fetch_json(marine_url)
    weather_data = fetch_json(weather_url)

    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "beaches": {}
    }

    alerts = []

    for idx, beach in enumerate(BEACHES):
        m_daily = marine_data[idx]["daily"]
        w_daily = weather_data[idx]["daily"]
        beach_days = []

        for d_idx, date_str in enumerate(m_daily["time"]):
            raw = {
                "date": date_str,
                "hs": m_daily["wave_height_max"][d_idx] or 1.2,
                "tp": m_daily["wave_period_max"][d_idx] or 9.0,
                "waveDir": m_daily["wave_direction_dominant"][d_idx] or 275,
                "wind": w_daily["wind_speed_10m_max"][d_idx] or 18.0,
                "windDir": w_daily["wind_direction_10m_dominant"][d_idx] or 270,
                "coeff": get_tide_coeff(date_str)
            }
            evaluated = evaluate_beach_day(beach, raw)
            beach_days.append(evaluated)

            if d_idx in (0, 1) and evaluated["status"] in ("cut", "dune"):
                alerts.append({
                    "date": date_str,
                    "beach": beach["name"],
                    "status": evaluated["status"],
                    "totalWater": evaluated["totalWater"],
                    "hs": evaluated["hs"],
                    "tp": evaluated["tp"],
                    "coeff": evaluated["coeff"]
                })

        output["beaches"][beach["id"]] = beach_days

    with open("data_littoral.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    send_alerts(alerts)

if __name__ == "__main__":
    main()
