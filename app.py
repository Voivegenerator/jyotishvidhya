import json
import os
from datetime import datetime, timedelta, date as date_cls

from flask import Flask, render_template, request, jsonify, Response, send_from_directory

import panchang as pg
import chatbot

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "data", "festivals.json"), encoding="utf-8") as f:
    FESTIVALS = json.load(f)
with open(os.path.join(BASE_DIR, "data", "rashifal.json"), encoding="utf-8") as f:
    RASHIFAL = json.load(f)

DEFAULT_CITY = {"name": "New Delhi, India", "lat": 28.6139, "lon": 77.2090, "tz": 5.5}

CITIES = {
    "new-delhi": {"name": "New Delhi", "lat": 28.6139, "lon": 77.2090, "tz": 5.5},
    "mumbai": {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777, "tz": 5.5},
    "kolkata": {"name": "Kolkata", "lat": 22.5726, "lon": 88.3639, "tz": 5.5},
    "chennai": {"name": "Chennai", "lat": 13.0827, "lon": 80.2707, "tz": 5.5},
    "bengaluru": {"name": "Bengaluru", "lat": 12.9716, "lon": 77.5946, "tz": 5.5},
    "hyderabad": {"name": "Hyderabad", "lat": 17.3850, "lon": 78.4867, "tz": 5.5},
    "pune": {"name": "Pune", "lat": 18.5204, "lon": 73.8567, "tz": 5.5},
    "jaipur": {"name": "Jaipur", "lat": 26.9124, "lon": 75.7873, "tz": 5.5},
    "lucknow": {"name": "Lucknow", "lat": 26.8467, "lon": 80.9462, "tz": 5.5},
    "patna": {"name": "Patna", "lat": 25.5941, "lon": 85.1376, "tz": 5.5},
    "varanasi": {"name": "Varanasi", "lat": 25.3176, "lon": 82.9739, "tz": 5.5},
    "ahmedabad": {"name": "Ahmedabad", "lat": 23.0225, "lon": 72.5714, "tz": 5.5},
}


def fmt_t(dt):
    if dt is None:
        return "--:--"
    return dt.strftime("%I:%M %p")


app.jinja_env.filters["fmt_t"] = fmt_t


@app.context_processor
def inject_globals():
    return {"cities": CITIES, "current_year": datetime.now().year}


@app.route("/")
def home():
    city_key = request.args.get("city", "new-delhi")
    city = CITIES.get(city_key, CITIES["new-delhi"])
    now = datetime.now()
    p = pg.calc_panchang(now, city["lat"], city["lon"], city["tz"])

    today_str = now.strftime("%Y-%m-%d")
    upcoming = [f for f in FESTIVALS if f["date"] >= today_str][:8]

    return render_template(
        "index.html", p=p, city=city, city_key=city_key, now=now, upcoming=upcoming,
    )


@app.route("/panchang/<datestr>")
def panchang_for_date(datestr):
    city_key = request.args.get("city", "new-delhi")
    city = CITIES.get(city_key, CITIES["new-delhi"])
    try:
        dt = datetime.strptime(datestr, "%Y-%m-%d").replace(hour=12)
    except ValueError:
        dt = datetime.now()
    p = pg.calc_panchang(dt, city["lat"], city["lon"], city["tz"])
    prev_day = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    next_day = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
    return render_template(
        "panchang_date.html", p=p, city=city, city_key=city_key, dt=dt,
        prev_day=prev_day, next_day=next_day,
    )


@app.route("/calendar")
@app.route("/calendar/<int:year>/<int:month>")
def calendar_view(year=None, month=None):
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    city_key = request.args.get("city", "new-delhi")
    city = CITIES.get(city_key, CITIES["new-delhi"])

    import calendar as cal
    cal.setfirstweekday(cal.SUNDAY)
    month_days = cal.monthcalendar(year, month)

    days_data = {}
    for week in month_days:
        for day in week:
            if day == 0:
                continue
            dt = datetime(year, month, day, 12)
            p = pg.calc_panchang(dt, city["lat"], city["lon"], city["tz"])
            days_data[day] = p

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render_template(
        "calendar.html", year=year, month=month, month_days=month_days,
        days_data=days_data, city=city, city_key=city_key,
        month_name_hi=HINDI_MONTHS[month - 1],
        prev_month=prev_month, prev_year=prev_year,
        next_month=next_month, next_year=next_year,
    )


HINDI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून",
                "जुलाई", "अगस्त", "सितम्बर", "अक्टूबर", "नवम्बर", "दिसम्बर"]


@app.route("/rashifal")
@app.route("/rashifal/<rashi>")
def rashifal(rashi=None):
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    results = {}
    for name, info in RASHIFAL.items():
        idx = day_of_year % len(info["daily"])
        results[name] = {**info, "today": info["daily"][idx]}
    return render_template(
        "rashifal.html", results=results, now=now, selected=rashi,
    )


