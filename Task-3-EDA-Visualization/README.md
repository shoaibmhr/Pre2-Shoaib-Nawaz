# News Articles Dataset: Exploratory Data Analysis

## Overview

Exploratory analysis of a scraped news corpus: **96,709 articles, 15 columns, 16 sources**. Every article carries a keyword-rule-based category label (`article_niche`, 7 values) together with a score (`niche_score`) and a margin (`niche_margin`) that describe how confident that label is.

The notebook follows a fixed workflow:

Load → Profile → Univariate → Grouped → Time → Relationships → Anomalies → Findings

## Data at a glance

| Item | Result |
|---|---|
| Rows / columns | 96,709 / 15 |
| Duplicates | None. `title`, `content` and `url` are all unique (96,709 each) |
| Missing values | Only `author_name`: 2,562 rows (2.65%). All other columns are complete |
| Repeated descriptions | `description` has 95,790 unique values, so a small number repeat |
| Dates | Day-level only (1,805 unique days, no time of day), so hourly analysis is not possible |
| Non-news rows | `is_non_news` is True for 2,068 rows, all from `abcnet` (gardening content). 94,641 rows remain without them. `abcnet` is set aside in a separate copy for display only; nothing was deleted from the original data |

## Key findings

1. **`news` is a fallback category, not a topic.** 66.1% of `news` rows (22,689 of 34,340) have `niche_score` 0, meaning no category keyword matched. Only 1,598 rows (4.7%) are true ties. About 95% of all margin-0 rows (25,460 in total, 26.3% of the data) sit in `news`.
2. **Article length differs only modestly by category.** Median words: stocks 508, news 562, politics 562, market 618, technology 571, energy 592, health 659. Means are higher than medians in every category, so length is right-skewed.
3. **Title length says almost nothing about article length.** Pearson 0.044, Spearman 0.113.
4. **No scraping-error pages were found by title.** Zero titles match "access denied", "captcha", "robot check", "page not found", "403 forbidden" or "enable javascript". The 64 "subscribe" and 7 "sign in" hits are ordinary articles (e.g. subscription news).
5. **Very short articles (<100 words) are mostly a source format.** 1,356 rows in total; `theverge` has 885 of them (13.7% of its articles) and `npr` 195 (3.1%). Sampled `theverge` rows are real short posts. Sampled `npr` rows look like podcast or audio episode pages.
6. **Very long articles (top 1%, 968 rows) look genuine.** Sampled rows are normal long-form pieces.
7. **The pipeline already flags non-news.** `is_non_news` equals `abcnet` exactly (2,068 rows) and is the column to use for filtering.

## Output files

| File / Folder | Content |
|---|---|
| `column_profile.csv` | Column dtypes, non-null counts, missing counts & percentages, unique counts |
| `source_distribution.csv` | Article volume per news source and share of dataset |
| `category_distribution.csv` | Article volume per thematic niche category |
| `category_by_source.csv` | Cross-tabulation of niche mix percentages across all 16 sources |
| `year_counts.csv` | Distribution of publication counts across years |
| `manual_check_200.csv` | 200 randomly sampled articles with human validation labels (84.0% accuracy) |
| `suspicious_candidates.csv` | Flagged review candidates (length outliers, non-news, suspected error keywords) |
| `articles_with_niche.csv` | Full dataset with engineered niche labels, scores, and margins |
| `by_category/*.csv` | Partitioned datasets split by category |
| `charts/*.png` | 13 production figures (Univariate, Source share, Temporal trends, Niche mix, Scatter correlation, Boxplots) |

## Limitations

- Category labels are keyword-rule-based. A manual check of 200 rows found about 84% of labels correct, so a noticeable share is probably wrong. Score 0 means the keyword list found nothing, not that the article has no topic.
- Flagged rows are review candidates, not confirmed bad data. Only small samples (12 to 15 rows) were inspected, so statements about why rows are short or long are indications, not proof.
- The nature of the short `npr` rows is inferred from 12 sampled titles.
- `stocks` has only 569 rows, so its length statistics are less reliable.
- Dates have no time component, which rules out hourly patterns.

## Reproducing

Run the notebook top to bottom. It needs `pandas` and `matplotlib`, and writes its outputs to the output folder configured as `OUT` in the first cells.