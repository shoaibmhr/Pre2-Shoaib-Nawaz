import argparse
import glob
import gzip
import json
import logging
import os
import random
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool
from urllib import robotparser
from urllib.parse import urlparse

import feedparser
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --------------------------------------------------------------------------- #
# CONFIG
# --------------------------------------------------------------------------- #
ARTICLES_PER_SOURCE = 1000
TOTAL_TARGET = 100000         # CHANGED: final CSV mein kitne articles chahiye
TOP_N_SOURCES = 10
OVERSAMPLE = 4.0                # CHANGED: pehle 1.6 tha, bohat kam tha
BATCH = 50
THREADS_PER_SOURCE = 3
DELAY_MIN, DELAY_MAX = 1.0, 2.0
MAX_SITEMAPS = 400              # CHANGED: pehle 60 tha
MIN_CONTENT_CHARS = 200
MAX_EMPTY_BATCHES = 8           # CHANGED: pehle 3 tha, source jaldi band ho jata tha
DATE_FORMAT = "%Y-%m-%d"
UNKNOWN_AUTHOR = "Unknown"
OUTPUT_DIR = "data"
FINAL_CSV = "all_articles.csv"
HUMAN_WAIT_TIMEOUT = 600
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


MIN_WORDS = 80
BOILERPLATE = re.compile(
    r"NPR does not offer|Copyright ©|hide caption|Accuracy and availability of NPR|"
    r"Preferred Source on Google|To view this video please enable|"
    r"Power up with unlimited access|Read the full story at|\[Image:|\[Product:|"
    r"produced by our advertising partner|Get the latest weather info", re.I)
MOJIBAKE = re.compile(r"Â[°\xa0 ]|â€|â\x80")

FIELDS = ["title", "description", "date_of_publication", "author_name", "content"]
COLS = FIELDS + ["url", "source"]

# CHANGED: globalvoices ke liye paginated WordPress feeds (page 1..80)
GLOBALVOICES_FEEDS = ["https://globalvoices.org/feed/"] + [
    f"https://globalvoices.org/feed/?paged={p}" for p in range(2, 81)
]

