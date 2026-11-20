import urllib.request, urllib.parse, xml.etree.ElementTree as ET
import json, re, datetime, email.utils, time, base64, html

BROKERS = {
 "Motilal Oswal": ["Motilal Oswal"],
 "ICICI Direct": ["ICICI Direct", "ICICI Securities"],
 "HDFC Securities": ["HDFC Securities", "HDFC Sec"],
 "Sharekhan": ["Sharekhan"],
 "Angel One": ["Angel One", "Angel Broking"],
 "Kotak Securities": ["Kotak Securities", "Kotak Institutional Equities"],
 "Axis Direct": ["Axis Direct", "Axis Securities"],
 "IIFL Capital": ["IIFL Capital", "IIFL Securities"],
 "SBI Securities": ["SBI Securities", "SBICAP Securities"],
 "Anand Rathi": ["Anand Rathi"],
 "Geojit": ["Geojit"],
 "Choice Broking": ["Choice Broking", "Choice Equity"],
 "Nuvama": ["Nuvama"],
 "JM Financial": ["JM Financial"],
 "SMC Global": ["SMC Global"],
 "Religare Broking": ["Religare Broking"],
 "Edelweiss": ["Edelweiss"],
 "IDBI Capital": ["IDBI Capital"],
 "BOBCAPS": ["BOBCAPS", "BOB Capital"],
 "Yes Securities": ["Yes Securities"],
 "Indiabulls Securities": ["Indiabulls Securities"],
 "Prabhudas Lilladher": ["Prabhudas Lilladher", "PL Capital"],
 "Ventura": ["Ventura Securities"],
 "5paisa": ["5paisa"],
}

STOCKS = ("Reliance Industries|Reliance|TCS|Tata Consultancy Services|Infosys|Wipro|"
"HCL Technologies|HCLTech|Tech Mahindra|LTIMindtree|Persistent Systems|Coforge|Mphasis|"
"KPIT|Tata Elxsi|Tata Technologies|HDFC Bank|ICICI Bank|State Bank of India|SBI Life|"
"SBI Cards|SBI|Axis Bank|Kotak Mahindra Bank|IndusInd Bank|Bank of Baroda|"
"Punjab National Bank|Canara Bank|Union Bank|Federal Bank|IDFC First Bank|"
"AU Small Finance Bank|Bandhan Bank|Bajaj Finance|Bajaj Finserv|HDFC Life|"
"ICICI Prudential|ICICI Lombard|LIC|Cholamandalam|Shriram Finance|Muthoot Finance|"
"Manappuram|Power Finance Corporation|PFC|REC|IRFC|Jio Financial|Tata Motors|"
"Maruti Suzuki|Mahindra & Mahindra|M&M|Bajaj Auto|Hero MotoCorp|Eicher Motors|"
"TVS Motor|Ashok Leyland|Tata Steel|JSW Steel|Hindalco|Vedanta|Jindal Steel|SAIL|"
"NMDC|Hindustan Zinc|Coal India|NTPC|Power Grid|NHPC|SJVN|Tata Power|ONGC|Oil India|"
"BPCL|Bharat Petroleum|HPCL|Hindustan Petroleum|IOC|Indian Oil|GAIL|Petronet LNG|"
"Adani Enterprises|Adani Ports|Adani Power|Adani Green|Adani Energy|Larsen & Toubro|L&T|"
"Siemens|ABB India|BHEL|Bharat Electronics|BEL|HAL|Hindustan Aeronautics|"
"Mazagon Dock|Cochin Shipyard|Bharat Forge|Cummins|Havells|Polycab|Dixon|Voltas|"
"Kaynes|Suzlon|Waaree|Titan|Trent|Avenue Supermarts|DMart|Zomato|Eternal Ltd|Swiggy|"
"Nykaa|Paytm|PB Fintech|Policybazaar|Info Edge|Hindustan Unilever|HUL|ITC|Nestle India|"
"Britannia|Dabur|Godrej Consumer|Marico|Tata Consumer|Varun Beverages|United Spirits|"
"Page Industries|Bata|Jubilant FoodWorks|Asian Paints|Berger Paints|Pidilite|"
"UltraTech Cement|Ambuja Cements|Shree Cement|ACC|Grasim|Dalmia Bharat|Sun Pharma|"
"Dr Reddy|Cipla|Divi's Laboratories|Divi's Labs|Lupin|Zydus|Aurobindo Pharma|"
"Torrent Pharma|Mankind Pharma|Apollo Hospitals|Max Healthcare|Fortis Healthcare|"
"Bharti Airtel|Vodafone Idea|Indus Towers|DLF|Godrej Properties|Lodha|"
"Macrotech Developers|Oberoi Realty|Prestige Estates|IndiGo|InterGlobe Aviation|IRCTC|"
"RVNL|UPL|SRF|PI Industries|Deepak Nitrite|CDSL|Container Corporation|Zee Entertainment|"
"Sun TV|Bosch|Motherson|Sona BLW|Exide|Amara Raja|Balkrishna|MRF|Apollo Tyres|CEAT|"
"Ola Electric|Lenskart|GMR Airports")

