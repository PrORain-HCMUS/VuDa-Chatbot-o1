# File: pages/3_📂_Dataset_Details.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.utils import get_all_datasets, get_dataset

st.set_page_config(page_title="📂 Dataset Details", layout="wide")
st.title("📂 Dataset Details")

# Helper to safely read CSV with fallback encodings
def safe_read_csv(file_path):
    for enc in ['utf-8', 'ISO-8859-1', 'utf-16', 'cp1252']:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Unable to decode file with common encodings.")

# Helper to compute stats per column
def analyze_column(col_name, series):
    info = {}
    info['name'] = col_name
    info['dtype'] = str(series.dtype)
    info['missing_pct'] = series.isna().mean() * 100
    info['unique'] = series.nunique()

    if pd.api.types.is_numeric_dtype(series):
        desc = series.describe()
        info['min'] = desc['min']
        info['max'] = desc['max']
        info['mean'] = desc['mean']
        info['median'] = series.median()
        info['std'] = desc['std']
        # Detect outliers using IQR
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        outlier_cond = (series < (q1 - 1.5 * iqr)) | (series > (q3 + 1.5 * iqr))
        info['outliers'] = outlier_cond.sum()
        info['type'] = '# Số'
    elif series.nunique() == 2:
        info['type'] = 'True/False'
    elif info['unique'] == len(series):
        info['type'] = 'ID'
    elif info['unique'] <= 20:
        info['type'] = 'Phân loại'
    else:
        info['type'] = 'Chuỗi'

    return info

# Helper to summarize column insights
def generate_insight(info):
    if info['type'] == 'ID':
        return "🔹 Cột này là mã định danh duy nhất và không nên dùng để phân tích thống kê."
    if info['missing_pct'] > 0:
        return f"⚠️ Cột này có {info['missing_pct']:.1f}% giá trị bị thiếu."
    if 'std' in info and info['std'] < 1e-3:
        return "⚠️ Độ lệch chuẩn rất nhỏ. Biến này có thể gần như không thay đổi."
    if info['unique'] < 5 and info['type'] == 'Phân loại':
        return f"ℹ️ Cột phân loại này có ít hơn 5 giá trị khác nhau."
    return "✅ Không có vấn đề nổi bật trong cột này."

# Helper to plot column distribution
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

# Load available datasets
datasets = get_all_datasets()
if not datasets:
    st.warning("No datasets found. Please upload one in the Dashboard.")
    st.stop()

options = {f"{d[0]} - {d[1]}": d[0] for d in datasets}
selected = st.selectbox("Select dataset:", list(options.keys()))
dataset_id = options[selected]
dataset = get_dataset(dataset_id)

try:
    df = safe_read_csv(dataset[2])
except Exception as e:
    st.error(f"Failed to load CSV: {e}")
    st.stop()

st.markdown(f"### Dataset: `{dataset[1]}` — {df.shape[0]} rows × {df.shape[1]} columns")

# Phân tích từng cột và hiển thị card
for col in df.columns:
    with st.container():
        col_info = analyze_column(col, df[col])
        stats = col_info.copy()
        st.markdown(f"#### 📌 {col}")
        cols = st.columns([2, 3])

        with cols[0]:
            st.markdown(f"**Loại:** `{stats['type']}`")
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