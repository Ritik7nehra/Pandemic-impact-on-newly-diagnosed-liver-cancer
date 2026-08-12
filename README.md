# COVID-19 Primary Liver Cancer Dashboard Project

This project analyzes how the first 12 months of the COVID-19 pandemic affected newly diagnosed primary liver cancer cases referred to the Newcastle-upon-Tyne NHS Foundation Trust HPB multidisciplinary team.

The source dataset compares:

- **Pre-pandemic:** March 2019 to February 2020
- **Pandemic:** March 2020 to February 2021

The dashboard is designed for descriptive analysis of case volume, presentation route, cancer type, stage, surveillance, treatment, and survival from MDM.

## Project structure

```text
covid_liver_cancer_dashboard/
├── app.py                              # Interactive Streamlit dashboard
├── requirements.txt                    # Python dependencies
├── data/
│   ├── covid-liver.csv                 # Raw uploaded dataset
│   ├── covid_liver_clean.csv           # Cleaned dataset with derived fields
│   └── data_dictionary.csv             # Source + derived column descriptions
├── scripts/
│   ├── prepare_data.py                 # Data cleaning and feature derivation
│   └── generate_static_dashboard.py    # Generates reports/static_dashboard.html
├── reports/
│   ├── static_dashboard.html           # Open directly in a browser
│   └── analysis_summary.md             # Written summary of findings
├── notebooks/
│   └── liver_cancer_eda.ipynb          # Reproducible EDA notebook
└── .streamlit/config.toml              # Dashboard theme
```

## How to run the interactive dashboard

From inside the project folder:

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Regenerate the cleaned data and static dashboard

```bash
python scripts/prepare_data.py --input data/covid-liver.csv --output data/covid_liver_clean.csv --dictionary data/data_dictionary.csv
python scripts/generate_static_dashboard.py
```

The static dashboard will be written to:

```text
reports/static_dashboard.html
```

## Important data note

The uploaded data dictionary describes `Cancer` as a Y/N flag, but the rows with `Cancer = N` mostly contain ICC TNM staging, while rows with `Cancer = Y` contain HCC staging. Therefore, the project uses a derived `Cancer_Type` field based on HCC and ICC staging columns. Cases with conflicting or missing staging are labelled as `Review` rather than removed.

## Dashboard pages

1. **Overview:** case volume, cancer type, presentation route, treatment category.
2. **Pandemic impact:** cohort-level shifts in volume, presentation, tumour size, and survival.
3. **Clinical profile:** age, gender, etiology, cirrhosis, HCC/ICC stage.
4. **Treatment and survival:** first-line therapy, treatment category, survival distribution, treatment interval flags.
5. **Surveillance:** surveillance programme, effectiveness, detection mode, months since last surveillance.
6. **Data explorer:** filtered table, data-quality metrics, missingness chart, CSV export.

## Descriptive headline findings in the uploaded dataset

- Total records: **450** primary liver cancer cases.
- Case volume declined from **266** pre-pandemic to **184** during the pandemic, a **30.8% decrease**.
- HCC cases declined from **190** to **120**, while ICC cases declined from **74** to **64** based on derived staging fields.
- Symptomatic presentation increased from **38.7%** to **53.3%** of cases.
- Surveillance presentation decreased from **26.7%** to **17.9%** of cases.
- Median survival from MDM shifted from **15.6** to **9.2** months in the observed cohort. This is descriptive and should not be interpreted causally without accounting for follow-up time and case mix.

## Cautions -

- The dataset is observational and referral-based.
- Missing values are common in surveillance and treatment-timing fields.
- Negative or extreme treatment intervals are flagged, not deleted.
- Survival comparisons are descriptive because follow-up windows and case mix can differ.
- This project is for analysis and education, not clinical decision-making.
