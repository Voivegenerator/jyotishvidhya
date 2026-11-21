"""
Jyotishvidhya Panchang Engine
-----------------------------
Real astronomical panchang calculation using the `ephem` library
(VSOP87/Moshier algorithms - the same class of algorithm family used by
most commercial panchang sites) with Lahiri ayanamsha applied to convert
tropical (sayana) longitudes to sidereal (nirayana) longitudes, which is
the standard used for Hindu Panchang.

No external paid API is required - everything here is computed locally,
for free, with no rate limit.
"""
import ephem
import math
from datetime import datetime, timedelta
import pytz

TITHI_NAMES = [
    "Shukla Pratipada", "Shukla Dwitiya", "Shukla Tritiya", "Shukla Chaturthi",
    "Shukla Panchami", "Shukla Shashthi", "Shukla Saptami", "Shukla Ashtami",
    "Shukla Navami", "Shukla Dashami", "Shukla Ekadashi", "Shukla Dwadashi",
    "Shukla Trayodashi", "Shukla Chaturdashi", "Purnima",
    "Krishna Pratipada", "Krishna Dwitiya", "Krishna Tritiya", "Krishna Chaturthi",
    "Krishna Panchami", "Krishna Shashthi", "Krishna Saptami", "Krishna Ashtami",
    "Krishna Navami", "Krishna Dashami", "Krishna Ekadashi", "Krishna Dwadashi",
    "Krishna Trayodashi", "Krishna Chaturdashi", "Amavasya",
]

TITHI_NAMES_HI = [
    "शुक्ल प्रतिपदा", "शुक्ल द्वितीया", "शुक्ल तृतीया", "शुक्ल चतुर्थी",
    "शुक्ल पंचमी", "शुक्ल षष्ठी", "शुक्ल सप्तमी", "शुक्ल अष्टमी",
    "शुक्ल नवमी", "शुक्ल दशमी", "शुक्ल एकादशी", "शुक्ल द्वादशी",
    "शुक्ल त्रयोदशी", "शुक्ल चतुर्दशी", "पूर्णिमा",
    "कृष्ण प्रतिपदा", "कृष्ण द्वितीया", "कृष्ण तृतीया", "कृष्ण चतुर्थी",
    "कृष्ण पंचमी", "कृष्ण षष्ठी", "कृष्ण सप्तमी", "कृष्ण अष्टमी",
    "कृष्ण नवमी", "कृष्ण दशमी", "कृष्ण एकादशी", "कृष्ण द्वादशी",
    "कृष्ण त्रयोदशी", "कृष्ण चतुर्दशी", "अमावस्या",
]

NAKSHATRA_NAMES_HI = [
    "अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा", "आर्द्रा",
    "पुनर्वसु", "पुष्य", "आश्लेषा", "मघा", "पूर्वा फाल्गुनी", "उत्तरा फाल्गुनी",
    "हस्त", "चित्रा", "स्वाती", "विशाखा", "अनुराधा", "ज्येष्ठा",
    "मूल", "पूर्वाषाढ़ा", "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा", "शतभिषा",
    "पूर्वा भाद्रपद", "उत्तरा भाद्रपद", "रेवती",
]

YOGA_NAMES_HI = [
    "विष्कुम्भ", "प्रीति", "आयुष्मान", "सौभाग्य", "शोभन", "अतिगण्ड",
    "सुकर्मा", "धृति", "शूल", "गण्ड", "वृद्धि", "ध्रुव", "व्याघात",
    "हर्षण", "वज्र", "सिद्धि", "व्यतीपात", "वरीयान", "परिघ", "शिव",
    "सिद्ध", "साध्य", "शुभ", "शुक्ल", "ब्रह्मा", "ऐन्द्र", "वैधृति",
]

KARANA_NAMES_HI = ["बव", "बालव", "कौलव", "तैतिल", "गरज", "वणिज", "विष्टि"]
FIXED_KARANA_HI = ["शकुनि", "चतुष्पद", "नाग", "किंस्तुघ्न"]

RASHI_NAMES_HI = [
    "मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या",
    "तुला", "वृश्चिक", "धनु", "मकर", "कुम्भ", "मीन",
]
RASHI_NAMES_EN = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena",
]

