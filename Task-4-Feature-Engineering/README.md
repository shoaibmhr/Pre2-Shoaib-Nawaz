Feature Engineering for Scraped News Data
LimeoX AI/ML Foundation Program: feature engineering on my own scraped news dataset.
Author: Shoaib Nawaz (BSSE51F23R052)
This repository contains the engineered features, the fitted transformers, the feature dictionary and the documented limitations. No model is trained here; this stage only builds and verifies the feature set.
---
1. Summary
Item	Value
Train rows	74,992
Test rows	19,649
Final feature matrix	1,336 columns = 36 numeric + 300 title TF-IDF + 1,000 body TF-IDF
Title embeddings	all-MiniLM-L6-v2, 384 dimensions (saved separately)
Feature dictionary	1,352 rows (every feature, including those not in X)
Leakage rule	Every vectorizer, selector and scaler is fitted on train only and only applied to test
---
2. Repository contents
File	What it is
`<your_notebook>.ipynb`	The notebook with the full feature engineering code
`X_train.npz`, `X_test.npz`	Sparse feature matrices (74,992 x 1,336 and 19,649 x 1,336), unscaled
`feature_names.csv`	Column names of `X_train` / `X_test`, in column order
`y_train_meta.csv`, `y_test_meta.csv`	`category` label and `domain_feature` for each row (index = original row index)
`feature_dictionary.csv`	Name, group, dtype, source column, calculation, missing-value handling, prediction-time availability, leakage risk, in X or not, validation improvement
`news_engineered_features.csv`	Human-readable table: url, domain, category, split, the 36 numeric features and the temporal features
`limitations.md`	Known limitations and design decisions
`fitted_objects.joblib`	Fitted title/body TF-IDF vectorizers, chi2 selectors, boilerplate set, StandardScaler, domain one-hot encoder
`domain_onehot_train.npz`, `domain_onehot_test.npz`	Publisher one-hot encoding (kept out of X on purpose, see leakage)
`title_embeddings_train_part1.npy`, `title_embeddings_train_part2.npy`	Train title embeddings, split in two because of GitHub's 100 MB file limit
`title_embeddings_test.npy`	Test title embeddings
Loading the data
```python
import numpy as np, pandas as pd, scipy.sparse as sp

X_train = sp.load_npz("X_train.npz")          # (74992, 1336)
X_test  = sp.load_npz("X_test.npz")           # (19649, 1336)
names   = pd.read_csv("feature_names.csv").iloc[:, 0].tolist()
y_train = pd.read_csv("y_train_meta.csv", index_col=0)["category"]
y_test  = pd.read_csv("y_test_meta.csv", index_col=0)["category"]

# Title embeddings: join the two train parts IN ORDER
E_train = np.concatenate([np.load(f"title_embeddings_train_part{i}.npy") for i in (1, 2)])
E_test  = np.load("title_embeddings_test.npy")
print(E_train.shape, E_test.shape)            # (74992, 384) (19649, 384)
```
Column order of X: the 36 numeric features, then 300 `title_tfidf_*`, then 1,000 `body_tfidf_*`. Embedding rows follow the same row order as `X_train` / `y_train_meta.csv`.
---
3. Pipeline
Cleaning and boilerplate removal. Publisher boilerplate was detected on the training set only and then applied to test. Moscow Times boilerplate was removed in two passes (a 5% frequency threshold, then a regex on fixed templates seen in train). Kyiv Independent has a template pass. Genuine attributions such as "told The Moscow Times" were kept. The cleaned body is stored as `text_nb` (and `text_nb_lower`).
Hand-crafted numeric features from title, body, and URL (section 4).
Text features: Bag of Words (exploration), title and body TF-IDF with unigrams and bigrams, chi2 selection (section 5).
Title embeddings with all-MiniLM-L6-v2 (section 6).
Feature selection and analysis: correlation, mutual information, chi2 (`SelectKBest`).
Export, dictionary, limitations, verification (sections 7 to 9).
---
4. Numeric features (36)
Group	Count	Features
Title	16	`title_char_count`, `title_word_count`, `title_avg_word_length`, `title_digit_count`, `title_uppercase_count`, `title_uppercase_ratio`, `title_exclamation_count`, `title_question_count`, `title_comma_count`, `title_colon_count`, `title_parentheses_count`, `title_unique_word_ratio`, `title_has_number`, `title_quote_count`, `title_allcaps_word_count`, `title_starts_with_digit`
Body (boilerplate-free text)	13	`body_word_count`, `body_sentence_count`, `body_avg_sentence_length`, `body_number_count`, `body_url_count`, `body_avg_word_length`, `body_unique_word_ratio`, `body_uppercase_word_count`, `body_comma_count`, `body_question_count`, `body_exclamation_count`, `body_quote_count`, `body_number_density`
Financial keywords	1	`financial_keyword_count`
URL	4	`url_length`, `url_path_depth`, `url_slug_length`, `url_slug_word_count`
Interaction	2	`title_body_length_ratio`, `financial_keyword_density` (count / body word count, 4 decimals)
Two exactly duplicated features were removed: `title_body_length_difference` and `body_char_count`. Other highly correlated pairs were kept on purpose; only exact duplicates were dropped.
All body features were recomputed from the boilerplate-free text, so none of them are based on publisher boilerplate length.
---
5. Text features
Block	Source text	Settings	Selection	Columns in X
Title TF-IDF	title	`max_features=5000`, `ngram_range=(1,2)`, `min_df=2`, no stop-word removal	chi2, top 300	300
Body TF-IDF	`text_nb_lower`	`max_features=10000`, `ngram_range=(1,2)`, `min_df=5`, `stop_words="english"`	chi2, top 1,000	1,000
A Bag of Words baseline (`CountVectorizer`, 5,000 features, English stop words, `min_df=2`) was built during exploration and is not part of the exported matrix.
---
6. Title embeddings
Model: `sentence-transformers/all-MiniLM-L6-v2`, normalised embeddings, 384 dimensions.
Train: 74,992 x 384, test: 19,649 x 384.
Saved separately and not concatenated into `X_train` / `X_test`.
The train file was split in two parts to fit GitHub's file size limit (see "Loading the data").
---
7. Temporal, categorical and publisher features (not in X)
Temporal: `published_year`, `published_month`, `published_day`, `published_dayofweek`, `published_is_weekend`, `published_day_sin/cos`, `published_month_sin/cos`. They are in `news_engineered_features.csv` but not in X.
Not possible: hour-of-day and article-age features. The data has publish date only (one unique hour) and no `scraped_at` column.
Categorical: the target is label-encoded (`category_encoded`, never used as a feature). The publisher (domain) is one-hot encoded and saved separately, because putting it in X lets a model learn the publisher instead of the content.
Publisher statistics (`domain_article_count`, `domain_avg_*`) exist in the working data but are not used in X.
Scaling: a `StandardScaler` fitted on train is saved in `fitted_objects.joblib`. The exported X is unscaled.
---
8. Feature dictionary
`feature_dictionary.csv` documents every feature with:
`feature`, `group`, `dtype`, `source_column`, `calculation`, `missing_value_handling`, `prediction_time_availability`, `leakage_risk`, `in_X_train`, `validation_improvement`
Leakage ratings are `low`, `medium: publisher proxy` (URL and writing-style features) or `high` (TF-IDF terms that contain publisher or topic words such as russia, ukraine, kyiv, moscow). `validation_improvement` is "not evaluated (modeling not done yet)" for X features.
---
9. Verification
A final read-only check script was run on the exported files. It verified:
row and column counts of X match the dataframes and `feature_names.csv`;
no NaN or inf in X, and no label or publisher columns in X;
the saved numeric block equals the dataframe values on a random sample;
labels align with X rows and test classes are all present in train;
embeddings and one-hot shapes and normalisation;
every X feature appears in the dictionary;
the saved body vectorizer and selector reproduce the test matrix;
file sizes against GitHub's limits.
Result: 54 checks passed. The only failure was the single 115 MB embeddings file, which is why it was split in two.
---
10. Limitations
Publisher proxy. Moscow Times (about 90%) and Kyiv Independent (about 97%) articles are politics-heavy, so the publisher identity can act as a proxy for the label. When modelling, use a domain-wise holdout or a publisher-feature ablation.
Topic words are also publisher words. russia, ukraine, kyiv and moscow identify both the topic and the publisher.
Style features. URL and writing-style features are rated "medium: publisher proxy".
TF-IDF settings. The body TF-IDF settings above are the final ones; the original body vectorizer object was overwritten during the work, so its exact earlier settings cannot be recovered.
`financial_keyword_density` is `count / body_word_count` (4 decimals) on boilerplate-free text, which differs slightly from the lesson notebook (unrounded, on the lightly cleaned text).
Attributions kept. Genuine attributions ("told The Moscow Times", "told the Kyiv Independent") remain in the text (about 11% of Moscow Times and 39% of Kyiv Independent articles).
No time of day, no scrape time. Hour and article-age features could not be built.
No modelling. No model was trained, so the contribution of each feature to validation performance is not evaluated.
See `limitations.md` for the same list in file form.
---
11. Possible next steps
Wrap all transformations in a single `sklearn` `Pipeline` / `ColumnTransformer` so raw data goes to the final matrix in one call.
Compare metadata-only, text-only and combined feature sets, plus a publisher-only baseline, using a domain-wise holdout.
Evaluate each feature group by its effect on validation performance and fill in the `validation_improvement` column.