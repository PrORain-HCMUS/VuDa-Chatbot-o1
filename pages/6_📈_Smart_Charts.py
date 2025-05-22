import streamlit as st
import pandas as pd
import plotly.express as px
from src.models.llms import load_llm
from src.models.config import COLOR_THEME
from datetime import datetime
from src.utils import get_all_datasets, get_dataset

st.set_page_config(page_title="📈 Smart Chart Suggestions", layout="wide")
st.title("📈 Smart Chart Suggestions")

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

# Basic info
st.markdown(f"**🧾 Dataset Info:** `{dataset[1]}` — {df.shape[0]} rows × {df.shape[1]} columns")

# Choose grouping column
group_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
group_col = st.selectbox("🧩 Select a grouping column (optional):", options=["None"] + group_cols)

if group_col != "None":
    group_values = sorted(df[group_col].dropna().unique())
    selected_groups = st.multiselect(f"Select one or more {group_col} to visualize", group_values, default=group_values[:1])
    filtered_df = df[df[group_col].isin(selected_groups)].copy()
else:
    group_col = None
    filtered_df = df.copy()

# Determine time/index column
if 'Date' in df.columns:
    filtered_df['Year'] = pd.to_datetime(filtered_df['Date'], errors='coerce').dt.year
    x_axis = 'Year'
elif 'Year' in df.columns:
    x_axis = 'Year'
else:
    filtered_df['Index'] = filtered_df.index
    x_axis = 'Index'

# Prompt area
st.subheader("💬 Describe the chart you want")
prompt = st.text_area("For example: 'Compare average score by gender over years'", placeholder="Enter chart description here...")

if st.button("🎨 Generate Chart"):
    if not prompt.strip():
        st.warning("⚠️ Please enter a prompt.")
    else:
        with st.spinner("🧠 Analyzing prompt and generating chart..."):
            columns = df.columns.tolist()
            llm_prompt = f"""
You are a Python data visualization assistant.
You're given a DataFrame `df` with columns: {columns}.
The user described a chart they want with the prompt: '{prompt}'.
Generate working Plotly Express code for Streamlit using this DataFrame.
Only return the code inside triple backticks.
"""
            response = llm.predict(llm_prompt)

            try:
                code = response.split("```python")[-1].split("```")[0]
                st.code(code, language="python")
                exec_globals = {"df": df.copy(), "px": px, "st": st, "pd": pd}
                exec(code, exec_globals)
            except Exception as e:
                st.error(f"❌ Error executing chart code:\n{e}")

st.markdown("---")
st.subheader("📊 Manual Chart Builder")

numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
selected_features = st.multiselect("📈 Select one or more numeric features", numeric_columns)

if selected_features:
    # Convert to long-form for better plotting
    df_melted = filtered_df.melt(id_vars=[x_axis] + ([group_col] if group_col else []),
                                value_vars=selected_features,
                                var_name='variable',
                                value_name='value')

    fig = px.line(
        df_melted,
        x=x_axis,
        y='value',
        color='variable' if not group_col else group_col,
        line_dash='variable' if group_col else None,
        title="Custom Chart",
    )
    fig.update_xaxes(title_text=x_axis, tickmode='linear')
    fig.update_yaxes(title_text="Value")
    st.plotly_chart(fig, use_container_width=True)
