
import csv
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path


# ============================================================
# MONEYCONTROL ONLY — ROLLING 10-DAY SWING PICK COLLECTOR
# ============================================================

SOURCE = "Moneycontrol"
OUTPUT_FILE = Path("media_picks.json")
MAX_ARTICLE_AGE_DAYS = 10
MAX_ARTICLES_PER_QUERY = 40
REQUEST_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
    )
}

SEARCH_QUERIES = [
    'site:moneycontrol.com "Trade Spotlight"',
    'site:moneycontrol.com "swing trade"',
    'site:moneycontrol.com "swing trading"',
    'site:moneycontrol.com "positional trade"',
    'site:moneycontrol.com "positional call"',
    'site:moneycontrol.com "short-term trade"',
]

# Names and symbols are used only to identify possible stock mentions.
# A mention alone is NOT treated as a confirmed recommendation.
STOCKS = {
    "Phoenix Mills": ["phoenix mills", "phoenix mills ltd"],
    "Marksans Pharma": ["marksans pharma", "marksans"],
    "Radico Khaitan": ["radico khaitan"],
    "Paytm": ["paytm", "one 97 communications"],
    "JK Tyre": ["jk tyre", "j k tyre"],
    "MCX": ["multi commodity exchange", "mcx"],
    "Federal Bank": ["federal bank"],
    "Mankind Pharma": ["mankind pharma"],
    "Canara Bank": ["canara bank"],
    "Bharat Dynamics": ["bharat dynamics", "bdl"],
    "Amara Raja Energy": ["amara raja energy", "amara raja"],
    "State Bank of India": ["state bank of india", "sbi"],
    "ITC": ["itc limited", "itc"],
    "Groww": ["groww", "billionbrains garage ventures"],
    "Godrej Consumer Products": ["godrej consumer products", "godrej consumer"],
    "General Insurance Corporation": [
        "general insurance corporation",
        "gic re",
        "gic of india",
    ],
    "Aditya Birla Real Estate": [
        "aditya birla real estate",
        "birla estates",
    ],
    "HDFC Bank": ["hdfc bank"],
    "ICICI Bank": ["icici bank"],
    "Reliance Industries": ["reliance industries"],
    "Tata Motors": ["tata motors"],
    "Infosys": ["infosys"],
    "TCS": ["tata consultancy services", "tcs"],
    "Larsen & Toubro": ["larsen and toubro", "l&t"],
    "Hindustan Unilever": ["hindustan unilever", "hul"],
    "Bharti Airtel": ["bharti airtel", "airtel"],
    "Tata Steel": ["tata steel"],
    "Coal India": ["coal india"],
    "Bajaj Finance": ["bajaj finance"],
    "Asian Paints": ["asian paints"],
    "Eicher Motors": ["eicher motors"],
    "Trent": ["trent limited"],
    "Zomato": ["zomato", "eternal limited"],
    "Adani Green Energy": ["adani green energy"],
    "Va Tech Wabag": ["va tech wabag", "wabag"],
}

BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "td", "th",
    "h1", "h2", "h3", "h4", "section", "article"
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self.skip += 1
        elif not self.skip and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header"):
            self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def text(self):
        return re.sub(r"\n{2,}", "\n", " ".join(self.parts)).strip()


def install_decoder():
    try:
        from googlenewsdecoder import gnewsdecoder
        return gnewsdecoder
    except ImportError:
        print("Installing Google News URL decoder...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--quiet", "googlenewsdecoder"
        ])
        from googlenewsdecoder import gnewsdecoder
        return gnewsdecoder


def fetch_url(url, timeout=REQUEST_TIMEOUT):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_date(value):
    if not value:
        return None
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def is_recent(dt, now):
    if dt is None:
        return False
    cutoff = now - timedelta(days=MAX_ARTICLE_AGE_DAYS)
    return cutoff <= dt <= now


