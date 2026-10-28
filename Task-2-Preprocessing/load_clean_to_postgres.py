import glob, os
import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()

df = pd.concat(
    [pd.read_csv(f) for f in sorted(glob.glob("output/articles_clean_part*.csv.zip"))],
    ignore_index=True,
)
df["published_at"] = pd.to_datetime(
    df["date_of_publication"], errors="coerce", utc=True, format="mixed"
)
print("Rows:", len(df))
print("Dates parse nahi huin:", df["published_at"].isna().sum())

cols = ["title", "description", "published_at", "author_name",
        "content", "url", "source"]

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute(open("schema_clean.sql", encoding="utf-8").read())
        with cur.copy(
            "COPY articles_clean (title, description, published_at, author_name, "
            "content, url, source) FROM STDIN WITH (FORMAT csv)"
        ) as copy:
            for i in range(0, len(df), 5000):
                copy.write(df[cols].iloc[i:i + 5000].to_csv(index=False, header=False))
        cur.execute("CREATE INDEX idx_clean_source ON articles_clean (source)")
        cur.execute("CREATE INDEX idx_clean_published_at ON articles_clean (published_at)")
    conn.commit()
print("Done")