# Task 2: Data Preprocessing

Input: Task-1 raw dataset (100000 articles, `Task-1-Web-Scraping-100k/dataset/`)
Output: `output/articles_clean_part1..5.csv.zip` (96934 articles)

## Cleaning steps

- Duplicate content removed: 1244
- Duplicate title removed: 313
- Puzzle hint articles (Wordle, Connections, Strands) removed: 1147
- Very long articles (5000+ words: live blogs, transcripts, deal trackers) removed: 362
- HTML tags, URLs, emails and extra spaces removed from content
- Title spacing fixed

Total: 100000 -> 96934 articles

## Columns

title, description, date_of_publication, author_name, content, url, source

## Verify

Run from inside the Task-2-Preprocessing folder:

    python -c "import pandas as pd, glob; df=pd.concat([pd.read_csv(f) for f in sorted(glob.glob('output/*.zip'))]); print(len(df)); print(df['source'].value_counts())"

## Run the notebook

    pip install -r requirements.txt

Then open `preprocessing.ipynb` and run all cells.