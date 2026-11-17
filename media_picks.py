#!/usr/bin/env python3
"""Moneycontrol-only swing/positional/short-term trade collector.

Uses Google News RSS for discovery and fetches the linked Moneycontrol article
for verification. Standard-library only; suitable for GitHub Actions.
"""

import datetime as dt
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

OUTPUT_FILE = Path("media_picks.json")
SOURCE_NAME = "Moneycontrol"
SOURCE_DOMAIN = "moneycontrol.com"
USER_AGENT = (
    "Mozilla/5.0 (compatible; BrokerPicksPro/1.0; "
    "+https://github.com/mvthegreat-appbuild/BrokerPicks)"
)

# Search separately to improve coverage without accepting generic stock lists.
SEARCH_QUERIES = [
    'site:moneycontrol.com "Trade Spotlight"',
    'site:moneycontrol.com "swing trade" OR "swing trading"',
    'site:moneycontrol.com "positional trade" OR "short-term trading ideas"',
    'site:moneycontrol.com "short-term trade" OR "short term trade"',
]

# Aliases are matched longest-first. Avoid ambiguous abbreviations where possible.
STOCKS = {
    "Aditya Birla Real Estate": ("ABREL", ["Aditya Birla Real Estate", "AB Real Estate"]),
    "General Insurance Corporation": ("GICRE", ["General Insurance Corporation", "General Insurance Corp", "GIC Re"]),
    "Godrej Consumer Products": ("GODREJCP", ["Godrej Consumer Products", "Godrej Consumer"]),
    "HDFC Bank": ("HDFCBANK", ["HDFC Bank"]),
    "ICICI Bank": ("ICICIBANK", ["ICICI Bank"]),
    "State Bank of India": ("SBIN", ["State Bank of India", "SBI"]),
    "Axis Bank": ("AXISBANK", ["Axis Bank"]),
    "Kotak Mahindra Bank": ("KOTAKBANK", ["Kotak Mahindra Bank", "Kotak Bank"]),
    "Bajaj Finance": ("BAJFINANCE", ["Bajaj Finance"]),
    "Bajaj Finserv": ("BAJAJFINSV", ["Bajaj Finserv"]),
    "Reliance Industries": ("RELIANCE", ["Reliance Industries", "Reliance"]),
    "Larsen & Toubro": ("LT", ["Larsen & Toubro", "Larsen and Toubro", "L&T"]),
    "Infosys": ("INFY", ["Infosys"]),
    "Tata Consultancy Services": ("TCS", ["Tata Consultancy Services", "TCS"]),
    "Wipro": ("WIPRO", ["Wipro"]),
    "HCL Technologies": ("HCLTECH", ["HCL Technologies", "HCL Tech"]),
    "Tech Mahindra": ("TECHM", ["Tech Mahindra"]),
    "Tata Motors": ("TMPV", ["Tata Motors"]),
    "Mahindra & Mahindra": ("M&M", ["Mahindra & Mahindra", "Mahindra and Mahindra"]),
    "Maruti Suzuki": ("MARUTI", ["Maruti Suzuki", "Maruti"]),
    "Eicher Motors": ("EICHERMOT", ["Eicher Motors"]),
    "TVS Motor": ("TVSMOTOR", ["TVS Motor", "TVS Motors"]),
    "Hero MotoCorp": ("HEROMOTOCO", ["Hero MotoCorp", "Hero Motocorp"]),
    "Asian Paints": ("ASIANPAINT", ["Asian Paints"]),
    "Hindustan Unilever": ("HINDUNILVR", ["Hindustan Unilever", "HUL"]),
    "ITC": ("ITC", ["ITC"]),
    "Titan Company": ("TITAN", ["Titan Company"]),
    "Trent": ("TRENT", ["Trent"]),
    "Sun Pharmaceutical": ("SUNPHARMA", ["Sun Pharmaceutical", "Sun Pharma"]),
    "Cipla": ("CIPLA", ["Cipla"]),
    "Dr Reddy's Laboratories": ("DRREDDY", ["Dr Reddy's Laboratories", "Dr. Reddy's"]),
    "Airtel": ("BHARTIARTL", ["Bharti Airtel"]),
    "Tata Steel": ("TATASTEEL", ["Tata Steel"]),
    "JSW Steel": ("JSWSTEEL", ["JSW Steel"]),
    "Hindalco Industries": ("HINDALCO", ["Hindalco Industries", "Hindalco"]),
    "Vedanta": ("VEDL", ["Vedanta"]),
    "Coal India": ("COALINDIA", ["Coal India"]),
    "ONGC": ("ONGC", ["Oil and Natural Gas Corporation", "ONGC"]),
    "NTPC": ("NTPC", ["NTPC"]),
    "Power Grid Corporation": ("POWERGRID", ["Power Grid Corporation", "Power Grid"]),
    "Tata Power": ("TATAPOWER", ["Tata Power"]),
    "Adani Ports": ("ADANIPORTS", ["Adani Ports", "Adani Ports and SEZ"]),
    "Adani Enterprises": ("ADANIENT", ["Adani Enterprises"]),
    "Bharat Electronics": ("BEL", ["Bharat Electronics", "BEL"]),
    "Hindustan Aeronautics": ("HAL", ["Hindustan Aeronautics", "HAL"]),
    "Bharat Dynamics": ("BDL", ["Bharat Dynamics"]),
    "BSE": ("BSE", ["BSE Ltd", "BSE Limited"]),
    "CDSL": ("CDSL", ["CDSL"]),
    "IRCTC": ("IRCTC", ["IRCTC"]),
    "DLF": ("DLF", ["DLF"]),
    "Zomato": ("ETERNAL", ["Zomato", "Eternal"]),
    "Eternal": ("ETERNAL", ["Eternal"]),
    "IndusInd Bank": ("INDUSINDBK", ["IndusInd Bank"]),
    "Federal Bank": ("FEDERALBNK", ["Federal Bank"]),
    "Bank of Baroda": ("BANKBARODA", ["Bank of Baroda"]),
    "Canara Bank": ("CANBK", ["Canara Bank"]),
    "Punjab National Bank": ("PNB", ["Punjab National Bank", "PNB"]),
    "Power Finance Corporation": ("PFC", ["Power Finance Corporation", "PFC"]),
    "REC": ("RECLTD", ["REC Limited", "REC Ltd"]),
    "Voltas": ("VOLTAS", ["Voltas"]),
    "Polycab India": ("POLYCAB", ["Polycab India", "Polycab"]),
    "Dixon Technologies": ("DIXON", ["Dixon Technologies", "Dixon Tech"]),
    "Fortis Healthcare": ("FORTIS", ["Fortis Healthcare", "Fortis"]),
    "Mankind Pharma": ("MANKIND", ["Mankind Pharma"]),
    "Havells India": ("HAVELLS", ["Havells India", "Havells"]),
    "MCX": ("MCX", ["Multi Commodity Exchange", "MCX"]),
    "Paytm": ("PAYTM", ["One 97 Communications", "Paytm"]),
    "Hindustan Zinc": ("HINDZINC", ["Hindustan Zinc"]),
    "Motherson": ("MOTHERSON", ["Samvardhana Motherson", "Motherson"]),
    "FACT": ("FACT", ["Fertilizers and Chemicals Travancore", "FACT"]),
    "JK Tyre": ("JKTYRE", ["JK Tyre", "J.K. Tyre"]),
    "Radico Khaitan": ("RADICO", ["Radico Khaitan"]),
    "Supreme Petrochem": ("SPL", ["Supreme Petrochem"]),
    "Jubilant Pharmova": ("JUBLPHARMA", ["Jubilant Pharmova"]),
    "Groww": ("GROWW", ["Billionbrains Garage Ventures", "Groww"]),
}

