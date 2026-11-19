# RiskPredict: Hereditary Cancer Risk Prediction

A Streamlit web app that estimates a patient's hereditary cancer risk from
genetic markers (BRCA1, BRCA2, APC, TP53), family history, age, sex and
smoking. It compares a rule-based clinical score with classical and **quantum**
machine-learning models, explains what drives each prediction, and turns the
results into a plain-language summary with Google Gemini.

> **Educational project.** The ML models are trained on *synthetic* (simulated)
> patients, not real people. Nothing here is a medical diagnosis.

## Features

- **Patient form** with validation: demographics, genetic markers, family history (1st- and 2nd-degree relatives), notes and lab report upload
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

## Reproduce the data and models

Run these from the `final_app` folder:

```powershell
python -m ml.synthetic_data   # writes data/synthetic_patients.csv (2,000 patients, seed 42)
python -m ml.train            # trains all models, writes models/*.joblib + models/metrics.json (~1 min)
```

## Results (500 held-out synthetic patients)

| Model | Test AUC | 5-fold CV AUC | Brier | Sensitivity | Specificity | F1 |
|---|---|---|---|---|---|---|
| Rule-based score | 0.761 | – | 0.114 | 67% | 74% | 0.46 |
| Logistic regression | 0.781 | 0.753 | 0.104 | 59% | 88% | 0.55 |
| Random forest | **0.810** | **0.790** | 0.104 | 64% | 82% | 0.51 |
| Quantum kernel SVM | 0.756 | 0.757 | 0.108 | 53% | 91% | 0.54 |

The best AUC any model could reach on this data (using the true simulated risk) is **0.805**.
Sensitivity, specificity and F1 count a predicted risk ≥ 20% as "at risk".

**What the results show:**
- The random forest does best because it captures the gene × age interaction built into the data.
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
  final_app.py        Streamlit entry point (assessment + model comparison tabs)
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
