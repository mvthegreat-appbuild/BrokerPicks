
#!/usr/bin/env python3
"""Moneycontrol swing and positional recommendation collector."""

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
MAX_AGE_DAYS = 10

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

# Display name, NSE symbol, aliases
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
    ("Adani Ports", "ADANIPORTS", ["Adani Ports and SEZ", "Adani Ports"]),
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
    ("Power Finance Corporation", "PFC", ["Power Finance Corporation"]),
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
    ("Jubilant Pharmova", "JUBLPHARMA", ["Jubilant Pharmova"]),
    ("Groww", "GROWW", ["Billionbrains Garage Ventures", "Groww"]),
    ("KPR Mill", "KPRMILL", ["KPR Mill"]),
    ("GE Vernova T&D India", "GVT&D", ["GE Vernova T&D India", "GE Vernova T&D"]),
    ("Blue Star", "BLUESTARCO", ["Blue Star"]),
    ("Kalyan Jewellers", "KALYANKJIL", ["Kalyan Jewellers India", "Kalyan Jewellers"]),
    ("Amara Raja Energy", "ARE&M", ["Amara Raja Energy", "Amara Raja"]),
]

TRADE_WORDS = re.compile(
    r"trade\s+spotlight|swing\s+trad|positional\s+(trade|call|pick)|"
    r"short[- ]term\s+(trade|trading|call|pick|idea)",
    re.I,
)


def fetch(url, attempts=2):
    error = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as response:
                return (
                    response.read(),
                    response.geturl(),
                    response.headers.get_content_charset() or "utf-8",
                )
        except Exception as exc:
            error = exc
            time.sleep(2 * (attempt + 1))
    raise error


class TextParser(HTMLParser):
    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "td", "th", "br"}
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif not self.skip and tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value + " ")


def extract_text(raw):
    parser = TextParser()
    parser.feed(raw)
    lines = []
    for part in "".join(parser.parts).splitlines():
        part = re.sub(r"\s+", " ", html.unescape(part)).strip()
        if part:
            lines.append(part)
    return "\n".join(lines)


def resolve_moneycontrol_url(url):
    """Follow Google News and look for the original Moneycontrol URL."""
    raw, final_url, charset = fetch(url)
    page = raw.decode(charset, errors="replace")

    candidates = []

    patterns = [
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)',
        r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)',
        r'https?://(?:www\.)?moneycontrol\.com/[^"\'\s<>]+',
    ]

    for pattern in patterns:
        for match in re.findall(pattern, page, re.I):
            candidates.append(html.unescape(match))

    for candidate in candidates:
        candidate = candidate.replace("\\u0026", "&").replace("\\/", "/")
        parsed = urllib.parse.urlparse(candidate)
        host = parsed.netloc.lower()

        if "moneycontrol.com" in host and parsed.path:
            return candidate

    parsed = urllib.parse.urlparse(final_url)
    if "moneycontrol.com" in parsed.netloc.lower():
        return final_url

    return ""


def google_rss(query):
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "en-IN",
        "gl": "IN",
        "ceid": "IN:en",
    })
    return "https://news.google.com/rss/search?" + params


def parse_rss(data):
    root = ET.fromstring(data)
    items = []

    for item in root.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        desc = item.findtext("description", "").strip()

        if title and link:
            items.append({
                "title": html.unescape(title),
                "link": link,
                "description": extract_text(desc),
                "pub_date": pub_date,
            })

    return items


def publication_date(value, now):
    if not value:
        return ""

    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        parsed = parsed.astimezone(dt.timezone.utc)

        if parsed > now:
            return ""

        if parsed < now - dt.timedelta(days=MAX_AGE_DAYS):
            return ""

        return parsed.isoformat()
    except Exception:
        return ""


def alias_pattern(alias):
    return (
        r"(?<![A-Za-z0-9])"
        + re.escape(alias)
        + r"(?![A-Za-z0-9])"
    )


