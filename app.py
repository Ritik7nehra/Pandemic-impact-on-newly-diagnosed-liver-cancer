from __future__ import annotations

import calendar
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "covid_liver_clean.csv"
RAW_PATH = BASE_DIR / "data" / "covid-liver.csv"

COHORT_ORDER = ["Pre-pandemic", "Pandemic"]
MONTH_ORDER = list(calendar.month_abbr[1:])
TREATMENT_ORDER = [
    "Curative intent",
    "Locoregional therapy",
    "Systemic medical therapy",
    "Supportive care",
    "Not recorded",
    "Other / review",
]
PLOT_TEMPLATE = "plotly_dark"
COLOR_SEQUENCE = ["#24f0b6", "#7c5cff", "#ffb86b", "#ff5c93", "#2dd4ff", "#f8f871", "#a3e635"]

st.set_page_config(
    page_title="COVID-19 Liver Cancer Dashboard",
    page_icon="LC",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .stApp {
        background:
            radial-gradient(circle at 10% 5%, rgba(36,240,182,0.14), transparent 26%),
            radial-gradient(circle at 90% 20%, rgba(124,92,255,0.16), transparent 28%),
            linear-gradient(135deg, #08111f 0%, #0e1726 48%, #070b14 100%);
    }
    .block-container { padding-top: 1.4rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c1728 0%, #101c2f 100%);
        border-right: 1px solid rgba(255,255,255,0.08);
    }
    h1, h2, h3 { letter-spacing: -0.03em; }
    .hero {
        padding: 1.25rem 1.4rem 1.15rem 1.4rem;
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(36,240,182,0.15), rgba(124,92,255,0.12));
        box-shadow: 0 22px 60px rgba(0,0,0,0.28);
        margin-bottom: 1.1rem;
    }
    .hero-title { font-size: 2.45rem; font-weight: 850; margin: 0; color: #f8fafc; }
    .hero-subtitle { font-size: 1.02rem; color: rgba(248,250,252,0.78); margin-top: 0.35rem; max-width: 980px; }
    .metric-card {
        border-radius: 20px;
        padding: 1.05rem 1.05rem 0.95rem 1.05rem;
        background: rgba(16,28,47,0.80);
        border: 1px solid rgba(255,255,255,0.09);
        box-shadow: 0 16px 45px rgba(0,0,0,0.25);
        min-height: 126px;
    }
    .metric-card p { margin: 0; color: rgba(248,250,252,0.68); font-size: 0.88rem; }
    .metric-card h2 { margin: 0.2rem 0 0.1rem 0; color: #f8fafc; font-size: 2.05rem; }
    .metric-card span { color: #24f0b6; font-size: 0.86rem; }
    .insight-box {
        border-left: 4px solid #24f0b6;
        padding: 0.85rem 1rem;
        background: rgba(36,240,182,0.08);
        border-radius: 14px;
        color: rgba(248,250,252,0.86);
        margin: 0.5rem 0 1rem 0;
    }
    div[data-testid="stMetric"] {
        background: rgba(16,28,47,0.68);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 0.9rem 1rem;
        border-radius: 18px;
    }
    .dataframe { font-size: 0.82rem; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        st.error("Clean data file not found. Run: python scripts/prepare_data.py")
        st.stop()
    df = pd.read_csv(DATA_PATH)
    return df


def ordered_unique(series: pd.Series, preferred: Iterable[str] | None = None) -> list[str]:
    values = [x for x in series.dropna().unique().tolist()]
    if preferred is None:
        return sorted(values)
    preferred = list(preferred)
    ordered = [x for x in preferred if x in values]
    ordered.extend(sorted([x for x in values if x not in ordered]))
    return ordered


def format_int(value: float | int) -> str:
    if pd.isna(value):
        return "-"
    return f"{int(round(value)):,}"


def format_pct(value: float | int) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.1f}%"


def format_float(value: float | int, digits: int = 1) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.{digits}f}"


def metric_card(title: str, value: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <p>{title}</p>
            <h2>{value}</h2>
            <span>{subtitle}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def base_fig_layout(fig: go.Figure, title: str | None = None) -> go.Figure:
    fig.update_layout(
        template=PLOT_TEMPLATE,
        title=dict(text=title, x=0.02, xanchor="left", font=dict(size=20)) if title else None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#eef2ff"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=70, b=40),
        hoverlabel=dict(bgcolor="#0b1220", font_size=13),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.12)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.12)")
    return fig


def count_bar(df: pd.DataFrame, x: str, color: str, title: str, barmode: str = "group") -> go.Figure:
    if df.empty:
        return base_fig_layout(go.Figure(), title)
    counts = df.groupby([x, color], dropna=False).size().reset_index(name="Cases")
    fig = px.bar(
        counts,
        x=x,
        y="Cases",
        color=color,
        barmode=barmode,
        color_discrete_sequence=COLOR_SEQUENCE,
        category_orders={"Cohort": COHORT_ORDER, "Month_Name": MONTH_ORDER, "Treatment_Category": TREATMENT_ORDER},
        text_auto=True,
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    return base_fig_layout(fig, title)


def percent_stacked_bar(df: pd.DataFrame, category: str, title: str, cohort_col: str = "Cohort") -> go.Figure:
    if df.empty:
        return base_fig_layout(go.Figure(), title)
    tmp = df.groupby([cohort_col, category], dropna=False).size().reset_index(name="Cases")
    denom = tmp.groupby(cohort_col)["Cases"].transform("sum")
    tmp["Percent"] = np.where(denom > 0, tmp["Cases"] / denom * 100, 0)
    fig = px.bar(
        tmp,
        x=cohort_col,
        y="Percent",
        color=category,
        text=tmp["Percent"].map(lambda v: f"{v:.0f}%"),
        color_discrete_sequence=COLOR_SEQUENCE,
        category_orders={"Cohort": COHORT_ORDER, "Treatment_Category": TREATMENT_ORDER},
        hover_data={"Cases": True, "Percent": ":.1f"},
    )
    fig.update_layout(yaxis_title="Percent of cases", xaxis_title="")
    fig.update_traces(textposition="inside", insidetextanchor="middle")
    return base_fig_layout(fig, title)


def monthly_trend(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return base_fig_layout(go.Figure(), "Monthly case volume")
    tmp = df.groupby(["Cohort", "Month_Order", "Month_Name"], dropna=False).size().reset_index(name="Cases")
    tmp = tmp.sort_values(["Cohort", "Month_Order"])
    fig = px.line(
        tmp,
        x="Month_Name",
        y="Cases",
        color="Cohort",
        markers=True,
        category_orders={"Month_Name": MONTH_ORDER, "Cohort": COHORT_ORDER},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig.update_traces(line=dict(width=4), marker=dict(size=10))
    fig.update_layout(xaxis_title="Month in cohort window", yaxis_title="Cases")
    return base_fig_layout(fig, "Monthly case volume by cohort")


def survival_box(df: pd.DataFrame, color: str = "Cohort") -> go.Figure:
    data = df.dropna(subset=["Survival_fromMDM"])
    if data.empty:
        return base_fig_layout(go.Figure(), "Survival from MDM")
    fig = px.box(
        data,
        x="Cohort",
        y="Survival_fromMDM",
        color=color,
        points="outliers",
        category_orders={"Cohort": COHORT_ORDER, "Treatment_Category": TREATMENT_ORDER},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig.update_layout(xaxis_title="", yaxis_title="Months")
    return base_fig_layout(fig, "Survival from MDM distribution")


def histogram(df: pd.DataFrame, column: str, title: str, labels: dict[str, str] | None = None) -> go.Figure:
    data = df.dropna(subset=[column])
    if data.empty:
        return base_fig_layout(go.Figure(), title)
    fig = px.histogram(
        data,
        x=column,
        color="Cohort",
        marginal="box",
        nbins=24,
        barmode="overlay",
        opacity=0.72,
        category_orders={"Cohort": COHORT_ORDER},
        color_discrete_sequence=COLOR_SEQUENCE,
        labels=labels,
    )
    return base_fig_layout(fig, title)


def missingness_chart(df: pd.DataFrame) -> go.Figure:
    miss = (df.isna().mean() * 100).sort_values(ascending=False).head(16).reset_index()
    miss.columns = ["Column", "Missing_Percent"]
    fig = px.bar(
        miss,
        x="Missing_Percent",
        y="Column",
        orientation="h",
        color="Missing_Percent",
        color_continuous_scale="Viridis",
        text=miss["Missing_Percent"].map(lambda v: f"{v:.1f}%"),
    )
    fig.update_layout(xaxis_title="Missing values (%)", yaxis_title="", showlegend=False)
    fig.update_yaxes(autorange="reversed")
    return base_fig_layout(fig, "Top missing-data fields")


def cohort_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cohort in COHORT_ORDER:
        sub = df[df["Cohort"] == cohort]
        if sub.empty:
            continue
        rows.append(
            {
                "Cohort": cohort,
                "Cases": len(sub),
                "HCC": int((sub["Cancer_Type_Simple"] == "HCC").sum()),
                "ICC": int((sub["Cancer_Type_Simple"] == "ICC").sum()),
                "Median age": sub["Age"].median(),
                "Median tumour size (mm)": sub["Size"].median(),
                "Median survival from MDM": sub["Survival_fromMDM"].median(),
                "Symptomatic (%)": (sub["Mode_Presentation"].eq("Symptomatic").mean() * 100),
                "Surveillance presentation (%)": (sub["Mode_Presentation"].eq("Surveillance").mean() * 100),
                "Supportive care (%)": (sub["Treatment_grps"].eq("Supportive care").mean() * 100),
            }
        )
    summary = pd.DataFrame(rows)
    return summary


def filter_data(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.title("Dashboard filters")
    st.sidebar.caption("Filter the cohort and all charts update instantly.")

    cohort_options = ordered_unique(df["Cohort"], COHORT_ORDER)
    cancer_options = ordered_unique(df["Cancer_Type_Simple"], ["HCC", "ICC", "Review"])
    gender_options = ordered_unique(df["Gender"])
    presentation_options = ordered_unique(df["Mode_Presentation"], ["Surveillance", "Incidental", "Symptomatic"])
    treatment_options = ordered_unique(df["Treatment_Category"], TREATMENT_ORDER)
    etiology_options = ordered_unique(df["Etiology"])
    cirrhosis_options = ordered_unique(df["Has_Cirrhosis"], ["Cirrhosis", "No cirrhosis", "Not recorded"])

    cohorts = st.sidebar.multiselect("Cohort", cohort_options, default=cohort_options)
    cancer_types = st.sidebar.multiselect("Cancer type", cancer_options, default=cancer_options)
    genders = st.sidebar.multiselect("Gender", gender_options, default=gender_options)
    presentations = st.sidebar.multiselect("Mode of presentation", presentation_options, default=presentation_options)
    treatments = st.sidebar.multiselect("Treatment category", treatment_options, default=treatment_options)
    etiologies = st.sidebar.multiselect("Etiology", etiology_options, default=etiology_options)
    cirrhosis = st.sidebar.multiselect("Cirrhosis status", cirrhosis_options, default=cirrhosis_options)

    min_age = int(np.nanmin(df["Age"])) if df["Age"].notna().any() else 0
    max_age = int(np.nanmax(df["Age"])) if df["Age"].notna().any() else 100
    age_range = st.sidebar.slider("Age range", min_age, max_age, (min_age, max_age))

    out = df[
        df["Cohort"].isin(cohorts)
        & df["Cancer_Type_Simple"].isin(cancer_types)
        & df["Gender"].isin(genders)
        & df["Mode_Presentation"].isin(presentations)
        & df["Treatment_Category"].isin(treatments)
        & df["Etiology"].isin(etiologies)
        & df["Has_Cirrhosis"].isin(cirrhosis)
        & df["Age"].between(age_range[0], age_range[1], inclusive="both")
    ].copy()
    return out


def render_header(df: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="hero">
            <p class="hero-title">COVID-19 impact on primary liver cancer care</p>
            <div class="hero-subtitle">
                Interactive dashboard for newly diagnosed primary liver cancer referrals to the Newcastle-upon-Tyne NHS Foundation Trust HPB MDT.
                The dashboard compares March 2019-February 2020 with March 2020-February 2021.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total_cases = len(df)
    hcc_cases = int((df["Cancer_Type_Simple"] == "HCC").sum())
    icc_cases = int((df["Cancer_Type_Simple"] == "ICC").sum())
    deaths = int((df["Alive_Dead"] == "Dead").sum())
    median_survival = df["Survival_fromMDM"].median()

    cols = st.columns(5)
    with cols[0]:
        metric_card("Cases in current selection", format_int(total_cases), "Primary liver cancer records")
    with cols[1]:
        metric_card("HCC cases", format_int(hcc_cases), f"{format_pct(hcc_cases / total_cases * 100) if total_cases else '-'} of selection")
    with cols[2]:
        metric_card("ICC cases", format_int(icc_cases), f"{format_pct(icc_cases / total_cases * 100) if total_cases else '-'} of selection")
    with cols[3]:
        metric_card("Deaths recorded", format_int(deaths), f"{format_pct(deaths / total_cases * 100) if total_cases else '-'} of selection")
    with cols[4]:
        metric_card("Median survival", f"{format_float(median_survival, 1)} mo", "From MDM")


def render_overview(df: pd.DataFrame) -> None:
    st.markdown("### Cohort overview")
    c1, c2 = st.columns([1.25, 1])
    with c1:
        st.plotly_chart(monthly_trend(df), use_container_width=True)
    with c2:
        st.plotly_chart(count_bar(df, "Cohort", "Cancer_Type_Simple", "Case mix by cohort"), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(percent_stacked_bar(df, "Mode_Presentation", "Presentation route share"), use_container_width=True)
    with c4:
        st.plotly_chart(percent_stacked_bar(df, "Treatment_Category", "Treatment category share"), use_container_width=True)

    summary = cohort_summary(df)
    if not summary.empty:
        display = summary.copy()
        for col in ["Median age", "Median tumour size (mm)", "Median survival from MDM", "Symptomatic (%)", "Surveillance presentation (%)", "Supportive care (%)"]:
            display[col] = display[col].map(lambda x: f"{x:.1f}" if pd.notna(x) else "-")
        st.dataframe(display, use_container_width=True, hide_index=True)


def render_pandemic_impact(df: pd.DataFrame) -> None:
    st.markdown("### Pandemic impact signals")
    summary = cohort_summary(df)
    if set(COHORT_ORDER).issubset(set(summary["Cohort"])):
        pre = summary[summary["Cohort"] == "Pre-pandemic"].iloc[0]
        pan = summary[summary["Cohort"] == "Pandemic"].iloc[0]
        case_change = (pan["Cases"] - pre["Cases"]) / pre["Cases"] * 100 if pre["Cases"] else np.nan
        symptomatic_change = pan["Symptomatic (%)"] - pre["Symptomatic (%)"]
        survival_change = pan["Median survival from MDM"] - pre["Median survival from MDM"]
        st.markdown(
            f"""
            <div class="insight-box">
                Cases changed from <b>{int(pre['Cases'])}</b> to <b>{int(pan['Cases'])}</b> ({case_change:.1f}%).
                Symptomatic presentation shifted by <b>{symptomatic_change:+.1f} percentage points</b> and median survival from MDM shifted by
                <b>{survival_change:+.1f} months</b> in the observed cohort. Interpret survival carefully because follow-up duration and case mix differ by cohort.
            </div>
            """,
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(percent_stacked_bar(df, "Cancer_Type_Simple", "Cancer type mix"), use_container_width=True)
    with c2:
        st.plotly_chart(percent_stacked_bar(df, "Alive_Dead", "Alive/dead outcome share"), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(histogram(df, "Size", "Tumour size distribution", labels={"Size": "Tumour size (mm)"}), use_container_width=True)
    with c4:
        st.plotly_chart(survival_box(df), use_container_width=True)


def render_clinical_profile(df: pd.DataFrame) -> None:
    st.markdown("### Clinical profile")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(histogram(df, "Age", "Age distribution", labels={"Age": "Age (years)"}), use_container_width=True)
    with c2:
        st.plotly_chart(percent_stacked_bar(df, "Gender", "Gender share"), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(percent_stacked_bar(df, "Etiology", "Etiology share"), use_container_width=True)
    with c4:
        st.plotly_chart(percent_stacked_bar(df, "Has_Cirrhosis", "Cirrhosis share"), use_container_width=True)

    hcc = df[df["Cancer_Type_Simple"] == "HCC"]
    icc = df[df["Cancer_Type_Simple"] == "ICC"]
    c5, c6 = st.columns(2)
    with c5:
        if not hcc.empty:
            st.plotly_chart(percent_stacked_bar(hcc, "HCC_BCLC_Stage", "HCC BCLC stage share"), use_container_width=True)
        else:
            st.info("No HCC cases in the current selection.")
    with c6:
        if not icc.empty:
            st.plotly_chart(percent_stacked_bar(icc, "ICC_TNM_Stage", "ICC TNM stage share"), use_container_width=True)
        else:
            st.info("No ICC cases in the current selection.")


def render_treatment_survival(df: pd.DataFrame) -> None:
    st.markdown("### Treatment and survival")
    c1, c2 = st.columns([1.1, 1])
    with c1:
        tx_counts = df.groupby(["Treatment_grps", "Cohort"], dropna=False).size().reset_index(name="Cases")
        fig = px.bar(
            tx_counts,
            x="Cases",
            y="Treatment_grps",
            color="Cohort",
            barmode="group",
            orientation="h",
            color_discrete_sequence=COLOR_SEQUENCE,
            category_orders={"Cohort": COHORT_ORDER},
            text_auto=True,
        )
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(base_fig_layout(fig, "First-line treatment counts"), use_container_width=True)
    with c2:
        st.plotly_chart(survival_box(df, color="Treatment_Category"), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(percent_stacked_bar(df, "PS", "Performance status share"), use_container_width=True)
    with c4:
        st.plotly_chart(histogram(df, "Time_MDM_1st_treatment", "MDM to first treatment", labels={"Time_MDM_1st_treatment": "Months"}), use_container_width=True)

    unusual = df["Diagnosis_to_Treatment_Flag"].value_counts(dropna=False).rename_axis("Flag").reset_index(name="Cases")
    st.caption("Treatment interval quality flags are shown to avoid over-interpreting negative or extreme interval values in the raw file.")
    st.dataframe(unusual, use_container_width=True, hide_index=True)


def render_surveillance(df: pd.DataFrame) -> None:
    st.markdown("### Surveillance pathway")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(percent_stacked_bar(df, "Surveillance_programme", "Formal surveillance programme"), use_container_width=True)
    with c2:
        st.plotly_chart(percent_stacked_bar(df, "Surveillance_effectiveness", "Surveillance effectiveness"), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(percent_stacked_bar(df, "Mode_of_surveillance_detection", "Mode of surveillance detection"), use_container_width=True)
    with c4:
        st.plotly_chart(histogram(df, "Months_from_last_surveillance", "Months from last surveillance", labels={"Months_from_last_surveillance": "Months"}), use_container_width=True)

    inc = df[df["Mode_Presentation"] == "Incidental"]
    if not inc.empty:
        st.plotly_chart(percent_stacked_bar(inc, "Type_of_incidental_finding", "Type of incidental finding among incidental presentations"), use_container_width=True)


def render_data_explorer(df: pd.DataFrame, full_df: pd.DataFrame) -> None:
    st.markdown("### Data explorer and quality checks")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.plotly_chart(missingness_chart(df), use_container_width=True)
    with c2:
        quality = pd.DataFrame(
            {
                "Metric": [
                    "Rows in current selection",
                    "Columns",
                    "Duplicate rows",
                    "Rows with review cancer type",
                    "Rows with negative diagnosis-to-treatment interval",
                ],
                "Value": [
                    len(df),
                    df.shape[1],
                    int(df.duplicated().sum()),
                    int((df["Cancer_Type_Simple"] == "Review").sum()),
                    int((df["Diagnosis_to_Treatment_Flag"] == "Negative interval - review").sum()),
                ],
            }
        )
        st.dataframe(quality, use_container_width=True, hide_index=True)
        st.download_button(
            label="Download filtered data as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="filtered_liver_cancer_data.csv",
            mime="text/csv",
        )

    default_columns = [
        "Cohort",
        "Month_Name",
        "Cancer_Type_Simple",
        "Age",
        "Gender",
        "Mode_Presentation",
        "Etiology",
        "Cirrhosis",
        "Size",
        "Stage_Group",
        "Treatment_grps",
        "Survival_fromMDM",
        "Alive_Dead",
    ]
    chosen = st.multiselect("Columns to display", full_df.columns.tolist(), default=[c for c in default_columns if c in full_df.columns])
    st.dataframe(df[chosen] if chosen else df, use_container_width=True, hide_index=True)


def main() -> None:
    df = load_data()
    filtered = filter_data(df)
    render_header(filtered)

    if filtered.empty:
        st.warning("No records match the current filters. Adjust the sidebar filters to continue.")
        return

    tabs = st.tabs([
        "Overview",
        "Pandemic impact",
        "Clinical profile",
        "Treatment and survival",
        "Surveillance",
        "Data explorer",
    ])
    with tabs[0]:
        render_overview(filtered)
    with tabs[1]:
        render_pandemic_impact(filtered)
    with tabs[2]:
        render_clinical_profile(filtered)
    with tabs[3]:
        render_treatment_survival(filtered)
    with tabs[4]:
        render_surveillance(filtered)
    with tabs[5]:
        render_data_explorer(filtered, df)

    st.caption(
        "Note: This dashboard is descriptive and intended for project analysis, not clinical decision-making. Missing fields are left as missing; no clinical imputation is performed."
    )


if __name__ == "__main__":
    main()