VARA_NAMES_HI = ["रविवार", "सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार"]

GRAHA_HI = {
    "Sun": "सूर्य", "Moon": "चन्द्र", "Mars": "मंगल", "Mercury": "बुध",
    "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि",
}

# Ganda Moola nakshatras (0-indexed into NAKSHATRA_NAMES_HI)
GANDA_MOOLA_INDICES = {0, 8, 9, 17, 18, 26}  # Ashwini, Ashlesha, Magha, Jyeshtha, Mula, Revati

NAKSHATRA_LORD_HI = [
    "केतु", "शुक्र", "सूर्य", "चन्द्र", "मंगल", "राहु", "गुरु", "शनि", "बुध",
    "केतु", "शुक्र", "सूर्य", "चन्द्र", "मंगल", "राहु", "गुरु", "शनि", "बुध",
    "केतु", "शुक्र", "सूर्य", "चन्द्र", "मंगल", "राहु", "गुरु", "शनि", "बुध",
]

# Rikta tithis (4th, 9th, 14th in each paksha) + Amavasya - traditionally avoided for shubh karya
RIKTA_TITHI_INDICES = {3, 8, 13, 18, 23, 28, 29}

GEMSTONE_DATA = [
    {"rashi_hi": "मेष", "rashi_en": "Mesha", "lord": "मंगल", "gemstone": "मूंगा (Red Coral)", "rudraksha": "तीन मुखी रुद्राक्ष", "day": "मंगलवार", "number": 9},
    {"rashi_hi": "वृषभ", "rashi_en": "Vrishabha", "lord": "शुक्र", "gemstone": "हीरा / सफेद पुखराज", "rudraksha": "छह मुखी रुद्राक्ष", "day": "शुक्रवार", "number": 6},
    {"rashi_hi": "मिथुन", "rashi_en": "Mithuna", "lord": "बुध", "gemstone": "पन्ना (Emerald)", "rudraksha": "चार मुखी रुद्राक्ष", "day": "बुधवार", "number": 5},
    {"rashi_hi": "कर्क", "rashi_en": "Karka", "lord": "चन्द्र", "gemstone": "मोती (Pearl)", "rudraksha": "दो मुखी रुद्राक्ष", "day": "सोमवार", "number": 2},
    {"rashi_hi": "सिंह", "rashi_en": "Simha", "lord": "सूर्य", "gemstone": "माणिक्य (Ruby)", "rudraksha": "एक मुखी / बारह मुखी रुद्राक्ष", "day": "रविवार", "number": 1},
    {"rashi_hi": "कन्या", "rashi_en": "Kanya", "lord": "बुध", "gemstone": "पन्ना (Emerald)", "rudraksha": "चार मुखी रुद्राक्ष", "day": "बुधवार", "number": 5},
    {"rashi_hi": "तुला", "rashi_en": "Tula", "lord": "शुक्र", "gemstone": "हीरा (Diamond)", "rudraksha": "छह मुखी रुद्राक्ष", "day": "शुक्रवार", "number": 6},
    {"rashi_hi": "वृश्चिक", "rashi_en": "Vrishchika", "lord": "मंगल", "gemstone": "मूंगा (Red Coral)", "rudraksha": "तीन मुखी रुद्राक्ष", "day": "मंगलवार", "number": 9},
    {"rashi_hi": "धनु", "rashi_en": "Dhanu", "lord": "गुरु", "gemstone": "पुखराज (Yellow Sapphire)", "rudraksha": "पाँच मुखी रुद्राक्ष", "day": "गुरुवार", "number": 3},
    {"rashi_hi": "मकर", "rashi_en": "Makara", "lord": "शनि", "gemstone": "नीलम (Blue Sapphire)", "rudraksha": "सात मुखी रुद्राक्ष", "day": "शनिवार", "number": 8},
    {"rashi_hi": "कुम्भ", "rashi_en": "Kumbha", "lord": "शनि", "gemstone": "नीलम (Blue Sapphire)", "rudraksha": "सात मुखी रुद्राक्ष", "day": "शनिवार", "number": 8},
    {"rashi_hi": "मीन", "rashi_en": "Meena", "lord": "गुरु", "gemstone": "पुखराज (Yellow Sapphire)", "rudraksha": "पाँच मुखी रुद्राक्ष", "day": "गुरुवार", "number": 3},
]