TRADE_PATTERNS = [
    r"\btrade\s+spotlight\b",
    r"\bswing\s+trades?\b", r"\bswing\s+trading\b",
    r"\bpositional\s+(?:trades?|calls?|picks?)\b",
    r"\bshort[- ]term\s+(?:trading\s+)?(?:ideas?|trades?|calls?|picks?)\b",
    r"\btrading\s+ideas?\s+for\s+the\s+short[- ]term\b",
]


def fetch_url(url, timeout=20, attempts=3):
    last_error = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.geturl(), response.headers.get_content_charset() or "utf-8"
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise last_error


class ArticleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg", "nav", "footer", "header"):
            self.skip_depth += 1
        if not self.skip_depth and tag in ("p", "li", "h1", "h2", "h3", "td", "th", "br"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg", "nav", "footer", "header") and self.skip_depth:
            self.skip_depth -= 1
        if not self.skip_depth and tag in ("p", "li", "h1", "h2", "h3", "td", "th"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth:
            clean = re.sub(r"\s+", " ", data).strip()
            if clean:
                self.parts.append(clean + " ")


def clean_text(raw):
    parser = ArticleTextParser()
    try:
        parser.feed(raw)
        text = " ".join(parser.parts)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_meta_description(raw):
    patterns = [
        r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:description|og:description)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, re.I)
        if match:
            return html.unescape(match.group(1))
    return ""


def decode_feed(feed_bytes):
    root = ET.fromstring(feed_bytes)
    records = []
    for node in root.findall(".//item"):
        title = node.findtext("title", default="").strip()
        link = node.findtext("link", default="").strip()
        description = node.findtext("description", default="").strip()
        pub_date = node.findtext("pubDate", default="").strip()
        source_node = node.find("source")
        feed_source = (source_node.text or "").strip() if source_node is not None else ""
        if title and link:
            records.append({"title": html.unescape(title), "link": link,
                            "description": clean_text(description), "pub_date": pub_date,
                            "feed_source": feed_source})
    return records


def parse_date(value):
    if not value:
        return ""
    try:
        parsed = dt.datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %Z")
        return parsed.replace(tzinfo=dt.timezone.utc).isoformat()
    except Exception:
        try:
            parsed = dt.datetime.strptime(value[:25], "%a, %d %b %Y %H:%M:%S")
            return parsed.replace(tzinfo=dt.timezone.utc).isoformat()
        except Exception:
            return ""


def has_trade_label(text):
    return any(re.search(pattern, text, re.I) for pattern in TRADE_PATTERNS)


def find_stocks(text):
    found = []
    for display_name, (symbol, aliases) in STOCKS.items():
        for alias in sorted(aliases, key=len, reverse=True):
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])", text, re.I):
                found.append((display_name, symbol))
                break
    # A stock/symbol pair should appear only once in each article.
    unique = {}
    for name, symbol in found:
        unique[symbol] = (name, symbol)
    return list(unique.values())