@app.route("/muhurat")
def muhurat():
    city_key = request.args.get("city", "new-delhi")
    city = CITIES.get(city_key, CITIES["new-delhi"])
    datestr = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    dt = datetime.strptime(datestr, "%Y-%m-%d").replace(hour=12)

    p_today = pg.calc_panchang(dt, city["lat"], city["lon"], city["tz"])
    tomorrow = dt + timedelta(days=1)
    p_tomorrow = pg.calc_panchang(tomorrow, city["lat"], city["lon"], city["tz"])

    vara_sun0 = dt.isoweekday() % 7
    rk = pg.calc_rahu_kalam(p_today["sunrise"], p_today["sunset"], vara_sun0)
    day_slots, night_slots = pg.calc_choghadiya(
        p_today["sunrise"], p_today["sunset"], p_tomorrow["sunrise"], vara_sun0
    )

    return render_template(
        "muhurat.html", p=p_today, city=city, city_key=city_key, dt=dt,
        rahu_kalam=rk, day_slots=day_slots, night_slots=night_slots,
    )


@app.route("/vrat-festival")
def vrat_festival():
    today_str = datetime.now().strftime("%Y-%m-%d")
    past = [f for f in FESTIVALS if f["date"] < today_str]
    upcoming = [f for f in FESTIVALS if f["date"] >= today_str]
    return render_template("vrat.html", upcoming=upcoming, past=past[-5:])


@app.route("/kundali", methods=["GET", "POST"])
def kundali():
    chart = None
    error = None
    form = {}
    if request.method == "POST":
        form = request.form.to_dict()
        try:
            name = form.get("name", "")
            bdate = form.get("date")
            btime = form.get("time", "12:00")
            city_key = form.get("city", "new-delhi")
            city = CITIES.get(city_key, CITIES["new-delhi"])
            hh, mm = [int(x) for x in btime.split(":")]
            y, mo, d = [int(x) for x in bdate.split("-")]
            dt = datetime(y, mo, d, hh, mm)
            chart = pg.calc_birth_chart(dt, city["lat"], city["lon"], city["tz"])
            chart_meta = {"name": name, "dt": dt, "city": city["name"]}
        except Exception as e:
            error = "कृपया सही जन्म तिथि, समय और शहर दर्ज करें।"
            chart_meta = None
    else:
        chart_meta = None

    return render_template(
        "kundali.html", chart=chart, chart_meta=chart_meta, error=error, form=form,
    )


@app.route("/nakshatra")
def nakshatra_page():
    city_key = request.args.get("city", "new-delhi")
    city = CITIES.get(city_key, CITIES["new-delhi"])
    now = datetime.now()
    p = pg.calc_panchang(now, city["lat"], city["lon"], city["tz"])
    nak_list = []
    for i, name in enumerate(pg.NAKSHATRA_NAMES_HI):
        nak_list.append({
            "index": i, "name": name, "lord": pg.NAKSHATRA_LORD_HI[i],
            "ganda_moola": i in pg.GANDA_MOOLA_INDICES,
        })
    return render_template(
        "nakshatra.html", p=p, nak_list=nak_list, city=city, city_key=city_key, now=now,
    )


@app.route("/panchang-utilities")
def panchang_utilities():
    city_key = request.args.get("city", "new-delhi")
    city = CITIES.get(city_key, CITIES["new-delhi"])
    now = datetime.now()
    p = pg.calc_panchang(now, city["lat"], city["lon"], city["tz"])
    vara_sun0 = now.isoweekday() % 7
    rk = pg.calc_rahu_kalam(p["sunrise"], p["sunset"], vara_sun0)
    abhijit = pg.calc_abhijit_muhurat(p["sunrise"], p["sunset"])
    ganda_moola = p["nakshatra_index"] in pg.GANDA_MOOLA_INDICES
    bhadra = (p["karana_name_hi"] == "विष्टि")
    return render_template(
        "panchang_utilities.html", p=p, city=city, city_key=city_key, now=now,
        rahu_kalam=rk, abhijit=abhijit, ganda_moola=ganda_moola, bhadra=bhadra,
    )


@app.route("/shubh-muhurat")
def shubh_muhurat():
    city_key = request.args.get("city", "new-delhi")
    city = CITIES.get(city_key, CITIES["new-delhi"])
    now = datetime.now()
    good_dates = []
    d = now
    count = 0
    while len(good_dates) < 15 and count < 150:
        dt = datetime(d.year, d.month, d.day, 12)
        p = pg.calc_panchang(dt, city["lat"], city["lon"], city["tz"])
        if (
            p["tithi_index"] not in pg.RIKTA_TITHI_INDICES
            and p["karana_name_hi"] != "विष्टि"
            and p["nakshatra_index"] not in pg.GANDA_MOOLA_INDICES
            and p["paksha"] == "शुक्ल पक्ष"
        ):
            good_dates.append({"date": dt, "p": p})
        d = d + timedelta(days=1)
        count += 1
    return render_template(
        "shubh_muhurat.html", good_dates=good_dates, city=city, city_key=city_key, now=now,
    )


