
#!/usr/bin/env python3
"""Moneycontrol-only trade recommendation collector."""

import datetime as dt
import email.utils
import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

OUTPUT = Path("media_picks.json")
SOURCE = "Moneycontrol"
DOMAIN = "moneycontrol.com"
MAX_ARTICLE_AGE_DAYS = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}

SEARCHES = [
    'site:moneycontrol.com "Trade Spotlight"',
    'site:moneycontrol.com "swing trade" OR "swing trading"',
    'site:moneycontrol.com "positional trade" OR "positional call"',
    'site:moneycontrol.com "short-term trade" OR "short term trading"',
]

# Stock name, NSE symbol, searchable aliases
STOCKS = [
    ("Aditya Birla Real Estate", "ABREL", ["Aditya Birla Real Estate", "AB Real Estate"]),
    ("General Insurance Corporation", "GICRE", ["General Insurance Corporation", "General Insurance Corp", "GIC Re"]),
    ("Godrej Consumer Products", "GODREJCP", ["Godrej Consumer Products", "Godrej Consumer"]),
    ("Phoenix Mills", "PHOENIXLTD", ["Phoenix Mills"]),
    ("Marksans Pharma", "MARKSANS", ["Marksans Pharma", "Marksans"]),
    ("Radico Khaitan", "RADICO", ["Radico Khaitan"]),
    ("Paytm", "PAYTM", ["One 97 Communications", "Paytm"]),
    ("JK Tyre", "JKTYRE", ["JK Tyre", "J.K. Tyre"]),
    ("HDFC Bank", "HDFCBANK", ["HDFC Bank"]),
    ("ICICI Bank", "ICICIBANK", ["ICICI Bank"]),
    ("State Bank of India", "SBIN", ["State Bank of India", "SBI"]),
    ("Axis Bank", "AXISBANK", ["Axis Bank"]),
    ("Kotak Mahindra Bank", "KOTAKBANK", ["Kotak Mahindra Bank", "Kotak Bank"]),
    ("Bajaj Finance", "BAJFINANCE", ["Bajaj Finance"]),
    ("Bajaj Finserv", "BAJAJFINSV", ["Bajaj Finserv"]),
    ("Reliance Industries", "RELIANCE", ["Reliance Industries", "Reliance"]),
    ("Larsen & Toubro", "LT", ["Larsen & Toubro", "Larsen and Toubro", "L&T"]),
    ("Infosys", "INFY", ["Infosys"]),
    ("Tata Consultancy Services", "TCS", ["Tata Consultancy Services", "TCS"]),
    ("Wipro", "WIPRO", ["Wipro"]),
    ("HCL Technologies", "HCLTECH", ["HCL Technologies", "HCL Tech"]),
    ("Tech Mahindra", "TECHM", ["Tech Mahindra"]),
    ("Tata Motors", "TMPV", ["Tata Motors"]),
    ("Mahindra & Mahindra", "M&M", ["Mahindra & Mahindra", "Mahindra and Mahindra"]),
    ("Maruti Suzuki", "MARUTI", ["Maruti Suzuki", "Maruti"]),
    ("Eicher Motors", "EICHERMOT", ["Eicher Motors"]),
    ("TVS Motor", "TVSMOTOR", ["TVS Motor", "TVS Motors"]),
    ("Hero MotoCorp", "HEROMOTOCO", ["Hero MotoCorp", "Hero Motocorp"]),
    ("Asian Paints", "ASIANPAINT", ["Asian Paints"]),
    ("Hindustan Unilever", "HINDUNILVR", ["Hindustan Unilever", "HUL"]),
    ("ITC", "ITC", ["ITC"]),
    ("Titan Company", "TITAN", ["Titan Company"]),
    ("Trent", "TRENT", ["Trent"]),
    ("Sun Pharma", "SUNPHARMA", ["Sun Pharmaceutical", "Sun Pharma"]),
    ("Cipla", "CIPLA", ["Cipla"]),
    ("Dr Reddy's Laboratories", "DRREDDY", ["Dr Reddy's Laboratories", "Dr. Reddy's"]),
    ("Bharti Airtel", "BHARTIARTL", ["Bharti Airtel"]),
    ("Tata Steel", "TATASTEEL", ["Tata Steel"]),
    ("JSW Steel", "JSWSTEEL", ["JSW Steel"]),
    ("Hindalco", "HINDALCO", ["Hindalco Industries", "Hindalco"]),
    ("Vedanta", "VEDL", ["Vedanta"]),
    ("Coal India", "COALINDIA", ["Coal India"]),
    ("ONGC", "ONGC", ["Oil and Natural Gas Corporation", "ONGC"]),
    ("NTPC", "NTPC", ["NTPC"]),
    ("Power Grid", "POWERGRID", ["Power Grid Corporation", "Power Grid"]),
    ("Tata Power", "TATAPOWER", ["Tata Power"]),
    ("Adani Ports", "ADANIPORTS", ["Adani Ports", "Adani Ports and SEZ"]),
    ("Adani Enterprises", "ADANIENT", ["Adani Enterprises"]),
    ("Bharat Electronics", "BEL", ["Bharat Electronics"]),
    ("Hindustan Aeronautics", "HAL", ["Hindustan Aeronautics"]),
    ("Bharat Dynamics", "BDL", ["Bharat Dynamics"]),
    ("BSE", "BSE", ["BSE Limited", "BSE Ltd"]),
    ("CDSL", "CDSL", ["CDSL"]),
    ("IRCTC", "IRCTC", ["IRCTC"]),
    ("DLF", "DLF", ["DLF"]),
    ("Eternal", "ETERNAL", ["Eternal", "Zomato"]),
    ("IndusInd Bank", "INDUSINDBK", ["IndusInd Bank"]),
    ("Federal Bank", "FEDERALBNK", ["Federal Bank"]),
    ("Bank of Baroda", "BANKBARODA", ["Bank of Baroda"]),
    ("Canara Bank", "CANBK", ["Canara Bank"]),
    ("Punjab National Bank", "PNB", ["Punjab National Bank"]),
    ("Power Finance Corporation", "PFC", ["Power Finance Corporation", "PFC"]),
    ("REC", "RECLTD", ["REC Limited", "REC Ltd"]),
    ("Voltas", "VOLTAS", ["Voltas"]),
    ("Polycab India", "POLYCAB", ["Polycab India", "Polycab"]),
    ("Dixon Technologies", "DIXON", ["Dixon Technologies", "Dixon Tech"]),
    ("Fortis Healthcare", "FORTIS", ["Fortis Healthcare"]),
    ("Mankind Pharma", "MANKIND", ["Mankind Pharma"]),
    ("Havells India", "HAVELLS", ["Havells India", "Havells"]),
    ("MCX", "MCX", ["Multi Commodity Exchange", "MCX"]),
    ("Hindustan Zinc", "HINDZINC", ["Hindustan Zinc"]),
    ("Motherson", "MOTHERSON", ["Samvardhana Motherson", "Motherson"]),
    ("FACT", "FACT", ["Fertilizers and Chemicals Travancore"]),
    ("Supreme Petrochem", "SPL", ["Supreme Petrochem"]),
    ("Jubilant Pharmova", "JUBLPHARMA", ["Jubilant Pharmova"]),
    ("Groww", "GROWW", ["Billionbrains Garage Ventures", "Groww"]),
    ("KPR Mill", "KPRMILL", ["KPR Mill"]),
    ("GE Vernova T&D India", "GVT&D", ["GE Vernova T&D India", "GE Vernova T&D"]),
    ("Blue Star", "BLUESTARCO", ["Blue Star"]),
    ("Mrs Bectors Food Specialities", "BECTORFOOD", ["Mrs Bectors Food Specialities", "Mrs Bectors"]),
    ("Kalyan Jewellers", "KALYANKJIL", ["Kalyan Jewellers India", "Kalyan Jewellers"]),
    ("Amara Raja Energy", "ARE&M", ["Amara Raja Energy", "Amara Raja"]),
]

