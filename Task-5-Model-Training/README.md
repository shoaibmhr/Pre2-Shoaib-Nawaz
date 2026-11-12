# Task 5: Model Training and Comparison

Multi-class news article classification (7 categories) using the features built in Task 4. Six classical models and one AutoML tool were trained and compared on a validation split. The best model was then evaluated once on the test set.

## 1. Goal

Predict the `category` of a news article from the engineered features in `Task-4-Feature-Engineering/`, and compare several model families on the same data.

## 2. Data

Loaded directly from the Task 4 folder (no copy is stored here):

| File | Content |
|---|---|
| `X_train.npz` | 74,992 rows x 1,336 features (36 numeric, 300 title TF-IDF, 1,000 body TF-IDF) |
| `X_test.npz` | 19,649 rows x 1,336 features |
| `y_train_meta.csv`, `y_test_meta.csv` | `category` target (publisher/domain column is kept out of the features) |
| `fitted_objects.joblib` | Fitted `num_scaler` (StandardScaler for the first 36 numeric columns) |

**Target classes (train):** politics 26,695, news 23,565, technology 19,009, health 2,212, energy 1,985, market 1,152, stocks 374. The data is strongly imbalanced, so macro F1 is reported next to accuracy.

**Baseline:** always predicting the majority class gives 0.356 accuracy on the validation split.

## 3. Method

- **Validation split:** 80/20 stratified split of the training set (59,993 train / 14,999 validation, `random_state=42`). All models were compared on the validation part.
- **Test set:** touched only once, for the best model at the end.
- **Scaling:** the Task 4 `num_scaler` was applied to the first 36 numeric columns only. TF-IDF columns were left as they are. Scaling was used for Logistic Regression, LinearSVC, KNN and SVC. Decision Tree, Random Forest and AutoGluon use unscaled features.
- **Class imbalance:** `class_weight="balanced"` (or `balanced_subsample` for Random Forest) wherever the model supports it. KNN has no class weights.
- **Metrics:** accuracy, macro F1, weighted F1, per-class precision/recall, confusion matrix, training time.

## 4. Models

| Model | Settings |
|---|---|
| Logistic Regression | `max_iter=1000`, balanced class weights |
| Linear SVM (LinearSVC) | `C=1.0`, `max_iter=5000`, balanced class weights |
| Decision Tree | `max_depth=30`, `min_samples_leaf=5`, balanced class weights |
| Random Forest | 200 trees, `min_samples_leaf=2`, `balanced_subsample` |
| KNN | `k=5`, distance weighting, Euclidean on scaled features |
| SVM (RBF kernel) | `C=1.0`, balanced class weights, trained on a 15,000-row stratified subsample |
| AutoGluon 1.6.3 | `medium_quality`, `time_limit=900`, `eval_metric=f1_macro`, KNN / NN_TORCH / FASTAI excluded |

## 5. Results (validation set, 14,999 rows)

| Model | Accuracy | Macro F1 | Weighted F1 | Train time (s) |
|---|---|---|---|---|
| **Linear SVM (LinearSVC)** | **0.8958** | **0.8013** | **0.8974** | 84.3 |
| AutoGluon | 0.8903 | 0.7741 | 0.8890 | 377.6 |
| Logistic Regression | 0.8675 | 0.7424 | 0.8728 | 33.7 |
| Random Forest | 0.8441 | 0.7006 | 0.8408 | 163.8 |
| Decision Tree | 0.7151 | 0.5521 | 0.7266 | 63.2 |
| SVM (RBF, 15k subsample) | 0.6193 | 0.4324 | 0.6359 | 347.3 |
| KNN (k=5) | 0.5894 | 0.3108 | 0.5733 | 0.1* |

\* KNN only stores the data when "training", so almost all of its time is spent in prediction, which is not included in this column.

## 6. Final test result (LinearSVC)

The best model (LinearSVC) was refit on the full training set (74,992 rows, so it also saw the validation part) and evaluated once on the test set (19,649 rows).

| Metric | Validation | Test |
|---|---|---|
| Accuracy | 0.8958 | 0.8810 |
| Macro F1 | 0.8013 | 0.8070 |
| Weighted F1 | 0.8974 | 0.8818 |

Per-class test F1: energy 0.785, health 0.793, market 0.724, news 0.900, politics 0.885, stocks 0.662, technology 0.901.

Validation and test scores are close, so no large overfitting was seen.

## 7. Observations

- **Linear models do best.** The features are mostly sparse TF-IDF columns, where a linear boundary is usually enough. LinearSVC beat every other model, including AutoGluon.
- **A single Decision Tree is weak** on sparse text features. Random Forest improves on it clearly (macro F1 0.552 to 0.701) but stays below the linear models.
- **KNN and RBF SVM performed poorly.** A likely reason is that distance-based methods lose meaning in 1,336 dimensions of mostly sparse features. The RBF SVM also saw only 25% of the training rows and was not tuned (for example `gamma`), so its result should not be read as the best a kernel SVM could do.
- **Small classes are hardest** (stocks, market, energy, health). Tree-based models and AutoGluon had high precision but low recall on them, while the class-weighted linear models had higher recall but lower precision.
- **Most common mistake for all models:** articles from politics and technology predicted as news. These categories overlap in content.

## 8. Limitations

- Model comparison uses one 80/20 split. Stocks has only 75 validation samples (179 in test), so its scores can move noticeably between splits.
- The test set has a different class distribution from the training set (for example technology is 12% of test but about 25% of train), so accuracy and weighted F1 can differ somewhat from validation.
- AutoGluon ran with limited free RAM and finished in about 368 s of the 900 s limit with only 3 models in its leaderboard (LightGBMXT, LightGBM, WeightedEnsemble_L2). It is not a full AutoGluon run.
- The RBF SVM used a 15,000-row subsample, and no hyperparameter tuning or cross-validation was done for any model.
- Publisher/domain features were kept out of the feature matrix (see Task 4 `limitations.md`), but article text can still carry publisher style, which may help predict the category.
- Features are from Task 4 only. No new features were added in this task.

## 9. Files

| File | Description |
|---|---|
| `model_training.ipynb` | Full notebook with all code and outputs |
| `requirements.txt` | Packages used |
| `outputs/model_comparison_validation.csv` | Validation comparison table |
| `outputs/model_comparison_macro_f1.png` | Macro F1 bar chart |
| `outputs/confusion_matrix_test.png` | Test confusion matrix of LinearSVC |
| `outputs/linearsvc_final.joblib` | Final trained LinearSVC |

The AutoGluon model folder (`outputs/autogluon/`) and the virtual environment (`venv_task5/`) are excluded from Git because of their size.

## 10. How to run

Python 3.13.7, scikit-learn 1.9.1, AutoGluon 1.6.3.

```powershell
cd Task-5-Model-Training
python -m venv venv_task5
.\venv_task5\Scripts\Activate.ps1
python -m pip install -r requirements.txt
jupyter notebook model_training.ipynb
```

The `Task-4-Feature-Engineering` folder must sit next to this folder, because the notebook loads its data from `../Task-4-Feature-Engineering/`. The notebook runs top to bottom; the AutoGluon cell takes about 6 to 7 minutes and needs several GB of free RAM.