def get_rss_items(query):
    encoded = urllib.parse.quote(query)
    url = (
        "https://news.google.com/rss/search?q="
        + encoded
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )

    xml_text = fetch_url(url)
    root = ET.fromstring(xml_text)
    results = []

    for item in root.findall(".//item")[:MAX_ARTICLES_PER_QUERY]:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()

        source_node = item.find("source")
        source_name = (
            source_node.text.strip()
            if source_node is not None and source_node.text
            else ""
        )

        source_url = (
            source_node.attrib.get("url", "")
            if source_node is not None
            else ""
        )

        if "moneycontrol" not in (
            source_name + " " + source_url + " " + title
        ).lower():
            continue

        results.append({
            "title": title,
            "google_link": link,
            "pub_date_raw": pub_date,
            "published": parse_date(pub_date),
        })

    return results


def resolve_article_url(google_link, decoder):
    if not google_link:
        return ""

    try:
        result = decoder(
            google_link,
            interval=0.5,
            timeout=15.0,
        )

        if result and result.get("success"):
            decoded = result.get("decoded_url", "")
            host = urllib.parse.urlparse(decoded).netloc.lower()

            if host.endswith("moneycontrol.com"):
                return decoded

    except Exception as exc:
        print("URL decode failed:", str(exc)[:160])

    return ""


def clean_text(value):
    value = re.sub(r"\s+", " ", value or "")
    return value.strip()


def get_article_text(article_url):
    html = fetch_url(article_url)
    parser = PageParser()
    parser.feed(html)
    return parser.text()


def find_stock_mentions(text):
    lower = text.lower()
    found = []

    for stock_name, aliases in STOCKS.items():
        for alias in aliases:
            pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
            if re.search(pattern, lower):
                found.append(stock_name)
                break

    return sorted(set(found))


def extract_stock_section(text, stock_name):
    """
    Prefer a labelled stock section.
    If none is found, return a limited context window around the mention.
    The fallback is not treated as proof of a recommendation.
    """
    lines = [clean_text(x) for x in text.splitlines()]
    lines = [x for x in lines if x]

    aliases = STOCKS.get(stock_name, [stock_name.lower()])
    start = None

    for i, line in enumerate(lines):
        low = line.lower()

        if any(alias in low for alias in aliases):
            if (
                "cmp" in low
                or "stock" in low
                or len(line) < 120
            ):
                start = i
                break

    if start is not None:
        end = min(start + 18, len(lines))
        section = "\n".join(lines[start:end])
        return section, True

    full = "\n".join(lines)
    low = full.lower()

    positions = []
    for alias in aliases:
        pos = low.find(alias)
        if pos >= 0:
            positions.append(pos)

    if positions:
        pos = min(positions)
        return full[max(0, pos - 350):pos + 1200], False

    return "", False


def extract_value(patterns, text):
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )
        if match:
            return clean_text(match.group(1))
    return ""


def extract_trade_levels(section):
    entry = extract_value([
        r"(?:entry|buying range|buy range|buy at|entry price)"
        r"\s*[:\-]?\s*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)",
        r"(?:buy above|buy near)\s*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)",
    ], section)

    target = extract_value([
        r"(?:target price|target)\s*[:\-]?\s*"
        r"(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)",
        r"(?:first target|upside target)\s*[:\-]?\s*"
        r"(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)",
    ], section)

    stop_loss = extract_value([
        r"(?:stop[\s-]?loss|stoploss|SL)\s*[:\-]?\s*"
        r"(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)",
        r"(?:keep a stop below|stop below)\s*"
        r"(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)",
    ], section)

    holding_period = extract_value([
        r"(?:holding period|time frame|timeframe|duration)"
        r"\s*[:\-]?\s*([^\n.;]{2,60})",
        r"(?:for the next|within the next)\s+"
        r"(\d+\s*(?:days?|weeks?|months?))",
    ], section)

    return {
        "entry": entry,
        "target": target,
        "stop_loss": stop_loss,
        "holding_period": holding_period,
    }


def classify_pick(title, section, labelled_section):
    combined = (title + " " + section).lower()

    swing_terms = [
        "swing trade", "swing trading",
        "positional trade", "positional call",
        "short-term trade", "short term trade",
        "trade spotlight",
    ]

    if not any(term in combined for term in swing_terms):
        return "Not confirmed as a swing/positional pick"

    if labelled_section:
        return "Trade section detected - verify holding period"

    return "Possible pick - article section not confirmed"


