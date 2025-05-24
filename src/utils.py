import matplotlib.pyplot as plt
import pandas as pd
import sqlite3
from datetime import datetime
import streamlit as st

DB_NAME = "db.sqlite"

def execute_plt_code(code: str, df: pd.DataFrame):
    try:
        # local_vars = {"plt": plt, "df": df}
        import seaborn as sns
        local_vars = {"plt": plt, "df": df, "sns": sns}

        compiled_code = compile(code, "<string>", "exec")
        exec(compiled_code, globals(), local_vars)
        return plt.gcf()
    except Exception as e:
        st.error(f"Error executing plt code: {e}")
        return None

def safe_read_csv(file_path):
    for enc in ['utf-8', 'ISO-8859-1', 'utf-16', 'cp1252']:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", b"", 0, 1, "Unable to decode file with common encodings.")

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            path TEXT,
            num_rows INTEGER,
            num_cols INTEGER,
            upload_time TEXT,
            status TEXT
        )''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER,
            timestamp TEXT,
            question TEXT,
            answer TEXT,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id)
        )''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS chart_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER,
            question TEXT,
            answer TEXT,
            code TEXT,
            created_at TEXT,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id)
        )''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER,
            title TEXT,
            created_at TEXT
        )''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        )''')
    conn.commit()
    conn.close()

def add_dataset(name, path, num_rows, num_cols, upload_time, status="Uploaded"):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO datasets (name, path, num_rows, num_cols, upload_time, status)
        VALUES (?, ?, ?, ?, ?, ?)''', (name, path, num_rows, num_cols, upload_time, status))
    conn.commit()
    conn.close()

def get_all_datasets():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, num_rows, num_cols, upload_time, status FROM datasets')
    rows = c.fetchall()
    conn.close()
    return rows

def get_dataset(id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM datasets WHERE id = ?', (id,))
    row = c.fetchone()
    conn.close()
    return row

def add_chat(dataset_id, question, answer):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO chat_history (dataset_id, timestamp, question, answer)
        VALUES (?, ?, ?, ?)''', (dataset_id, timestamp, question, answer))
    conn.commit()
    conn.close()

def get_chats_by_dataset(dataset_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT timestamp, question, answer FROM chat_history WHERE dataset_id = ? ORDER BY id', (dataset_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_chart_card(dataset_id, question, answer, code):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO chart_cards (dataset_id, question, answer, code, created_at)
        VALUES (?, ?, ?, ?, ?)''', (dataset_id, question, answer, code, timestamp))
    conn.commit()
    conn.close()

def get_chart_cards_by_dataset(dataset_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT question, answer, code, created_at
        FROM chart_cards
        WHERE dataset_id = ?
        ORDER BY id DESC''', (dataset_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def create_chat_session(dataset_id, title):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO chat_sessions (dataset_id, title, created_at)
        VALUES (?, ?, ?)''', (dataset_id, title, timestamp))
    conn.commit()
    session_id = c.lastrowid
    conn.close()
    return session_id

def get_sessions_by_dataset(dataset_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, title, created_at
        FROM chat_sessions
        WHERE dataset_id = ?
        ORDER BY created_at DESC''', (dataset_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_chat_message(session_id, role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO chat_messages (session_id, role, content, created_at)
        VALUES (?, ?, ?, ?)''', (session_id, role, content, timestamp))
    conn.commit()
    conn.close()

def get_chat_messages(session_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, role, content, created_at
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY id
    ''', (session_id,))
    messages = c.fetchall()
    conn.close()
    return messages


def delete_chat_message(session_id, message_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        DELETE FROM chat_messages
        WHERE session_id = ? AND id = ?
    ''', (session_id, message_id))
    conn.commit()
    conn.close()


def delete_chat_session(session_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
    c.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
    conn.commit()
    conn.close()


def rename_chat_session(session_id, new_title):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE chat_sessions
        SET title = ?
        WHERE id = ?
    ''', (new_title, session_id))
    conn.commit()
    conn.close()


def delete_dataset(dataset_id):
    conn = get_connection()
    c = conn.cursor()
    
    # Xoá liên quan (nếu cần)
    c.execute('DELETE FROM chat_messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE dataset_id = ?)', (dataset_id,))
    c.execute('DELETE FROM chat_sessions WHERE dataset_id = ?', (dataset_id,))
    c.execute('DELETE FROM chart_cards WHERE dataset_id = ?', (dataset_id,))

    # Xoá chính dataset
    c.execute('DELETE FROM datasets WHERE id = ?', (dataset_id,))
    
    conn.commit()
    conn.close()

def rename_dataset(dataset_id, new_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE datasets
        SET name = ?
        WHERE id = ?
    ''', (new_name, dataset_id))
    conn.commit()
    conn.close()

def delete_chart_card(dataset_id: int, question: str, created_at: str):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM chart_cards WHERE dataset_id = ? AND question = ? AND created_at = ?",
        (dataset_id, question, created_at)
    )
    conn.commit()
    conn.close()


# ---------------------------- Hàm Export ---------------------------- 
import os
import shutil
import base64
import pdfkit
import matplotlib.pyplot as plt
import seaborn as sns
from uuid import uuid4