def find_stock_sections(text):
    """Find stock headings such as 'Stock Name | CMP: Rs ...'."""
    headings = []

    for name, symbol, aliases in STOCKS:
        for alias in aliases:
            pattern = (
                alias_pattern(alias)
                + r"(?:\s+Futures)?\s*\|\s*CMP\s*:"
            )
            for match in re.finditer(pattern, text, re.I):
                headings.append((match.start(), name, symbol))

    headings.sort(key=lambda x: x[0])

    # Remove duplicate aliases pointing to the same heading.
    unique = []
    used_positions = set()

    for position, name, symbol in headings:
        if position not in used_positions:
            unique.append((position, name, symbol))
            used_positions.add(position)

    sections = []

    for index, (start, name, symbol) in enumerate(unique):
        end = (
            unique[index + 1][0]
            if index + 1 < len(unique)
            else min(len(text), start + 9000)
        )
        sections.append((name, symbol, text[start:end]))

    return sections


def fallback_stock_sections(text, title):
    """Use headline-mentioned stocks only if CMP headings are unavailable."""
    sections = []

    for name, symbol, aliases in STOCKS:
        if not any(
            re.search(alias_pattern(alias), title, re.I)
            for alias in aliases
        ):
            continue

        positions = []

        for alias in aliases:
            positions.extend(
                m.start()
                for m in re.finditer(alias_pattern(alias), text, re.I)
            )

        if positions:
            start = min(positions)
            sections.append((name, symbol, text[start:start + 3500]))

    return sections


