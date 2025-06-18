import streamlit as st
import json
import os
from collections import Counter
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

st.set_page_config(page_title="Human Activity Dashboard", layout="wide")

DATA_PATH = '/home/iryandae/kafka_2.13-3.7.0/FP/output/predictions.json'

# === CONFIGURATION ===
REFRESH_RATE_SECONDS = 10  # Auto refresh every N seconds

# === LOAD PREDICTIONS ===
def load_predictions():
    if not os.path.exists(DATA_PATH):
        return []

    predictions = []
    with open(DATA_PATH, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if 'timestamp' not in entry:
                    entry['timestamp'] = datetime.now().isoformat()
                predictions.append(entry)
            except json.JSONDecodeError:
                continue
    return predictions

# === TITLE & TABS ===
st.title("📊 Human Activity Recognition Dashboard")
tab1, tab2 = st.tabs(["📈 Overview", "📋 Event Log"])

# === LOAD DATA ===
predictions = load_predictions()
warning_placeholder = st.empty()

if not predictions:
    # Delay before showing warning to avoid flash on auto-refresh
    time.sleep(1)  # You can tune this
    if not load_predictions():  # Check again after delay
        warning_placeholder.warning("❗ No predictions found.")
else:
    # Pie Chart
    labels = [p['prediction'] for p in predictions]
    counter = Counter(labels)
    df_percent = pd.DataFrame({
        'Activity': list(counter.keys()),
        'Count': list(counter.values())
    })
    df_percent['Percentage'] = (df_percent['Count'] / df_percent['Count'].sum() * 100).round(2)

    fig = px.pie(df_percent, names='Activity', values='Percentage',
                 title='Activity Distribution (%)', hole=0.3)
    fig.update_traces(textinfo='label+percent', textposition='inside')

    with tab1:
        st.subheader("📌 Activity Distribution Overview")
        st.plotly_chart(fig, use_container_width=True)

    # Event Log
    df_log = pd.DataFrame(predictions)
    df_log['timestamp'] = pd.to_datetime(df_log['timestamp'])
    df_log = df_log[['filename', 'prediction', 'timestamp', 'confidence']]
    df_log.columns = ['File Name', 'Activity', 'Timestamp', 'Confidence']

    with tab2:
        st.subheader("📋 Detailed Event Log")
        st.dataframe(df_log.sort_values(by='Timestamp', ascending=False), use_container_width=True)

# === AUTO REFRESH ===
time.sleep(REFRESH_RATE_SECONDS)
st.rerun()