VRAT_KATHA_DATA = [
    {
        "slug": "satyanarayan",
        "title": "श्री सत्यनारायण व्रत कथा",
        "summary": "काशी नगरी में भ्रमण के दौरान ब्राह्मणों के एक समूह ने नारद मुनि से दुःख दूर करने और सुख पाने का उपाय पूछा। नारद जी ने उन्हें भगवान विष्णु के सत्यनारायण स्वरूप की कथा सुनाई और बताया कि पूर्णिमा अथवा एकादशी के दिन श्रद्धापूर्वक व्रत व पूजन करने से घर में सुख-समृद्धि आती है। कथा में एक निर्धन ब्राह्मण, एक लकड़हारा, एक राजा और एक व्यापारी की कहानियाँ आती हैं, जिन्होंने व्रत का संकल्प लेकर बाद में उसे भुला दिया और कष्ट भोगे, परंतु पुनः श्रद्धापूर्वक व्रत करने पर उनके सभी दुःख दूर हो गए। इस कथा का मूल संदेश है — सत्य, श्रद्धा और संकल्प की पूर्ति का महत्व।",
    },
    {
        "slug": "ekadashi",
        "title": "एकादशी व्रत माहात्म्य",
        "summary": "पौराणिक मान्यता के अनुसार एकादशी तिथि भगवान विष्णु को अत्यंत प्रिय है। कथा के अनुसार प्राचीन समय में 'मृदुमान्य' नामक असुर का नाश करने के लिए देवी एकादशी स्वयं भगवान विष्णु की शक्ति से प्रकट हुई थीं, इसीलिए इस तिथि का नाम एकादशी पड़ा। माना जाता है कि एकादशी के दिन निराहार अथवा फलाहार व्रत रखने और भगवान विष्णु की पूजा करने से व्यक्ति के पापों का नाश होता है तथा मोक्ष की प्राप्ति होती है। हर माह में दो एकादशी (शुक्ल व कृष्ण पक्ष) आती हैं और प्रत्येक का अलग-अलग नाम व महत्व होता है।",
    },
    {
        "slug": "karwa-chauth",
        "title": "करवा चौथ व्रत कथा",
        "summary": "एक प्रचलित कथा के अनुसार वीरवती नामक एक रानी ने अपने पति की दीर्घायु के लिए निर्जला करवा चौथ व्रत रखा था, परंतु भूख-प्यास से व्याकुल होकर उसने चन्द्रमा के समय से पहले ही व्रत तोड़ लिया, जिससे उसके पति पर संकट आ गया। बाद में श्रद्धापूर्वक विधिवत व्रत पूर्ण करने पर उसके पति का जीवन पुनः सामान्य हो गया। इसी कारण इस दिन सुहागिन स्त्रियाँ अपने पति की लंबी आयु व सुखी दांपत्य जीवन की कामना से सूर्योदय से चन्द्रोदय तक निर्जला व्रत रखती हैं और रात में चन्द्र दर्शन के पश्चात व्रत खोलती हैं।",
    },
    {
        "slug": "ahoi-ashtami",
        "title": "अहोई अष्टमी व्रत कथा",
        "summary": "कथा के अनुसार एक साहूकार की पत्नी से भूलवश स्याहु (साही) के बच्चे की मृत्यु हो गई, जिससे उसकी संतानों पर संकट आ गया। पंडित के बताए अनुसार उसने अहोई माता की पूजा व व्रत का संकल्प लिया और अपनी भूल के लिए क्षमा-याचना की, जिसके फलस्वरूप उसकी संतानें पुनः स्वस्थ व सुरक्षित हो गईं। इसी मान्यता के अनुसार संतान की दीर्घायु व सुरक्षा हेतु माताएँ कार्तिक कृष्ण अष्टमी को निर्जला व्रत रखकर संध्या में तारों को अर्घ्य देकर व्रत खोलती हैं।",
    },
]


