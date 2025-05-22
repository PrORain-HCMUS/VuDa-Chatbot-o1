# File: pages/4_📊_Visual_Summary.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from src.utils import init_db, get_all_datasets, get_chart_cards_by_dataset, get_dataset, safe_read_csv, execute_plt_code


st.set_page_config(page_title="📊 Visual Summary", layout="wide")
st.title("📊 Charts History")

# Initialize database
init_db()

# Get list of datasets
datasets = get_all_datasets()
if not datasets:
    st.warning("Please upload some datasets first.")
    st.stop()

# Select dataset from dropdown
options = {f"{d[0]} - {d[1]}": d[0] for d in datasets}
selected = st.selectbox("Select dataset:", list(options.keys()))
dataset_id = options[selected]
dataset = get_dataset(dataset_id)

# Load dataframe safely
try:
    st.session_state.df = safe_read_csv(dataset[2])
except Exception as e:
    st.error(f"❌ Failed to load dataframe: {e}")
    st.stop()

# Get chart cards related to this dataset
cards = get_chart_cards_by_dataset(dataset_id)
if not cards:
    st.info("No chart insights found for this dataset.")
    st.stop()

# Display visual summaries
st.markdown("---")
st.subheader("🧩 Chart-based Insights")

for i, (question, answer, code, timestamp) in enumerate(cards):
    with st.container():
        cols = st.columns([2, 3])

        with cols[0]:
            st.markdown(f"### 🕓 {timestamp}")
            st.markdown(f"❓ **Question {i+1}:** {question}")
            st.markdown(f"💬 **Answer:** {answer}")
            with st.expander("📄 View Code"):
                st.code(code, language="python")

        with cols[1]:
            fig = execute_plt_code(code, st.session_state.df)
            if fig:
                st.pyplot(fig)
            else:
                st.warning("⚠️ No chart could be rendered from saved code.")

    st.markdown("---")