def main():
    now = datetime.now(timezone.utc)
    decoder = install_decoder()

    articles = {}
    errors = {}
    excluded_old = 0
    excluded_undated = 0
    excluded_future = 0

    print("Moneycontrol collector started.")
    print("Rolling publication-date window: last 10 days.")

    for query in SEARCH_QUERIES:
        try:
            for item in get_rss_items(query):
                published = item["published"]

                if published is None:
                    excluded_undated += 1
                    continue

                if published > now:
                    excluded_future += 1
                    continue

                if not is_recent(published, now):
                    excluded_old += 1
                    continue

                key = item["google_link"] or item["title"]
                if key not in articles:
                    articles[key] = item

        except Exception as exc:
            errors[query] = str(exc)[:250]
            print("RSS query error:", str(exc)[:150])

    print("Unique recent articles:", len(articles))

    output_items = []
    decoded_count = 0
    article_fetch_failures = 0
    unresolved_links = 0

    for item in articles.values():
        title = item["title"]
        published = item["published"]

        print("Processing:", title[:100])

        article_url = resolve_article_url(
            item["google_link"],
            decoder
        )

        if not article_url:
            unresolved_links += 1
            continue

        decoded_count += 1

        try:
            article_text = get_article_text(article_url)
        except Exception as exc:
            article_fetch_failures += 1
            errors[article_url] = "Article fetch failed: " + str(exc)[:180]
            continue

        stocks = find_stock_mentions(title + "\n" + article_text)

        for stock_name in stocks:
            section, labelled_section = extract_stock_section(
                article_text,
                stock_name
            )

            if not section:
                continue

            levels = extract_trade_levels(section)
            status = classify_pick(
                title,
                section,
                labelled_section
            )

            # Do not include generic stock mentions as recommendations.
            # Keep only articles with a relevant trade-pick context.
            if status == "Not confirmed as a swing/positional pick":
                continue

            output_items.append({
                "source": SOURCE,
                "stock": stock_name,
                "title": title,
                "published_at": published.isoformat(),
                "article_url": article_url,
                "link": article_url,
                "entry": levels["entry"],
                "target": levels["target"],
                "stop_loss": levels["stop_loss"],
                "holding_period": levels["holding_period"],
                "recommendation_status": status,
                "section_verified": labelled_section,
                "extraction_note": (
                    "Values extracted only when explicitly labelled. "
                    "Blank fields mean the article section did not provide "
                    "a clearly labelled value."
                ),
            })

        time.sleep(0.4)

    # Remove duplicate stock/article records.
    unique = {}
    for item in output_items:
        key = (
            item["stock"].lower(),
            item["article_url"].lower()
        )
        unique[key] = item

    final_items = list(unique.values())
    final_items.sort(
        key=lambda x: x["published_at"],
        reverse=True
    )

    result = {
        "updated": now.isoformat(),
        "sources": [SOURCE],
        "source_counts": {
            SOURCE: len(final_items)
        },
        "collection_window_days": MAX_ARTICLE_AGE_DAYS,
        "errors": errors,
        "method_note": (
            "Moneycontrol-only pilot. Articles are filtered using "
            "Google News RSS publication dates within the rolling last "
            "10 days. Undated, old and future-dated items are excluded. "
            "Google News links are decoded to original Moneycontrol URLs. "
            "Only trade-related articles are considered. Stock mentions "
            "are not automatically treated as confirmed recommendations. "
            "Entry, target, stop-loss and holding period are extracted "
            "only when explicitly labelled in the article text. "
            "Missing values remain blank. Publisher pages may block "
            "automated access or change their layout."
        ),
        "diagnostics": {
            "rss_unique_recent_articles": len(articles),
            "decoded_moneycontrol_urls": decoded_count,
            "unresolved_google_links": unresolved_links,
            "article_fetch_failures": article_fetch_failures,
            "excluded_old": excluded_old,
            "excluded_undated": excluded_undated,
            "excluded_future": excluded_future,
        },
        "items": final_items,
    }

    OUTPUT_FILE.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("-----------------------------------")
    print("Moneycontrol collection completed.")
    print("Decoded article URLs:", decoded_count)
    print("Stock records:", len(final_items))
    print("Unresolved Google links:", unresolved_links)
    print("Article fetch failures:", article_fetch_failures)
    print("Excluded old articles:", excluded_old)
    print("Excluded undated articles:", excluded_undated)
    print("Excluded future articles:", excluded_future)
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
