
import json
import re
import time
import html
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


# --------------------------------------------------
# 1. MEDIA SOURCES
# --------------------------------------------------

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


# --------------------------------------------------
# 2. STOCK NAMES AND NSE SYMBOLS
# --------------------------------------------------

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


# --------------------------------------------------
# 3. EXPLICIT SWING / POSITIONAL KEYWORDS
# --------------------------------------------------

KEYWORDS = (
    "swing trade",
    "swing trading",
    "swing trader",
    "positional trade",
    "positional trading",
    "positional pick",
    "positional call",
    "short-term trade",
    "short term trade",
    "short-term pick",
    "short term pick",
    "short-term call",
    "short term call"
)


# --------------------------------------------------
# 4. STOCK IDENTIFICATION
# --------------------------------------------------

def find_stocks(text):
    found = []

    for name, (symbol, aliases) in STOCKS.items():
        for alias in aliases:
            pattern = (
                r"(?<![A-Za-z0-9])"
                + re.escape(alias)
                + r"(?![A-Za-z0-9])"
            )

            if re.search(pattern, text, re.I):
                found.append((name, symbol))
                break

    return found


# --------------------------------------------------
# 5. TARGET PRICE EXTRACTION
# --------------------------------------------------

def get_target(text):
    match = re.search(
        r"(?:target|tgt)\s*(?:of|at|:)?\s*"
        r"(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.\d+)?)",
        text,
        re.I
    )

    if match:
        return match.group(1).replace(",", "")

    return ""


# --------------------------------------------------
# 6. CLEAN ARTICLE DESCRIPTION
# --------------------------------------------------

def clean_description(description):
    description = html.unescape(description or "")
    description = re.sub(r"<[^>]+>", " ", description)
    description = re.sub(r"\s+", " ", description)

    return description.strip()


# --------------------------------------------------
# 7. CHECK EXPLICIT TRADE KEYWORDS
# --------------------------------------------------

def has_trade_keyword(text):
    text = text.lower()

    return any(keyword in text for keyword in KEYWORDS)


# --------------------------------------------------
# 8. READ ONE MEDIA SOURCE
# --------------------------------------------------

def read_source(source, domain):

    query = (
        f'site:{domain} '
        '("swing trade" OR "swing trading" OR '
        '"positional trade" OR "positional trading" OR '
        '"positional pick" OR "short-term trade" OR '
        '"short term trade" OR "short-term pick")'
    )

    url = (
        "https://news.google.com/rss/search?"
        + urllib.parse.urlencode({
            "q": query,
            "hl": "en-IN",
            "gl": "IN",
            "ceid": "IN:en"
        })
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
            )
        }
    )

    root = None

    # Retry temporary failures and rate limits.
    for attempt in range(3):

        try:
            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                root = ET.fromstring(response.read())

            break

        except urllib.error.HTTPError as error:

            if error.code not in (429, 500, 502, 503, 504):
                raise

            if attempt == 2:
                raise

            wait_time = 5 * (attempt + 1)
            print(source, "HTTP", error.code,
                  "- retrying in", wait_time, "seconds")

            time.sleep(wait_time)

        except Exception:

            if attempt == 2:
                raise

            time.sleep(5 * (attempt + 1))

    if root is None:
        return []

    results = []

    for article in root.findall("./channel/item"):

        title = (
            article.findtext("title") or ""
        ).strip()

        description = clean_description(
            article.findtext("description") or ""
        )

        link = (
            article.findtext("link") or ""
        ).strip()

        pubdate = (
            article.findtext("pubDate") or ""
        )

        # Check both headline and article description.
        content = title + " " + description

        # Include only explicitly labelled trade ideas.
        if not has_trade_keyword(content):
            continue

        stocks_found = find_stocks(content)

        if not stocks_found:
            continue

        try:
            date = parsedate_to_datetime(
                pubdate
            ).astimezone(timezone.utc).isoformat()

        except Exception:
            date = pubdate

        target = get_target(content)

        for stock, symbol in stocks_found:

            results.append({
                "source": source,
                "stock": stock,
                "symbol": symbol,
                "title": title,
                "link": link,
                "date": date,
                "entry": "",
                "target1": target,
                "target2": "",
                "target3": "",
                "stop_loss": "",
                "holding_period": "",
                "analyst": ""
            })

    return results


# --------------------------------------------------
# 9. COLLECT ALL EIGHT SOURCES
# --------------------------------------------------

def main():

    items = []
    errors = {}
    source_counts = {}

    for source, domain in SOURCES.items():

        try:
            found = read_source(source, domain)

            items.extend(found)
            source_counts[source] = len(found)

            print(
                source,
                ":",
                len(found),
                "records"
            )

        except Exception as error:

            errors[source] = str(error)
            source_counts[source] = 0

            print(
                "Error:",
                source,
                error
            )

        # Avoid sending requests too quickly.
        time.sleep(3)

    # Remove duplicate records from the same source.
    unique = {}

    for item in items:

        key = (
            item["source"],
            item["stock"],
            item["link"]
        )

        unique[key] = item

    final_items = sorted(
        unique.values(),
        key=lambda item: item["date"],
        reverse=True
    )

    # --------------------------------------------------
    # 10. SAVE JSON FILE
    # --------------------------------------------------

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),

        "sources": list(SOURCES.keys()),

        "source_counts": source_counts,

        "errors": errors,

        "method_note": (
            "RSS-based media headline collection. "
            "Only explicit swing or positional trade "
            "keywords and recognised stock names are included. "
            "Article descriptions are also checked. "
            "Entry prices, stop losses and missing targets "
            "are not guessed. Recommendations are not "
            "independently verified investment advice."
        ),

        "items": final_items
    }

    Path("media_picks.json").write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("--------------------------------")
    print(
        "Saved media_picks.json:",
        len(final_items),
        "records"
    )
    print("--------------------------------")


if __name__ == "__main__":
    main()
