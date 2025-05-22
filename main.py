import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from src.models.llms import load_llm, create_agent_from_csv
from src.utils import (
    add_chart_card,
    init_db,
    get_all_datasets,
    get_dataset,
    safe_read_csv,
    create_chat_session,
    get_sessions_by_dataset,
    add_chat_message,
    get_chat_messages,
    execute_plt_code,
    delete_chat_message,
    delete_chat_session,
    rename_chat_session
)

st.set_page_config(page_title="🧠 VuDa-GPT", layout="wide")
st.title("🧠 VuDa-GPT")
col1, col2 = st.columns(2)

with col1:
    st.image("assets/img/vuda_logo.png", use_container_width=True)

with col2:
    st.image("assets/img/tools.png", use_container_width=True)


# Load environment variables
load_dotenv()

# Initialize DB
init_db()

def smart_patch_code(code: str, df: pd.DataFrame, max_categories=10) -> str:
    import re

    patched_code = code

    # 1. Xử lý các cột ngày tháng
    date_cols = [col for col in df.columns if "date" in col.lower() or df[col].dtype == "object" and "date" in col.lower()]
    for col in date_cols:
        if col in code and f"{col}.dt.year" not in code:
            patched_code = (
                f"df['{col}'] = pd.to_datetime(df['{col}'], errors='coerce')\n"
                f"df['{col}_year'] = df['{col}'].dt.year\n"
                + patched_code.replace(f"'{col}'", f"'{col}_year'")
            )

    # 2. Giới hạn số lượng nhóm phân loại (barplot, boxplot,...)
    cat_cols = df.select_dtypes(include=['object', 'category']).columns
    for col in cat_cols:
        if col in patched_code and df[col].nunique() > max_categories:
            patched_code = (
                f"top_cats = df['{col}'].value_counts().nlargest({max_categories}).index\n"
                f"df = df[df['{col}'].isin(top_cats)]\n"
                + patched_code
            )
            break

    # 3. Với biểu đồ có plt → thêm rotate x-axis, logscale nếu lớn
    if "plt" in patched_code:
        if "xticks" not in patched_code:
            patched_code += "\nplt.xticks(rotation=45)"
        if "tight_layout" not in patched_code:
            patched_code += "\nplt.tight_layout()"

    # 4. Nếu scatter plot → thêm alpha
    if "scatter" in patched_code and "alpha" not in patched_code:
        patched_code = re.sub(r"scatter\((.*?)\)", r"scatter(\1, alpha=0.5)", patched_code)

    return patched_code


def enhance_prompt(prompt: str, df: pd.DataFrame) -> str:
    prompt = prompt.strip()
    suggestions = []

    # 1. Giới hạn số nhóm nếu là plot dạng nhóm
    if "bar" in prompt.lower() or "box" in prompt.lower() or "count" in prompt.lower():
        for col in df.columns:
            if df[col].nunique() > 30:
                suggestions.append(f"Limit the number of distinct '{col}' values to top 10 for clarity.")

    # 2. Xử lý trục với giá trị lớn
    numeric_cols = df.select_dtypes(include='number')
    if not numeric_cols.empty:
        if any(numeric_cols[col].max() > 1e8 for col in numeric_cols.columns):
            suggestions.append("Consider using a log scale for large numeric axes.")
    
    # 3. Có cột thời gian hoặc năm → gợi ý group by year/month
    for col in df.columns:
        if "year" in col.lower() or "date" in col.lower():
            suggestions.append(f"Group the data by `{col}` if it helps visualization.")

    # 4. Gợi ý biểu đồ phù hợp nếu thấy scatter/correlation
    if "correlation" in prompt.lower() or "relationship" in prompt.lower():
        suggestions.append("You may use a scatter plot or heatmap to visualize correlation.")
    
    # 5. Nếu là scatter plot thì nên thêm alpha nếu dữ liệu nhiều
    if "scatter" in prompt.lower() and len(df) > 1000:
        suggestions.append("Use transparency (e.g., alpha=0.5) to handle overlapping points in scatter plot.")

    # 6. Cuối cùng: thêm đề nghị format
    suggestions.append("Ensure axis labels are readable (e.g., rotate x-axis labels).")
    suggestions.append("Show values or summaries directly on chart if possible.")

    return prompt + "\n\n" + " ".join(suggestions)