@app.route("/gemstone")
def gemstone():
    return render_template("gemstone.html", data=pg.GEMSTONE_DATA)


@app.route("/vrat-katha")
def vrat_katha():
    return render_template("vrat_katha.html", kathas=pg.VRAT_KATHA_DATA)


def _parse_birth_form(form):
    name = form.get("name", "")
    bdate = form.get("date")
    btime = form.get("time", "12:00")
    city_key = form.get("city", "new-delhi")
    city = CITIES.get(city_key, CITIES["new-delhi"])
    hh, mm = [int(x) for x in btime.split(":")]
    y, mo, d = [int(x) for x in bdate.split("-")]
    dt = datetime(y, mo, d, hh, mm)
    return name, dt, city


@app.route("/mangal-dosha", methods=["GET", "POST"])
def mangal_dosha():
    chart = None
    error = None
    form = {}
    result = None
    chart_meta = None
    if request.method == "POST":
        form = request.form.to_dict()
        try:
            name, dt, city = _parse_birth_form(form)
            chart = pg.calc_birth_chart(dt, city["lat"], city["lon"], city["tz"])
            chart_meta = {"name": name, "dt": dt, "city": city["name"]}

            lagna_idx = int(chart["Lagna"]["longitude"] // 30)
            moon_idx = int(chart["Moon"]["longitude"] // 30)
            mars_idx = int(chart["Mars"]["longitude"] // 30)
            house_from_lagna = ((mars_idx - lagna_idx) % 12) + 1
            house_from_moon = ((mars_idx - moon_idx) % 12) + 1
            manglik_houses = {1, 2, 4, 7, 8, 12}
            is_manglik = house_from_lagna in manglik_houses or house_from_moon in manglik_houses
            result = {
                "is_manglik": is_manglik,
                "house_from_lagna": house_from_lagna,
                "house_from_moon": house_from_moon,
            }
        except Exception:
            error = "कृपया सही जन्म तिथि, समय और शहर दर्ज करें।"
    return render_template(
        "mangal_dosha.html", chart=chart, chart_meta=chart_meta, result=result,
        error=error, form=form,
    )


@app.route("/kalasarpa-yoga", methods=["GET", "POST"])
def kalasarpa_yoga():
    chart = None
    error = None
    form = {}
    result = None
    chart_meta = None
    if request.method == "POST":
        form = request.form.to_dict()
        try:
            name, dt, city = _parse_birth_form(form)
            chart = pg.calc_birth_chart(dt, city["lat"], city["lon"], city["tz"])
            chart_meta = {"name": name, "dt": dt, "city": city["name"]}

            rahu_lon = chart["Rahu"]["longitude"]
            grahas = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
            diffs = [((chart[g]["longitude"] - rahu_lon) % 360) for g in grahas]
            is_kalasarpa = all(d < 180 for d in diffs) or all(d > 180 for d in diffs)
            result = {"is_kalasarpa": is_kalasarpa}
        except Exception:
            error = "कृपया सही जन्म तिथि, समय और शहर दर्ज करें।"
    return render_template(
        "kalasarpa_yoga.html", chart=chart, chart_meta=chart_meta, result=result,
        error=error, form=form,
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/privacy-policy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/ads.txt")
def ads_txt():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "ads.txt", mimetype="text/plain")


@app.route("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {request.url_root.rstrip('/')}/sitemap.xml",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    base = request.url_root.rstrip("/")
    paths = ["/", "/calendar", "/rashifal", "/muhurat", "/vrat-festival",
             "/kundali", "/about", "/privacy-policy", "/terms", "/contact",
             "/nakshatra", "/panchang-utilities", "/shubh-muhurat", "/gemstone",
             "/vrat-katha", "/mangal-dosha", "/kalasarpa-yoga"]
    urls = "".join(f"<url><loc>{base}{p}</loc></url>" for p in paths)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return Response(xml, mimetype="application/xml")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", ""))[:500]
    try:
        reply = chatbot.get_reply(message, FESTIVALS, RASHIFAL)
    except Exception:
        reply = "माफ़ कीजिए, अभी जवाब देने में समस्या आ रही है। कृपया फिर से कोशिश करें।"
    return jsonify({"reply": reply})


@app.route("/api/panchang")
def api_panchang():
    city_key = request.args.get("city", "new-delhi")
    city = CITIES.get(city_key, CITIES["new-delhi"])
    datestr = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    dt = datetime.strptime(datestr, "%Y-%m-%d").replace(hour=12)
    p = pg.calc_panchang(dt, city["lat"], city["lon"], city["tz"])
    out = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in p.items()}
    return jsonify(out)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