def lahiri_ayanamsha(date):
    """
    Approximate Lahiri (Chitrapaksha) ayanamsha in degrees for a given
    ephem.Date, using the standard linear-rate approximation anchored at
    J2000 (23.85 degrees on 2000-01-01, precessing ~50.29 arcsec/year).
    This matches published Lahiri values to within ~0.01-0.02 degrees,
    which is adequate for tithi/nakshatra boundaries.
    """
    jd = ephem.Date(date)
    jd2000 = ephem.Date('2000/1/1')
    years = (jd - jd2000) / 365.25636
    ayanamsha = 23.85 + years * (50.2719 / 3600.0)
    return ayanamsha


def sidereal_longitude(body, date, observer=None):
    body.compute(date, epoch=date) if observer is None else body.compute(observer)
    tropical_lon = math.degrees(body.hlon) if False else math.degrees(ephem.Ecliptic(body).lon)
    ayan = lahiri_ayanamsha(date)
    sidereal = (tropical_lon - ayan) % 360
    return sidereal


def get_sun_moon_sidereal(date):
    sun = ephem.Sun()
    moon = ephem.Moon()
    sun.compute(date)
    moon.compute(date)
    ayan = lahiri_ayanamsha(date)
    sun_lon = (math.degrees(ephem.Ecliptic(sun).lon) - ayan) % 360
    moon_lon = (math.degrees(ephem.Ecliptic(moon).lon) - ayan) % 360
    return sun_lon, moon_lon


