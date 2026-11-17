
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


# ==================================================
# 1. EIGHT MEDIA SOURCES
# ==================================================

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


# ==================================================
# 2. SEARCH PHRASES
# ==================================================

SEARCH_GROUPS = [
    '"trade spotlight" OR "stocks to buy" OR "stock picks"',
    '"swing trade" OR "positional trade" OR "trading ideas"',
    '"short-term gains" OR "short term gains" OR "buy recommendations"'
]


# ==================================================
# 3. STOCK DATABASE
# ==================================================

STOCKS = {
    "Reliance Industries": ("RELIANCE", ["Reliance Industries", "Reliance Industries Ltd"]),
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
    "Hindustan Aeronautics": ("HAL", ["Hindustan Aeronautics"]),
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
    "Adani Green Energy": ("ADANIGREEN", ["Adani Green Energy"]),
    "Adani Enterprises": ("ADANIENT", ["Adani Enterprises"]),
    "Maruti Suzuki": ("MARUTI", ["Maruti Suzuki"]),
    "Mahindra & Mahindra": ("M&M", ["Mahindra & Mahindra"]),
    "Sun Pharma": ("SUNPHARMA", ["Sun Pharma"]),
    "Cipla": ("CIPLA", ["Cipla"]),
    "Bharti Airtel": ("BHARTIARTL", ["Bharti Airtel", "Airtel"]),
    "Titan": ("TITAN", ["Titan Company", "Titan"]),
    "Trent": ("TRENT", ["Trent"]),
    "DLF": ("DLF", ["DLF"]),
    "Eternal": ("ETERNAL", ["Eternal", "Zomato"]),
    "BSE": ("BSE", ["BSE Limited"]),
    "CDSL": ("CDSL", ["CDSL"]),
    "IRCTC": ("IRCTC", ["IRCTC"]),
    "Bharat Electronics": ("BEL", ["Bharat Electronics"]),
    "Tata Consumer Products": ("TATACONSUM", ["Tata Consumer"]),
    "Asian Paints": ("ASIANPAINT", ["Asian Paints"]),
    "Hindustan Unilever": ("HINDUNILVR", ["Hindustan Unilever"]),
    "Eicher Motors": ("EICHERMOT", ["Eicher Motors"]),
    "TVS Motor": ("TVSMOTOR", ["TVS Motor"]),
    "Hero MotoCorp": ("HEROMOTOCO", ["Hero MotoCorp"]),
    "IndusInd Bank": ("INDUSINDBK", ["IndusInd Bank"]),
    "Federal Bank": ("FEDERALBNK", ["Federal Bank"]),
    "Bank of Baroda": ("BANKBARODA", ["Bank of Baroda"]),
    "Canara Bank": ("CANBK", ["Canara Bank"]),
    "Power Finance Corporation": ("PFC", ["Power Finance Corporation"]),
    "REC Limited": ("RECLTD", ["REC Limited"]),
    "Voltas": ("VOLTAS", ["Voltas"]),
    "Polycab": ("POLYCAB", ["Polycab"]),
    "Dixon Technologies": ("DIXON", ["Dixon Technologies"]),
    "General Insurance Corporation": ("GICRE", ["General Insurance Corporation", "GIC Re"]),
    "Aditya Birla Real Estate": ("ABREL", ["Aditya Birla Real Estate"]),
    "Godrej Consumer Products": ("GODREJCP", ["Godrej Consumer"]),
    "Fortis Healthcare": ("FORTIS", ["Fortis Healthcare"]),
    "KPR Mill": ("KPRMILL", ["KPR Mill"]),
    "Alicon Castalloy": ("ALICON", ["Alicon Castalloy"]),
    "Ramkrishna Forgings": ("RKFORGE", ["Ramkrishna Forgings"]),
    "Kwality Wall's": ("KWIL", ["Kwality Walls", "Kwality Wall's"]),
    "Indus Towers": ("INDUSTOWER", ["Indus Towers"]),
    "GE Vernova T&D India": ("GVT&D", ["GE Vernova T&D", "GE Vernova"]),
    "Lloyds Engineering Works": ("LLOYDSENGG", ["Lloyds Engineering Works"]),
    "Acutaas Chemicals": ("ACUTAAS", ["Acutaas Chemicals", "Acutaas"]),
    "NOCIL": ("NOCIL", ["NOCIL"]),
    "Heritage Foods": ("HERITGFOOD", ["Heritage Foods"]),
    "BEML": ("BEML", ["BEML"]),
    "Venky's India": ("VENKEYS", ["Venky's India", "Venkys India"]),
    "Supreme Petrochem": ("SUPPETRO", ["Supreme Petrochem"]),
    "Jubilant Pharmova": ("JUBLPHARMA", ["Jubilant Pharmova"]),
    "Groww": ("GROWW", ["Groww"]),
    "Force Motors": ("FORCEMOT", ["Force Motors"]),
    "Mankind Pharma": ("MANKIND", ["Mankind Pharma"]),
    "Havells India": ("HAVELLS", ["Havells"]),
    "MCX": ("MCX", ["MCX India"]),
    "Devyani International": ("DEVYANI", ["Devyani International"]),
    "Samvardhana Motherson": ("MOTHERSON", ["Samvardhana Motherson", "Motherson"]),
    "FACT": ("FACT", ["FACT Limited"]),
    "Hindustan Zinc": ("HINDZINC", ["Hindustan Zinc"]),
    "Bharat Dynamics": ("BDL", ["Bharat Dynamics"]),
    "J K Tyre": ("JKTYRE", ["JK Tyre"]),
    "Marksans Pharma": ("MARKSANS", ["Marksans Pharma"]),
    "Paytm": ("PAYTM", ["Paytm"]),
    "Radico Khaitan": ("RADICO", ["Radico Khaitan"]),
    "Nifty": ("NIFTY", ["Nifty 50"]),
    "Bank Nifty": ("BANKNIFTY", ["Bank Nifty"])
}


