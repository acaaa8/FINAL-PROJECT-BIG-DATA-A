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
REFRESH_RATE_SECONDS = 10  # Auto refresh

# Load data
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

# === UI Layout ===
st.title("📊 Human Activity Recognition Dashboard")
tab1, tab2, tab3 = st.tabs(["📈 Overview", "📋 Event Log", "📊 Activity Trends"])
warning_placeholder = st.empty()
predictions = load_predictions()

if not predictions:
    time.sleep(1)
    if not load_predictions():
        warning_placeholder.warning("❗ No predictions found.")
else:
    df = pd.DataFrame(predictions)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Summary Metrics
    most_common = df['prediction'].mode()[0]
    st.metric("📂 Total Predictions", len(df))
    st.metric("🏷️ Most Frequent Activity", most_common)

    # Overview Pie Chart
    with tab1:
        st.subheader("📌 Activity Distribution")
        labels = df['prediction']
        counter = Counter(labels)
        df_percent = pd.DataFrame({
            'Activity': list(counter.keys()),
            'Count': list(counter.values())
        })
        df_percent['Percentage'] = (df_percent['Count'] / df_percent['Count'].sum() * 100).round(2)

        fig = px.pie(df_percent, names='Activity', values='Percentage', hole=0.3,
                     title='Activity Distribution (%)')
        fig.update_traces(textinfo='label+percent', textposition='inside')
        st.plotly_chart(fig, use_container_width=True)

    # Event Log
    with tab2:
        st.subheader("📋 Event Log")

        # Filter Options
        selected_activity = st.selectbox("🔍 Filter by Activity", options=["All"] + sorted(df['prediction'].unique().tolist()))
        start_date = st.date_input("Start Date", df['timestamp'].min().date())
        end_date = st.date_input("End Date", df['timestamp'].max().date())

        filtered_df = df.copy()
        if selected_activity != "All":
            filtered_df = filtered_df[filtered_df['prediction'] == selected_activity]
        filtered_df = filtered_df[(filtered_df['timestamp'].dt.date >= start_date) &
                                  (filtered_df['timestamp'].dt.date <= end_date)]

        filtered_df = filtered_df[['filename', 'prediction', 'timestamp', 'confidence']]
        filtered_df.columns = ['File Name', 'Activity', 'Timestamp', 'Confidence']

        st.dataframe(filtered_df.sort_values(by='Timestamp', ascending=False), use_container_width=True)

        # Download button
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Filtered Log as CSV", data=csv, file_name='activity_log.csv', mime='text/csv')

# Auto refresh
time.sleep(REFRESH_RATE_SECONDS)
st.rerun()
