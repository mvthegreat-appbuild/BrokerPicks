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

# MONEYCONTROL ONLY — STRICT ROLLING 10-DAY TRADE PICK COLLECTOR
SOURCE = "Moneycontrol"
OUTPUT_FILE = Path("media_picks.json")
MAX_ARTICLE_AGE_DAYS = 10
MAX_ARTICLES_PER_QUERY = 40
REQUEST_TIMEOUT = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"}
SEARCH_QUERIES = [
    'site:moneycontrol.com "Trade Spotlight"',
    'site:moneycontrol.com "swing trade"',
    'site:moneycontrol.com "swing trading"',
    'site:moneycontrol.com "positional trade"',
    'site:moneycontrol.com "positional call"',
    'site:moneycontrol.com "short-term trade"',
]

# Match only explicit stock headings, never arbitrary mentions in sidebars or prose.
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
    "Godrej Consumer Products": ["godrej consumer products", "godrej consumer"],
    "General Insurance Corporation": ["general insurance corporation", "gic re", "gic of india"],
    "Aditya Birla Real Estate": ["aditya birla real estate", "birla estates"],
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
    "Trent": ["trent limited", "trent"],
    "Zomato": ["zomato", "eternal limited"],
    "Adani Green Energy": ["adani green energy"],
    "Va Tech Wabag": ["va tech wabag", "wabag"],
    "TVS Motor": ["tvs motor company", "tvs motor"],
    "Quess Corp": ["quess corp", "quess"],
    "Gabriel India": ["gabriel india"],
    "Avenue Supermarts": ["avenue supermarts", "dmart"],
    "Bharat Electronics": ["bharat electronics", "bel"],
    "Indian Railway Finance Corporation": ["indian railway finance corporation", "irfc"],
    "Pidilite Industries": ["pidilite industries", "pidilite"],
    "Gujarat Fluorochemicals": ["gujarat fluorochemicals", "gfl"],
    "EIH": ["eih", "eih limited"],
    "Bajaj Holdings": ["bajaj holdings and investment", "bajaj holdings"],
    "Power Grid Corporation": ["power grid corporation of india", "power grid corporation", "power grid"],
    "Coromandel International": ["coromandel international", "coromandel"],
    "Indian Hotels": ["indian hotels company", "indian hotels"],
}

BLOCK_TAGS = {"p", "div", "br", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "section", "article"}