ALIAS = {"Reliance": "Reliance Industries", "Tata Consultancy Services": "TCS",
 "SBI": "State Bank of India", "L&T": "Larsen & Toubro",
 "M&M": "Mahindra & Mahindra", "HUL": "Hindustan Unilever",
 "HCLTech": "HCL Technologies", "PFC": "Power Finance Corporation",
 "BEL": "Bharat Electronics", "HAL": "Hindustan Aeronautics",
 "IOC": "Indian Oil", "BPCL": "Bharat Petroleum", "HPCL": "Hindustan Petroleum",
 "DMart": "Avenue Supermarts", "Zomato": "Eternal (Zomato)",
 "Eternal Ltd": "Eternal (Zomato)", "InterGlobe Aviation": "IndiGo",
 "Policybazaar": "PB Fintech", "Divi's Labs": "Divi's Laboratories",
 "Macrotech Developers": "Lodha", "Dr Reddy": "Dr Reddy's"}

NAMES = sorted(set(STOCKS.split("|")), key=len, reverse=True)
PATS = [(n, re.compile(r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9])",
                       re.I if len(n) > 5 else 0)) for n in NAMES]

# ---------- settings for reading article text (target / stop loss / period) ----------
MAX_ARTICLES = 120        # max articles opened per run
ARTICLE_TIMEOUT = 12      # seconds per request
UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"}

NUM = r"([\d,]+(?:\.\d+)?)"
RS = r"(?:Rs\.?|INR|₹)?\s?"
TARGET_RE = re.compile(r"(?:target(?:\s*price)?|TP)\s*(?:of|at|:|is|to|price of)?\s*(?:Rs\.?|INR|₹)\s?" + NUM, re.I)
SL_RE = re.compile(r"(?:stop[\s\-]?loss|\bSL\b)\s*(?:of|at|:|is|below|placed at)?\s*" + RS + NUM, re.I)
PERIOD_RE = re.compile(r"(?:in|within|over|for|horizon of|period of|time frame of)\s+(?:the\s+next\s+)?"
                       r"(\d+(?:\s*(?:-|–|to)\s*\d+)?\s*(?:months?|weeks?|days?|years?|sessions?))", re.I)


def clean_num(s):
    s = (s or "").replace(",", "").strip()
    try:
        return s if float(s) > 0 else ""
    except Exception:
        return ""


def extract_levels(text):
    """Return (target, stop_loss, period) found in text. Empty string if not found."""
    t = TARGET_RE.search(text)
    s = SL_RE.search(text)
    p = PERIOD_RE.search(text)
    return (clean_num(t.group(1)) if t else "",
            clean_num(s.group(1)) if s else "",
            re.sub(r"\s+", " ", p.group(1)).strip() if p else "")


def find_stocks(title, aliases):
    work = title
    for a in aliases:
        work = re.sub(re.escape(a), " ", work, flags=re.I)
    found = []
    for n, p in PATS:
        if p.search(work):
            c = ALIAS.get(n, n)
            if c not in found:
                found.append(c)
            work = p.sub(" ", work)
    return found


# ---------- Google News link -> real article link ----------
def http_get(url, data=None, headers=None, timeout=ARTICLE_TIMEOUT):
    h = dict(UA)
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h)
    return urllib.request.urlopen(req, timeout=timeout).read()


