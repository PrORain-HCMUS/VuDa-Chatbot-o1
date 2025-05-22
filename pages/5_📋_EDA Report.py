import streamlit as st
import pandas as pd
import os
from datetime import datetime
from src.utils import init_db, add_dataset, get_all_datasets, delete_dataset, rename_dataset, safe_read_csv
from pygwalker.api.streamlit import StreamlitRenderer
import matplotlib.pyplot as plt
import seaborn as sns
import json
import textwrap

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

st.set_page_config(page_title="EDA Report", layout="wide")
st.title("🧠 Exploratory Data Analysis (EDA) Report")

# LangChain LLM setup
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

def generate_eda_report_with_llm(df):
    prompt = f"""
You are a professional data analyst. Given a dataset `df`, perform an in-depth exploratory data analysis (EDA) and return your findings in JSON. Your response **must** be valid JSON with the following fields:

1. introduction: Markdown introduction about dataset size and types.
2. data_quality: Description of missing values, duplicates, and column quality.
3. univariate: A list where each element is a dictionary with the following fields:
   - insight: One-sentence description of what the column represents and what makes it interesting.
   - code: Python matplotlib or seaborn code to visualize the column. Use best-practice chart types:
       - For numeric columns: use `sns.histplot(df['col'], bins=30, kde=True)`
       - For categorical columns: if `nunique <= 20`, use `sns.countplot`; else use barplot for top 10 values.
       - Skip columns with more than 100 unique values.
   - insight_after_chart: A brief markdown explanation of the chart. Mention distribution shape (e.g., right-skewed, symmetric), any outliers, or dominant categories. Be concise but meaningful.
4. correlation: A dictionary with the following keys:
- "insight": A paragraph describing the purpose of correlation analysis, what variables are expected to correlate, and which relationships are most interesting to explore.
- "code": Python code using seaborn or matplotlib to generate a correlation heatmap of all numerical columns in the dataset. Use `sns.heatmap(df.corr(), annot=True, cmap='coolwarm')` and add an informative title.
- "insight_after_chart": A detailed interpretation of the heatmap. Include:
    - Mention of the strongest positive and negative correlations (with variable names).
    - Whether any correlations are unexpected or counterintuitive.
    - Any variables that appear unrelated to others (low correlation across the board).
    - A short conclusion about how correlation insights can support downstream tasks (e.g., prediction, feature selection).
5. insights: List of bullet insights
6. recommendations: List of recommendations

Make sure your output is JSON only and properly escaped.

Dataset Metadata Preview:
- Head:
{df.head().to_json(orient="records")}
- Missing values:
{df.isnull().sum()[df.isnull().sum() > 0].to_dict()}
- Dtypes:
{df.dtypes.astype(str).to_dict()}
- Description:
{df.describe().to_dict()}
"""

    response = llm([HumanMessage(content=prompt)]).content

    try:
        report = json.loads(response)
        return report
    except json.JSONDecodeError:
        st.error("❌ LLM response is not valid JSON. Below is the raw output:")
        st.code(response)
        raise

def generate_final_summary_prompt(sections):
    return textwrap.dedent("""
        You are a senior data analyst tasked with writing a detailed, professional final EDA report for a dataset of student performance.
        Your report will be shown directly to stakeholders (e.g., school administrators, data science teams) so it must be comprehensive, insightful, and written in fluent natural language.

        Structure the report in well-formatted markdown with the following sections:

        ## 📘 Introduction
        Summarize the dataset contents (number of rows, columns, types of data), and its purpose. Include a preview table.

        ## 🧼 Data Quality
        Comment on missing values, duplicate records, and overall reliability. Describe any data cleaning needed or already done.

        ## 🔍 Univariate Analysis
        Summarize key patterns found in individual columns, especially numeric ones. Mention distributions, common values, and outliers.
        Include references to charts like histograms or bar charts, and place each chart directly after its related point. Ensure insights and related charts appear together in rendering.

        ## 📊 Correlation Insights
        Describe the key relationships discovered between pairs of variables. Interpret the heatmap and point out strong/weak correlations. Provide real-world implications. Show the correlation heatmap near the description.

        ## 💡 Final Insights & Recommendations
        Summarize your conclusions about student behavior and performance.
        Offer practical recommendations (e.g., data improvement, focus areas, policy suggestions).

        Use markdown only. No bullet lists unless summarizing final actions.
        Length: around 600-800 words.
        Tone: analytical, structured, helpful for stakeholders.
    """) + f"""

Context:
- Introduction: {sections['introduction']}
- Data Quality: {sections['data_quality']}
- Univariate: {[b['insight_after_chart'] for b in sections['univariate'] if 'insight_after_chart' in b]}
- Correlation: {sections['correlation']['insight_after_chart']}
- Key Insights: {sections['insights']}
- Recommendations: {sections['recommendations']}
"""