TRADE_PATTERNS = [
    r"\btrade\s+spotlight\b",
    r"\bswing\s+trades?\b",
    r"\bswing\s+trading\b",
    r"\bpositional\s+(?:trades?|calls?|picks?)\b",
    r"\bshort[- ]term\s+(?:trading\s+)?(?:ideas?|trades?|calls?|picks?)\b",
]


def fetch(url, attempts=3):
    error = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=25) as response:
                return (
                    response.read(),
                    response.geturl(),
                    response.headers.get_content_charset() or "utf-8",
                )
        except Exception as exc:
            error = exc
            time.sleep(2 * (attempt + 1))
    raise error


class PageParser(HTMLParser):
    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "td", "th", "br"}
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
            return
        if not self.skip and tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if not self.skip and tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value + " ")


def page_text(raw):
    parser = PageParser()
    try:
        parser.feed(raw)
        value = "".join(parser.parts)
    except Exception:
        value = re.sub(r"<[^>]+>", " ", raw)

    value = html.unescape(value)
    lines = [re.sub(r"\s+", " ", x).strip() for x in value.splitlines()]
    return "\n".join(x for x in lines if x)


def meta_description(raw):
    patterns = [
        r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:description|og:description)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, re.I)
        if match:
            return html.unescape(match.group(1))
    return ""


