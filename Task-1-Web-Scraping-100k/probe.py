import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import news_scraper_10k as ns

# feeds khali ho to script homepage se khud dhoondti hai
CANDIDATES = [
    {"name": "tribune", "root": "https://tribune.com.pk", "feeds": [
        "https://tribune.com.pk/feed/home", "https://tribune.com.pk/feed/world"]},
    {"name": "hindustantimes", "root": "https://www.hindustantimes.com", "feeds": [
        "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "https://www.hindustantimes.com/feeds/rss/world-news/rssfeed.xml"]},
    {"name": "dw", "root": "https://www.dw.com", "feeds": [
        "https://rss.dw.com/rdf/rss-en-all", "https://rss.dw.com/rdf/rss-en-world"]},
    {"name": "npr", "root": "https://www.npr.org", "feeds": [
        "https://feeds.npr.org/1001/rss.xml", "https://feeds.npr.org/1004/rss.xml"]},
    {"name": "bbc", "root": "https://www.bbc.com", "feeds": [
        "http://feeds.bbci.co.uk/news/rss.xml", "http://feeds.bbci.co.uk/news/world/rss.xml"]},
    {"name": "guardian", "root": "https://www.theguardian.com", "feeds": [
        "https://www.theguardian.com/world/rss", "https://www.theguardian.com/business/rss"]},
    {"name": "scmp", "root": "https://www.scmp.com", "feeds": [
        "https://www.scmp.com/rss/91/feed", "https://www.scmp.com/rss/2/feed"]},
    {"name": "dawn", "root": "https://www.dawn.com", "feeds": [
        "https://www.dawn.com/feeds/home", "https://www.dawn.com/feeds/pakistan"]},
    {"name": "france24", "root": "https://www.france24.com", "feeds": []},
    {"name": "euronews", "root": "https://www.euronews.com", "feeds": []},
    {"name": "techcrunch", "root": "https://techcrunch.com", "feeds": []},
    {"name": "arstechnica", "root": "https://arstechnica.com", "feeds": []},
    {"name": "theverge", "root": "https://www.theverge.com", "feeds": []},
    {"name": "wired", "root": "https://www.wired.com", "feeds": []},
    {"name": "phys", "root": "https://phys.org", "feeds": []},
    {"name": "propublica", "root": "https://www.propublica.org", "feeds": []},
    {"name": "globalvoices", "root": "https://globalvoices.org", "feeds": []},
    {"name": "thediplomat", "root": "https://thediplomat.com", "feeds": []},
    {"name": "abcnews", "root": "https://abcnews.go.com", "feeds": []},
    {"name": "cbsnews", "root": "https://www.cbsnews.com", "feeds": []},
    {"name": "thenational", "root": "https://www.thenationalnews.com", "feeds": []},
    {"name": "cna", "root": "https://www.channelnewsasia.com", "feeds": []},
]


def make_plain_session():
    s = requests.Session()          # retry nahi: blocked sites jaldi fail hon
    s.headers.update({"User-Agent": ns.USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
    return s


def discover_feeds(s, root):
    try:
        r = s.get(root, timeout=15)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        found = []
        for link in soup.find_all("link", rel="alternate"):
            t = (link.get("type") or "").lower()
            if ("rss" in t or "atom" in t) and link.get("href"):
                found.append(urljoin(root, link["href"]))
        return list(dict.fromkeys(found))[:6]
    except requests.RequestException:
        return []


def probe(cand):
    name = cand["name"]
    s = make_plain_session()

    def raw_get(url):
        try:
            r = s.get(url, timeout=15)
            return r.content if r.status_code == 200 else None
        except requests.RequestException:
            return None

    try:
        feeds = list(cand["feeds"]) or discover_feeds(s, cand["root"])
        cfg = {"name": name, "root": cand["root"], "feeds": feeds, "category": "simple"}
        rows = ns.collect_feed_rows(cfg, s) if feeds else []
        feed_n = len(rows)
        sm = ns.collect_sitemap_entries(cfg, raw_get, 2000, max_sitemaps=15)
        total = len({r["url"] for r in rows} | {u for u, _ in sm})

        samples = rows[:5]
        if len(samples) < 5:
            have = {r["url"] for r in samples}
            samples += [ns.blank_row(u, lm, name) for u, lm in sm if u not in have][:5 - len(samples)]

        valid = 0
        for row in samples:
            try:
                if not ns.allowed_by_robots(row["url"]):
                    continue
                r = s.get(row["url"], timeout=20)
                if r.status_code != 200 or ns.is_challenge(r.text, r.status_code):
                    continue
                page = ns.parse_page(r.text)
                for f in ns.FIELDS:
                    row[f] = row[f] or page[f]
                if ns.is_valid(row):
                    valid += 1
            except requests.RequestException:
                pass

        if total >= 1000 and valid >= 4:
            verdict = "GOOD"
        elif total >= 1000 and valid >= 2:
            verdict = "MAYBE (content/date kabhi kabhi missing)"
        elif total < 1000:
            verdict = "BAD: kam URLs"
        else:
            verdict = "BAD: content/date nahi nikal raha (paywall/block?)"
        return (name, feed_n, len(sm), total, valid, len(samples), verdict)
    except Exception as e:
        return (name, 0, 0, 0, 0, 0, f"BAD: error {e}")


if __name__ == "__main__":
    only = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
    cands = [c for c in CANDIDATES if not only or c["name"] in only]
    with ThreadPoolExecutor(5) as pool:
        results = list(pool.map(probe, cands))
    print(f"\n{'source':<16}{'feeds':>6}{'sitemap':>9}{'total':>8}{'valid':>8}  verdict")
    for name, f, sm, total, valid, n, verdict in sorted(results, key=lambda x: (x[6][0] != "G", -x[3])):
        print(f"{name:<16}{f:>6}{sm:>9}{total:>8}{valid:>5}/{n}  {verdict}")