# 1LAKH (G): euronews hata diya (captcha unattended run mein atakta hai),
#            thenational aur guardian RESERVE se SOURCES mein aa gaye
SOURCES = [
    {"name": "tribune", "category": "simple", "root": "https://tribune.com.pk", "feeds": [
        "https://tribune.com.pk/feed/home", "https://tribune.com.pk/feed/pakistan",
        "https://tribune.com.pk/feed/world", "https://tribune.com.pk/feed/business"]},
    {"name": "scmp", "category": "simple", "root": "https://www.scmp.com", "feeds": [
        "https://www.scmp.com/rss/91/feed", "https://www.scmp.com/rss/2/feed",
        "https://www.scmp.com/rss/3/feed", "https://www.scmp.com/rss/4/feed"]},
    {"name": "npr", "category": "simple", "root": "https://www.npr.org", "feeds": [
        "https://feeds.npr.org/1001/rss.xml", "https://feeds.npr.org/1004/rss.xml"]},
    {"name": "cbsnews", "category": "simple", "root": "https://www.cbsnews.com", "feeds": []},
    {"name": "theverge", "category": "simple", "root": "https://www.theverge.com", "feeds": [
        "https://www.theverge.com/rss/index.xml"]},
    {"name": "hindustantimes", "category": "simple", "root": "https://www.hindustantimes.com", "feeds": [
        "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "https://www.hindustantimes.com/feeds/rss/world-news/rssfeed.xml",
        "https://www.hindustantimes.com/feeds/rss/business/rssfeed.xml"]},
    {"name": "globalvoices", "category": "simple", "root": "https://globalvoices.org",
     "feeds": GLOBALVOICES_FEEDS},                                   # CHANGED
    {"name": "wired", "category": "simple", "root": "https://www.wired.com", "feeds": []},
    {"name": "dw", "category": "simple", "root": "https://www.dw.com", "feeds": [
        "https://rss.dw.com/rdf/rss-en-all", "https://rss.dw.com/rdf/rss-en-world",
        "https://rss.dw.com/rdf/rss-en-bus"]},
    {"name": "thenational", "category": "simple", "root": "https://www.thenationalnews.com", "feeds": [
        # CHANGED: Arc-style feed (agar kaam na kare to warning aayegi, sitemap phir bhi chalega)
        "https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml"]},
    {"name": "guardian", "category": "simple", "root": "https://www.theguardian.com", "feeds": [
        # CHANGED: 4 ki jagah bohat saare sections
        f"https://www.theguardian.com/{sec}/rss" for sec in [
            "world", "business", "technology", "science", "uk-news", "us-news",
            "australia-news", "politics", "environment", "society", "culture",
            "commentisfree", "lifeandstyle", "travel", "money", "education",
            "global-development", "media", "football", "sport"]]},
    # 1LAKH: probe2.py se GOOD aaye huye 12 naye sources
    {"name": "jakartapost", "category": "simple", "root": "https://www.thejakartapost.com", "feeds": []},
    {"name": "abcnet", "category": "simple", "root": "https://www.abc.net.au", "feeds": []},
    {"name": "irishtimes", "category": "simple", "root": "https://www.irishtimes.com", "feeds": []},
    {"name": "engadget", "category": "simple", "root": "https://www.engadget.com", "feeds": []},
    {"name": "zdnet", "category": "simple", "root": "https://www.zdnet.com", "feeds": []},
    {"name": "cnet", "category": "simple", "root": "https://www.cnet.com", "feeds": []},
    {"name": "vox", "category": "simple", "root": "https://www.vox.com", "feeds": []},
    {"name": "theconversation", "category": "simple", "root": "https://theconversation.com", "feeds": []},
    {"name": "nbcnews", "category": "simple", "root": "https://www.nbcnews.com", "feeds": []},
    {"name": "foxnews", "category": "simple", "root": "https://www.foxnews.com", "feeds": []},
    {"name": "moscowtimes", "category": "simple", "root": "https://www.themoscowtimes.com", "feeds": []},
    {"name": "kyivindependent", "category": "simple", "root": "https://kyivindependent.com", "feeds": []},
    # 1LAKH: probe2.py se jo naye sources GOOD aayen, unhe yahan add karo, jaise:
    # {"name": "arabnews", "category": "simple", "root": "https://www.arabnews.com", "feeds": []},
]

RESERVE = [
    {"name": "bbc", "category": "simple", "root": "https://www.bbc.com", "feeds": [
        "http://feeds.bbci.co.uk/news/rss.xml", "http://feeds.bbci.co.uk/news/world/rss.xml",
        "http://feeds.bbci.co.uk/news/business/rss.xml", "http://feeds.bbci.co.uk/news/technology/rss.xml"]},
    {"name": "dawn", "category": "simple", "root": "https://www.dawn.com", "feeds": [
        "https://www.dawn.com/feeds/home", "https://www.dawn.com/feeds/pakistan",
        "https://www.dawn.com/feeds/world", "https://www.dawn.com/feeds/business"]},
    {"name": "cna", "category": "simple", "root": "https://www.channelnewsasia.com", "feeds": [
        "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml"]},
]

CHALLENGE_MARKERS = [
    "captcha", "are you a robot", "verify you are human", "verifying you are human",
    "just a moment", "unusual traffic", "press & hold", "access denied",
    "checking your browser", "cf-challenge",
]
EXCLUDE_URL = re.compile(
    r"/(tag|tags|topic|topics|author|authors|video|videos|gallery|photos|podcast|"
    r"podcasts|live|search|category|profile|section|subscribe)/|\.(jpg|jpeg|png|gif|pdf|xml)$",
    re.I)
