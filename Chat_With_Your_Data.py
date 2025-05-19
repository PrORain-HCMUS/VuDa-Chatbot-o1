# import matplotlib.pyplot as plt
# import pandas as pd
# import streamlit as st
# from dotenv import load_dotenv
# from langchain_experimental.agents.agent_toolkits.pandas.base import create_pandas_dataframe_agent
# from langchain_openai import ChatOpenAI

# from src.logger.base import BaseLogger
# from src.models.llms import load_llm
# from src.utils import execute_plt_code

# # load environment varibles
# load_dotenv()
# logger = BaseLogger()
# MODEL_NAME = "gpt-3.5-turbo"


# def process_query(da_agent, query):

#     response = da_agent(query)

#     action = response["intermediate_steps"][-1][0].tool_input["query"]

#     if "plt" in action:
#         st.write(response["output"])

#         fig = execute_plt_code(action, df=st.session_state.df)
#         if fig:
#             st.pyplot(fig)

#         st.write("**Executed code:**")
#         st.code(action)

#         to_display_string = response["output"] + "\n" + f"```python\n{action}\n```"
#         st.session_state.history.append((query, to_display_string))

#     else:
#         st.write(response["output"])
#         st.session_state.history.append((query, response["output"]))


# def display_chat_history():
#     st.markdown("## Chat History: ")
#     for i, (q, r) in enumerate(st.session_state.history):
#         st.markdown(f"**Query: {i+1}:** {q}")
#         st.markdown(f"**Response: {i+1}:** {r}")
#         st.markdown("---")


# def main():

#     # Set up streamlit interface
#     st.set_page_config(page_title="📊 Smart Data Analysis Tool", page_icon="📊", layout="centered")
#     st.header("📊 Smart Data Analysis Tool")
#     st.write(
#         "### Welcome to our data analysis tool. This tools can assist your daily data analysis tasks. Please enjoy !"
#     )

#     # Load llms model
#     llm = load_llm(model_name=MODEL_NAME)
#     logger.info(f"### Successfully loaded {MODEL_NAME} !###")

#     # Upload csv file
#     with st.sidebar:
#         uploaded_file = st.file_uploader("Upload your csv file here", type="csv")

#     # Initial chat history
#     if "history" not in st.session_state:
#         st.session_state.history = []

#     # Read csv file
#     if uploaded_file is not None:
#         st.session_state.df = pd.read_csv(uploaded_file)
#         st.write("### Your uploaded data: ", st.session_state.df.head())

#         # Create data analysis agent to query with our data
#         da_agent = create_pandas_dataframe_agent(
#             llm=llm,
#             df=st.session_state.df,
#             agent_type="tool-calling",
#             allow_dangerous_code=True, 
#             verbose=True,
#             return_intermediate_steps=True,
#         )
#         logger.info("### Sucessfully loaded data analysis agent !###")

#         # Input query and process query
#         query = st.text_input("Enter your questions: ")

#         if st.button("Run query"):
#             with st.spinner("Processing..."):
#                 process_query(da_agent, query)

#     # Display chat history
#     st.divider()
#     display_chat_history()


# if __name__ == "__main__":
#     main()



# File: pages/2_🤖_Chat_With_Your_Data.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from src.models.llms import load_llm, create_agent_from_csv
from src.utils import (
    add_chart_card,
    init_db,
    get_all_datasets,
    get_dataset,
    get_chats_by_dataset,
    add_chat,
    execute_plt_code,
    safe_read_csv
)

st.set_page_config(page_title="🤖 Chat With Your Data", layout="wide")
st.title("🤖 Chat With Your Data")

from dotenv import load_dotenv
load_dotenv()

# Initialize DB
init_db()

# Load available datasets
datasets = get_all_datasets()
if not datasets:
    st.warning("Please upload a dataset in the Dashboard page first.")
    st.stop()

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
    st.dataframe(df.head())
except Exception as e:
    st.error(f"❌ Error loading CSV: {e}")
    st.stop()

# Show previous Q&A
st.markdown("### 🕓 Previous Q&A")
history = get_chats_by_dataset(dataset_id)
if history:
    for ts, question, answer in history[::-1]:
        with st.expander(f"🗓️ {ts} — Q: {question[:60]}..."):
            st.markdown(f"**Q:** {question}")
            st.markdown(f"**A:** {answer}")
else:
    st.info("No chat history yet for this dataset.")

# Ask a new question
st.markdown("---")
st.subheader("💬 Ask a new question")

with st.form("query_form"):
    user_query = st.text_area("Enter your question:")
    selected_model = st.selectbox("Select LLM model:", ["gpt-3.5-turbo", "gpt-4"])
    submitted = st.form_submit_button("Run")

if submitted and user_query:
    with st.spinner("⏳ Thinking..."):
        try:
            agent = create_agent_from_csv(selected_model, file_path, return_steps=True)
            response = agent(user_query)

            steps = response.get("intermediate_steps", [])
            action_code = steps[-1][0].tool_input["query"] if steps else ""

            st.success("✅ Answer:")
            st.markdown(response["output"])

            if "plt" in action_code:
                fig = execute_plt_code(action_code, df)
                if fig:
                    st.pyplot(fig)
                st.code(action_code, language="python")
                add_chart_card(dataset_id, user_query, response["output"], action_code)

            add_chat(dataset_id, user_query, response["output"])
        except Exception as e:
            st.error(f"❌ Failed: {e}")

