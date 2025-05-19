import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import sqlite3
from datetime import datetime


DB_NAME = "db.sqlite"

def execute_plt_code(code: str, df: pd.DataFrame):
    """Execute the passing code to plot figure

    Args:
        code (str): action string (containing plt code)
        df (pd.DataFrame): our dataframe

    Returns:
        _type_: plt figure
    """
    try:
        local_vars = {"plt": plt, "df": df}
        compiled_code = compile(code, "<string>", "exec")
        exec(compiled_code, globals(), local_vars)
        return plt.gcf()
    except Exception as e:
        st.error(f"Error excuting plt code: {e}")
        return None

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Tạo bảng datasets lưu thông tin các file CSV
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
    # Tạo bảng chat_history lưu lịch sử hỏi đáp
    c.execute('''
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_id INTEGER,
        timestamp TEXT,
        question TEXT,
        answer TEXT,
        FOREIGN KEY (dataset_id) REFERENCES datasets(id)
    )''')
    # Tạo bảng chart_cards lưu insight có biểu đồ
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
    conn.commit()
    conn.close()

def add_dataset(name, path, num_rows, num_cols, upload_time, status="Uploaded"):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO datasets (name, path, num_rows, num_cols, upload_time, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, path, num_rows, num_cols, upload_time, status))
    conn.commit()
    conn.close()

def get_all_datasets():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, num_rows, num_cols, upload_time, status FROM datasets')
    datasets = c.fetchall()
    conn.close()
    return datasets

def get_dataset(id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM datasets WHERE id = ?', (id,))
    dataset = c.fetchone()
    conn.close()
    return dataset

def add_chat(dataset_id, question, answer):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO chat_history (dataset_id, timestamp, question, answer)
        VALUES (?, ?, ?, ?)
    ''', (dataset_id, timestamp, question, answer))
    conn.commit()
    conn.close()

def get_chats_by_dataset(dataset_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT timestamp, question, answer FROM chat_history WHERE dataset_id = ? ORDER BY id', (dataset_id,))
    chats = c.fetchall()
    conn.close()
    return chats

def add_chart_card(dataset_id, question, answer, code):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO chart_cards (dataset_id, question, answer, code, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (dataset_id, question, answer, code, timestamp))
    conn.commit()
    conn.close()

def get_chart_cards_by_dataset(dataset_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT question, answer, code, created_at
        FROM chart_cards
        WHERE dataset_id = ?
        ORDER BY created_at DESC
    ''', (dataset_id,))
    rows = c.fetchall()
    conn.close()
    return rows



import pandas as pd

def safe_read_csv(file_path):
    """Tries reading CSV with multiple encodings."""
    for enc in ['utf-8', 'ISO-8859-1', 'utf-16', 'cp1252']:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", b"", 0, 1, "Unable to decode file with common encodings.")

