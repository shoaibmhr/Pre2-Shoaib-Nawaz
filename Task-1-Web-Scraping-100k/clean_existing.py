import glob
import os
import shutil

import pandas as pd

import news_scraper_10k as ns

if not os.path.exists("data_backup_10k"):
    shutil.copytree("data", "data_backup_10k")
    print("backup bana: data_backup_10k")

for f in sorted(glob.glob("data/*.csv")):
    df = pd.read_csv(f).fillna("")
    before = len(df)
    keep = df.apply(lambda r: ns.is_valid(r.to_dict()), axis=1)
    df = df[keep].drop_duplicates(subset="url").drop_duplicates(subset="title")
    df.to_csv(f, index=False, encoding="utf-8-sig")
    print(f"{os.path.basename(f):<22}{before:>6} -> {len(df):>6}")