class PageParser(HTMLParser):
    """Keep line boundaries; omit scripts, navigation, footer and header."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_tags = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header", "noscript", "svg"):
            self.skip_tags.append(tag)
        elif not self.skip_tags and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header", "noscript", "svg"):
            if tag in self.skip_tags:
                self.skip_tags.reverse()
                self.skip_tags.remove(tag)
                self.skip_tags.reverse()
        elif not self.skip_tags and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_tags:
            self.parts.append(data)

    def text(self):
        text = "".join(self.parts).replace("\xa0", " ")
        return "\n".join(clean_text(x) for x in text.splitlines() if clean_text(x))


def install_decoder():
    try:
        from googlenewsdecoder import gnewsdecoder
        return gnewsdecoder
    except ImportError:
        print("Installing Google News URL decoder...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "googlenewsdecoder"])
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
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def extract_original_publication_date(html):
    patterns = [
        r'<meta[^>]+(?:property|name)=["\']article:published_time["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']article:published_time["\']',
        r'<meta[^>]+(?:name|property)=["\'](?:pubdate|publishdate|date|dc\.date|dc\.date\.issued)["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:pubdate|publishdate|date|dc\.date|dc\.date\.issued)["\']',
        r'"datePublished"\s*:\s*"([^"]+)"', r'"dateCreated"\s*:\s*"([^"]+)"',
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
    return dt is not None and now - timedelta(days=MAX_ARTICLE_AGE_DAYS) <= dt <= now


def get_rss_items(query):
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + "&hl=en-IN&gl=IN&ceid=IN:en"
    root = ET.fromstring(fetch_url(url))
    results = []
    for item in root.findall(".//item")[:MAX_ARTICLES_PER_QUERY]:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        source_node = item.find("source")
        source_name = source_node.text.strip() if source_node is not None and source_node.text else ""
        source_url = source_node.attrib.get("url", "") if source_node is not None else ""
        if "moneycontrol" not in (source_name + " " + source_url + " " + title).lower():
            continue
        results.append({"title": title, "google_link": link, "rss_published": parse_date(pub_date)})
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
    return r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"


def stock_heading_match(lines, index):
    """Return canonical stock if this line is a stock heading with nearby CMP."""
    line = clean_text(lines[index]).lower()
    # Do not accept stock names buried in sentences or chart annotations.
    for stock_name, aliases in sorted(STOCKS.items(), key=lambda x: max(map(len, x[1])), reverse=True):
        for alias in sorted(aliases, key=len, reverse=True):
            if re.match(r"^\s*" + alias_pattern(alias), line):
                heading_tail = line[len(alias):]
                nearby = " ".join(lines[index:min(index + 3, len(lines))]).lower()
                if re.search(r"\bcmp\b", heading_tail) or re.search(r"\bcmp\b", nearby):
                    return stock_name
    return ""


def extract_stock_sections(article_text):
    """Build sections only from explicit `Stock | CMP` headings.

    This intentionally does not scan arbitrary stock mentions in the full page,
    so related stories, navigation and chart labels cannot create fake picks.
    """
    lines = [clean_text(line) for line in article_text.splitlines()]
    lines = [line for line in lines if line]
    starts = []
    for i in range(len(lines)):
        stock = stock_heading_match(lines, i)
        if stock:
            starts.append((i, stock))
    sections = []
    for pos, (start, stock) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines)
        # Stop before common author/related-story page furniture.
        for j in range(start + 1, end):
            low = lines[j].lower()
            if low in ("related stories", "related articles", "read more") or low.startswith(("related stories ", "related articles ")):
                end = j
                break
            if re.match(r"^(?:by |written by |author\s*:)", low):
                end = j
                break
        section = "\n".join(lines[start:end])
        sections.append((stock, section, True))
    return sections


def extract_values_after_label(label_pattern, text):
    # Read the complete labelled line so multiple targets are retained,
    # including formats such as "Target: Rs 385. Rs 400".
    match = re.search(label_pattern + r"\s*[:\-]?\s*([^\n]+)", text, flags=re.IGNORECASE)
    if not match:
        return ""
    raw = match.group(1)
    # Stop at a sentence boundary only when it is followed by prose, not a
    # second Rs/₹ target value. Then extract all numeric values on the line.
    raw = re.split(r"\s+[A-Za-z][A-Za-z ]{2,}:\s*", raw, maxsplit=1)[0]
    nums = re.findall(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?", raw)
    return ", ".join(n.replace(",", "") for n in nums)


def extract_trade_levels(section):
    entry = extract_values_after_label(r"(?:CMP|current market price|entry(?: price)?|buying range|buy range|buy at)", section)
    if not entry:
        entry = extract_values_after_label(r"(?:buy above|buy near)", section)
    target = extract_values_after_label(r"(?:target price|targets?|upside target|price target)(?:\s+(?:of|at))?", section)
    if not target:
        target = extract_values_after_label(r"first target", section)
    stop_loss = extract_values_after_label(r"(?:stop[\s-]?loss|stoploss|SL)(?:\s+(?:at|of))?", section)
    holding = ""
    hm = re.search(r"(?:holding period|time frame|timeframe|duration)\s*[:\-]?\s*([^\n.;]{2,60})|(?:for the next|within the next)\s+(\d+\s*(?:days?|weeks?|months?))", section, re.I)
    if hm:
        holding = clean_text(hm.group(1) or hm.group(2))
    strategy_match = re.search(r"\bstrategy\s*:\s*(buy|sell|accumulate|avoid)\b", section, re.I)
    strategy = strategy_match.group(1).title() if strategy_match else ""
    return {"entry": entry, "target": target, "stop_loss": stop_loss, "holding_period": holding, "strategy": strategy}


def build_record(stock_name, title, article_url, published, section, labelled):
    levels = extract_trade_levels(section)
    confirmed = bool(labelled and levels["strategy"] and levels["entry"] and levels["target"] and levels["stop_loss"])
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
        "recommendation_status": "Confirmed recommendation - verify before trading" if confirmed else "Unverified article - not a confirmed recommendation",
        "section_verified": bool(labelled),
        "date_verified": True,
        "extraction_note": "Original Moneycontrol publication date verified within 10 days. Stock is accepted only from an explicit stock heading containing CMP; values are extracted only from that stock's section. Confirmed records require Strategy, CMP/entry, target and stop-loss. Missing values are never estimated."
    }


def deduplicate(items):
    unique = {}
    for item in items:
        key = (item["stock"].lower(), item["article_url"].lower())
        unique[key] = item
    result = list(unique.values())
    result.sort(key=lambda x: x["published_at"], reverse=True)
    return result


def main():
    now = datetime.now(timezone.utc)
    decoder = install_decoder()
    articles = {}
    errors = {}
    excluded_rss_old = excluded_rss_undated = excluded_rss_future = 0
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
                articles.setdefault(item["google_link"] or item["title"], item)
        except Exception as exc:
            errors[query] = str(exc)[:250]
            print("RSS query error:", str(exc)[:150])

    confirmed_items, watchlist_items = [], []
    decoded_count = unresolved_links = article_fetch_failures = 0
    excluded_original_old = excluded_original_undated = excluded_original_future = 0
    detected_sections = 0

    for item in articles.values():
        title = item["title"]
        article_url = resolve_article_url(item["google_link"], decoder)
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
            errors[article_url] = "Article fetch/date verification failed: " + str(exc)[:180]
            continue

        # Only explicit stock/CMP headings count. Do not use title or sidebar mentions.
        sections = extract_stock_sections(article_text)
        detected_sections += len(sections)
        for stock_name, section, labelled in sections:
            record = build_record(stock_name, title, article_url, original_date, section, labelled)
            if record["recommendation_status"].startswith("Confirmed"):
                confirmed_items.append(record)
            else:
                # Keep a section in watchlist only if it contains trade details.
                if re.search(r"\b(?:strategy|target|stop[\s-]?loss|\bSL\b|CMP|entry)\b", section, re.I):
                    watchlist_items.append(record)
        time.sleep(0.35)

    confirmed_items = deduplicate(confirmed_items)
    watchlist_items = deduplicate(watchlist_items)
    result = {
        "updated": now.isoformat(),
        "sources": [SOURCE],
        "source_counts": {SOURCE: len(confirmed_items)},
        "collection_window_days": MAX_ARTICLE_AGE_DAYS,
        "errors": errors,
        "method_note": "Moneycontrol-only strict collector. Google News RSS is used for discovery only. Every article must have a publication date verified from the original Moneycontrol page and be within the rolling last 10 days. A stock is accepted only from an explicit stock heading containing CMP; related stories, navigation, chart labels and arbitrary article mentions are not treated as picks. Confirmed items require Strategy, CMP/entry, target and stop-loss from the same stock section. Incomplete stock sections are stored separately in watchlist_items. Old, undated and future-dated pages are excluded. Missing values are never invented. This is automated extraction, not investment advice.",
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
            "unverified_trade_candidates": len(watchlist_items),
            "explicit_stock_sections_detected": detected_sections
        },
        "items": confirmed_items,
        "watchlist_items": watchlist_items
    }
    OUTPUT_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("-----------------------------------")
    print("Moneycontrol collection completed.")
    print("Confirmed recommendations:", len(confirmed_items))
    print("Unverified candidates:", len(watchlist_items))
    print("Explicit stock sections:", detected_sections)
    print("Original-date old exclusions:", excluded_original_old)
    print("Original-date undated exclusions:", excluded_original_undated)
    print("Article fetch failures:", article_fetch_failures)
    print("Saved:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