def rss_items(data):
    root = ET.fromstring(data)
    result = []

    for item in root.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        desc = item.findtext("description", "").strip()
        date = item.findtext("pubDate", "").strip()

        source_node = item.find("source")
        source_text = (
            source_node.text.strip()
            if source_node is not None and source_node.text
            else ""
        )

        if title and link:
            result.append({
                "title": html.unescape(title),
                "link": link,
                "description": page_text(desc),
                "pub_date": date,
                "feed_source": source_text,
            })

    return result


def parse_date(value):
    if not value:
        return ""

    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc).isoformat()
    except Exception:
        return ""


def is_within_last_10_days(value, now):
    """Accept only valid publication dates in the rolling 10-day window."""
    published = parse_date(value)

    if not published:
        return ""

    published_dt = dt.datetime.fromisoformat(published)

    if published_dt > now:
        return ""

    cutoff = now - dt.timedelta(days=MAX_ARTICLE_AGE_DAYS)

    if published_dt < cutoff:
        return ""

    return published


def has_trade_label(text):
    return any(re.search(pattern, text, re.I) for pattern in TRADE_PATTERNS)


def identify_stocks(text):
    found = {}

    for name, symbol, aliases in STOCKS:
        for alias in sorted(aliases, key=len, reverse=True):
            pattern = (
                r"(?<![A-Za-z0-9])"
                + re.escape(alias)
                + r"(?![A-Za-z0-9])"
            )
            if re.search(pattern, text, re.I):
                found[symbol] = (name, symbol)
                break

    return list(found.values())


def stock_section(text, stock_name, symbol):
    """Return the section for a stock when a labelled CMP heading exists."""
    headings = []
    own = []

    for name, other_symbol, aliases in STOCKS:
        for alias in aliases:
            pattern = (
                r"(?<![A-Za-z0-9])"
                + re.escape(alias)
                + r"(?:\s+Futures)?\s*\|\s*CMP\s*:"
            )

            for match in re.finditer(pattern, text, re.I):
                headings.append(match.start())
                if other_symbol == symbol:
                    own.append(match.start())

    if own:
        start = min(own)
        later = [pos for pos in set(headings) if pos > start]
        end = min(later) if later else min(len(text), start + 8000)
        return text[start:end]

    aliases = next(
        (aliases for name, sym, aliases in STOCKS if sym == symbol),
        [stock_name],
    )

    positions = []
    for alias in aliases:
        positions.extend(
            match.start()
            for match in re.finditer(re.escape(alias), text, re.I)
        )

    if not positions:
        return ""

    start = min(positions)
    return text[start:min(len(text), start + 3000)]


def extract_levels(section):
    """Extract explicitly labelled values only. Never calculate or guess."""
    section = section.replace("₹", "Rs ")

    def clean(value):
        return value.replace(",", "").strip() if value else ""

    entry = ""
    entry_patterns = [
        r"\bentry(?:\s+price|\s+range)?\s*[:\-]?\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)\s*(?:to|[-–])\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
        r"\bentry(?:\s+price)?\s*[:\-]?\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
        r"\bbuy\s+(?:above|at)\s+(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
        r"\b(?:long\s+)?positions?\s+in\s+(?:the\s+)?(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)\s*(?:to|[-–])\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
    ]

    for pattern in entry_patterns:
        match = re.search(pattern, section, re.I)
        if match:
            entry = clean(match.group(1))
            if match.lastindex and match.lastindex >= 2 and match.group(2):
                entry += "-" + clean(match.group(2))
            break

    target = ""
    target_patterns = [
        r"\btargets?\s*[:\-]?\s*(?:of\s*)?(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?(?:\s*(?:,|/|and|to|[-–])\s*(?:Rs\.?\s*)?[0-9,]+(?:\.\d+)?)*)",
        r"\btarget\s+price\s*(?:of|at|:)?\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
    ]

    for pattern in target_patterns:
        match = re.search(pattern, section, re.I)
        if match:
            target = re.sub(r"\s+", " ", match.group(1)).strip()
            break

    stop = ""
    stop_patterns = [
        r"\bstop[- ]loss(?:\s+level)?\s*(?:at|of|:|-)?\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
        r"\bstoploss\s*(?:at|of|:|-)?\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
        r"\bSL\s*[:\-]?\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
    ]

    for pattern in stop_patterns:
        match = re.search(pattern, section, re.I)
        if match:
            stop = clean(match.group(1))
            break

    holding = ""
    holding_patterns = [
        r"\bholding\s+period\s*(?:of|:)?\s*(\d+\s*(?:days?|weeks?|months?))",
        r"\bfor\s+the\s+next\s+(\d+\s*(?:days?|weeks?|months?))",
        r"\b(?:time|investment)\s+horizon\s*(?:of|:)?\s*(\d+\s*(?:days?|weeks?|months?))",
    ]

    for pattern in holding_patterns:
        match = re.search(pattern, section, re.I)
        if match:
            holding = match.group(1)
            break

    return {
        "entry": entry,
        "target": target,
        "stop_loss": stop,
        "holding_period": holding,
    }