# ==================================================
# 4. RECOMMENDATION FILTERS
# ==================================================

TRADE_PATTERNS = [
    "trade spotlight",
    "swing trade",
    "swing trading",
    "positional trade",
    "positional pick",
    "positional call",
    "short-term",
    "short term",
    "stocks to buy",
    "stock picks",
    "trading ideas",
    "trading recommendation",
    "buy recommendations",
    "top stocks to buy",
    "short-term gains",
    "short term gains"
]

RECOMMENDATION_PATTERNS = [
    "strategy: buy",
    "buying recommended",
    "recommended to buy",
    "buy recommendation",
    "buy call",
    "target price",
    "stop-loss",
    "stop loss",
    "stocks to buy",
    "stock picks",
    "trading ideas",
    "trade spotlight",
    "short-term gains",
    "short term gains",
    "recommends buying"
]


# ==================================================
# 5. TEXT CLEANING
# ==================================================

def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


# ==================================================
# 6. STOCK IDENTIFICATION
# ==================================================

def find_stocks(text):
    found = {}

    for name, (symbol, aliases) in STOCKS.items():

        for alias in aliases:

            pattern = (
                r"(?<![A-Za-z0-9])"
                + re.escape(alias)
                + r"(?![A-Za-z0-9])"
            )

            if re.search(pattern, text, re.I):
                found[symbol] = (name, symbol)
                break

    return list(found.values())


# ==================================================
# 7. RECOMMENDATION VALIDATION
# ==================================================

def is_trade_recommendation(text):

    lower = text.lower()

    has_trade_style = any(
        phrase in lower for phrase in TRADE_PATTERNS
    )

    has_recommendation = any(
        phrase in lower for phrase in RECOMMENDATION_PATTERNS
    )

    return has_trade_style and has_recommendation


# ==================================================
# 8. TARGET EXTRACTION
# ==================================================

def get_targets(text):

    patterns = [
        r"(?:target|tgt)\s*(?:price)?\s*(?:of|at|:)?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.\d+)?)",
        r"target\s*(?:of|at)\s*(?:Rs\.?|₹)?\s*([0-9,]+(?:\.\d+)?)"
    ]

    for pattern in patterns:

        matches = re.findall(pattern, text, re.I)

        if matches:
            return [
                value.replace(",", "")
                for value in matches[:3]
            ]

    return []


# ==================================================
# 9. STOP LOSS EXTRACTION
# ==================================================

def get_stop_loss(text):

    match = re.search(
        r"(?:stop[\s-]*loss|SL)\s*[:\-]?\s*"
        r"(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.\d+)?)",
        text,
        re.I
    )

    if match:
        return match.group(1).replace(",", "")

    return ""


# ==================================================
# 10. ENTRY PRICE EXTRACTION
# ==================================================

def get_entry(text):

    patterns = [
        r"(?:buying recommended|buy around|buy at|entry)\s*"
        r"(?:Rs\.?|₹)?\s*([0-9,]+(?:\.\d+)?)"
        r"\s*(?:to|-|–)\s*"
        r"(?:Rs\.?|₹)?\s*([0-9,]+(?:\.\d+)?)",

        r"(?:buying recommended|buy around|buy at|entry)\s*"
        r"(?:Rs\.?|₹)?\s*([0-9,]+(?:\.\d+)?)"
    ]

    for pattern in patterns:

        match = re.search(pattern, text, re.I)

        if match:

            values = [
                value.replace(",", "")
                for value in match.groups()
                if value
            ]

            return "-".join(values)

    return ""


