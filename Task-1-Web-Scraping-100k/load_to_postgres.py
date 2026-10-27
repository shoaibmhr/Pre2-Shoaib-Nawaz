import os
import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()

df = pd.read_csv("all_articles.csv")
df["published_at"] = pd.to_datetime(
    df["date_of_publication"], errors="coerce", utc=True, format="mixed"
)
print("Rows:", len(df))
print("Dates jo parse nahi huin:", df["published_at"].isna().sum())
print(df[df["published_at"].isna()].groupby("source").size())

cols = ["title", "description", "published_at", "author_name",
        "content", "url", "source"]

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute(open("schema.sql", encoding="utf-8").read())
        with cur.copy(
            "COPY articles (title, description, published_at, author_name, "
            "content, url, source) FROM STDIN WITH (FORMAT csv)"
        ) as copy:
            for i in range(0, len(df), 5000):
                copy.write(df[cols].iloc[i:i + 5000].to_csv(index=False, header=False))
        cur.execute("CREATE INDEX idx_articles_source ON articles (source)")
        cur.execute("CREATE INDEX idx_articles_published_at ON articles (published_at)")
    conn.commit()
print("Done")