pdfkit_config = pdfkit.configuration(
    wkhtmltopdf=r"D:\TeraBoxDownload\wkhtmltopdf\bin\wkhtmltopdf.exe"
)


def format_summary_to_html(summary_text):
    """Chuyển đoạn markdown hoặc text thành HTML chia đoạn và bullet rõ ràng."""
    lines = summary_text.strip().split("\n")
    html_parts = []
    in_list = False

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("- ") or line.startswith("• "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{line.lstrip('-• ').strip()}</li>")
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<p>{line}</p>")

    if in_list:
        html_parts.append("</ul>")
    return "\n".join(html_parts)


def image_to_base64(path):
    with open(path, "rb") as img_f:
        return base64.b64encode(img_f.read()).decode("utf-8")

def export_eda_report_to_pdf(eda_sections, df, summary_response, dataset_name):
    """Tạo file PDF báo cáo EDA hoàn chỉnh và trả về dạng bytes để tải xuống."""

    img_dir = "temp_images"
    os.makedirs(img_dir, exist_ok=True)

    # --- Load icons ---
    icon_dir = "assets/icon"
    icon_intro = image_to_base64(os.path.join(icon_dir, "book.png"))
    icon_quality = image_to_base64(os.path.join(icon_dir, "broom.png"))
    icon_uni = image_to_base64(os.path.join(icon_dir, "search.png"))
    icon_corr = image_to_base64(os.path.join(icon_dir, "combo-chart.png"))
    icon_final = image_to_base64(os.path.join(icon_dir, "idea.png"))

    # --- Render Univariate Charts ---
    univariate_html = ""
    for idx, block in enumerate(eda_sections.get("univariate", [])):
        img_path = os.path.join(img_dir, f"univar_{idx}.png")
        try:
            exec(block['code'], {"df": df, "plt": plt, "sns": sns})
            plt.savefig(img_path)
            plt.clf()
            with open(img_path, "rb") as img_f:
                img_base64 = base64.b64encode(img_f.read()).decode("utf-8")
            chart_img = f'<img src="data:image/png;base64,{img_base64}" style="width:600px;">'
        except Exception as e:
            chart_img = f"<p><em>Chart error: {e}</em></p>"

        univariate_html += f"""
        <h4>{block['insight']}</h4>
        <pre><code>{block['code']}</code></pre>
        {chart_img}
        <p><em>{block.get('insight_after_chart', '')}</em></p>
        <hr>
        """

    # --- Correlation Heatmap ---
    cor_img_path = os.path.join(img_dir, "correlation.png")
    try:
        exec(eda_sections['correlation']['code'], {"df": df, "plt": plt, "sns": sns})
        plt.savefig(cor_img_path)
        plt.clf()
        with open(cor_img_path, "rb") as img_f:
            cor_base64 = base64.b64encode(img_f.read()).decode("utf-8")
        cor_html = f"""
        <pre><code>{eda_sections['correlation']['code']}</code></pre>
        <img src="data:image/png;base64,{cor_base64}" style="width:600px;">
        <p><em>{eda_sections['correlation'].get('insight_after_chart', '')}</em></p>
        """
    except Exception as e:
        cor_html = f"<p><em>Heatmap error: {e}</em></p>"

    # --- Compose HTML ---
    html_report = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        h2 {{ color: #2c3e50; }}
        pre {{ background-color: #f8f8f8; padding: 10px; border-left: 3px solid #ccc; white-space: pre-wrap; word-wrap: break-word; }}
        img {{ margin: 10px 0; }}
        .icon-title {{
            vertical-align: middle;
            width: 24px;
            margin-right: 8px;
        }}
    </style>
    </head>
    <body>
        <h2><img src="data:image/png;base64,{icon_intro}" class="icon-title">Introduction</h2>
        <p>{eda_sections['introduction']}</p>

        <h2><img src="data:image/png;base64,{icon_quality}" class="icon-title">Data Quality</h2>
        <p>{eda_sections['data_quality']}</p>

        <h2><img src="data:image/png;base64,{icon_uni}" class="icon-title">Univariate Analysis</h2>
        {univariate_html}

        <h2><img src="data:image/png;base64,{icon_corr}" class="icon-title">Correlation Insights</h2>
        <p>{eda_sections['correlation']['insight']}</p>
        {cor_html}

        <h2><img src="data:image/png;base64,{icon_final}" class="icon-title">Final Insights & Recommendations</h2>
        <div class="final-section">
        {format_summary_to_html(summary_response)}
        </div>

    </body>
    </html>
    """

    # --- Export PDF ---
    html_dir = os.path.join("report", "html")
    os.makedirs(html_dir, exist_ok=True)

    html_file = os.path.join(html_dir, f"eda_report_{uuid4().hex}.html")
    pdf_file = html_file.replace(".html", ".pdf")

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_report)

    try:
        pdfkit.from_file(html_file, pdf_file, configuration=pdfkit_config)
        with open(pdf_file, "rb") as f:
            pdf_bytes = f.read()
    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {e}")

    # --- Cleanup ---
    try:
        shutil.rmtree(img_dir)
        os.remove(html_file)
        os.remove(pdf_file)
    except Exception:
        pass

    return pdf_bytes