# Analysis Summary: COVID-19 and Primary Liver Cancer Referrals

## Objective

Assess the descriptive impact of the COVID-19 pandemic on newly diagnosed primary liver cancer cases in the uploaded dataset.

## Dataset snapshot

- Records: 450
- Cohorts: pre-pandemic and pandemic
- Main clinical endpoints in the dashboard: cancer type, presentation route, stage, treatment, survival from MDM, alive/dead status, surveillance pathway, and treatment timing.

## Data preparation decisions

1. The raw CSV uses Windows-1252 encoding, so the preparation script reads the file with a fallback encoding strategy.
2. The raw cohort label `Prepandemic` is standardized to `Pre-pandemic`; `Pandemic` is retained.
3. `Cancer_Type` is derived from staging fields:
   - HCC if HCC TNM or BCLC staging is present without ICC staging.
   - ICC if ICC TNM staging is present without HCC staging.
   - Review if both or neither are present.
4. Missing clinical fields are not imputed.
5. Negative or extreme diagnosis-to-treatment intervals are flagged for review rather than dropped.

## Descriptive findings

### Case volume

The cohort includes 266 pre-pandemic cases and 184 pandemic-period cases. This is a 30.8% lower case volume during the first pandemic year.

### Cancer type

Using derived cancer type:

- HCC decreased from 190 to 120 cases.
- ICC decreased from 74 to 64 cases.
- Two pre-pandemic records require review because staging is conflicting or missing.

### Presentation

The presentation route changed notably:

- Symptomatic presentation increased from 38.7% to 53.3%.
- Surveillance presentation decreased from 26.7% to 17.9%.
- Incidental presentation decreased from 34.6% to 28.8%.

### Treatment

Supportive care remained the most common first-line treatment in both cohorts. Curative-intent treatment share was similar overall, but detailed interpretation should account for cancer type, stage, performance status, and missing treatment-timing data.

### Survival

Median survival from MDM was 15.6 months pre-pandemic and 9.2 months during the pandemic in the observed dataset. This should be interpreted as descriptive because survival depends on follow-up time, censoring, cancer type, stage, treatment, and performance status.

## Recommended project extensions

- Add statistical testing for cohort differences in presentation, stage, and treatment.
- Build a survival analysis model with censoring if exact follow-up/censoring definitions are available.
- Validate ambiguous records against the original clinical source.
- Add an exportable PDF report for stakeholders.