init_db()

# Load all datasets
datasets = get_all_datasets()
if not datasets:
    st.warning("Please upload a dataset in the Dashboard first.")
    st.stop()

# Dataset selection
dataset_options = {f"{d[0]} - {d[1]}": d for d in datasets}
selected = st.selectbox("Select dataset to generate report:", list(dataset_options.keys()))
dataset_id, name, rows, cols, uploaded, _ = dataset_options[selected]
file_path = os.path.join("data", "uploads", name)
df = safe_read_csv(file_path)

# Call LLM-generated EDA content
tabs = st.tabs(["📘 Introduction", "🧼 Data Quality", "🔍 Univariate", "📊 Correlation", "💡 Insights", "📄 Full Report"])
eda_sections = generate_eda_report_with_llm(df)

# --- 📘 Introduction ---
with tabs[0]:
    st.markdown(eda_sections['introduction'])
    st.subheader("📌 Dataset Preview")
    st.dataframe(df.head(10))

# --- 🧼 Data Quality ---
with tabs[1]:
    st.markdown(eda_sections['data_quality'])
    st.subheader("Missing Values")
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        st.dataframe(missing)
    else:
        st.success("No missing values detected.")
    st.subheader("Duplicate Rows")
    st.write(f"Number of duplicate rows: **{df.duplicated().sum()}**")

    # Detailed per-column analysis
    st.subheader("🔎 Column-wise Analysis")
    for col in df.columns:
        st.markdown(f"### 📌 `{col}`")
        col_data = df[col]
        st.write(f"- Data type: `{col_data.dtype}`")
        st.write(f"- Missing values: `{col_data.isnull().sum()}` ({col_data.isnull().mean():.2%})")

        if pd.api.types.is_numeric_dtype(col_data):
            desc = col_data.describe()
            st.dataframe(desc.to_frame())
            try:
                fig, ax = plt.subplots()
                sns.histplot(col_data.dropna(), kde=True, ax=ax)
                ax.set_title(f"Distribution of {col}")
                st.pyplot(fig)
            except Exception as e:
                st.warning(f"Could not plot: {e}")
        elif pd.api.types.is_categorical_dtype(col_data) or col_data.dtype == object:
            value_counts = col_data.value_counts().head(10)
            st.dataframe(value_counts.to_frame(name='Count'))
            try:
                fig, ax = plt.subplots()
                sns.countplot(y=col_data, order=value_counts.index, ax=ax)
                ax.set_title(f"Top values in {col}")
                st.pyplot(fig)
            except Exception as e:
                st.warning(f"Could not plot: {e}")

# --- 🔍 Univariate Analysis ---
with tabs[2]:
    for block in eda_sections['univariate']:
        st.markdown(block['insight'])
        st.code(block['code'], language='python')
        try:
            local_env = {"df": df, "plt": plt, "sns": sns}
            exec(block['code'], local_env)
            st.pyplot(plt.gcf())
            plt.clf()
            if 'insight_after_chart' in block:
                st.info(block['insight_after_chart'])
        except Exception as e:
            st.error(f"Error rendering chart: {e}")

