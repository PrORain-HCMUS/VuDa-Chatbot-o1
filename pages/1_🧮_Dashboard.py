import streamlit as st
import pandas as pd
import os
from datetime import datetime
from src.utils import init_db, add_dataset, get_all_datasets, delete_dataset, rename_dataset, safe_read_csv
from pygwalker.api.streamlit import StreamlitRenderer

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

# Prevent duplicate upload and browser freeze
if uploaded_file and "uploaded_filename" not in st.session_state:
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{now}_{uploaded_file.name}"
    file_path = os.path.join('data', 'uploads', filename)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    df = safe_read_csv(file_path)
    rows, cols = df.shape
    upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_dataset(filename, file_path, rows, cols, upload_time)
    st.session_state.uploaded_filename = filename
    st.success(f"✅ Uploaded and saved {filename}")
    st.rerun()

# Clear session upload flag after rerun
if "uploaded_filename" in st.session_state:
    del st.session_state.uploaded_filename

# Load datasets
datasets = get_all_datasets()

# Summary header
if datasets:
    st.markdown("### 📦 Summary")
    st.write(f"**Total datasets:** {len(datasets)}")
    st.write(f"**Total rows:** {sum([d[2] for d in datasets])}, **columns:** {sum([d[3] for d in datasets])}")
else:
    st.info("No datasets available.")

# Show dataset management
st.markdown("### 🧾 Uploaded Datasets")
for dataset in datasets:
    id_, name, rows, cols, uploaded, status = dataset
    with st.expander(f"📁 {name} — {rows} rows × {cols} cols"):
        file_path = os.path.join("data", "uploads", name)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🗑️ Delete", key=f"del_{id_}", help="Remove this dataset"):
                delete_dataset(id_)
                st.warning(f"Deleted dataset {name}")
                st.rerun()

        with col2:
            new_name = st.text_input("Rename", value=name, label_visibility="collapsed", key=f"rename_{id_}")
            if st.button("✅ Rename", key=f"rename_btn_{id_}", help="Change dataset name"):
                rename_dataset(id_, new_name)
                st.success("Renamed successfully.")
                st.rerun()

        with col3:
            if st.button("🔍 Open Overview", key=f"overview_{id_}", help="Explore this dataset"):
                st.session_state.df = safe_read_csv(file_path)
                st.session_state.selected_name = name
                st.session_state.activate_overview = True

        # Preview table
        try:
            preview_df = safe_read_csv(file_path)
            st.dataframe(preview_df.head(5), use_container_width=True)
        except Exception as e:
            st.error(f"Could not preview: {e}")

# ================== Overview Tab with Pygwalker ==================
if st.session_state.get("activate_overview", False):
    st.markdown("## 🧠 Dataset Overview")
    st.success(f"Now analyzing: `{st.session_state.selected_name}`")

    import pygwalker as pyg
    import streamlit.components.v1 as components

    pyg_html = pyg.to_html(st.session_state.df, dark="media", use_kernel_calc=True, default_tab="data")
    components.html(pyg_html, height=800, scrolling=True)

    st.session_state.activate_overview = False