def extract_levels(section):
    """Only extract labelled values. Never calculate or estimate."""
    section = section.replace("₹", " Rs ")
    section = re.sub(r"\s+", " ", section)

    def number(value):
        return value.replace(",", "").strip()

    entry = ""
    entry_patterns = [
        r"(?:entry(?:\s+price|\s+range)?|buy\s+in\s+the\s+range\s+of)"
        r"\s*[:\-]?\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)"
        r"\s*(?:to|[-–])\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
        r"\bbuy\s+between\s+(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)"
        r"\s+and\s+(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
        r"\bentry(?:\s+price)?\s*[:\-]\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
        r"\bbuy\s+(?:above|at)\s+(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
    ]

    for pattern in entry_patterns:
        match = re.search(pattern, section, re.I)
        if match:
            entry = number(match.group(1))
            if match.lastindex and match.lastindex >= 2 and match.group(2):
                entry += "-" + number(match.group(2))
            break

    target = ""
    target_patterns = [
        r"\btargets?\s*[:\-]?\s*(?:of|at)?\s*"
        r"(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)"
        r"((?:\s*(?:,|/|and|to|[-–])\s*(?:Rs\.?\s*)?"
        r"[0-9,]+(?:\.\d+)?)*)",
        r"\btarget\s+price\s*(?:of|at|:)?\s*"
        r"(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
    ]

    for pattern in target_patterns:
        match = re.search(pattern, section, re.I)
        if match:
            target = number(match.group(1))
            if match.lastindex and match.lastindex >= 2:
                target += re.sub(r"\s+", "", match.group(2))
            break

    stop = ""
    stop_patterns = [
        r"\bstop[- ]loss(?:\s+level)?\s*(?:at|of|:|-)?\s*"
        r"(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
        r"\bstoploss\s*(?:at|of|:|-)?\s*(?:Rs\.?\s*)?"
        r"([0-9,]+(?:\.\d+)?)",
        r"\bSL\s*[:\-]\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?)",
    ]

    for pattern in stop_patterns:
        match = re.search(pattern, section, re.I)
        if match:
            stop = number(match.group(1))
            break

    holding = ""
    holding_patterns = [
        r"\bholding\s+period\s*(?:of|:)?\s*"
        r"(\d+\s*(?:days?|weeks?|months?))",
        r"\bfor\s+the\s+next\s+(\d+\s*(?:days?|weeks?|months?))",
        r"\b(?:time|investment)\s+horizon\s*(?:of|:)?\s*"
        r"(\d+\s*(?:days?|weeks?|months?))",
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


def classify_trade(title, article_text):
    if re.search(r"trade\s+spotlight", title, re.I):
        return "Trade Spotlight - verify holding period"
    if re.search(r"swing\s+trad", article_text, re.I):
        return "Swing"
    if re.search(r"positional\s+(trade|call|pick)", article_text, re.I):
        return "Positional"
    return "Short-term - verify holding period"


def collect():
    now = dt.datetime.now(dt.timezone.utc)
    errors = {}
    articles = {}
    excluded = 0

    # 1. Discover Moneycontrol articles from Google News RSS.
    for query in SEARCHES:
        try:
            data, _, charset = fetch(google_rss(query))
            for item in parse_rss(data):
                date = publication_date(item["pub_date"], now)

                if not date:
                    excluded += 1
                    continue

                item["date"] = date
                key = re.sub(r"\W+", " ", item["title"].lower()).strip()
                articles[key] = item

        except Exception as exc:
            errors[query] = str(exc)[:250]

        time.sleep(1)

    output = []
    seen = set()
    direct_links = 0
    article_failures = 0

    # 2. Resolve the original publisher URL and fetch the full article.
    for item in articles.values():
        title = item["title"]
        google_link = item["link"]

        try:
            direct_url = resolve_moneycontrol_url(google_link)

            if not direct_url:
                article_failures += 1
                continue

            direct_links += 1
            raw, final_url, charset = fetch(direct_url)
            page = raw.decode(charset, errors="replace")

            host = urllib.parse.urlparse(final_url).netloc.lower()
            if "moneycontrol.com" not in host:
                continue

            article_text = title + "\n" + extract_text(page)

            if not TRADE_WORDS.search(title + " " + article_text):
                continue

            # 3. Prefer stock-specific CMP sections.
            sections = find_stock_sections(article_text)

            if not sections:
                sections = fallback_stock_sections(
                    article_text,
                    title,
                )

            trade_type = classify_trade(title, article_text)

            for stock_name, symbol, section in sections:
                key = (symbol, final_url)

                if key in seen:
                    continue

                seen.add(key)
                levels = extract_levels(section)

                record = {
                    "source": SOURCE,
                    "stock": stock_name,
                    "symbol": symbol,
                    "title": title,
                    "link": final_url,
                    "date": item["date"],
                    "trade_type": trade_type,
                    "entry": levels["entry"],
                    "target": levels["target"],
                    "stop_loss": levels["stop_loss"],
                    "holding_period": levels["holding_period"],
                }

                if not any([
                    levels["entry"],
                    levels["target"],
                    levels["stop_loss"],
                    levels["holding_period"],
                ]):
                    record["extraction_note"] = (
                        "Article fetched, but no labelled levels "
                        "were detected in this stock section. "
                        "Please verify the original article."
                    )

                output.append(record)

        except Exception as exc:
            article_failures += 1
            errors[title[:100]] = str(exc)[:200]

        time.sleep(0.7)

    output.sort(
        key=lambda x: (x["date"], x["stock"]),
        reverse=True,
    )

    result = {
        "updated": now.isoformat(),
        "sources": [SOURCE],
        "source_counts": {SOURCE: len(output)},
        "diagnostics": {
            "rss_articles_in_window": len(articles),
            "direct_moneycontrol_links_resolved": direct_links,
            "article_fetch_failures": article_failures,
            "old_undated_or_future_articles_excluded": excluded,
        },
        "errors": errors,
        "method_note": (
            "Moneycontrol-only pilot. Rolling 10-day publication-date "
            "filter. Google News RSS is used for discovery; the collector "
            "attempts to resolve direct Moneycontrol URLs and fetch full "
            "publisher articles. Stock-specific CMP sections are preferred "
            "for extracting entry, target, stop-loss and holding period. "
            "Missing values remain blank and are never estimated. "
            "Trade Spotlight is not automatically confirmed as a swing "
            "trade. Verify all recommendations against the original article."
        ),
        "items": output,
    }

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Moneycontrol RSS articles:", len(articles))
    print("Direct article links resolved:", direct_links)
    print("Article fetch failures:", article_failures)
    print("Stock records:", len(output))
    print("Old/undated/future articles excluded:", excluded)
    print("Errors:", json.dumps(errors, ensure_ascii=False))
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    collect()