# --- 📊 Correlation ---
with tabs[3]:
    st.markdown(eda_sections['correlation']['insight'])
    st.code(eda_sections['correlation']['code'], language='python')
    try:
        local_env = {"df": df, "plt": plt, "sns": sns}
        exec(eda_sections['correlation']['code'], local_env)
        st.pyplot(plt.gcf())
        plt.clf()
        if 'insight_after_chart' in eda_sections['correlation']:
            st.info(eda_sections['correlation']['insight_after_chart'])
    except Exception as e:
        st.error(f"Error rendering correlation heatmap: {e}")


# --- 💡 Insights ---
with tabs[4]:
    st.subheader("🔖 Key Takeaways & Recommendations")
    prompt_summary = f"""
        You are a professional data analyst. Given the following summaries from the EDA process:

        1. Dataset introduction:
        {eda_sections['introduction']}

        2. Data quality issues:
        {eda_sections['data_quality']}

        3. Univariate insights:
        {[b['insight_after_chart'] for b in eda_sections['univariate'] if 'insight_after_chart' in b]}

        4. Correlation insight:
        {eda_sections['correlation']['insight_after_chart']}

        Write a cohesive summary paragraph (~200-300 words) that:
        - Interprets patterns or problems in the dataset.
        - Highlights important relationships.
        - Mentions unexpected findings.
        - Proposes actionable insights.

        End with a short list of recommendations in bullet format.
        Respond in markdown.
        """
    
    summary_response = llm([HumanMessage(content=prompt_summary)]).content
    st.markdown(summary_response)







# --- 📄 Full Report ---
with tabs[5]:
    st.markdown("## 📄 Final Report Summary")

    # Render introduction + preview
    st.markdown("### 📘 Introduction")
    st.markdown(eda_sections['introduction'])
    st.dataframe(df.head())

    # Data Quality
    st.markdown("### 🧼 Data Quality")
    st.markdown(eda_sections['data_quality'])

    # Univariate
    st.markdown("### 🔍 Univariate Analysis")
    for block in eda_sections['univariate']:
        st.markdown(f"- {block['insight']}")
        st.code(block['code'], language="python")
        try:
            local_env = {"df": df, "plt": plt, "sns": sns}
            exec(block['code'], local_env)
            st.pyplot(plt.gcf())
            plt.clf()
            if 'insight_after_chart' in block:
                st.markdown(f"_{block['insight_after_chart']}_")
        except Exception as e:
            st.error(f"Error: {e}")

    # Correlation
    st.markdown("### 📊 Correlation Insights")
    st.markdown(eda_sections['correlation']['insight'])
    st.code(eda_sections['correlation']['code'], language="python")
    try:
        local_env = {"df": df, "plt": plt, "sns": sns}
        exec(eda_sections['correlation']['code'], local_env)
        st.pyplot(plt.gcf())
        plt.clf()
        st.markdown(f"_{eda_sections['correlation']['insight_after_chart']}_")
    except Exception as e:
        st.error(f"Heatmap error: {e}")

    # Final Summary from tab 4
    st.markdown("### 💡 Final Insights & Recommendations")
    st.markdown(summary_response)

    # Export Markdown Report
    st.markdown("### 📤 Export Report")

    # Tạo phần Univariate Markdown trước để tránh lỗi f-string với \n
    univariate_md = ""
    for b in eda_sections['univariate']:
        univariate_md += f"- {b['insight']}\n\n```python\n{b['code']}\n```\n\n_{b.get('insight_after_chart', '')}_\n\n"

    # Gộp toàn bộ báo cáo (chỉ để xuất file, không hiển thị)
    full_report_md = f"""
## 📘 Introduction
{eda_sections['introduction']}

## 🧼 Data Quality
{eda_sections['data_quality']}

## 🔍 Univariate Analysis
{univariate_md}

## 📊 Correlation Insights
{eda_sections['correlation']['insight']}

```python
{eda_sections['correlation']['code']}
```

_{eda_sections['correlation'].get('insight_after_chart', '')}_

## 💡 Final Insights & Recommendations
{summary_response}
"""

    # Nút tải xuống Markdown, không hiển thị nội dung
    st.download_button(
        label="📥 Download Markdown Report",
        data=full_report_md,
        file_name=f"EDA_Report_{name}.md",
        mime="text/markdown"
    )



