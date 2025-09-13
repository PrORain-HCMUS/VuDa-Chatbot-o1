# ==========================================================================================================================
# 📊 Smart Chart Builder
# - Sidebar (Cột 1): Chọn dataset, cấu hình trục X/Y, nhóm màu, loại biểu đồ, nhập yêu cầu thêm cho LLM, nút sinh biểu đồ.
# - Chart (Cột 2): Hiển thị biểu đồ Plotly cơ bản và biểu đồ nâng cao do LLM sinh ra.
# - Insights (Cột 3): Hiển thị code vẽ biểu đồ, các insights phân tích dữ liệu và bảng thống kê do LLM sinh ra.
# ==========================================================================================================================
#   Update Log (13.09.2025):
# - Fix lỗi reload trang khi tạo chart mới từ phần add instructions bằng cách thêm Placeholders chỉ 1 lần
# - Cải thiện prompt để LLM luôn sử dụng tên/thông tin thực tế từ dataset, không dùng placeholder
# - Thêm hàm _sanitize_plotly_code để loại bỏ fig.show(), plt.show
# - Thêm phần chart sau khi modify bằng instructions bên dưới chart ban đầu
# ==========================================================================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from src.models.llms import load_llm
from src.models.config import COLOR_THEME
from datetime import datetime
from src.utils import (
    get_all_datasets, 
    get_dataset, 
    inject_cards_css
)
import re

st.set_page_config(page_title="📈 Smart Chart Builder", layout="wide")
# st.title("📈 Smart Chart Builder")
inject_cards_css()
st.markdown(
    """
    <div style="background:linear-gradient(90deg,#1f6feb,#2ea043);
                border-radius:16px;padding:18px 22px;margin-bottom:12px;">
      <h1 style="margin:0;color:white;font-weight:800;letter-spacing:.3px;">
        📈 Smart Chart Builder
      </h1>
      <div style="color:#dbe8ff;opacity:.95;font-size:15px;">
        Create and analyze charts with AI-powered insights. 
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


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

# Placeholders (chỉ 1 lần, không tạo trang mới)
chart_placeholder = chart_col.container()
insight_placeholder = llm_col.container()

def _sanitize_plotly_code(code: str) -> str:
    """Loại bỏ fig.show(), plt.show(), st.plotly_chart(...)"""
    code = re.sub(r"\b(fig|plt)\.show\(\)\s*;?", "", code)
    code = re.sub(r"st\.plotly_chart\([^\)]*\)\s*", "", code, flags=re.S)
    return code

if generate:
    color = group_by if group_by != "None" else None
    st.session_state["chart_config"] = {
        "chart_type": chart_type,
        "x_axis": x_axis,
        "y_axis": y_axis,
        "color": color,
    }

    # ===== 1) Chart cơ bản ban đầu ở cột 2 =====
    try:
        if chart_type == "line":
            base_fig = px.line(df, x=x_axis, y=y_axis, color=color)
        elif chart_type == "bar":
            base_fig = px.bar(df, x=x_axis, y=y_axis, color=color)
        elif chart_type == "scatter":
            base_fig = px.scatter(df, x=x_axis, y=y_axis, color=color)
        else:
            base_fig = None

        if base_fig:
            chart_placeholder.markdown("### 📊 Generated / Updated Chart")
            rev = st.session_state.get("chart_rev", 0) + 1
            st.session_state["chart_rev"] = rev
            chart_placeholder.plotly_chart(base_fig, use_container_width=True, key=f"base_chart_{rev}")
    except Exception as e:
        chart_placeholder.error(f"❌ Error generating chart: {e}")

    # ===== 2) Gọi LLM để lấy code + insights =====
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
            - ⚠️ Do NOT use placeholders like "Artist A" or "Group 1" — always use actual names/labels from `df`
            3. **Output 5 statistics (mean, median, min, max, std)** as a **Markdown table**, broken down by `{color}` if applicable.

            Respond in Markdown with:
            - A code block for the chart
            - A bold **Insights:** section with bullet points (no placeholders)
            - A bold **Statistics:** section rendered as a Markdown table, like:

            | Metric | Drake | Taylor Swift | The Weeknd |
            |--------|-------|--------------|------------|
            | Mean   | 85.2  | 82.1         | 79.5       |
            | Median | 87.0  | 84.0         | 81.0       |

            ⚠️ Important:
            - Use **real values and real names** from the dataset
            - NEVER use placeholders like "Region A", "Artist B", or "Category C"
            - Insights must be specific and data-driven
            """


        result = llm.predict(prompt)

        # Cột 3: hiển thị code + insights + table từ LLM
        insight_placeholder.markdown(result)

        # Parse code từ LLM → update chart ở cột 2
        code_blocks = re.findall(r"```(?:python)?(.*?)```", result, re.S)
        if code_blocks:
            raw_code = code_blocks[0].strip()
            code_to_run = _sanitize_plotly_code(raw_code)

            try:
                local_vars = {"df": df, "px": px}
                exec(code_to_run, {}, local_vars)

                if "fig" in local_vars and local_vars["fig"] is not None:
                    chart_placeholder.markdown("### 📊 Generated / Updated Chart")
                    rev = st.session_state.get("chart_rev", 0) + 1
                    st.session_state["chart_rev"] = rev
                    chart_placeholder.plotly_chart(local_vars["fig"], use_container_width=True, key=f"llm_chart_{rev}")
                    chart_placeholder.code(code_to_run, language="python")
            except Exception as e:
                insight_placeholder.error(f"⚠️ Error executing LLM code: {e}")
