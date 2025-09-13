# ==========================================================================================================================
# 📊 Charts History
# - Hiển thị lịch sử các biểu đồ đã tạo, kèm code, insights và thời gian tạo
# - Cho phép xem lại, xóa từng biểu đồ mà không cần reload trang
# - Tích hợp preview code, kết quả biểu đồ và nội dung trả lời từ LLM
# - Hỗ trợ quản lý biểu đồ theo từng dataset, giúp người dùng dễ dàng tra cứu lại
# ==========================================================================================================================
#   Update Log (13.09.2025):
# - Chỉ thêm placeholder 1 lần để tránh reload trang khi xóa biểu đồ, thêm css-injected cards
# ==========================================================================================================================


import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from src.utils import (
    init_db, 
    get_all_datasets, 
    get_chart_cards_by_dataset, 
    get_dataset, 
    safe_read_csv, 
    execute_plt_code, 
    delete_chart_card,
    inject_cards_css
)


st.set_page_config(page_title="📊 Visual Summary", layout="wide")
# st.title("📊 Charts History")
inject_cards_css()
st.markdown(
    """
    <div style="background:linear-gradient(90deg,#1f6feb,#2ea043);
                border-radius:16px;padding:18px 22px;margin-bottom:12px;">
      <h1 style="margin:0;color:white;font-weight:800;letter-spacing:.3px;">
        📊 Charts History
      </h1>
      <div style="color:#dbe8ff;opacity:.95;font-size:15px;">
        Review and manage your chart-based codes, insights.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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

# for i, (question, answer, code, timestamp) in enumerate(cards):
#     with st.container():
#         cols = st.columns([2, 3])

#         with cols[0]:
#             st.markdown(f"### 🕓 {timestamp}")
#             st.markdown(f"❓ **Question {i+1}:** {question}")
#             st.markdown(f"💬 **Answer:** {answer}")
#             with st.expander("📄 View Code"):
#                 st.code(code, language="python")

#         with cols[1]:
#             fig = execute_plt_code(code, st.session_state.df)
#             if fig:
#                 st.pyplot(fig)
#             else:
#                 st.warning("⚠️ No chart could be rendered from saved code.")


# Ghi nhớ biểu đồ đã xoá để ẩn ngay mà không cần reload
if "deleted_charts" not in st.session_state:
    st.session_state.deleted_charts = set()

for i, (question, answer, code, timestamp) in enumerate(cards):
    unique_key = f"{question}-{timestamp}"
    if unique_key in st.session_state.deleted_charts:
        continue  # Ẩn khỏi UI nếu đã xoá

    with st.container():
        cols = st.columns([2, 3])

        with cols[0]:
            st.markdown(f"### 🕓 {timestamp}")
            st.markdown(f"❓ **Question {i+1}:** {question}")
            st.markdown(f"💬 **Answer:** {answer}")
            with st.expander("📄 View Code"):
                st.code(code, language="python")

            if st.button("🗑️ Delete Chart", key=f"del_card_{i}"):
                delete_chart_card(dataset_id, question, timestamp)
                st.toast("🗑️ Chart deleted!", icon="✅")
                st.rerun()  # 

        with cols[1]:
            fig = execute_plt_code(code, st.session_state.df)
            if fig:
                st.pyplot(fig)
            else:
                st.warning("⚠️ No chart could be rendered from saved code.")

    st.markdown("---")
