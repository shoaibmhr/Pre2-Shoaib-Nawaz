# Task 2: Data Preprocessing and Validation

Input: Task-1 raw dataset (100000 articles, `Task-1-Web-Scraping-100k/dataset/`)
Output: `output/articles_clean_part1..5.csv.zip` (96709 clean articles)

Policy: rows are flagged, not silently deleted. Every rejected row is saved
with its reason, so clean + rejected = raw (96709 + 3291 = 100000).

## Preprocessing (preprocessing.ipynb)

Version 1 (EDA and first cleaning) is kept at the top of the notebook.
Version 2 (lecture-based pipeline) starts from the raw data:

- Missing tokens ("N/A", "null", "-") and author "Unknown" converted to NULL
- HTML tags and entities removed, Unicode (NFKC) normalized, invisible
  characters removed, curly quotes standardized, whitespace normalized
  (title, description, author, content)
- URL validity check, date parsing (UTC)
- Length features, block/paywall check, duplicate flags
- Near-duplicate detection (TF-IDF cosine similarity on titles, per source)

### Rejected: 3291 (saved with reasons in `output/news_rejected.csv`)

- duplicate content: 1250
- puzzle/template pages (Wordle, Connections, Strands): 1149
- very long articles (5000+ words: live blogs, transcripts): 366
- duplicate title: 329 (exact) + 19 (after lowercase and punctuation removal) = 348
- near duplicate (similarity >= 0.97): 180

Note: a row can have more than one reason, so the reason counts may add up
to slightly more than 3291. Exact counts are in
`output/news_preprocessing_summary.json`.

### Review: 0

`output/news_review.csv` is empty. Rows that were earlier only flagged
(duplicate title) are now rejected.

Missing author is stored as NULL (2562 rows, 2.65%), not as "Unknown".

## Validation (validation.ipynb)

Data contract, rule IDs with severity, issue log, and dispositions.
Final file-level check on the saved output: 34/34 checks passed
(no nulls in title/content/url/source, unique url/title/content/normalized
title, no HTML/entities/invisible characters, content 30 to 5000 words,
valid dates, no puzzle or block pages). Outputs are in `output/validation/`.

## Limitations

- Near-duplicates were removed only at similarity >= 0.97. About 298 pairs
  between 0.90 and 0.97 remain (many are different stories with similar
  titles). For model training, split train/test by date or source, not randomly.
- Validation checks format and duplicates, not factual quality or bias.

## Columns

title, description, date_of_publication, author_name, content, url, source

## Verify

Run from inside the Task-2-Preprocessing folder:

    python -c "import pandas as pd, glob; df=pd.concat([pd.read_csv(f) for f in sorted(glob.glob('output/articles_clean_part*.zip'))]); print(len(df)); print(df['source'].value_counts())"

Expected: 96709 rows.

## Run the notebooks

    pip install -r requirements.txt

Then open `preprocessing.ipynb` and `validation.ipynb` and run all cells
from top to bottom.

## Load clean data into PostgreSQL

Clean data is stored in a separate table `articles_clean` (96709 rows). The raw
table `articles` (100000 rows, from Task-1) is left untouched.

1. Create a database named `newsdb`.
2. Copy `.env.example` to `.env` and write your password:

        DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/newsdb

3. Run the loader (it creates the table from `schema_clean.sql` and loads
   the data from `output/articles_clean_part*.csv.zip`):

        python load_clean_to_postgres.py

Table columns: id, title, description, published_at, author_name, content, url, source

Check in PostgreSQL:

    SELECT count(*) FROM articles_clean;   -- 96709

## Files

- `preprocessing.ipynb`, `validation.ipynb`: the two notebooks
- `output/articles_clean_part1..5.csv.zip`: clean dataset
- `output/news_rejected.csv`: rejected rows with reasons
- `output/news_review.csv`: rows flagged for review (empty)
- `output/news_quality_report.csv`, `news_source_quality.csv`, `news_preprocessing_summary.json`: quality reports
- `output/validation/`: validation issue log, warnings, summary
- `schema_clean.sql`: table structure
- `load_clean_to_postgres.py`: loads the zip parts into PostgreSQL
- `.env.example`: example connection settings (the real `.env` is not on GitHub)