"""
JyotishVidhya Chat Agent
------------------------
A free, rule-based (no paid AI API, no external calls) Hindi chat assistant
that answers common astrology/panchang questions using the site's own
computed data (panchang.py, data/rashifal.json, data/festivals.json).

Zero ongoing cost: everything here is plain Python string matching plus
the astronomical calculations the site already does for its pages.
"""
from datetime import datetime

import panchang as pg

GREETING_KW = ["नमस्ते", "नमस्कार", "hello", "hii", "hi", "hey", "जय श्री राम", "radhe radhe", "राधे राधे"]
THANKS_KW = ["धन्यवाद", "शुक्रिया", "thanks", "thank you", "thx"]
PANCHANG_KW = ["पंचांग", "तिथि", "आज क्या", "panchang", "tithi", "aaj ka din", "आज का दिन"]
NAKSHATRA_KW = ["नक्षत्र", "nakshatra"]
RASHIFAL_KW = ["राशिफल", "rashifal", "horoscope", "राशि फल"]
MUHURAT_KW = ["मुहूर्त", "राहु काल", "rahu kalam", "muhurat", "चौघड़िया", "choghadiya", "अभिजीत"]
FESTIVAL_KW = ["त्योहार", "व्रत", "festival", "vrat", "छुट्टी"]
GEMSTONE_KW = ["रत्न", "रुद्राक्ष", "gemstone", "rudraksha", "पत्थर"]
KUNDALI_KW = ["कुंडली", "kundali", "जन्म कुंडली", "janam kundali", "birth chart"]
MANGAL_DOSHA_KW = ["मांगलिक", "mangal dosha", "manglik"]
KALASARPA_KW = ["कालसर्प", "kalasarpa", "kaal sarp"]
HELP_KW = ["मदद", "help", "क्या कर सकते", "कैसे use", "कैसे इस्तेमाल"]

DEFAULT_CITY = {"name": "New Delhi", "lat": 28.6139, "lon": 77.2090, "tz": 5.5}

RASHI_ALIASES = {}
for hi, en in zip(pg.RASHI_NAMES_HI, pg.RASHI_NAMES_EN):
    RASHI_ALIASES[hi] = hi
    RASHI_ALIASES[en.lower()] = hi
# common Hinglish spellings
_EXTRA = {
    "mesh": "मेष", "vrishabh": "वृषभ", "vrisabh": "वृषभ", "mithun": "मिथुन",
    "kark": "कर्क", "karka": "कर्क", "singh": "सिंह", "simha": "सिंह",
    "kanya": "कन्या", "tula": "तुला", "vrishchik": "वृश्चिक", "vrischik": "वृश्चिक",
    "dhanu": "धनु", "makar": "मकर", "kumbh": "कुम्भ", "meen": "मीन", "meena": "मीन",
}
RASHI_ALIASES.update(_EXTRA)


def _contains_any(text, keywords):
    return any(k in text for k in keywords)


def _find_rashi(text):
    for alias, canonical in RASHI_ALIASES.items():
        if alias.lower() in text:
            return canonical
    return None


def _today_panchang_reply():
    now = datetime.now()
    p = pg.calc_panchang(now, DEFAULT_CITY["lat"], DEFAULT_CITY["lon"], DEFAULT_CITY["tz"])
    return (
        f"आज ({now.strftime('%d-%m-%Y')}, नई दिल्ली के अनुसार) का पंचांग:\n"
        f"🗓️ तिथि: {p['tithi_name_hi']}\n"
        f"⭐ नक्षत्र: {p['nakshatra_name_hi']}\n"
        f"🔆 योग: {p['yoga_name_hi']}\n"
        f"📿 करण: {p['karana_name_hi']}\n"
        f"📍 वार: {p['vara_name_hi']}\n"
        f"विस्तार से देखने के लिए होम पेज पर जाएं।"
    )


def _nakshatra_reply():
    now = datetime.now()
    p = pg.calc_panchang(now, DEFAULT_CITY["lat"], DEFAULT_CITY["lon"], DEFAULT_CITY["tz"])
    idx = p["nakshatra_index"]
    lord = pg.NAKSHATRA_LORD_HI[idx]
    gm = "हाँ (गंडमूल नक्षत्र है)" if idx in pg.GANDA_MOOLA_INDICES else "नहीं"
    return (
        f"आज का नक्षत्र {p['nakshatra_name_hi']} है, जिसका स्वामी ग्रह {lord} है। "
        f"गंडमूल नक्षत्र: {gm}। अधिक जानकारी के लिए 'नक्षत्र विवरण' पेज देखें।"
    )


def _rashifal_reply(rashifal_data, rashi):
    if rashi not in rashifal_data:
        return None
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    info = rashifal_data[rashi]
    idx = day_of_year % len(info["daily"])
    today = info["daily"][idx]
    return (
        f"{rashi} राशि का आज का राशिफल:\n{today}\n\n"
        f"शुभ रंग: {info.get('lucky_color', '-')}, शुभ अंक: {info.get('lucky_number', '-')}"
    )


def _muhurat_reply():
    now = datetime.now()
    p_today = pg.calc_panchang(now, DEFAULT_CITY["lat"], DEFAULT_CITY["lon"], DEFAULT_CITY["tz"])
    vara_sun0 = now.isoweekday() % 7
    rk = pg.calc_rahu_kalam(p_today["sunrise"], p_today["sunset"], vara_sun0)
    rahu_start, rahu_end = rk["rahu_kaal"]
    abhijit = pg.calc_abhijit_muhurat(p_today["sunrise"], p_today["sunset"])
    return (
        f"आज (नई दिल्ली के अनुसार) राहु काल: "
        f"{rahu_start.strftime('%I:%M %p')} से {rahu_end.strftime('%I:%M %p')} तक।\n"
        f"अभिजीत मुहूर्त: {abhijit[0].strftime('%I:%M %p')} से {abhijit[1].strftime('%I:%M %p')} तक।\n"
        f"पूरी चौघड़िया सारणी के लिए 'मुहूर्त' पेज देखें।"
    )


