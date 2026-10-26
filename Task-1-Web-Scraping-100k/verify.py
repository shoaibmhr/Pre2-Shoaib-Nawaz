import sys

import pandas as pd

path = sys.argv[1] if len(sys.argv) > 1 else "all_articles.csv"
target_total = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
per_source = int(sys.argv[3]) if len(sys.argv) > 3 else 1000

df = pd.read_csv(path).fillna("")
required = ["title", "description", "date_of_publication",
            "author_name", "content", "url", "source"]
problems = []

print(f"File: {path}")
print(f"Total rows: {len(df)}\n")

missing_cols = [c for c in required if c not in df.columns]
if missing_cols:
    print("MISSING COLUMNS:", missing_cols)
    raise SystemExit(1)

print("Articles per source:")
print(df["source"].value_counts().to_string(), "\n")

print("Empty values per column:")
empty = {c: int((df[c].astype(str).str.strip() == "").sum()) for c in required}
print(empty, "\n")

dates = pd.to_datetime(df["date_of_publication"], errors="coerce")
print("Date range:", dates.min(), "->", dates.max())
print("Unparseable dates:", int(dates.isna().sum()))
future = int((dates > pd.Timestamp.now()).sum())
print("Future dates:", future, "\n")

words = df["content"].astype(str).str.split().str.len()
print("Content words: min", int(words.min()), "| median", int(words.median()),
      "| max", int(words.max()))
short = int((df["content"].astype(str).str.len() < 200).sum())
print("Content shorter than 200 chars:", short)

unknown = int((df["author_name"] == "Unknown").sum())
print(f"Author 'Unknown': {unknown} ({unknown / len(df):.0%})")
dup_url = int(df.duplicated("url").sum())
dup_title = int(df.duplicated(["source", "title"]).sum())
bad_url = int((~df["url"].astype(str).str.startswith("http")).sum())
print("Duplicate URLs:", dup_url, "| Duplicate titles:", dup_title,
      "| Bad URLs:", bad_url, "\n")

# ---- pass / fail ----
if len(df) < target_total:
    problems.append(f"total {len(df)} < target {target_total}")
if df["source"].nunique() < 10:
    problems.append(f"only {df['source'].nunique()} sources (need 10)")
if (df["source"].value_counts() > per_source).any():
    problems.append(f"some source has more than {per_source} articles")
if any(v > 0 for k, v in empty.items() if k != "author_name"):
    problems.append("empty values in required columns")
if dup_url or dup_title:
    problems.append("duplicates found")
if dates.isna().sum() or future:
    problems.append("invalid or future dates")
if short:
    problems.append("some articles have very short content")
if bad_url:
    problems.append("invalid URLs")

print("=" * 40)
if problems:
    print("RESULT: FAIL")
    for p in problems:
        print(" -", p)
else:
    print("RESULT: PASS")

print("\nRandom samples (open these URLs in a browser and compare manually):")
for _, r in df.sample(min(5, len(df)), random_state=1).iterrows():
    print(f"\n[{r['source']}] {r['title']}\n  date: {r['date_of_publication']}"
          f" | author: {r['author_name']}\n  {r['url']}\n  {str(r['content'])[:150]}...")