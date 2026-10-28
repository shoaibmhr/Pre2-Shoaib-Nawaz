# Task 2: Data Preprocessing

Input: Task-1 raw dataset (100000 articles, `Task-1-Web-Scraping-100k/dataset/`)
Output: `output/articles_clean_part1..5.csv.zip` (96922 articles)

## Cleaning steps

- Duplicate content removed: 1244
- Duplicate title removed: 313
- Puzzle hint articles (Wordle, Connections, Strands) removed: 1147
- Very long articles (5000+ words: live blogs, transcripts, deal trackers) removed: 362
- HTML tags, URLs, emails and extra spaces removed from content
- Title spacing fixed
- Duplicates re-checked after text cleaning: 12 removed

Total: 100000 -> 96922 articles

## Columns

title, description, date_of_publication, author_name, content, url, source

## Verify

Run from inside the Task-2-Preprocessing folder:

    python -c "import pandas as pd, glob; df=pd.concat([pd.read_csv(f) for f in sorted(glob.glob('output/*.zip'))]); print(len(df)); print(df['source'].value_counts())"

## Run the notebook

    pip install -r requirements.txt

Then open `preprocessing.ipynb` and run all cells.

## Load clean data into PostgreSQL

Clean data is stored in a separate table `articles_clean` (96922 rows). The raw
table `articles` (100000 rows, from Task-1) is left untouched.

1. Create a database named `newsdb`.
2. Copy `.env.example` to `.env` and write your password:

        DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/newsdb

3. Run the loader (it creates the table from `schema_clean.sql` and loads
   the data from `output/articles_clean_part*.csv.zip`):

        python load_clean_to_postgres.py

Table columns: id, title, description, published_at, author_name, content, url, source

Check in PostgreSQL:

    SELECT count(*) FROM articles_clean;   -- 96922

Files:
- `schema_clean.sql`: table structure
- `load_clean_to_postgres.py`: loads the zip parts into PostgreSQL
- `.env.example`: example of the connection settings (the real `.env` is not on GitHub)