# Task 0: Web Scraping (10k pilot)

First pilot scrape of 10000 news articles (1000 per source) from 10 news
websites, before scaling to 100000 articles in Task-1.

Sources (1000 articles each): cbsnews, dw, globalvoices, hindustantimes,
npr, scmp, thenational, theverge, tribune, wired

Files:
- all_articles_10k.csv: final combined file (10000 rows)
- data_backup_10k/: per-source CSV files from the pilot run
- news_scraper_10k.py: scraper

Columns: title, description, date_of_publication, author_name, content, url, source

## Setup

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt

## Run

    python news_scraper_10k.py --limit 1000