"""
probe2.py - naye sources test karta hai (URL supply + asli content yield).

Ye news_scraper_10k.py ke apne functions use karta hai, isliye jo result yahan
GOOD aaye wo asli run mein bhi (lagbhag) waisa hi chalega.

Chalane ka tareeqa:   python probe2.py
Saare candidates mein ~15-25 minute lagte hain.
"""
import random
import time
from concurrent.futures import ThreadPoolExecutor

import news_scraper_10k as ns

SAMPLE = 20          # har source ke kitne random article pages fetch karke dekhne hain
MIN_URLS = 3000      # kam az kam itne article URLs (ye lower bound hai, 60 sitemaps tak)
MIN_YIELD = 0.5      # kam az kam 50% pages valid honi chahiyen (80+ words, date, title)
WORKERS = 4          # ek waqt mein 4 alag sites test hongi

# Ye sirf candidates hain, test nahi huye. Jo GOOD aayein wohi SOURCES mein dalo.
CANDIDATES = [
    ("arabnews", "https://www.arabnews.com"),
    ("aljazeera", "https://www.aljazeera.com"),
    ("thehindu", "https://www.thehindu.com"),
    ("indianexpress", "https://indianexpress.com"),
    ("ndtv", "https://www.ndtv.com"),
    ("thenews", "https://www.thenews.com.pk"),
    ("geo", "https://www.geo.tv"),
    ("brecorder", "https://www.brecorder.com"),
    ("japantimes", "https://www.japantimes.co.jp"),
    ("koreaherald", "https://www.koreaherald.com"),
    ("straitstimes", "https://www.straitstimes.com"),
    ("bangkokpost", "https://www.bangkokpost.com"),
    ("jakartapost", "https://www.thejakartapost.com"),
    ("france24", "https://www.france24.com"),
    ("abcnet", "https://www.abc.net.au"),
    ("smh", "https://www.smh.com.au"),
    ("nzherald", "https://www.nzherald.co.nz"),
    ("irishtimes", "https://www.irishtimes.com"),
    ("independent", "https://www.independent.co.uk"),
    ("techcrunch", "https://techcrunch.com"),
    ("arstechnica", "https://arstechnica.com"),
    ("engadget", "https://www.engadget.com"),
    ("zdnet", "https://www.zdnet.com"),
    ("cnet", "https://www.cnet.com"),
    ("vox", "https://www.vox.com"),
    ("theconversation", "https://theconversation.com"),
    ("propublica", "https://www.propublica.org"),
    ("time", "https://time.com"),
    ("newsweek", "https://www.newsweek.com"),
    ("huffpost", "https://www.huffpost.com"),
    ("nbcnews", "https://www.nbcnews.com"),
    ("usatoday", "https://www.usatoday.com"),
    ("foxnews", "https://www.foxnews.com"),
    ("moscowtimes", "https://www.themoscowtimes.com"),
    ("kyivindependent", "https://kyivindependent.com"),
]


def probe(item):
    name, root = item
    cfg = {"name": name, "category": "simple", "root": root, "feeds": []}
    fetcher = ns.SimpleFetcher(cfg)
    try:
        try:
            ents = ns.collect_sitemap_entries(cfg, fetcher.get_raw, 8000, max_sitemaps=60)
        except Exception as exc:
            return name, root, 0, 0.0, f"sitemap error: {exc}"

        urls = [u for u, _ in ents]
        if not urls:
            return name, root, 0, 0.0, "no sitemap urls (blocked ya sitemap nahi)"

        sample = random.sample(urls, min(SAMPLE, len(urls)))
        ok = 0
        for u in sample:
            try:
                if not ns.allowed_by_robots(u):
                    continue
                time.sleep(random.uniform(ns.DELAY_MIN, ns.DELAY_MAX))
                html = fetcher.get(u)
                if not html:
                    continue
                row = {**ns.parse_page(html), "url": u}
                if ns.is_valid(row):
                    ok += 1
            except Exception:
                continue
        return name, root, len(urls), ok / len(sample), ""
    finally:
        fetcher.close()


def main():
    existing = {s["name"] for s in ns.SOURCES + ns.RESERVE}
    todo = [c for c in CANDIDATES if c[0] not in existing]

    print(f"{len(todo)} candidates test ho rahe hain... (thora waqt lagega)\n")
    print(f"{'source':<18}{'urls':>8}{'yield':>8}  verdict")

    good = []
    with ThreadPoolExecutor(WORKERS) as pool:
        for name, root, n_urls, yld, err in pool.map(probe, todo):
            if err:
                verdict = f"BAD ({err})"
            elif yld < MIN_YIELD:
                verdict = "BAD (valid pages kam)"
            elif n_urls < MIN_URLS:
                verdict = "WEAK (URLs kam)"
            else:
                verdict = "GOOD"
                good.append((name, root))
            print(f"{name:<18}{n_urls:>8}{yld:>8.0%}  {verdict}", flush=True)

    print(f"\n{len(good)} GOOD sources. Ye lines SOURCES list mein paste karo:\n")
    for name, root in good:
        print(f'    {{"name": "{name}", "category": "simple", "root": "{root}", "feeds": []}},')


if __name__ == "__main__":
    main()