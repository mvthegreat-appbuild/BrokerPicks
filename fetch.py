import urllib.request, urllib.parse, xml.etree.ElementTree as ET
import json, re, datetime, email.utils

BROKERS = ["Motilal Oswal", "Anand Rathi", "Morgan Stanley", "Jefferies",
           "Goldman Sachs", "Kotak Securities", "ICICI Securities",
           "HDFC Securities", "Nuvama", "Axis Securities"]

items, seen = [], set()
for b in BROKERS:
    q = urllib.parse.quote(f'"{b}" stocks to buy target price when:7d')
    url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
    except Exception as e:
        print("skip", b, e)
        continue
    n = 0
    for it in root.iter("item"):
        title = it.findtext("title", "")
        link = it.findtext("link", "")
        if b.lower() not in title.lower() or link in seen or n >= 12:
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
        m = re.search(r"(?:Rs\.?|₹)\s?([\d,]+(?:\.\d+)?)", title)
        t = title.lower()
        call = ""
        if re.search(r"\b(buy|accumulate|outperform|overweight|bullish)\b", t):
            call = "BUY"
        elif re.search(r"\b(sell|reduce|underperform|underweight|bearish)\b", t):
            call = "SELL"
        items.append({"broker": b, "title": title, "source": src,
                      "link": link, "date": date,
                      "target": m.group(1) if m else "", "call": call})

items.sort(key=lambda x: x["date"], reverse=True)
out = {"updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
       "items": items}
json.dump(out, open("picks.json", "w"), ensure_ascii=False, indent=1)
print(len(items), "items")