def _festival_reply(festivals):
    today_str = datetime.now().strftime("%Y-%m-%d")
    upcoming = [f for f in festivals if f["date"] >= today_str][:5]
    if not upcoming:
        return "आने वाले व्रत-त्योहारों की जानकारी फिलहाल उपलब्ध नहीं है।"
    lines = [f"{f['date']} - {f['name']}" for f in upcoming]
    return "आने वाले व्रत-त्योहार:\n" + "\n".join(lines) + "\n\nपूरी सूची 'व्रत-त्योहार' पेज पर है।"


def _gemstone_reply(rashi):
    if not rashi:
        return "कृपया अपनी राशि बताएं (जैसे: मेष, वृषभ, सिंह आदि), मैं उसके अनुसार रत्न व रुद्राक्ष बताऊंगा।"
    for g in pg.GEMSTONE_DATA:
        if g["rashi_hi"] == rashi:
            return (
                f"{rashi} राशि के लिए:\n"
                f"रत्न: {g['gemstone']}\nरुद्राक्ष: {g['rudraksha']}\n"
                f"शुभ दिन: {g['day']}, शुभ अंक: {g['number']}\n\n"
                f"किसी भी रत्न को धारण करने से पहले योग्य ज्योतिषी से सलाह अवश्य लें।"
            )
    return None


def get_reply(message, festivals, rashifal_data):
    """Return a Hindi text reply for the given user message."""
    text = (message or "").strip()
    if not text:
        return "कृपया अपना सवाल लिखें।"
    lower = text.lower()

    if _contains_any(lower, THANKS_KW):
        return "आपका बहुत स्वागत है! 🙏 कोई और सवाल हो तो पूछ सकते हैं।"

    if _contains_any(lower, GREETING_KW):
        return (
            "नमस्ते! 🙏 मैं ज्योतिषविद्या का सहायक हूँ। आप मुझसे पूछ सकते हैं:\n"
            "• आज का पंचांग / तिथि / नक्षत्र\n"
            "• किसी राशि का आज का राशिफल (जैसे: 'मेष राशिफल')\n"
            "• आज का राहु काल / शुभ मुहूर्त\n"
            "• आने वाले व्रत-त्योहार\n"
            "• किसी राशि का रत्न व रुद्राक्ष\n"
            "• कुंडली, मांगलिक दोष या कालसर्प योग कैसे जांचें"
        )

    rashi = _find_rashi(lower)

    if _contains_any(lower, GEMSTONE_KW):
        return _gemstone_reply(rashi)

    if _contains_any(lower, RASHIFAL_KW) or (rashi and "राशिफल" in lower):
        if rashi:
            r = _rashifal_reply(rashifal_data, rashi)
            if r:
                return r
        return "कृपया अपनी राशि बताएं (जैसे: 'मेष राशिफल' या 'सिंह horoscope'), मैं आज का राशिफल बता दूंगा।"

    if rashi and not _contains_any(lower, GEMSTONE_KW):
        # bare rashi name mentioned - give rashifal by default
        r = _rashifal_reply(rashifal_data, rashi)
        if r:
            return r

    if _contains_any(lower, MUHURAT_KW):
        return _muhurat_reply()

    if _contains_any(lower, NAKSHATRA_KW):
        return _nakshatra_reply()

    if _contains_any(lower, PANCHANG_KW):
        return _today_panchang_reply()

    if _contains_any(lower, FESTIVAL_KW):
        return _festival_reply(festivals)

    if _contains_any(lower, KUNDALI_KW):
        return (
            "जन्म कुंडली बनाने के लिए 'कुंडली' पेज पर जाएं और अपना नाम, जन्म तिथि, समय व शहर दर्ज करें। "
            "वहाँ से आप मांगलिक दोष व कालसर्प योग भी जांच सकते हैं।"
        )

    if _contains_any(lower, MANGAL_DOSHA_KW):
        return "मांगलिक दोष जांचने के लिए 'कुंडली' मेनू में 'मांगलिक दोष जांच' पेज पर जाएं और अपनी जन्म-जानकारी दर्ज करें।"

    if _contains_any(lower, KALASARPA_KW):
        return "कालसर्प योग जांचने के लिए 'कुंडली' मेनू में 'कालसर्प योग जांच' पेज पर जाएं और अपनी जन्म-जानकारी दर्ज करें।"

    if _contains_any(lower, HELP_KW):
        return (
            "मैं इनमें मदद कर सकता हूँ: आज का पंचांग, किसी राशि का राशिफल, राहु काल/शुभ मुहूर्त, "
            "आने वाले व्रत-त्योहार, राशि अनुसार रत्न-रुद्राक्ष, और कुंडली/मांगलिक/कालसर्प पेज तक पहुंचने में मार्गदर्शन।"
        )

    return (
        "माफ़ कीजिए, मैं यह ठीक से समझ नहीं पाया। आप पूछ सकते हैं जैसे: "
        "'आज का पंचांग', 'मेष राशिफल', 'आज का राहु काल', 'आने वाले व्रत-त्योहार'।"
    )