def google_rss(query):
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "en-IN",
        "gl": "IN",
        "ceid": "IN:en",
    })
    return "https://news.google.com/rss/search?" + params


def collect():
    now = dt.datetime.now(dt.timezone.utc)
    updated = now.isoformat()

    errors = {}
    articles = {}
    excluded_old_or_undated = 0

    # Discover articles through Google News RSS.
    for query in SEARCHES:
        try:
            data, _, charset = fetch(google_rss(query))

            for item in rss_items(data):
                # Strict publication-date filter: last 10 days only.
                published_iso = is_within_last_10_days(
                    item.get("pub_date", ""),
                    now,
                )

                if not published_iso:
                    excluded_old_or_undated += 1
                    continue

                item["published_at"] = published_iso

                combined = (
                    item["title"]
                    + " "
                    + item["description"]
                    + " "
                    + item["feed_source"]
                ).lower()

                if "moneycontrol" not in combined:
                    continue

                key = re.sub(
                    r"\W+",
                    " ",
                    item["title"].lower(),
                ).strip()

                articles[key] = item

        except Exception as exc:
            errors[query] = str(exc)[:250]

        time.sleep(1)

    output = []
    seen = set()

    for item in articles.values():
        title = item["title"]
        article_url = item["link"]

        text = title + "\n" + item["description"]
        final_url = article_url
        article_error = ""

        # Fetch the full publisher article where accessible.
        try:
            raw_bytes, final_url, charset = fetch(
                article_url,
                attempts=2,
            )
            raw = raw_bytes.decode(charset, errors="replace")

            text = "\n".join([
                title,
                meta_description(raw),
                item["description"],
                page_text(raw),
            ])

        except Exception as exc:
            article_error = str(exc)[:200]

        final_host = urllib.parse.urlparse(final_url).netloc.lower()

        # Do not include another publisher's page.
        if DOMAIN not in final_host and "moneycontrol" not in title.lower():
            continue

        if not has_trade_label(text):
            continue

        stocks = identify_stocks(text)

        if not stocks:
            continue

        for stock_name, symbol in stocks:
            unique_key = (symbol, title.lower())

            if unique_key in seen:
                continue

            seen.add(unique_key)

            section = stock_section(text, stock_name, symbol)
            levels = extract_levels(section)

            if re.search(r"trade\s+spotlight", title, re.I):
                trade_type = "Trade Spotlight - verify holding period"
            elif re.search(r"swing\s+trad", text, re.I):
                trade_type = "Swing"
            elif re.search(
                r"positional\s+(?:trade|call|pick)",
                text,
                re.I,
            ):
                trade_type = "Positional"
            else:
                trade_type = "Short-term"

            record = {
                "source": SOURCE,
                "stock": stock_name,
                "symbol": symbol,
                "title": title,
                "link": final_url,
                "date": item["published_at"],
                "trade_type": trade_type,
                "entry": levels["entry"],
                "target": levels["target"],
                "stop_loss": levels["stop_loss"],
                "holding_period": levels["holding_period"],
            }

            if article_error:
                record["extraction_note"] = (
                    "Article page could not be fetched. "
                    "Only RSS information was available; "
                    "verify missing levels."
                )
            elif not any([
                levels["entry"],
                levels["target"],
                levels["stop_loss"],
                levels["holding_period"],
            ]):
                record["extraction_note"] = (
                    "No labelled trade levels were detected "
                    "in the extracted stock section."
                )

            output.append(record)

        time.sleep(0.7)

    output.sort(
        key=lambda x: (
            x.get("date", ""),
            x.get("stock", ""),
        ),
        reverse=True,
    )

    result = {
        "updated": updated,
        "sources": [SOURCE],
        "source_counts": {
            SOURCE: len(output),
        },
        "errors": errors,
        "method_note": (
            "Moneycontrol-only pilot. Only articles with valid "
            "publication dates within the rolling last 10 days "
            "are included. Older, undated and future-dated articles "
            "are excluded. Google News RSS is used for discovery. "
            "The collector attempts to open publisher articles and "
            "extract stock-specific entry, target, stop loss and "
            "holding period. Missing values remain blank and are "
            "never estimated. Trade Spotlight is labelled for "
            "verification and is not automatically confirmed as "
            "a swing trade. Publisher access and article formatting "
            "may limit extraction."
        ),
        "items": output,
    }

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Moneycontrol articles discovered:", len(articles))
    print("Moneycontrol stock records:", len(output))
    print(
        "Old, undated or future-dated articles excluded:",
        excluded_old_or_undated,
    )
    print("Errors:", json.dumps(errors, ensure_ascii=False))
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    collect()