def nearby_values(text, stock_name, symbol):
    aliases = STOCKS.get(stock_name, (symbol, [stock_name]))[1]
    positions = []
    for alias in aliases:
        for match in re.finditer(re.escape(alias), text, re.I):
            positions.append(match.start())
    if not positions:
        return {"entry": "", "target": "", "stop_loss": ""}
    start = min(positions)
    # Restrict values to a local block around the stock mention to avoid
    # assigning another stock's levels to this stock.
    chunk = text[max(0, start - 250): start + 1400]
    money = r"(?:₹|Rs\.?\s?|INR\s*)\s*([0-9,]+(?:\.\d+)?)"

    def first(pattern):
        match = re.search(pattern, chunk, re.I)
        return match.group(1).replace(",", "") if match else ""

    entry = first(r"(?:entry|buy\s+(?:above|at|range)|entry\s+range)\s*[:\-]?\s*" + money)
    target = first(r"(?:target(?:s)?|tgt)\s*[:\-]?\s*" + money)
    stop = first(r"(?:stop[- ]loss|stoploss|sl)\s*[:\-]?\s*" + money)
    return {"entry": entry, "target": target, "stop_loss": stop}


def google_news_url(query):
    params = urllib.parse.urlencode({
        "q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"
    })
    return "https://news.google.com/rss/search?" + params


