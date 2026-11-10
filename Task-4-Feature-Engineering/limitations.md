# Limitations
- Boilerplate: Moscow Times boilerplate removed in two passes (5% frequency threshold, then regex on fixed templates seen in train); Kyiv Independent via a template pass. Boilerplate was detected on train only and only applied to val/test.
- Real attributions such as "told The Moscow Times" / "told the Kyiv Independent" were kept (MT ~11%, KI ~39% of articles).
- Publisher proxy: MT (~90%) and KI (~97%) are politics-heavy, so publisher identity can act as a proxy for the label. When modelling, use a domain-wise holdout or publisher-feature ablation.
- Words like russia, ukraine, kyiv, moscow are both topic words and publisher identity.
- URL and style features are rated "medium: publisher proxy".
- TF-IDF: title max_features=5000 -> chi2 top 300 (max_features=5000, ngram_range=(1, 2), min_df=2, stop_words=None); body -> chi2 top 1000 (max_features=10000, ngram_range=(1, 2), min_df=5, stop_words=english). These are the final settings (the original body vectorizer object was overwritten, so its exact settings are not recoverable).
- financial_keyword_density = count / body_word_count (4 decimals) on boilerplate-free text; differs from the lesson notebook (unrounded, text_clean).
- Data has publish date only (1 unique hour) and no scraped_at, so hour features and article age could not be built. Day/month sin-cos features exist but are not in the exported matrix.
- Publisher aggregates (domain_*) and domain one-hot are not in X_train/X_test (leakage risk); one-hot saved separately.
- Exported X is unscaled; the StandardScaler (fit on train) is saved in fitted_objects.joblib.
- Embeddings: all-MiniLM-L6-v2 title embeddings (384-dim) saved separately: (74992, 384), (19649, 384); not part of X_train/X_test.
- No model was trained; validation improvement per feature is not evaluated.

- title_embeddings_train.npy was split into 2 row-ordered parts (title_embeddings_train_part1..2.npy) because of GitHub's 100 MB file limit; np.concatenate them in order to restore the (74992, 384) array.
