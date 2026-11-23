
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

# MONEYCONTROL ONLY — VERIFIED 10-DAY TRADE PICK COLLECTOR
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

STOCKS = {
    "Phoenix Mills": ["phoenix mills"],
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
    "Godrej Consumer Products": [
        "godrej consumer products", "godrej consumer"
    ],
    "General Insurance Corporation": [
        "general insurance corporation", "gic re", "gic of india"
    ],
    "Aditya Birla Real Estate": [
        "aditya birla real estate", "birla estates"
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
    "TVS Motor": ["tvs motor company", "tvs motor"],
    "Quess Corp": ["quess corp", "quess"],
    "Gabriel India": ["gabriel india"],
    "Avenue Supermarts": ["avenue supermarts", "dmart"],
    "Bharat Electronics": ["bharat electronics", "bel"],
    "Indian Railway Finance Corporation": [
        "indian railway finance corporation", "irfc"
    ],
    "Pidilite Industries": ["pidilite industries", "pidilite"],
    "Gujarat Fluorochemicals": ["gujarat fluorochemicals", "gfl"],
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
        # Preserve paragraph and heading boundaries for stock sections.
        return re.sub(r"\n+", "\n", "".join(self.parts)).strip()


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

    value = str(value).strip()

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    for fmt in (
        "%Y-%m-%d", "%d %B %Y", "%d %b %Y",
        "%B %d, %Y", "%b %d, %Y", "%d-%m-%Y",
        "%Y/%m/%d", "%d/%m/%Y"
    ):
        try:
            return datetime.strptime(
                value, fmt
            ).replace(tzinfo=timezone.utc)
        except Exception:
            continue

    return None


def extract_original_publication_date(html):
    patterns = [
        r'<meta[^>]+(?:property|name)=["\']article:published_time["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']article:published_time["\']',
        r'<meta[^>]+(?:name|property)=["\'](?:pubdate|publishdate|date|dc\.date|dc\.date\.issued)["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:pubdate|publishdate|date|dc\.date|dc\.date\.issued)["\']',
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'"dateCreated"\s*:\s*"([^"]+)"',
        r'<time[^>]+datetime=["\']([^"\']+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            dt = parse_date(match.group(1))
            if dt:
                return dt

    return None


def is_recent(dt, now):
    return (
        dt is not None
        and now - timedelta(days=MAX_ARTICLE_AGE_DAYS) <= dt <= now
    )


def get_rss_items(query):
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )

    root = ET.fromstring(fetch_url(url))
    results = []

    for item in root.findall(".//item")[:MAX_ARTICLES_PER_QUERY]:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        source_node = item.find("source")

        source_name = (
            source_node.text.strip()
            if source_node is not None and source_node.text else ""
        )
        source_url = (
            source_node.attrib.get("url", "")
            if source_node is not None else ""
        )

        if "moneycontrol" not in (
            source_name + " " + source_url + " " + title
        ).lower():
            continue

        results.append({
            "title": title,
            "google_link": link,
            "rss_published": parse_date(pub_date)
        })

    return results


def resolve_article_url(google_link, decoder):
    if not google_link:
        return ""

    try:
        result = decoder(google_link, interval=0.5, timeout=15.0)

        if result and result.get("success"):
            decoded = result.get("decoded_url", "")
            host = urllib.parse.urlparse(decoded).netloc.lower()

            if host.endswith("moneycontrol.com"):
                return decoded

    except Exception as exc:
        print("URL decode failed:", str(exc)[:160])

    return ""


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def alias_pattern(alias):
    return (
        r"(?<![a-z0-9])"
        + re.escape(alias)
        + r"(?![a-z0-9])"
    )


def find_stock_mentions(text):
    lower = text.lower()
    found = []

    for stock_name, aliases in STOCKS.items():
        for alias in aliases:
            if re.search(alias_pattern(alias), lower):
                found.append(stock_name)
                break

    return sorted(set(found))


def extract_stock_section(text, stock_name):
    lines = [clean_text(x) for x in text.splitlines()]
    lines = [x for x in lines if x]

    aliases = STOCKS.get(stock_name, [stock_name.lower()])
    field_words = re.compile(
        r"\b(cmp|entry|target|stop.?loss|buy|sell|sl)\b",
        re.IGNORECASE
    )

    matches = []

    for i, line in enumerate(lines):
        low = line.lower()

        if any(re.search(alias_pattern(a), low) for a in aliases):
            # Prefer a stock heading or a line containing trade fields.
            starts_with_stock = any(
                re.match(alias_pattern(a), low) for a in aliases
            )
            has_fields = bool(field_words.search(line))

            if starts_with_stock or has_fields:
                matches.append((i, True))
            else:
                matches.append((i, False))

    if not matches:
        return "", False

    # Prefer the nearest explicit stock heading / trade-field line.
    index, labelled = matches[0]

    # Keep the section local to the stock, not the whole article.
    end = min(index + 24, len(lines))

    for next_index, _ in matches[1:]:
        if next_index > index:
            end = min(end, next_index)
            break

    section = "\n".join(lines[index:end])

    # If the stock name appears in ordinary prose, inspect nearby lines.
    if not labelled:
        start = max(0, index - 3)
        end = min(len(lines), index + 12)
        section = "\n".join(lines[start:end])

    return section, labelled


def extract_value(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))

    return ""


def extract_trade_levels(section):
    return {
        "entry": extract_value([
            r"(?:entry(?: price)?|buying range|buy range|buy at|CMP|current market price|market price)\s*[:\-]?\s*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)",
            r"(?:buy above|buy near)\s*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)"
        ], section),

        "target": extract_value([
            r"(?:target price|target|upside target|price target)(?:\s+(?:of|at))?\s*[:\-]?\s*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)",
            r"(?:first target)\s*[:\-]?\s*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)"
        ], section),

        "stop_loss": extract_value([
            r"(?:stop[\s-]?loss|stoploss|SL)(?:\s+(?:at|of))?\s*[:\-]?\s*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)",
            r"(?:keep a stop below|stop below)\s*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)"
        ], section),

        "holding_period": extract_value([
            r"(?:holding period|time frame|timeframe|duration)\s*[:\-]?\s*([^\n.;]{2,60})",
            r"(?:for the next|within the next)\s+(\d+\s*(?:days?|weeks?|months?))"
        ], section)
    }


def has_actionable_recommendation(title, section):
    text = (title + " " + section).lower()

    terms = (
        "buy", "sell", "accumulate", "avoid", "entry",
        "buy above", "buy near", "trading strategy",
        "trade setup", "target", "stop loss", "stop-loss"
    )

    return any(term in text for term in terms)


def build_record(stock_name, title, article_url, published, section, labelled):
    levels = extract_trade_levels(section)

    confirmed = (
        labelled
        and has_actionable_recommendation(title, section)
        and bool(levels["entry"])
        and bool(levels["target"])
        and bool(levels["stop_loss"])
    )

    return {
        "source": SOURCE,
        "stock": stock_name,
        "title": title,
        "published_at": published.isoformat(),
        "article_url": article_url,
        "link": article_url,
        "entry": levels["entry"] if confirmed else "",
        "target": levels["target"] if confirmed else "",
        "stop_loss": levels["stop_loss"] if confirmed else "",
        "holding_period": levels["holding_period"] if confirmed else "",
        "recommendation_status": (
            "Confirmed recommendation - verify before trading"
            if confirmed else
            "Unverified article - not a confirmed recommendation"
        ),
        "section_verified": bool(labelled),
        "date_verified": True,
        "extraction_note": (
            "Original Moneycontrol publication date verified within "
            "10 days. Confirmed records require a labelled stock section "
            "and explicitly extracted entry/CMP, target and stop-loss. "
            "Missing values are never estimated."
        )
    }


def deduplicate(items):
    unique = {}

    for item in items:
        key = (
            item["stock"].lower(),
            item["article_url"].lower()
        )
        unique[key] = item

    result = list(unique.values())
    result.sort(key=lambda x: x["published_at"], reverse=True)

    return result


def main():
    now = datetime.now(timezone.utc)
    decoder = install_decoder()

    articles = {}
    errors = {}

    excluded_rss_old = 0
    excluded_rss_undated = 0
    excluded_rss_future = 0

    print("Moneycontrol strict collector started.")
    print("Original publisher date must be within the last 10 days.")

    for query in SEARCH_QUERIES:
        try:
            for item in get_rss_items(query):
                rss_date = item["rss_published"]

                if rss_date is None:
                    excluded_rss_undated += 1
                    continue

                if rss_date > now:
                    excluded_rss_future += 1
                    continue

                if not is_recent(rss_date, now):
                    excluded_rss_old += 1
                    continue

                key = item["google_link"] or item["title"]
                articles.setdefault(key, item)

        except Exception as exc:
            errors[query] = str(exc)[:250]
            print("RSS query error:", str(exc)[:150])

    confirmed_items = []
    watchlist_items = []

    decoded_count = 0
    unresolved_links = 0
    article_fetch_failures = 0

    excluded_original_old = 0
    excluded_original_undated = 0
    excluded_original_future = 0

    for item in articles.values():
        title = item["title"]
        article_url = resolve_article_url(
            item["google_link"], decoder
        )

        if not article_url:
            unresolved_links += 1
            continue

        decoded_count += 1

        try:
            html = fetch_url(article_url)
            original_date = extract_original_publication_date(html)

            if original_date is None:
                excluded_original_undated += 1
                continue

            if original_date > now:
                excluded_original_future += 1
                continue

            if not is_recent(original_date, now):
                excluded_original_old += 1
                continue

            parser = PageParser()
            parser.feed(html)
            article_text = parser.text()

        except Exception as exc:
            article_fetch_failures += 1
            errors[article_url] = (
                "Article fetch/date verification failed: "
                + str(exc)[:180]
            )
            continue

        stocks = find_stock_mentions(
            title + "\n" + article_text
        )

        for stock_name in stocks:
            section, labelled = extract_stock_section(
                article_text, stock_name
            )

            if not section:
                continue

            if not has_actionable_recommendation(title, section):
                continue

            record = build_record(
                stock_name,
                title,
                article_url,
                original_date,
                section,
                labelled
            )

            if record["recommendation_status"].startswith("Confirmed"):
                confirmed_items.append(record)
            else:
                watchlist_items.append(record)

        time.sleep(0.35)

    confirmed_items = deduplicate(confirmed_items)
    watchlist_items = deduplicate(watchlist_items)

    result = {
        "updated": now.isoformat(),
        "sources": [SOURCE],
        "source_counts": {
            SOURCE: len(confirmed_items)
        },
        "collection_window_days": MAX_ARTICLE_AGE_DAYS,
        "errors": errors,
        "method_note": (
            "Moneycontrol-only strict collector. Google News RSS is "
            "used for discovery only. Every article must have a "
            "publication date verified from the original Moneycontrol "
            "page and be within the rolling last 10 days. Confirmed "
            "items require a labelled stock section and explicitly "
            "extracted entry/CMP, target and stop-loss. Unverified "
            "trade-related candidates are stored separately in "
            "watchlist_items. Old, undated and future-dated pages "
            "are excluded. Missing values are never invented. "
            "This is automated extraction, not investment advice."
        ),
        "diagnostics": {
            "rss_unique_recent_articles": len(articles),
            "decoded_moneycontrol_urls": decoded_count,
            "unresolved_google_links": unresolved_links,
            "article_fetch_failures": article_fetch_failures,
            "excluded_rss_old": excluded_rss_old,
            "excluded_rss_undated": excluded_rss_undated,
            "excluded_rss_future": excluded_rss_future,
            "excluded_original_old": excluded_original_old,
            "excluded_original_undated": excluded_original_undated,
            "excluded_original_future": excluded_original_future,
            "confirmed_recommendations": len(confirmed_items),
            "unverified_trade_candidates": len(watchlist_items)
        },
        "items": confirmed_items,
        "watchlist_items": watchlist_items
    }

    OUTPUT_FILE.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("-----------------------------------")
    print("Moneycontrol collection completed.")
    print("Confirmed recommendations:", len(confirmed_items))
    print("Unverified candidates:", len(watchlist_items))
    print("Original-date old exclusions:", excluded_original_old)
    print("Original-date undated exclusions:", excluded_original_undated)
    print("Article fetch failures:", article_fetch_failures)
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