JUNK_TAGS = ["script", "style", "nav", "aside", "footer", "form",
             "figure", "noscript", "iframe", "header"]

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(processName)s] %(message)s")
log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# HELPERS
# --------------------------------------------------------------------------- #
def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
    retry = Retry(total=3, backoff_factor=2, respect_retry_after_header=True,
                  status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def is_challenge(html, status=200):
    if status in (403, 429, 503) or not html:
        return True
    soup = BeautifulSoup(html[:30000], "lxml")
    title = soup.title.string.lower() if soup.title and soup.title.string else ""
    visible = soup.get_text(" ", strip=True)[:1500].lower()
    return any(m in title or m in visible for m in CHALLENGE_MARKERS)


_robots = {}


def allowed_by_robots(url):
    """robots.txt check (403/404 on robots.txt = no rules)."""
    p = urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    if root not in _robots:
        rp = None
        try:
            r = requests.get(root + "/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=10)
            if r.status_code == 200:
                rp = robotparser.RobotFileParser()
                rp.parse(r.text.splitlines())
        except requests.RequestException:
            pass
        _robots[root] = rp
    rp = _robots[root]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def clean_text(html):
    return re.sub(r"\s+", " ", BeautifulSoup(html or "", "lxml").get_text(" ", strip=True)).strip()


def fmt_date(raw):
    if not raw:
        return ""
    try:
        return dtparser.parse(raw).strftime(DATE_FORMAT)
    except Exception:
        return ""


def blank_row(url, lastmod="", source=""):
    return {"title": "", "description": "", "date_of_publication": "",
            "author_name": "", "content": "", "url": url, "source": source,
            "_lastmod": lastmod}


# --------------------------------------------------------------------------- #
# LAYER 1: RSS FEEDS
# --------------------------------------------------------------------------- #
def entry_to_row(e, source):
    author = e.get("author", "")
    if not author and e.get("authors"):
        author = ", ".join(a.get("name", "") for a in e["authors"] if a.get("name"))
    if e.get("published_parsed"):
        date = time.strftime(DATE_FORMAT, e["published_parsed"])
    elif e.get("updated_parsed"):
        date = time.strftime(DATE_FORMAT, e["updated_parsed"])
    else:
        date = fmt_date(e.get("published") or e.get("updated"))

    content = ""
    if e.get("content"):
        try:
            content = clean_text(e["content"][0].get("value", ""))
        except Exception:
            content = ""

    row = blank_row(e.get("link", ""), source=source)
    row.update({
        "title": clean_text(e.get("title", "")),
        "description": clean_text(e.get("summary") or e.get("description", "")),
        "date_of_publication": date,
        "author_name": clean_text(author),
        # 1LAKH (D): feed ka adhoora teaser ab content nahi banega
        "content": content if (len(content.split()) >= MIN_WORDS
                               and not BOILERPLATE.search(content)
                               and not MOJIBAKE.search(content)) else "",
    })
    return row


def read_feed(session, url):
    try:
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            log.warning("feed %s -> HTTP %s", url, r.status_code)
            return []
        d = feedparser.parse(r.content)
        if d.bozo and not d.entries:
            log.warning("feed %s could not be parsed", url)
        return d.entries
    except requests.RequestException as e:
        log.warning("feed %s failed: %s", url, e)
        return []


def collect_feed_rows(cfg, session):
    rows, seen = [], set()
    for url in cfg["feeds"]:
        entries = read_feed(session, url)
        log.info("[%s] feed %s -> %d entries", cfg["name"], url, len(entries))
        # CHANGED: paginated feed khatam ho gayi to aage ke pages try na karo
        if not entries and "paged=" in url:
            log.info("[%s] paginated feed ended at %s", cfg["name"], url)
            break
        for e in entries:
            row = entry_to_row(e, cfg["name"])
            if row["url"] and row["title"] and row["url"] not in seen:
                seen.add(row["url"])
                rows.append(row)
        time.sleep(random.uniform(0.3, 0.8))
    return rows


# --------------------------------------------------------------------------- #
# LAYER 2: SITEMAPS
# --------------------------------------------------------------------------- #
def make_link_filter(cfg):
    if cfg.get("link_regex"):
        rx = re.compile(cfg["link_regex"])
        return lambda u: bool(rx.search(u))
    domain = urlparse(cfg["root"]).netloc.replace("www.", "")

    def looks_like_article(u):
        p = urlparse(u)
        if domain not in p.netloc:
            return False
        path = p.path
        return (len(path) >= 25 and ("-" in path or any(c.isdigit() for c in path))
                and not EXCLUDE_URL.search(u))
    return looks_like_article


def discover_sitemaps(cfg, raw_get):
    found = list(cfg.get("sitemaps", []))
    data = raw_get(cfg["root"] + "/robots.txt")
    if data:
        text = data.decode("utf-8", "ignore")
        found += re.findall(r"(?im)^\s*sitemap:\s*(\S+)", text)
    return list(dict.fromkeys(found)) or [cfg["root"] + "/sitemap.xml"]


def collect_sitemap_entries(cfg, raw_get, want, max_sitemaps=MAX_SITEMAPS):
    """
    Sitemap indexes recursively read karta hai.
    Returns: [(url, lastmod)] newest first.

    Note: lastmod sirf sorting ke liye use hota hai,
    publish date ke taur par save nahi hota.
    """
    link_ok = make_link_filter(cfg)
    queue = [(u, "") for u in discover_sitemaps(cfg, raw_get)]
    entries = {}
    opened = 0

    while queue and opened < max_sitemaps and len(entries) < want:
        queue.sort(key=lambda x: x[1], reverse=True)
        url, _ = queue.pop(0)

        data = raw_get(url)
        opened += 1
        if not data:
            continue

        try:
            if data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            soup = BeautifulSoup(data, "xml")
        except Exception as exc:
            log.warning("Could not parse sitemap %s: %s", url, exc)
            continue

        # Agar current sitemap ek sitemap index hai
        if soup.find("sitemapindex"):
            for sm in soup.find_all("sitemap"):
                if not sm.loc:
                    continue
                sitemap_url = sm.loc.text.strip()
                lastmod = sm.lastmod.text.strip() if sm.lastmod else ""
                queue.append((sitemap_url, lastmod))
        # Agar current sitemap mein article URLs hain
        else:
            for item in soup.find_all("url"):
                if not item.loc:
                    continue
                article_url = item.loc.text.strip()
                if not article_url or article_url in entries:
                    continue
                if not link_ok(article_url):
                    continue
                lastmod = item.lastmod.text.strip() if item.lastmod else ""
                entries[article_url] = lastmod

    results = sorted(entries.items(), key=lambda item: item[1], reverse=True)
    log.info("Sitemap scan completed: %d unique URLs found; %d sitemap files opened",
             len(results), opened)
    return results


# --------------------------------------------------------------------------- #
# LAYER 3: ARTICLE-PAGE FETCHERS
# --------------------------------------------------------------------------- #
def make_driver():
    from selenium import webdriver
    opts = webdriver.ChromeOptions()
    opts.add_argument(f"--user-agent={USER_AGENT}")
    opts.add_argument("--window-size=1200,900")
    return webdriver.Chrome(options=opts)


def wait_for_human(driver, name):
    start = time.time()
    if is_challenge(driver.page_source):
        log.warning("[%s] Challenge detected - please solve it in the browser window...", name)
    while is_challenge(driver.page_source):
        if time.time() - start > HUMAN_WAIT_TIMEOUT:
            raise TimeoutError("CAPTCHA not solved in time")
        time.sleep(3)


def browser_fetch_text(driver, url):
    js = ("const cb = arguments[arguments.length-1];"
          "fetch(arguments[0], {credentials:'include'})"
          ".then(r => r.ok ? r.text() : null).then(cb).catch(() => cb(null));")
    try:
        driver.set_script_timeout(60)
        txt = driver.execute_async_script(js, url)
        return txt.encode("utf-8") if txt else None
    except Exception:
        return None


class SimpleFetcher:
    """Category 1: plain requests."""
    def __init__(self, cfg):
        self.name = cfg["name"]
        self.session = make_session()

    def get(self, url):
        # 1LAKH (C): galat encoding (Â°) ka fix + slow sites ke liye 30s timeout
        try:
            r = self.session.get(url, timeout=30)
            if "charset" not in r.headers.get("Content-Type", "").lower():
                r.encoding = "utf-8"
            return None if is_challenge(r.text, r.status_code) else r.text
        except requests.RequestException:
            return None

    def get_raw(self, url):
        try:
            r = self.session.get(url, timeout=30)
            return r.content if r.status_code == 200 else None
        except requests.RequestException:
            return None

    def close(self):
        self.session.close()


class CaptchaFetcher(SimpleFetcher):
    """Category 2: human verifies once in Chrome, cookies reused with requests."""
    def __init__(self, cfg):
        super().__init__(cfg)
        self.driver = make_driver()
        self.driver.get(cfg["root"])
        wait_for_human(self.driver, self.name)
        self._sync()

    def _sync(self):
        for c in self.driver.get_cookies():
            self.session.cookies.set(c["name"], c["value"], domain=c.get("domain"))

    def get(self, url):
        html = super().get(url)
        if html:
            return html
        self.driver.get(url)
        wait_for_human(self.driver, self.name)
        self._sync()
        return self.driver.page_source

    def get_raw(self, url):
        return super().get_raw(url) or browser_fetch_text(self.driver, url)

    def close(self):
        super().close()
        self.driver.quit()


class ContinuousFetcher:
    """Category 3: every page in a real browser; pause on every challenge."""
    def __init__(self, cfg):
        self.name = cfg["name"]
        self.driver = make_driver()
        self.driver.get(cfg["root"])
        wait_for_human(self.driver, self.name)

    def get(self, url):
        try:
            self.driver.get(url)
            time.sleep(random.uniform(2, 4))
            wait_for_human(self.driver, self.name)
            return self.driver.page_source
        except Exception as e:
            log.warning("[%s] browser error on %s: %s", self.name, url, e)
            return None

    def get_raw(self, url):
        return browser_fetch_text(self.driver, url)

    def close(self):
        self.driver.quit()


FETCHERS = {"simple": SimpleFetcher, "captcha": CaptchaFetcher,
            "continuous": ContinuousFetcher}


def extract_body(soup, ld_body=""):
    """Article text: JSON-LD articleBody, warna <article>/<main> ke paragraphs."""
    ld_body = re.sub(r"\s+", " ", clean_text(ld_body))
    if len(ld_body) >= MIN_CONTENT_CHARS:
        return ld_body
    container = (soup.find("article")
                 or soup.find(attrs={"itemprop": "articleBody"})
                 or soup.find("main")
                 or soup.body)
    if container is None:
        return ""
    for junk in container.find_all(JUNK_TAGS):
        junk.decompose()
    paragraphs = []
    for p in container.find_all("p"):
        text = re.sub(r"\s+", " ", p.get_text(" ", strip=True)).strip()
        # 1LAKH (E): boilerplate paragraphs bahar
        if (len(text) >= 40 and not BOILERPLATE.search(text)
                and (not paragraphs or paragraphs[-1] != text)):
            paragraphs.append(text)
    return "\n".join(paragraphs)


def parse_page(html):
    """Extract fields from an article page (JSON-LD first, then meta tags)."""
    soup = BeautifulSoup(html, "lxml")
    out = {f: "" for f in FIELDS}
    ld_body = ""

    def author_str(a):
        if isinstance(a, str):
            return a
        if isinstance(a, dict):
            return str(a.get("name", ""))
        if isinstance(a, list):
            return ", ".join(filter(None, (author_str(x) for x in a)))
        return ""

    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        items = data if isinstance(data, list) else (
            data.get("@graph", [data]) if isinstance(data, dict) else [])
        for it in items:
            if isinstance(it, dict) and "Article" in str(it.get("@type", "")):
                out["title"] = out["title"] or str(it.get("headline", ""))
                out["description"] = out["description"] or str(it.get("description", ""))
                out["date_of_publication"] = out["date_of_publication"] or fmt_date(
                    str(it.get("datePublished", "")))
                out["author_name"] = out["author_name"] or author_str(it.get("author"))
                ld_body = ld_body or str(it.get("articleBody", ""))

    def meta(*names):
        for n in names:
            el = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
            if el and el.get("content"):
                return el["content"].strip()
        return ""

    out["title"] = out["title"] or meta("og:title", "twitter:title") or (
        soup.title.string.strip() if soup.title and soup.title.string else "")
    out["description"] = out["description"] or meta("og:description", "description")
    out["date_of_publication"] = out["date_of_publication"] or fmt_date(
        meta("article:published_time", "datePublished", "pubdate", "date"))
    if not out["date_of_publication"]:
        t = soup.find("time")
        if t:
            out["date_of_publication"] = fmt_date(t.get("datetime") or t.get_text(strip=True))
    out["author_name"] = out["author_name"] or meta("author", "article:author", "byl")
    out["content"] = extract_body(soup, ld_body)
    return out


# --------------------------------------------------------------------------- #
# ONE SOURCE (runs in its own process)
# --------------------------------------------------------------------------- #
def is_valid(row):
    # 1LAKH (B): 80 words, boilerplate, mojibake aur sponsored filter
    content = str(row["content"])
    return bool(row["title"] and row["date_of_publication"]
                and len(content.split()) >= MIN_WORDS
                and not BOILERPLATE.search(content)
                and not MOJIBAKE.search(content)
                and "/presented/" not in str(row["url"]))


def needs_page(row, mode):
    if mode == "all":
        return True
    return not is_valid(row) or not row["description"] or not row["author_name"]


def scrape_source(cfg):
    name, target = cfg["name"], cfg["limit"]
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{name}.csv")

    rows, done = [], set()
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        try:
            old = pd.read_csv(out_path).fillna("")
            rows, done = old.to_dict("records"), set(old["url"])
            log.info("[%s] resuming with %d saved articles", name, len(rows))
        except Exception:
            pass

    # 1LAKH (H): jo URL fetch ho kar reject hue (short/no-date) unhe yaad rakho,
    #            taake har resume par dobara fetch na hon
    seen_path = os.path.join(OUTPUT_DIR, f"{name}.rejected.txt")
    rejected = set()
    if os.path.exists(seen_path):
        with open(seen_path, encoding="utf-8") as fh:
            rejected = {ln.strip() for ln in fh if ln.strip()}

    if len(rows) >= target:
        log.info("[%s] already has %d >= %d, skipping", name, len(rows), target)
        return {"name": name, "path": out_path, "count": len(rows)}

    session = make_session()
    holder = {"fetcher": None}

    # CHANGED: skip hone ki wajah ginne ke liye counters (thread-safe)
    stats = Counter()
    stats_lock = threading.Lock()

    def bump(key):
        with stats_lock:
            stats[key] += 1

    def get_fetcher():
        if holder["fetcher"] is None:
            log.info("[%s] starting %s fetcher", name, cfg["category"])
            holder["fetcher"] = FETCHERS[cfg["category"]](cfg)
        return holder["fetcher"]

    def raw_get(url):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200 and r.content:
                return r.content
        except requests.RequestException:
            pass
        if cfg["category"] != "simple":
            try:
                return get_fetcher().get_raw(url)
            except Exception as e:
                log.warning("[%s] browser fetch failed for %s: %s", name, url, e)
        return None

    pool = ThreadPoolExecutor(THREADS_PER_SOURCE) if cfg["category"] in ("simple", "captcha") else None
    try:
        # 1LAKH (H): rejected URLs candidates se bahar
        cands = [r for r in collect_feed_rows(cfg, session)
                 if r["url"] not in done and r["url"] not in rejected]
        need = target - len(rows)
        log.info("[%s] feeds gave %d new candidates (need %d)", name, len(cands), need)

        if len(cands) < need * OVERSAMPLE:
            # CHANGED: + len(done) taake resume par purane URLs naye URLs ki jagah na gheren
            # 1LAKH (H): + len(rejected) bhi, wajah wohi
            ents = collect_sitemap_entries(
                cfg, raw_get, int(need * OVERSAMPLE) + len(done) + len(rejected))

            seen = set(done) | rejected
            seen.update(c["url"] for c in cands)
            added = 0
            for u, lm in ents:
                if u in seen:
                    continue
                cands.append(blank_row(u, lm, name))
                seen.add(u)
                added += 1
            log.info("[%s] sitemaps gave %d article urls; added %d new candidates",
                     name, len(ents), added)

        log.info("[%s] %d candidates for %d missing articles", name, len(cands), need)

        def enrich_factory(fetcher):
            def enrich(row):
                try:
                    if not allowed_by_robots(row["url"]):
                        bump("blocked_by_robots")      # CHANGED
                        return
                    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                    html = fetcher.get(row["url"])
                    if not html:
                        bump("fetch_failed_or_challenge")   # CHANGED
                        return
                    page = parse_page(html)
                    for f in FIELDS:
                        row[f] = row[f] or page[f]
                except Exception as e:
                    bump("exception")                  # CHANGED
                    log.warning("[%s] skipped %s: %s", name, row["url"], e)
            return enrich

        empty_batches = 0
        for i in range(0, len(cands), BATCH):
            if len(rows) >= target:
                break
            batch = cands[i:i + BATCH]
            todo = [r for r in batch if needs_page(r, cfg["enrich"])]
            if todo:
                fetcher = get_fetcher()
                enrich = enrich_factory(fetcher)
                if pool and cfg["category"] == "simple":
                    list(pool.map(enrich, todo))
                else:
                    for r in todo:
                        enrich(r)

            added = 0
            for r in batch:
                if r["url"] in done or len(rows) >= target:
                    continue
                if not is_valid(r):
                    # CHANGED: kyun invalid hua, ye bhi count karo
                    # 1LAKH (H): title mil gaya matlab page fetch hua tha, to reject yaad rakho
                    if not r["title"]:
                        bump("invalid_no_title")
                    else:
                        bump("invalid_no_date" if not r["date_of_publication"]
                             else "invalid_short_content")
                        rejected.add(r["url"])
                        with open(seen_path, "a", encoding="utf-8") as fh:
                            fh.write(r["url"] + "\n")
                    continue
                r["description"] = r["description"] or r["content"][:300]
                r["author_name"] = r["author_name"] or UNKNOWN_AUTHOR
                r["source"] = name
                rows.append(r)
                done.add(r["url"])
                added += 1
            pd.DataFrame(rows, columns=COLS).to_csv(out_path, index=False, encoding="utf-8-sig")
            log.info("[%s] %d/%d articles | batch added %d | stats %s",
                     name, len(rows), target, added, dict(stats))

            empty_batches = empty_batches + 1 if added == 0 else 0
            if empty_batches >= MAX_EMPTY_BATCHES:
                log.error("[%s] %d batches in a row gave nothing - source stopped "
                          "(blocked or wrong feeds/selectors). stats=%s",
                          name, MAX_EMPTY_BATCHES, dict(stats))
                break
    except Exception as e:
        log.error("[%s] stopped by error: %s", name, e)
    finally:
        if pool:
            pool.shutdown()
        session.close()
        if holder["fetcher"]:
            try:
                holder["fetcher"].close()
            except Exception:
                pass
        if rows:
            pd.DataFrame(rows, columns=COLS).to_csv(out_path, index=False, encoding="utf-8-sig")
        flag = "OK" if len(rows) >= target else "SHORT"
        log.info("[%s] finished: %d/%d articles (%s) | final stats %s",
                 name, len(rows), target, flag, dict(stats))
    return {"name": name, "path": out_path, "count": len(rows)}


# --------------------------------------------------------------------------- #
# CHECK, MERGE, MAIN
# --------------------------------------------------------------------------- #
def check_sources(sources, limit):
    s = requests.Session()          # retry nahi: blocked sites jaldi fail hon
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})

    def raw_get(url):
        try:
            r = s.get(url, timeout=15)
            return r.content if r.status_code == 200 else None
        except requests.RequestException:
            return None

    print(f"\n{'source':<15}{'category':<12}{'feeds':>7}{'sitemap':>9}{'total':>8}  verdict")
    for cfg in sources:
        feed_urls = {r["url"] for r in collect_feed_rows(cfg, s)}
        sm = collect_sitemap_entries(cfg, raw_get, limit * 2, max_sitemaps=MAX_SITEMAPS)
        total = len(feed_urls | {u for u, _ in sm})
        if total >= limit:
            verdict = "OK (URLs only, content not tested)"
        elif total == 0 and cfg["category"] != "simple":
            verdict = "blocked for plain requests (browser will be used)"
        else:
            verdict = "SHORT - add feeds/sitemaps or use a reserve"
        print(f"{cfg['name']:<15}{cfg['category']:<12}{len(feed_urls):>7}{len(sm):>9}{total:>8}  {verdict}")


