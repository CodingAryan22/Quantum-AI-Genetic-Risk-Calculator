# RiskPredict: Hereditary Cancer Risk Prediction

A Streamlit web app that estimates a patient's hereditary cancer risk from
genetic markers (BRCA1, BRCA2, APC, TP53), family history, age, sex and
smoking. It compares a rule-based clinical score with classical and **quantum**
machine-learning models, explains what drives each prediction, and turns the
results into a plain-language summary with Google Gemini.

> **Educational project.** The ML models are trained on *synthetic* (simulated)
> patients, not real people. Nothing here is a medical diagnosis.

## Features

- **Six pages** in a sidebar menu: Home, New assessment, Results (Overview / Models / Details tabs), Patient records, Model comparison, About & method
- **3-step patient form** (Demographics → Markers & history → Notes): Next unlocks only when the step is complete
- **Lab report reader:** upload a PDF genetic test report and the genes it reports (pathogenic, VUS, negative) are found automatically and can be applied to the form. Try `samples/sample_lab_report.pdf` (fictional). Scanned image-only PDFs can't be read.
- **Patient records in MongoDB:** every assessment is saved; the records page lists patients with their risk history and linked diseases
- **Rule-based score** with 1,500-run **Monte Carlo** uncertainty (mean and 90% interval)
- **Three trained models** predicting 20-year risk:
  - Logistic regression
  - Random forest
  - **Quantum kernel SVM**: 9-qubit Qiskit ZZ feature map with a state-fidelity kernel
- **Explainability:** exact per-patient factor contributions from the logistic regression
- **Model comparison tab:** AUC, cross-validated AUC, Brier score, sensitivity, specificity, F1, ROC curves, timings, feature importance
- **Privacy:** the AI only receives de-identified data (no name, age band instead of exact age, emails, phone numbers and IDs scrubbed from notes)
- **PDF report export**, dark mode, mobile layout

## Run it

```powershell
pip install -r requirements.txt
cd final_app
streamlit run final_app.py
```

For the AI summary, put your key in `final_app/.streamlit/secrets.toml`, or set it as the `GEMINI_API_KEY` environment variable:

```toml
GEMINI_API_KEY = "your-key"
```

`secrets.toml` is git-ignored. The rest of the app works without a key.

**Gemini limits.** The free tier allows about 20 requests per day per model. The app tries
`gemini-2.5-flash` first, then `gemini-flash-lite-latest` (a separate quota). If both are
unavailable it writes a standard summary from the results instead, labels it clearly, and
offers a **Retry AI summary** button. To change the order, add
`GEMINI_MODELS = "model-a,model-b"` to `secrets.toml`.

## Database (MongoDB)

Every generated assessment is saved to MongoDB, in the `assessments` collection of the
`riskpredict` database (one document per assessment, grouped into patients by name).

