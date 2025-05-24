import streamlit as st
import pandas as pd
import plotly.express as px
from src.models.llms import load_llm
from src.models.config import COLOR_THEME
from datetime import datetime
from src.utils import get_all_datasets, get_dataset

st.set_page_config(page_title="📈 Smart Chart Builder", layout="wide")
st.title("📈 Smart Chart Builder")

llm = load_llm("gpt-3.5-turbo")

# Load datasets
datasets = get_all_datasets()
if not datasets:
    st.warning("⚠️ Please upload a dataset from the Dashboard page.")
    st.stop()

dataset_options = {f"{d[0]} - {d[1]}": d[0] for d in datasets}
selected = st.selectbox("📂 Select dataset to analyze:", list(dataset_options.keys()))
dataset_id = dataset_options[selected]
dataset = get_dataset(dataset_id)
file_path = dataset[2]

@st.cache_data
def load_csv(file_path):
    for enc in ['utf-8', 'ISO-8859-1', 'utf-16', 'cp1252']:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except:
            continue
    raise ValueError("❌ Cannot decode CSV file.")

df = load_csv(file_path)

st.markdown(f"**🧾 Dataset Info:** `{dataset[1]}` — {df.shape[0]} rows × {df.shape[1]} columns")

# Layout: Sidebar | Chart | Insights
sidebar, chart_col, llm_col = st.columns([1, 3, 2])

with sidebar:
    st.markdown("### ⚙️ Chart Settings")
    x_axis = st.selectbox("X-axis", options=df.columns.tolist())
    y_axis = st.selectbox("Y-axis", options=df.select_dtypes(include=['number']).columns.tolist())
    group_by = st.selectbox("Color By", options=["None"] + df.select_dtypes(include=['object', 'category']).columns.tolist())
    chart_type = st.selectbox("Chart Type", options=["line", "bar", "scatter"])
    user_prompt = st.text_area("📝 Extra LLM Instructions", placeholder="e.g., add markers, use dark theme...")
    generate = st.button("🚀 Generate & Analyze")

if generate:
    color = group_by if group_by != "None" else None

    with chart_col:
        st.markdown("### 📊 Generated Chart")
        try:
            if chart_type == "line":
                fig = px.line(df, x=x_axis, y=y_axis, color=color)
            elif chart_type == "bar":
                fig = px.bar(df, x=x_axis, y=y_axis, color=color)
            elif chart_type == "scatter":
                fig = px.scatter(df, x=x_axis, y=y_axis, color=color)
            else:
                st.warning("Unsupported chart type.")
                fig = None

            if fig:
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"❌ Error generating chart: {e}")

    with llm_col:
        st.markdown("### 🧠 Chart Code & Insights")
        with st.spinner("Generating chart code and insights..."):
            prompt = f"""
                You are a professional data analyst and visualization expert working with Python and pandas.
                The dataset is preloaded in the DataFrame `df` and contains these columns: {df.columns.tolist()}.

                The user has just generated a Plotly {chart_type} chart with:
                - X-axis: `{x_axis}`
                - Y-axis: `{y_axis}`
                - Color grouping: `{color}`
                {f"- Extra request: {user_prompt.strip()}" if user_prompt.strip() else ""}

                Your tasks:
                1. **Generate the Plotly Express code only using `df`**, do NOT redefine or reload data.
                2. **Extract 3 meaningful insights using real values and labels from df**:
                - Example: "Artist 'Ed Sheeran' has the highest Spotify Popularity (97) and Track Score (420)"
                - Include comparisons, extremes, or correlations with exact numbers
                3. **Output 5 statistics (mean, median, min, max, std)** as a **Markdown table**, broken down by `{color}` if applicable

                Respond in Markdown with:
                - A code block for the chart
                - A bold **Insights:** section with bullet points (no placeholders)
                - A bold **Statistics:** section rendered as a Markdown table, like:

                | Metric | Group A | Group B | Group C |
                |--------|---------|---------|---------|
                | Mean   | 58.2    | 63.1    | 47.9    |
                | Median | ...     | ...     | ...     |

                ⚠️ Important:
                - Use **real values and real names** from the dataset
                - NEVER use placeholders like "Region A" or "Artist B"
                - Insights must be specific and data-driven
                """

            result = llm.predict(prompt)
            st.markdown(result)