def calc_panchang(dt_local, lat, lon, tz_offset_hours):
    """
    dt_local: naive datetime in local civil time for the place
    Returns a dict with tithi, nakshatra, yoga, karana, vara, sunrise, sunset,
    moonsign, sunsign and the raw longitudes.
    """
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.elevation = 0
    # ephem works in UT; convert local civil time -> UT
    dt_utc = dt_local - timedelta(hours=tz_offset_hours)
    observer.date = dt_utc

    sun_lon, moon_lon = get_sun_moon_sidereal(observer.date)

    # Tithi: angular distance Moon - Sun, each tithi = 12 degrees
    diff = (moon_lon - sun_lon) % 360
    tithi_index = int(diff // 12)  # 0..29
    tithi_frac = (diff % 12) / 12.0

    # Nakshatra: Moon's sidereal longitude, each nakshatra = 13.3333 degrees (360/27)
    nak_span = 360.0 / 27.0
    nak_index = int(moon_lon // nak_span)
    nak_frac = (moon_lon % nak_span) / nak_span
    pada = int(nak_frac * 4) + 1

    # Yoga: (Sun + Moon) sidereal longitude, each yoga = 13.3333 degrees
    yoga_sum = (sun_lon + moon_lon) % 360
    yoga_index = int(yoga_sum // nak_span)

    # Karana: half-tithi, each karana = 6 degrees, 60 per lunar month (cyclical naming)
    karana_num = int(diff // 6)  # 0..59
    if karana_num == 0:
        karana_name = FIXED_KARANA_HI[0]  # Kimstughna (special, only at start)
    elif karana_num >= 57:
        karana_name = FIXED_KARANA_HI[karana_num - 56]  # 57,58,59 -> Shakuni, Chatushpada, Naga
    else:
        karana_name = KARANA_NAMES_HI[(karana_num - 1) % 7]

    # Weekday (vara) - based on local sunrise day
    vara_index = dt_local.weekday()  # Mon=0..Sun=6
    vara_index = (vara_index + 1) % 7  # convert to Sun=0..Sat=6
    vara_index_from_sun = (dt_local.isoweekday() % 7)  # Sun=0

    # Moon sign / Sun sign (rashi), each rashi = 30 degrees
    moonsign_index = int(moon_lon // 30)
    sunsign_index = int(sun_lon // 30)

    # Sunrise / sunset for the given date at this location
    observer.date = dt_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        sunrise_utc = observer.next_rising(ephem.Sun())
        sunset_utc = observer.next_setting(ephem.Sun())
        sunrise_local = ephem.Date(sunrise_utc).datetime() + timedelta(hours=tz_offset_hours)
        sunset_local = ephem.Date(sunset_utc).datetime() + timedelta(hours=tz_offset_hours)
    except Exception:
        sunrise_local = None
        sunset_local = None

    paksha = "शुक्ल पक्ष" if tithi_index < 15 else "कृष्ण पक्ष"

    return {
        "tithi_index": tithi_index,
        "tithi_name_hi": TITHI_NAMES_HI[tithi_index],
        "tithi_name_en": TITHI_NAMES[tithi_index],
        "tithi_percent_left": round((1 - tithi_frac) * 100, 1),
        "paksha": paksha,
        "nakshatra_index": nak_index % 27,
        "nakshatra_name_hi": NAKSHATRA_NAMES_HI[nak_index % 27],
        "pada": pada,
        "yoga_index": yoga_index % 27,
        "yoga_name_hi": YOGA_NAMES_HI[yoga_index % 27],
        "karana_name_hi": karana_name,
        "vara_name_hi": VARA_NAMES_HI[dt_local.isoweekday() % 7],
        "moonsign_hi": RASHI_NAMES_HI[moonsign_index],
        "moonsign_en": RASHI_NAMES_EN[moonsign_index],
        "sunsign_hi": RASHI_NAMES_HI[sunsign_index],
        "sunsign_en": RASHI_NAMES_EN[sunsign_index],
        "sunrise": sunrise_local,
        "sunset": sunset_local,
        "sun_lon": sun_lon,
        "moon_lon": moon_lon,
    }


def calc_choghadiya(sunrise, sunset, next_sunrise, vara_index_sun0):
    """
    Returns list of (name, start, end, nature) for day (sunrise->sunset, 8 parts)
    and night (sunset->next_sunrise, 8 parts). vara_index_sun0: Sun=0 .. Sat=6
    """
    DAY_SEQ = {
        0: ["Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg"],
        1: ["Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit"],
        2: ["Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog"],
        3: ["Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh"],
        4: ["Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh"],
        5: ["Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal"],
        6: ["Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal"],
    }
    NIGHT_SEQ = {
        0: ["Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh"],
        1: ["Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Chal"],
        2: ["Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Chal", "Rog", "Kaal"],
        3: ["Udveg", "Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg"],
        4: ["Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit"],
        5: ["Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Chal", "Rog"],
        6: ["Labh", "Udveg", "Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh"],
    }
    GOOD = {"Amrit", "Shubh", "Labh", "Chal"}
    NAME_HI = {
        "Udveg": "उद्वेग", "Chal": "चल", "Labh": "लाभ", "Amrit": "अमृत",
        "Kaal": "काल", "Shubh": "शुभ", "Rog": "रोग",
    }

    day_names = DAY_SEQ[vara_index_sun0]
    night_names = NIGHT_SEQ[vara_index_sun0]

    day_slots = []
    day_dur = (sunset - sunrise) / 8
    for i, name in enumerate(day_names):
        start = sunrise + day_dur * i
        end = sunrise + day_dur * (i + 1)
        day_slots.append({
            "name_hi": NAME_HI[name], "start": start, "end": end,
            "good": name in GOOD,
        })

    night_slots = []
    night_dur = (next_sunrise - sunset) / 8
    for i, name in enumerate(night_names):
        start = sunset + night_dur * i
        end = sunset + night_dur * (i + 1)
        night_slots.append({
            "name_hi": NAME_HI[name], "start": start, "end": end,
            "good": name in GOOD,
        })

    return day_slots, night_slots


def calc_rahu_kalam(sunrise, sunset, vara_index_sun0):
    """Rahu Kaal, Yamaganda, Gulika Kaal - standard 8-part day division."""
    day_dur = (sunset - sunrise) / 8
    # Standard segment index (0-7) for each weekday, Sun=0..Sat=6
    RAHU_SEG = {0: 7, 1: 1, 2: 6, 3: 4, 4: 5, 5: 3, 6: 2}
    YAMA_SEG = {0: 4, 1: 3, 2: 2, 3: 1, 4: 0, 5: 6, 6: 5}
    GULIKA_SEG = {0: 6, 1: 5, 2: 4, 3: 3, 4: 2, 5: 1, 6: 0}

    def seg(idx):
        return sunrise + day_dur * idx, sunrise + day_dur * (idx + 1)

    return {
        "rahu_kaal": seg(RAHU_SEG[vara_index_sun0]),
        "yamaganda": seg(YAMA_SEG[vara_index_sun0]),
        "gulika_kaal": seg(GULIKA_SEG[vara_index_sun0]),
    }


def calc_abhijit_muhurat(sunrise, sunset):
    """Abhijit Muhurat: the 8th of 15 muhurtas of the day, centred on solar noon."""
    day_dur = sunset - sunrise
    muhurat_dur = day_dur / 15
    solar_noon = sunrise + day_dur / 2
    return solar_noon - muhurat_dur / 2, solar_noon + muhurat_dur / 2


def calc_birth_chart(dt_local, lat, lon, tz_offset_hours):
    """Simplified Lagna (Ascendant) + 9 graha sidereal positions for a Kundali."""
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.elevation = 0
    dt_utc = dt_local - timedelta(hours=tz_offset_hours)
    observer.date = dt_utc

    ayan = lahiri_ayanamsha(observer.date)

    bodies = {
        "Sun": ephem.Sun(), "Moon": ephem.Moon(), "Mars": ephem.Mars(),
        "Mercury": ephem.Mercury(), "Jupiter": ephem.Jupiter(),
        "Venus": ephem.Venus(), "Saturn": ephem.Saturn(),
    }
    positions = {}
    for name, body in bodies.items():
        body.compute(observer)
        lon_sid = (math.degrees(ephem.Ecliptic(body).lon) - ayan) % 360
        positions[name] = {
            "longitude": round(lon_sid, 2),
            "rashi_hi": RASHI_NAMES_HI[int(lon_sid // 30)],
            "rashi_en": RASHI_NAMES_EN[int(lon_sid // 30)],
            "degree_in_rashi": round(lon_sid % 30, 2),
        }

    # Rahu/Ketu: Moon's mean ascending/descending node (approx)
    # Mean lunar node regresses ~19.3549 deg/year, epoch value at J2000 ~125.04452 (tropical)
    jd2000 = ephem.Date('2000/1/1')
    years = (ephem.Date(observer.date) - jd2000) / 365.25636
    rahu_tropical = (125.04452 - 19.3549 * years) % 360
    rahu_sid = (rahu_tropical - ayan) % 360
    ketu_sid = (rahu_sid + 180) % 360
    positions["Rahu"] = {
        "longitude": round(rahu_sid, 2),
        "rashi_hi": RASHI_NAMES_HI[int(rahu_sid // 30)],
        "rashi_en": RASHI_NAMES_EN[int(rahu_sid // 30)],
        "degree_in_rashi": round(rahu_sid % 30, 2),
    }
    positions["Ketu"] = {
        "longitude": round(ketu_sid, 2),
        "rashi_hi": RASHI_NAMES_HI[int(ketu_sid // 30)],
        "rashi_en": RASHI_NAMES_EN[int(ketu_sid // 30)],
        "degree_in_rashi": round(ketu_sid % 30, 2),
    }

    # Lagna (Ascendant) - using sidereal time and standard formula via ephem's radec_of
    ra, dec = observer.radec_of(0, '90')  # not exact ascendant; fallback approximation below
    sidereal_time = observer.sidereal_time()
    lst_deg = math.degrees(sidereal_time)
    eps = math.radians(23.4367)  # mean obliquity of ecliptic
    phi = math.radians(lat)
    lst_rad = math.radians(lst_deg)
    y = -math.cos(lst_rad)
    x = math.sin(eps) * math.tan(phi) + math.cos(eps) * math.sin(lst_rad)
    asc_tropical = math.degrees(math.atan2(y, x)) % 360
    asc_sid = (asc_tropical - ayan) % 360

    positions["Lagna"] = {
        "longitude": round(asc_sid, 2),
        "rashi_hi": RASHI_NAMES_HI[int(asc_sid // 30)],
        "rashi_en": RASHI_NAMES_EN[int(asc_sid // 30)],
        "degree_in_rashi": round(asc_sid % 30, 2),
    }

    return positions
