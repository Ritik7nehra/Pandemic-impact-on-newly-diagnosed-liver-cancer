# COVID-19 Impact on Newly Diagnosed Liver Cancer

Interactive Streamlit dashboard analyzing how the first 12 months of the COVID-19 pandemic affected newly diagnosed primary liver cancer cases referred to the Newcastle-upon-Tyne NHS Foundation Trust HPB multidisciplinary team.

## Study windows

- **Pre-pandemic:** March 2019-February 2020
- **Pandemic:** March 2020-February 2021

## Repository structure

```text
Pandemic-impact-on-newly-diagnosed-liver-cancer/
├── app.py                    # Streamlit dashboard
├── prepare_data.py           # Data cleaning and derived fields
├── generate_static_dashboard.py
├── requirements.txt
├── covid-liver.csv           # Source dataset
├── covid_liver_clean.csv     # Dashboard-ready dataset
├── data_dictionary.csv
├── liver_cancer_eda.ipynb
├── analysis_summary.md
├── static_dashboard.html     # Generated static dashboard
└── .streamlit/config.toml    # Streamlit theme
```

## Run locally

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

The cleaned dataset is already included, so the dashboard can be started immediately:

```bash
streamlit run app.py
```

## Rebuild the cleaned dataset

If the raw CSV changes, regenerate the derived dataset and data dictionary:

```bash
python prepare_data.py
```

You can also provide explicit paths:

```bash
python prepare_data.py --input covid-liver.csv --output covid_liver_clean.csv --dictionary data_dictionary.csv
```

Then restart Streamlit so the cached dataset is refreshed.

## Generate the static dashboard

```bash
python generate_static_dashboard.py
```

This creates `static_dashboard.html` in the repository root.

## Dashboard features

1. **Overview** - case volume, cancer type, presentation route, treatment mix, and cohort summary.
2. **Pandemic impact** - cohort differences in volume, presentation, tumour size, outcome, and survival.
3. **Clinical profile** - age, gender, etiology, cirrhosis, HCC BCLC stage, and ICC TNM stage.
4. **Treatment and survival** - first-line treatment, performance status, treatment timing, and quality flags.
5. **Surveillance** - programme status, effectiveness, detection mode, and time since last surveillance.
6. **Data explorer** - filters, missingness, data-quality checks, and CSV export.

## Data-quality and analysis notes

The application is intentionally descriptive. It does not impute clinical values or silently remove unusual records.

- Missing values remain missing and are shown in the data-quality view.
- Negative or unusually long diagnosis-to-treatment intervals are **flagged for review**, not deleted.
- `Cancer_Type` is derived from the available HCC and ICC staging fields. Records containing both HCC and ICC staging, or neither, are labelled `Review` rather than being forced into a cancer type.
- `Treatment_Category` groups first-line treatment into curative intent, locoregional therapy, systemic medical therapy, supportive care, not recorded, and other/review.
- Survival comparisons are descriptive. They should not be interpreted as causal effects of the pandemic because follow-up time, referral patterns, and case mix can differ between cohorts.

## Streamlit Community Cloud

Use these deployment settings:

- **Repository:** `Ritik7nehra/Pandemic-impact-on-newly-diagnosed-liver-cancer`
- **Branch:** `main`
- **Main file:** `app.py`

The required `requirements.txt` is in the repository root and the Streamlit theme is in `.streamlit/config.toml`.

## Important

The dataset contains research/clinical information. Follow the applicable data-governance, privacy, and institutional requirements when sharing or deploying the project. This dashboard is for analysis and education, not clinical decision-making.