def merge_to_csv(total, per_source_cap=None):
    """
    CHANGED: ab data/ folder ki SAARI CSV files merge hoti hain (sirf top-N nahi),
    duplicates hatate hain, newest first sort karke `total` articles rakhte hain.
    """
    files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.csv")))
    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)
        except Exception as e:
            log.warning("could not read %s: %s", f, e)
            continue
        if df.empty:
            continue
        if "source" not in df.columns or df["source"].isna().all():
            df["source"] = os.path.splitext(os.path.basename(f))[0]
        df = df.drop_duplicates(subset=["url"])
        if per_source_cap:
            df["_d"] = pd.to_datetime(df["date_of_publication"], errors="coerce")
            df = df.sort_values("_d", ascending=False).head(per_source_cap)
        frames.append(df)

    if not frames:
        log.error("No data found in %s/", OUTPUT_DIR)
        return

    final = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["url"])
    final["_d"] = pd.to_datetime(final["date_of_publication"], errors="coerce")
    final = final.sort_values("_d", ascending=False).head(total)
    final[COLS].to_csv(FINAL_CSV, index=False, encoding="utf-8-sig")

    print("\n=========== REPORT ===========")
    print("Per source (data/ folder):")
    for df in sorted(frames, key=len, reverse=True):
        print(f"  {df['source'].iloc[0]:<15}{len(df):>6} articles")
    print("\nIn final CSV:")
    for src, n in final["source"].value_counts().items():
        print(f"  {src:<15}{n:>6}")
    print(f"\nFINAL CSV: {FINAL_CSV}  ->  {len(final)} articles (target {total})")
    if len(final) < total:
        print(f"SHORT by {total - len(final)} -> aur scrape karein "
              f"(e.g. --limit ko barhayein) phir --merge-only chalayein.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated source names (primary or reserve)")
    ap.add_argument("--limit", type=int, default=ARTICLES_PER_SOURCE, help="articles per source")
    ap.add_argument("--total", type=int, default=TOTAL_TARGET, help="articles in final CSV")
    ap.add_argument("--enrich", choices=["missing", "all"], default="missing",
                    help="fetch article pages: when a field is missing / always")
    ap.add_argument("--no-reserve", action="store_true", help="do not use reserve sources")
    ap.add_argument("--check", action="store_true", help="dry run: count reachable links")
    ap.add_argument("--merge-only", action="store_true",
                    help="scrape mat karo, sirf data/*.csv se final CSV banao")
    args = ap.parse_args()

    if args.merge_only:
        merge_to_csv(args.total)
        raise SystemExit

    primaries = SOURCES
    if args.only:
        wanted = {n.strip() for n in args.only.split(",")}
        primaries = [s for s in SOURCES + RESERVE if s["name"] in wanted]

    if args.check:
        check_sources(primaries + ([] if args.only else RESERVE), args.limit)
        raise SystemExit

    def prep(lst):
        return [{**s, "limit": args.limit, "enrich": args.enrich} for s in lst]

    # 1LAKH (F): zyada sources hon to bhi ek waqt mein sirf 12 processes
    with Pool(processes=min(len(primaries), 12)) as p:
        results = p.map(scrape_source, prep(primaries))

    short = [r for r in results if r["count"] < args.limit]
    if short and not args.only and not args.no_reserve:
        spare = RESERVE[:len(short)]
        log.warning("%d source(s) ended short -> scraping reserves: %s",
                    len(short), ", ".join(s["name"] for s in spare))
        with Pool(processes=min(len(spare), 10)) as p:
            results += p.map(scrape_source, prep(spare))

    merge_to_csv(args.total)