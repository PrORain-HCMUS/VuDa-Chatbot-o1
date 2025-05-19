import streamlit as st
import pandas as pd
import os
from datetime import datetime
from src.utils import init_db, add_dataset, get_all_datasets

st.set_page_config(page_title="📂 Dashboard", layout="wide")
st.title("📂 Dataset Dashboard")

init_db()
if not os.path.exists('data/uploads'):
    os.makedirs('data/uploads')

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

def safe_read_csv(file_path):
    for enc in ['utf-8', 'ISO-8859-1', 'utf-16', 'cp1252']:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Unable to decode file with common encodings.")

if uploaded_file:
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{now}_{uploaded_file.name}"
    file_path = os.path.join('data', 'uploads', filename)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    # df = pd.read_csv(file_path)
    df = safe_read_csv(file_path)

    rows, cols = df.shape
    upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_dataset(filename, file_path, rows, cols, upload_time)
    st.success(f"Uploaded and saved {filename}")

st.subheader("Uploaded Datasets")
datasets = get_all_datasets()
if datasets:
    df_list = pd.DataFrame(datasets, columns=["ID", "Name", "Rows", "Cols", "Uploaded", "Status"])
    st.dataframe(df_list)
else:
    st.info("No datasets available.")