def resolve_google_link(link):
    m = re.search(r"/articles/([^?/]+)", link)
    if not m:
        return link
    gid = m.group(1)
    # old style links hold the real URL inside the id
    try:
        raw = base64.urlsafe_b64decode(gid + "=" * (-len(gid) % 4)).decode("latin1")
        mm = re.search(r"https?://[^\x00-\x20\"<>]+", raw)
        if mm and "google." not in mm.group(0):
            return mm.group(0)
    except Exception:
        pass
    # new style links need one lookup
    try:
        page = http_get(f"https://news.google.com/rss/articles/{gid}").decode("utf-8", "ignore")
        sg = re.search(r'data-n-a-sg="([^"]+)"', page).group(1)
        ts = re.search(r'data-n-a-ts="([^"]+)"', page).group(1)
        inner = ["garturlreq",
                 [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
                  "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0], gid, int(ts), sg]
        payload = [[["Fbv4je", json.dumps(inner), None, "generic"]]]
        body = ("f.req=" + urllib.parse.quote(json.dumps(payload))).encode()
        resp = http_get("https://news.google.com/_/DotsSplashUi/data/batchexecute", data=body,
                        headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}).decode("utf-8", "ignore")
        parsed = json.loads(resp.split("\n\n")[1])[:-2]
        return json.loads(parsed[0][2])[1]
    except Exception:
        return ""


def article_text(link):
    real = resolve_google_link(link)
    if not real or "news.google." in real:
        return ""
    page = http_get(real).decode("utf-8", "ignore")
    page = re.sub(r"(?is)<(script|style|noscript|svg|header|footer|nav)[^>]*>.*?</\1>", " ", page)
    paras = re.findall(r"(?is)<p[^>]*>(.*?)</p>", page)
    text = " ".join(paras) if paras else page
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text)[:8000]


items = []
for b, aliases in BROKERS.items():
    terms = " OR ".join(f'"{a}"' for a in aliases[:2])
    q = urllib.parse.quote(f"({terms}) stock buy target when:7d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
    except Exception as e:
        print("skip", b, e)
        continue
    seen, n = set(), 0
    for it in root.iter("item"):
        title = it.findtext("title", "")
        link = it.findtext("link", "")
        low = title.lower()
        if not any(a.lower() in low for a in aliases):
            continue
        if link in seen or n >= 15:
            continue
        seen.add(link)
        n += 1
        src = it.findtext("source", "")
        if " - " in title:
            title = title.rsplit(" - ", 1)[0]
        try:
            d = email.utils.parsedate_to_datetime(it.findtext("pubDate"))
            date = d.strftime("%Y-%m-%d")
        except Exception:
            date = ""
        tgt, sl, period = extract_levels(title)
        if not tgt:
            m = re.search(r"(?:Rs\.?|₹)\s?([\d,]+(?:\.\d+)?)", title)
            tgt = clean_num(m.group(1)) if m else ""
        t = title.lower()
        call = ""
        if re.search(r"\b(buy|accumulate|outperform|overweight|bullish)\b", t):
            call = "BUY"
        elif re.search(r"\b(sell|reduce|underperform|underweight|bearish)\b", t):
            call = "SELL"
        items.append({"broker": b, "title": title, "source": src, "link": link,
                      "date": date, "target": tgt, "stop_loss": sl, "period": period,
                      "call": call, "stocks": find_stocks(title, aliases)})
    time.sleep(0.5)

if not items:
    print("nothing found, keeping old file")
    raise SystemExit

items.sort(key=lambda x: x["date"], reverse=True)

# ---------- open articles that still miss a stop loss or target ----------
opened = 0
for it in items:
    if opened >= MAX_ARTICLES:
        break
    # article text can mix several stocks, so only use it when the article is about one stock
    if len(it["stocks"]) != 1 or it["call"] == "SELL":
        continue
    if it["target"] and it["stop_loss"] and it["period"]:
        continue
    opened += 1
    try:
        text = article_text(it["link"])
    except Exception as e:
        print("article skip:", it["title"][:50], e)
        continue
    if not text:
        continue
    tgt, sl, period = extract_levels(text)
    if not it["target"] and tgt:
        it["target"] = tgt
    if not it["stop_loss"] and sl:
        it["stop_loss"] = sl
    if not it["period"] and period:
        it["period"] = period
    time.sleep(0.5)

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
json.dump({"updated": now, "brokers": list(BROKERS.keys()), "items": items},
          open("picks.json", "w"), ensure_ascii=False, indent=1)
print(len(items), "items |", sum(1 for i in items if i["target"]), "with target |",
      sum(1 for i in items if i["stop_loss"]), "with stop loss |", opened, "articles opened")