def collect():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    errors = {}
    candidates = {}

    for query in SEARCH_QUERIES:
        try:
            feed, _, charset = fetch_url(google_news_url(query))
            for item in decode_feed(feed):
                # Keep only Moneycontrol-origin results.
                if SOURCE_DOMAIN not in urllib.parse.urlparse(item["link"]).netloc.lower():
                    # Google News links are redirects, so source/title must also identify MC.
                    if ("moneycontrol" not in item["title"].lower()
                            and "moneycontrol" not in item["description"].lower()
                            and "moneycontrol" not in item.get("feed_source", "").lower()):
                        continue
                key = re.sub(r"\W+", " ", item["title"].lower()).strip()
                candidates[key] = item
        except Exception as exc:
            errors[query] = str(exc)[:250]
        time.sleep(0.7)

    output_items = []
    seen = set()
    for item in candidates.values():
        title = item["title"]
        link = item["link"]
        article_text = item["description"]
        final_url = link
        article_error = ""
        try:
            page_bytes, final_url, charset = fetch_url(link, timeout=25, attempts=2)
            raw = page_bytes.decode(charset, errors="replace")
            page_text = clean_text(raw)
            description = extract_meta_description(raw)
            article_text = " ".join(part for part in [title, description, article_text, page_text] if part)
        except Exception as exc:
            article_error = str(exc)[:180]
            article_text = " ".join([title, item["description"]])

        host = urllib.parse.urlparse(final_url).netloc.lower()
        if SOURCE_DOMAIN not in host and "moneycontrol" not in title.lower():
            continue
        if not has_trade_label(article_text):
            continue

        stocks = find_stocks(article_text)
        if not stocks:
            continue

        published = parse_date(item["pub_date"])
        for stock_name, symbol in stocks:
            # Same article + same stock is one recommendation record.
            unique_key = (symbol, re.sub(r"\W+", " ", title.lower()).strip())
            if unique_key in seen:
                continue
            seen.add(unique_key)
            levels = nearby_values(article_text, stock_name, symbol)
            record = {
                "source": SOURCE_NAME,
                "stock": stock_name,
                "symbol": symbol,
                "title": title,
                "link": final_url,
                "date": published,
                "trade_type": "Trade Spotlight" if re.search(r"trade\s+spotlight", article_text, re.I)
                              else "Swing" if re.search(r"swing\s+trad", article_text, re.I)
                              else "Positional" if re.search(r"positional\s+(?:trade|call|pick)", article_text, re.I)
                              else "Short-term",
                "entry": levels["entry"],
                "target": levels["target"],
                "stop_loss": levels["stop_loss"],
            }
            if article_error:
                record["extraction_note"] = "Article page could not be fully read; verify missing trade details."
            output_items.append(record)
        time.sleep(0.5)

    output_items.sort(key=lambda x: (x.get("date", ""), x["stock"]), reverse=True)
    result = {
        "updated": now,
        "sources": [SOURCE_NAME],
        "source_counts": {SOURCE_NAME: len(output_items)},
        "errors": errors,
        "method_note": (
            "Moneycontrol-only pilot. Includes only articles whose headline or article text "
            "explicitly identifies Trade Spotlight, swing, positional, or short-term trading. "
            "Generic stocks-to-buy/watchlist articles are excluded. Missing entry, target, and "
            "stop-loss values are left blank; article-level duplicate stock records are removed. "
            "RSS/article coverage depends on publisher and Google News availability."
        ),
        "items": output_items,
    }
    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Moneycontrol items:", len(output_items))
    print("Errors:", json.dumps(errors, ensure_ascii=False))
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    collect()
