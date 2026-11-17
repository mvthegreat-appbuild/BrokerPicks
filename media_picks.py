
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

SOURCES = {
    "Moneycontrol": "moneycontrol.com",
    "Business Today": "businesstoday.in",
    "Economic Times": "economictimes.indiatimes.com",
    "Zee Business": "zeebiz.com",
    "LiveMint": "livemint.com",
    "NDTV Profit": "ndtvprofit.com",
    "CNBC-TV18": "cnbctv18.com",
    "ET NOW": "timesnownews.com"
}

# Company names and NSE symbols
STOCKS = {
    "Reliance Industries": ("RELIANCE", ["Reliance Industries"]),
    "HDFC Bank": ("HDFCBANK", ["HDFC Bank"]),
    "ICICI Bank": ("ICICIBANK", ["ICICI Bank"]),
    "State Bank of India": ("SBIN", ["State Bank of India", "SBI"]),
    "Infosys": ("INFY", ["Infosys"]),
    "TCS": ("TCS", ["Tata Consultancy Services", "TCS"]),
    "Wipro": ("WIPRO", ["Wipro"]),
    "Tata Motors": ("TMPV", ["Tata Motors"]),
    "Bajaj Finance": ("BAJFINANCE", ["Bajaj Finance"]),
    "Bajaj Finserv": ("BAJAJFINSV", ["Bajaj Finserv"]),
    "Axis Bank": ("AXISBANK", ["Axis Bank"]),
    "Kotak Mahindra Bank": ("KOTAKBANK", ["Kotak Mahindra Bank"]),
    "Larsen & Toubro": ("LT", ["Larsen & Toubro", "L&T"]),
    "Hindustan Aeronautics": ("HAL", ["Hindustan Aeronautics", "HAL"]),
    "ITC": ("ITC", ["ITC"]),
    "Tata Steel": ("TATASTEEL", ["Tata Steel"]),
    "JSW Steel": ("JSWSTEEL", ["JSW Steel"]),
    "Vedanta": ("VEDL", ["Vedanta"]),
    "Coal India": ("COALINDIA", ["Coal India"]),
    "ONGC": ("ONGC", ["ONGC"]),
    "NTPC": ("NTPC", ["NTPC"]),
    "Power Grid": ("POWERGRID", ["Power Grid"]),
    "Tata Power": ("TATAPOWER", ["Tata Power"]),
    "Adani Ports": ("ADANIPORTS", ["Adani Ports"]),
    "Maruti Suzuki": ("MARUTI", ["Maruti Suzuki"]),
    "Mahindra & Mahindra": ("M&M", ["Mahindra & Mahindra"]),
    "Sun Pharma": ("SUNPHARMA", ["Sun Pharma"]),
    "Cipla": ("CIPLA", ["Cipla"]),
    "Bharti Airtel": ("BHARTIARTL", ["Bharti Airtel"]),
    "Titan": ("TITAN", ["Titan"]),
    "Trent": ("TRENT", ["Trent"]),
    "DLF": ("DLF", ["DLF"]),
    "Zomato": ("ETERNAL", ["Zomato", "Eternal"]),
    "BSE": ("BSE", ["BSE"]),
    "CDSL": ("CDSL", ["CDSL"]),
    "IRCTC": ("IRCTC", ["IRCTC"]),
    "BEL": ("BEL", ["Bharat Electronics", "BEL"]),
    "Tata Consumer Products": ("TATACONSUM", ["Tata Consumer"]),
    "Asian Paints": ("ASIANPAINT", ["Asian Paints"]),
    "Hindustan Unilever": ("HINDUNILVR", ["Hindustan Unilever", "HUL"]),
    "Eicher Motors": ("EICHERMOT", ["Eicher Motors"]),
    "TVS Motor": ("TVSMOTOR", ["TVS Motor"]),
    "Hero MotoCorp": ("HEROMOTOCO", ["Hero MotoCorp"]),
    "IndusInd Bank": ("INDUSINDBK", ["IndusInd Bank"]),
    "Federal Bank": ("FEDERALBNK", ["Federal Bank"]),
    "Bank of Baroda": ("BANKBARODA", ["Bank of Baroda"]),
    "Canara Bank": ("CANBK", ["Canara Bank"]),
    "PFC": ("PFC", ["Power Finance Corporation", "PFC"]),
    "REC": ("RECLTD", ["REC Limited"]),
    "Voltas": ("VOLTAS", ["Voltas"]),
    "Polycab": ("POLYCAB", ["Polycab"]),
    "Dixon Technologies": ("DIXON", ["Dixon Technologies"])
}

KEYWORDS = (
    "swing trade", "swing trading", "positional trade",
    "positional pick", "short-term trade"
)

def find_stocks(title):
    found = []
    for name, (symbol, aliases) in STOCKS.items():
        for alias in aliases:
            pattern = r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])"
            if re.search(pattern, title, re.I):
                found.append((name, symbol))
                break
    return found

def get_target(title):
    match = re.search(
        r"(?:target|tgt)\s*(?:of|at|:)?\s*(?:Rs\.?|₹)?\s*([0-9,]+(?:\.\d+)?)",
        title, re.I
    )
    return match.group(1).replace(",", "") if match else ""

def read_source(source, domain):
    query = f'site:{domain} ("swing trade" OR "swing trading" OR "positional trade") stocks'
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"
    })

    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        root = ET.fromstring(response.read())

    results = []

    for article in root.findall("./channel/item"):
        title = (article.findtext("title") or "").strip()
        link = (article.findtext("link") or "").strip()
        pubdate = article.findtext("pubDate") or ""

        if not any(word in title.lower() for word in KEYWORDS):
            continue

        try:
            date = parsedate_to_datetime(pubdate).astimezone(
                timezone.utc
            ).isoformat()
        except Exception:
            date = pubdate

        for stock, symbol in find_stocks(title):
            results.append({
                "source": source,
                "stock": stock,
                "symbol": symbol,
                "title": title,
                "link": link,
                "date": date,
                "entry": "",
                "target1": get_target(title),
                "target2": "",
                "target3": "",
                "stop_loss": "",
                "holding_period": "",
                "analyst": ""
            })

    return results

def main():
    items = []
    errors = {}

    for source, domain in SOURCES.items():
        try:
            found = read_source(source, domain)
            items.extend(found)
            print(source, ":", len(found), "records")
        except Exception as error:
            errors[source] = str(error)
            print("Error:", source, error)

        time.sleep(1)

    unique = {}
    for item in items:
        key = (item["source"], item["stock"], item["link"])
        unique[key] = item

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "sources": list(SOURCES.keys()),
        "errors": errors,
        "method_note": (
            "Only explicitly swing/positional headlines with a recognised "
            "stock name are included. Missing entry, targets and stop loss "
            "are not guessed. Headlines are not verified trade advice."
        ),
        "items": sorted(
            unique.values(),
            key=lambda item: item["date"],
            reverse=True
        )
    }

    Path("media_picks.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("Saved media_picks.json:", len(output["items"]), "records")

if __name__ == "__main__":
    main()
