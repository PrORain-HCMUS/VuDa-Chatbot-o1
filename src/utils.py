import matplotlib.pyplot as plt
import pandas as pd
import sqlite3
from datetime import datetime
import streamlit as st

DB_NAME = "db.sqlite"

def execute_plt_code(code: str, df: pd.DataFrame):
    try:
        local_vars = {"plt": plt, "df": df}
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
        ORDER BY created_at DESC''', (dataset_id,))
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
