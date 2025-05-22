import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from src.utils import get_all_datasets, get_dataset
from src.models.llms import load_llm

st.set_page_config(page_title="📂 Dataset Details", layout="wide")
st.title("📂 Dataset Details")

llm = load_llm("gpt-3.5-turbo")

# ---------- Helper functions ----------
def safe_read_csv(file_path):
    for enc in ['utf-8', 'ISO-8859-1', 'utf-16', 'cp1252']:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Unable to decode file with common encodings.")

def analyze_column(col_name, series):
    info = {'name': col_name, 'dtype': str(series.dtype), 'missing_pct': series.isna().mean() * 100, 'unique': series.nunique()}
    if pd.api.types.is_numeric_dtype(series):
        desc = series.describe()
        info.update({
            'min': desc['min'], 'max': desc['max'], 'mean': desc['mean'],
            'median': series.median(), 'std': desc['std'],
            'outliers': ((series < (desc['25%'] - 1.5*(desc['75%'] - desc['25%']))) | (series > (desc['75%'] + 1.5*(desc['75%'] - desc['25%'])))).sum(),
            'type': 'Numeric'
        })
    elif series.nunique() == 2:
        info['type'] = 'Boolean'
    elif info['unique'] == len(series):
        info['type'] = 'ID'
    elif info['unique'] <= 20:
        info['type'] = 'Category'
    else:
        info['type'] = 'Text'
    return info

def guess_column_semantic_llm(col_name):
    prompt = f"What is the semantic type or meaning of a column named '{col_name}' in a dataset? Answer in 3-5 words."
    return llm.predict(prompt)

@st.cache_data(show_spinner=False)
def get_cleaning_suggestions(col_stats):
    cols_description = "\n".join([
        f"Column: {col['name']} | Type: {col['dtype']} | Missing: {col['missing_pct']:.2f}%" for col in col_stats
    ])
    prompt = f"""
Given the following summary of columns in a dataset:
{cols_description}

Please suggest a cleaning plan with the following rules:
- Drop columns only if missing percentage > 50%.
- For columns with missing values ≤ 50%:
    - If numeric: fill using median.
    - If categorical: fill using mode.
- Only remove outliers from columns with numeric data that have no missing values.
- Normalize numeric columns only if they are not filled or outlier-removed, and max value is much greater than 1.
- Do not apply more than two cleaning steps on the same column.
- Group columns logically and explain briefly in comments.

Return the plan as a clear bullet list.
"""
    return llm.predict(prompt)

@st.cache_data(show_spinner=False)
def refine_cleaning_strategy(user_input, base_plan):
    prompt = f"""
Current cleaning plan:
{base_plan}

User wants to: {user_input}

Update the cleaning plan accordingly.
"""
    return llm.predict(prompt)

@st.cache_data(show_spinner=False)
def generate_cleaning_code_from_plan(plan):
    prompt = f"""
Convert the following cleaning plan into valid Python code using pandas.
Only return Python code that can be executed directly in Python.
Assume the dataframe is named `df`.

Before applying `.str` methods (e.g. `.str.replace`), always check the column's dtype like this:
if df[\"column_name\"].dtype == \"object\":
    df[\"column_name\"] = df[\"column_name\"].str.replace(",", "").astype(float)

Also ensure any strings like '1,000' or '2,500.50' are converted to numeric values before further cleaning.

Cleaning Plan:
{plan}
"""
    return llm.predict(prompt)

def extract_valid_code(llm_response):
    match = re.search(r"```(?:python)?\n(.*?)```", llm_response.strip(), re.DOTALL)
    if match:
        return match.group(1)
    lines = llm_response.splitlines()
    code_lines = [line for line in lines if line.strip() and not line.strip().startswith("#")]
    return "\n".join(code_lines)

def generate_insight(info):
    if info['type'] == 'ID':
        return "🔹 This is a unique identifier column."
    if info['missing_pct'] > 0:
        return f"⚠️ {info['missing_pct']:.1f}% missing values."
    if 'std' in info and info['std'] < 1e-3:
        return "⚠️ Very low variance."
    if info['unique'] < 5 and info['type'] == 'Category':
        return "ℹ️ Category with <5 distinct values."
    return "✅ No major issues detected."