**Local MongoDB (default).** Install [MongoDB Community Server](https://www.mongodb.com/try/download/community)
and make sure it's running. On Windows it runs as the "MongoDB" service. The app connects to
`mongodb://localhost:27017` automatically; nothing to configure.

**MongoDB Atlas (cloud).** Create a free cluster, add a database user, allow your IP under
*Network Access*, copy the connection string, and add it to `final_app/.streamlit/secrets.toml`:

```toml
MONGODB_URI = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/"
MONGODB_DB = "riskpredict"   # optional, this is the default
```

**No database?** If MongoDB can't be reached, the app keeps working and saves records to
`final_app/data/patient_records.json` instead (git-ignored); the Patient records page shows
which storage is in use. To browse the data directly, use MongoDB Compass with the same URI.

## Reproduce the data and models

Run these from the `final_app` folder:

```powershell
python -m ml.synthetic_data   # writes data/synthetic_patients.csv (2,000 patients, seed 42)
python -m ml.train            # trains all models, writes models/*.joblib + models/metrics.json (~1 min)
```

## Results (500 held-out synthetic patients)

| Model | Test AUC (95% CI) | 5-fold CV AUC | Brier | Sensitivity | Specificity | F1 |
|---|---|---|---|---|---|---|
| Rule-based score | 0.761 (0.695–0.823) | – | 0.114 | 67% | 74% | 0.46 |
| Logistic regression | 0.781 (0.718–0.835) | 0.753 | 0.104 | 59% | 88% | 0.55 |
| Random forest | **0.810** (0.753–0.862) | **0.790** | 0.104 | 64% | 82% | 0.51 |
| Quantum kernel SVM | 0.755 (0.688–0.816) | 0.757 | 0.108 | 53% | 91% | 0.54 |

**Are the differences real?** A paired bootstrap (2,000 resamples of the test patients,
every model scored on the same resample) gives a 95% interval for each AUC gap:

| Random forest vs | AUC gap | 95% interval | p | Verdict |
|---|---|---|---|---|
| Quantum kernel SVM | +0.055 | +0.018 to +0.096 | < 0.001 | real difference |
| Rule-based score | +0.050 | +0.006 to +0.090 | 0.023 | real difference |
| Logistic regression | +0.030 | −0.010 to +0.066 | 0.127 | could be chance |

The best AUC any model could reach on this data (using the true simulated risk) is **0.805**.
Sensitivity, specificity and F1 count a predicted risk ≥ 20% as "at risk".

**What the results show:**
- The random forest does best because it captures the gene × age interaction built into the data. Its lead over the quantum model and the rule-based score is statistically real; its lead over logistic regression is not (the interval includes zero).
- The quantum kernel SVM is competitive with logistic regression, but it doesn't beat the classical models.
- Cross-validation picked very small rotation angles for the quantum model. That's when its kernel behaves most like a smooth classical kernel, which matches published findings that quantum kernels rarely help on small, low-dimensional tabular data.

## How the synthetic data is made

See `final_app/ml/synthetic_data.py` for the full description. In short:

1. **Lifetime risk to age 80** for each gene and sex comes from published figures: NCI (BRCA1/2), GeneReviews (APC, TP53) and SEER (general population).
2. **Assumed multipliers** (not published effect sizes) are applied for family history and smoking.
3. A **Weibull age-of-onset curve** turns lifetime risk into the risk over the next 20 years. Carriers develop cancer earlier.
4. Each outcome (0/1) is drawn at random from that risk.
5. The cohort is enriched with mutation carriers (about 18%), like a genetics-clinic population.

## Project structure

```
final_app/
  final_app.py        Streamlit entry point: sidebar navigation, theme
  views.py            pages: Home, New assessment, Results, Patient records, Model comparison, About
  storage.py          saves assessments to MongoDB (local JSON file if MongoDB is unavailable)
  data_manager.py     patient form and validation
  quantum_engine.py   rule-based score + Monte Carlo uncertainty simulation
  ai_synthesizer.py   de-identified Gemini prompt and summary
  pdf_builder.py      PDF report
  ui_modules.py       theme, cards, charts, tables
  features.py         marker status normalisation
  ml/
    schema.py         the 9 model features; form -> feature vector
    synthetic_data.py synthetic cohort generator
    quantum_kernel.py Qiskit feature map, fidelity kernel, QuantumKernelSVM
    train.py          training, evaluation, metrics.json
    predictor.py      loads models, predicts and explains one patient
  data/               synthetic_patients.csv
  models/             trained models + metrics.json
tests/                pytest suite (run: python -m pytest tests)
archive/              earlier prototypes, kept for reference
.github/workflows/    CI: runs the tests on every push
```

## Tests

```powershell
python -m pytest -q tests
```

The suite covers:
- form validation
- the Monte Carlo simulation
- PDF text cleanup
- feature encoding
- synthetic data
- the quantum kernel (symmetric, positive semi-definite)
- end-to-end training
- that the saved models load and predict sensibly
- that the explanations add up exactly to the prediction
- that the Gemini prompt contains no identifiers