# Load available datasets
datasets = get_all_datasets()
if not datasets:
    st.warning("Please upload a dataset in the Dashboard page first.")
    st.stop()

edited_prompt = st.session_state.pop("edited_prompt", None)

# Dataset selection dropdown
dataset_options = {f"{d[0]} - {d[1]}": d[0] for d in datasets}
selected = st.selectbox("Select dataset to analyze:", list(dataset_options.keys()))
dataset_id = dataset_options[selected]
dataset = get_dataset(dataset_id)
file_path = dataset[2]
num_rows, num_cols = dataset[3], dataset[4]

st.markdown(f"**📊 Dataset Info:** `{dataset[1]}` — {num_rows} rows × {num_cols} columns")

# Load CSV safely
try:
    df = safe_read_csv(file_path)
    st.session_state.df = df
except Exception as e:
    st.error(f"❌ Error loading CSV: {e}")
    st.stop()

# Chat session selection/creation
st.markdown("### 📬 Chat Sessions")
sessions = get_sessions_by_dataset(dataset_id)
session_titles = {f"{s[0]} - {s[1]} ({s[2]})": s[0] for s in sessions}

new_session_title = st.text_input("Start a new session (optional title):")
use_existing = st.radio("Choose session:", ("Use existing", "Create new"))

if use_existing == "Use existing" and sessions:
    session_display = st.selectbox("Select session:", list(session_titles.keys()))
    session_id = session_titles[session_display]

    # Tính năng đổi tên hoặc xóa phiên session
    with st.expander("⚙️ Manage this session"):
        new_name = st.text_input("Rename this session:")
        if st.button("Rename") and new_name:
            rename_chat_session(session_id, new_name)
            st.rerun()
        if st.button("❌ Delete this session"):
            delete_chat_session(session_id)
            st.success("Deleted session")
            st.rerun()

elif use_existing == "Create new" or not sessions:
    default_title = new_session_title or "New Session"
    session_id = create_chat_session(dataset_id, default_title)
    st.success(f"✅ Created new session: {default_title}")

# Load chat history
chat_history = get_chat_messages(session_id)

if chat_history:
    st.markdown("### 🔈️ Conversation History")
    for idx, (msg_id, role, content, ts) in enumerate(chat_history):
        with st.chat_message(role):
            cols = st.columns([10, 1])
            with cols[0]:
                st.markdown(content)
            with cols[1]:
                if role == "user":
                    with st.popover("⋮", use_container_width=True):
                        if st.button("✏️ Edit", key=f"edit_{idx}"):
                            st.session_state.edited_prompt = content
                            delete_chat_message(session_id, idx + 1)
                            delete_chat_message(session_id, idx + 2)  # chatbot reply
                            st.rerun()

                        if st.button("🗑️ Delete", key=f"del_{msg_id}"):
                            delete_chat_message(session_id, msg_id)
                            # Optional: nếu message sau đó là bot → xóa tiếp
                            if idx + 1 < len(chat_history) and chat_history[idx + 1][1] == "assistant":
                                delete_chat_message(session_id, chat_history[idx + 1][0])
                            st.rerun()


                        st.button("📋 Copy", key=f"copy_{idx}")

# Chat input area
prompt = st.session_state.pop("submitted_edited_prompt", None) or st.chat_input("Ask something about this dataset...")
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    add_chat_message(session_id, "user", prompt)

    with st.chat_message("assistant"):
        try:
            agent = create_agent_from_csv("gpt-3.5-turbo", file_path, return_steps=True)
            # response = agent(prompt)
            prompt_to_send = enhance_prompt(prompt, df)
            response = agent(prompt_to_send)


            steps = response.get("intermediate_steps", [])
            action_code = steps[-1][0].tool_input["query"] if steps else ""

            st.markdown(response["output"])
            add_chat_message(session_id, "assistant", response["output"])

            if "plt" in action_code:
                # fig = execute_plt_code(action_code, df)
                patched_code = smart_patch_code(action_code, df)
                fig = execute_plt_code(patched_code, df)
                st.code(patched_code, language="python")

                if fig:
                    st.pyplot(fig)
                st.code(action_code, language="python")

                # Save chart card so it appears in Visual Summary
                add_chart_card(dataset_id, prompt, response["output"], action_code)

        except Exception as e:
            st.error(f"❌ Failed: {e}")