# ==================================================
# 11. DATE CONVERSION
# ==================================================

def get_date(pubdate):

    try:
        return parsedate_to_datetime(
            pubdate
        ).astimezone(timezone.utc).isoformat()

    except Exception:
        return pubdate


# ==================================================
# 12. FETCH ONE RSS SEARCH
# ==================================================

def fetch_rss(query):

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
            "User-Agent": "Mozilla/5.0"
        }
    )

    for attempt in range(3):

        try:

            with urllib.request.urlopen(
                request,
                timeout=25
            ) as response:

                root = ET.fromstring(response.read())

            return root.findall("./channel/item")

        except urllib.error.HTTPError as error:

            if error.code not in (429, 500, 502, 503, 504):
                raise

            if attempt == 2:
                raise

            wait = 5 * (attempt + 1)

            print(
                "Temporary HTTP error",
                error.code,
                "- waiting",
                wait,
                "seconds"
            )

            time.sleep(wait)

        except Exception:

            if attempt == 2:
                raise

            time.sleep(5 * (attempt + 1))

    return []


# ==================================================
# 13. COLLECT ONE PUBLISHER
# ==================================================

def read_source(source, domain):

    articles = {}

    for phrase_group in SEARCH_GROUPS:

        query = (
            f'site:{domain} ({phrase_group})'
        )

        try:

            found = fetch_rss(query)

            for article in found:

                title = clean_text(
                    article.findtext("title") or ""
                )

                description = clean_text(
                    article.findtext("description") or ""
                )

                link = (
                    article.findtext("link") or ""
                ).strip()

                pubdate = (
                    article.findtext("pubDate") or ""
                )

                key = link or title

                if key:
                    articles[key] = {
                        "title": title,
                        "description": description,
                        "link": link,
                        "date": get_date(pubdate)
                    }

        except Exception as error:

            print(
                source,
                "search warning:",
                str(error)
            )

        time.sleep(1)

    results = []

    for article in articles.values():

        title = article["title"]
        description = article["description"]

        content = title + " " + description

        if not is_trade_recommendation(content):
            continue

        stocks_found = find_stocks(content)

        if not stocks_found:
            continue

        targets = get_targets(content)

        for stock, symbol in stocks_found:

            results.append({
                "source": source,
                "stock": stock,
                "symbol": symbol,
                "title": title,
                "link": article["link"],
                "date": article["date"],
                "entry": get_entry(content),
                "target1": targets[0] if len(targets) > 0 else "",
                "target2": targets[1] if len(targets) > 1 else "",
                "target3": targets[2] if len(targets) > 2 else "",
                "stop_loss": get_stop_loss(content),
                "holding_period": "",
                "analyst": ""
            })

    return results


# ==================================================
# 14. MAIN COLLECTION
# ==================================================

def main():

    all_items = []
    errors = {}
    source_counts = {}

    print("Starting media recommendation collection")

    for source, domain in SOURCES.items():

        try:

            records = read_source(source, domain)

            all_items.extend(records)

            source_counts[source] = len(records)

            print(
                source,
                ":",
                len(records),
                "recommendations"
            )

        except Exception as error:

            errors[source] = str(error)
            source_counts[source] = 0

            print(
                "ERROR:",
                source,
                str(error)
            )

        time.sleep(2)

    # Remove duplicate articles for the same publisher and stock.
    unique = {}

    for item in all_items:

        key = (
            item["source"],
            item["symbol"],
            item["link"]
        )

        unique[key] = item

    final_items = sorted(
        unique.values(),
        key=lambda item: item["date"],
        reverse=True
    )

    # ==================================================
    # 15. SAVE JSON
    # ==================================================

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),

        "sources": list(SOURCES.keys()),

        "source_counts": source_counts,

        "errors": errors,

        "method_note": (
            "Google News RSS searches across eight publishers. "
            "Multiple search phrases are used. Headlines and RSS "
            "descriptions are checked. Only explicit trade-style "
            "and recommendation wording with recognised stock "
            "names is included. Entry, target and stop-loss values "
            "are extracted only when visible in the available text. "
            "Missing values are not guessed. RSS coverage is not "
            "complete and every recommendation requires verification."
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

    print("------------------------------------")
    print("MEDIA COLLECTION COMPLETED")
    print("Total records:", len(final_items))
    print("Publisher errors:", len(errors))
    print("------------------------------------")


if __name__ == "__main__":
    main()