def plot_distribution(col_name, series):
    fig, ax = plt.subplots()
    if pd.api.types.is_numeric_dtype(series):
        ax.hist(series.dropna(), bins=20, color='#69b3a2')
        ax.set_xlabel(col_name)
        ax.set_ylabel('Frequency')
    else:
        vc = series.fillna("NaN").value_counts().head(20)
        ax.bar(vc.index.astype(str), vc.values, color='#8c54ff')
        ax.set_xticklabels(vc.index, rotation=45, ha='right')
        ax.set_ylabel('Count')
    ax.set_title(f"Distribution: {col_name}")
    st.pyplot(fig)

def fix_numeric_strings(df):
    for col in df.select_dtypes(include='object').columns:
        if df[col].dropna().apply(lambda x: isinstance(x, str)).all():
            try:
                df[col] = df[col].str.replace(',', '', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception as e:
                print(f"Failed to clean column {col}: {e}")
    return df

def show_skew_kurtosis(df, cleaned_df):
    raw_cols = df.select_dtypes(include='number').columns
    clean_cols = cleaned_df.select_dtypes(include='number').columns
    numeric_cols = list(set(raw_cols).intersection(set(clean_cols)))

    if not numeric_cols:
        st.info("No common numeric columns available for skewness/kurtosis report.")
        return

    report = pd.DataFrame(index=numeric_cols)
    report['Skew (Before)'] = df[numeric_cols].skew()
    report['Kurtosis (Before)'] = df[numeric_cols].kurtosis()
    report['Skew (After)'] = cleaned_df[numeric_cols].skew()
    report['Kurtosis (After)'] = cleaned_df[numeric_cols].kurtosis()
    st.dataframe(report.round(2), use_container_width=True)

    st.markdown("### 📊 Visualization")

    fig1, ax1 = plt.subplots()
    report[['Skew (Before)', 'Skew (After)']].plot(kind='bar', ax=ax1)
    ax1.set_title('Skewness Before vs After Cleaning')
    ax1.set_ylabel('Skewness')
    ax1.set_xlabel('Feature')
    ax1.legend()
    st.pyplot(fig1)

    try:
        insight1 = llm.predict(f"""
Interpret this skewness bar chart comparing before vs after cleaning:
{report[['Skew (Before)', 'Skew (After)']].to_markdown()}
""")
        st.markdown("#### 🤖 Insight on Skewness")
        st.info(insight1)
    except Exception:
        st.warning("Failed to interpret skewness chart via LLM.")

    fig2, ax2 = plt.subplots()
    report[['Kurtosis (Before)', 'Kurtosis (After)']].plot(kind='bar', ax=ax2)
    ax2.set_title('Kurtosis Before vs After Cleaning')
    ax2.set_ylabel('Kurtosis')
    ax2.set_xlabel('Feature')
    ax2.legend()
    st.pyplot(fig2)

    try:
        insight2 = llm.predict(f"""
Interpret this kurtosis bar chart comparing before vs after cleaning:
{report[['Kurtosis (Before)', 'Kurtosis (After)']].to_markdown()}
""")
        st.markdown("#### 🤖 Insight on Kurtosis")
        st.info(insight2)
    except Exception:
        st.warning("Failed to interpret kurtosis chart via LLM.")

    try:
        interpretation = llm.predict(f"""
Please analyze the following:
1. The skewness and kurtosis table below.
2. The bar charts comparing before vs after cleaning.

Then provide:
- An interpretation of how cleaning affected distribution symmetry and tail behavior.
- An evaluation of whether the cleaned data is now more suitable for statistical analysis.
- Suggested next steps if improvements are still needed.

Data summary:
{report.to_markdown()}
""")
        st.markdown("### 📘 Interpretation by LLM")
        st.write(interpretation)
    except Exception:
        st.warning("Failed to interpret the report via LLM.")




# Load Dataset and Display Tabs
datasets = get_all_datasets()
if datasets:
    selected = st.selectbox("Select dataset:", [f"{d[0]} - {d[1]}" for d in datasets])
    dataset_id = int(selected.split(" - ")[0])
    dataset = get_dataset(dataset_id)
    df = safe_read_csv(dataset[2])
    st.markdown(f"### Dataset: `{dataset[1]}` — {df.shape[0]} rows × {df.shape[1]} columns")

    tab1, tab2, tab3 = st.tabs(["📊 Overview", "🧼 Cleaning", "📈 Skewness & Kurtosis"])

    with tab1:
        for col in df.columns:
            with st.container():
                stats = analyze_column(col, df[col])
                st.markdown(f"#### 📌 {col}")
                cols = st.columns([2, 3])
                with cols[0]:
                    st.markdown(f"**Type:** `{stats['type']}`")
                    if 'min' in stats:
                        st.markdown(f"- Min: `{stats['min']}`")
                        st.markdown(f"- Max: `{stats['max']}`")
                        st.markdown(f"- Mean: `{stats['mean']:.2f}`")
                        st.markdown(f"- Median: `{stats['median']}`")
                        st.markdown(f"- Std: `{stats['std']:.2f}`")
                        st.markdown(f"- Outliers: `{stats['outliers']}`")
                    st.markdown(f"- Unique: `{stats['unique']}`")
                    st.markdown(f"- Missing: `{stats['missing_pct']:.2f}%`")
                    st.info(generate_insight(stats))
                with cols[1]:
                    plot_distribution(col, df[col])
            st.markdown("---")

    with tab2:
        col_stats = [dict(analyze_column(col, df[col]), semantic=guess_column_semantic_llm(col)) for col in df.columns]
        summary_df = pd.DataFrame([{**c, 'Missing %': f"{c['missing_pct']:.2f}"} for c in col_stats])
        st.session_state.col_stats = col_stats
        st.session_state.summary_df = summary_df

        st.dataframe(summary_df[['name', 'dtype', 'semantic', 'type', 'unique', 'Missing %']])
        base_plan = get_cleaning_suggestions(col_stats)
        st.session_state.base_cleaning_plan = base_plan
        st.markdown("### 🧼 Cleaning Plan")
        st.markdown(base_plan)

        if st.toggle("🛠 Customize Cleaning Plan"):
            user_input = st.text_input("✍️ Modify the cleaning plan:")
            if user_input:
                st.session_state.base_cleaning_plan = refine_cleaning_strategy(user_input, base_plan)
                st.rerun()

        code_raw = generate_cleaning_code_from_plan(st.session_state.base_cleaning_plan)
        code_clean = extract_valid_code(code_raw)
        st.session_state.code_clean = code_clean
        with st.expander("🧪 Raw Cleaning Code (debug)"):
            st.code(code_raw, language="markdown")

        try:
            exec_globals = {'df': df.copy(), 'pd': pd, 'np': np, 'fix_numeric_strings': fix_numeric_strings}
            exec("df = fix_numeric_strings(df)\n" + code_clean, exec_globals)
            cleaned_df = exec_globals['df']

            # Chỉ khi không lỗi mới gán vào session_state
            st.session_state.cleaned_df = cleaned_df
            st.session_state.raw_df = df

            st.markdown("### ✅ Cleaned Data Preview")
            st.dataframe(cleaned_df.head())

        except Exception as e:
            st.error(f"Error while executing cleaning code: {e}")
            st.code(code_clean, language="python")

        if 'cleaned_df' in st.session_state:
            st.download_button(
                label="🧹 Clean & Export",
                data=st.session_state.cleaned_df.to_csv(index=False).encode('utf-8'),
                file_name="cleaned_dataset.csv",
                mime="text/csv"
            )

            with st.expander("🧾 Python Code Used"):
                st.code(code_clean, language="python")




    with tab3:
        st.markdown("### 📈 Skewness & Kurtosis Report")
        if "cleaned_df" in st.session_state and "raw_df" in st.session_state:
            show_skew_kurtosis(st.session_state.raw_df, st.session_state.cleaned_df)
        else:
            st.info("Please run cleaning in the '🧼 Cleaning' tab first.")
else:
    st.warning("No datasets found. Please upload one in the Dashboard.")
