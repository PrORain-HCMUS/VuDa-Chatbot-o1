import streamlit as st
from PIL import Image
import os

st.set_page_config(page_title="📖 About Project", layout="wide")
st.title("📖 About This Project")

st.markdown("""
Welcome to **Delight-GPT** — a smart, LLM-powered data analysis platform built for intuitive EDA and visualization.


### 🚀 Features
- Upload CSV datasets and preview instantly  
- Auto-generate full EDA reports using GPT-3.5 via LangChain  
- Dynamic chart generation (Matplotlib, Seaborn, Plotly)  
- Save and reuse insightful charts  
- AI-powered chatbot to ask questions about the data  
- Export professional PDF reports with rich formatting  

### 🧱 Data Flow Pipeline
""", unsafe_allow_html=True)

# Hiển thị ảnh pipeline
pipeline_path = os.path.join("assets", "img", "pipeline.png")
if os.path.exists(pipeline_path):
    st.image(pipeline_path, use_container_width=True)

else:
    st.warning(f"⚠️ Cannot find pipeline image at {pipeline_path}")

st.markdown("""

### 🧰 Tech Stack
- **Frontend**: Streamlit  
- **AI Engine**: OpenAI GPT-3.5-turbo + LangChain  
- **Data Viz**: Matplotlib, Seaborn, Plotly, PyGWalker  
- **Storage**: SQLite  
- **Export**: pdfkit + wkhtmltopdf  


### 💡 Motivation
This project was created to:

- Make data exploration easier for non-programmers  
- Integrate LLM reasoning into EDA  
- Produce visually compelling reports with minimal effort  

---

### 👨‍💻 Contributing
Made with ❤️ by Delay group.
""", unsafe_allow_html=True)

with st.sidebar:
    st.page_link("pages/📖_About_Project.py", label="📖 About Project", icon="📘")
