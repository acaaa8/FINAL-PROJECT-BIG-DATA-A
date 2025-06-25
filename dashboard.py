import streamlit as st
import json, base64, os
from collections import Counter
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
from kafka import KafkaProducer
from minio import Minio
from io import BytesIO

# CONFIG
BUCKET = 'training-images'
OUTPUT_PREFIX = 'output/'
REFRESH_RATE_SECONDS = 10
TOPIC = 'raw-images'

# Streamlit Setup 
st.set_page_config(page_title="Human Activity Dashboard", layout="wide")
st.title("📊 Human Activity Recognition Dashboard")
tab1, tab2, tab3 = st.tabs(["📈 Overview", "📋 Event Log", "📤 Upload Gambar"])

# Kafka Producer
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# MinIO Client 
minio_client = Minio(
    'localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False
)

# Load Predictions from MinIO 
@st.cache_data(ttl=10)
def load_predictions_from_minio():
    predictions = []
    objects = minio_client.list_objects(BUCKET, prefix=OUTPUT_PREFIX, recursive=True)
    for obj in objects:
        if not obj.object_name.endswith('.json'):
            continue
        try:
            resp = minio_client.get_object(BUCKET, obj.object_name)
            data = json.load(resp)
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
            predictions.append(data)
        except Exception as e:
            print(f"❌ Failed to load {obj.object_name}: {e}")
    return predictions

# Load and Display
predictions = load_predictions_from_minio()

if not predictions:
    st.warning("❗ No predictions found in MinIO.")
else:
    df = pd.DataFrame(predictions)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    most_common = df['prediction'].mode()[0]
    st.metric("📂 Total Predictions", len(df))
    st.metric("🏷️ Most Frequent Activity", most_common)

    # Overview (Improved Visualization)
    with tab1:
        st.subheader("📌 Activity Distribution (Bar Chart)")
        counter = Counter(df['prediction'])
        df_percent = pd.DataFrame({
            'Activity': list(counter.keys()),
            'Count': list(counter.values())
        })
        df_percent = df_percent.sort_values(by='Count', ascending=True)

        fig = px.bar(
            df_percent,
            x='Count',
            y='Activity',
            orientation='h',
            color='Activity',
            text='Count',
            color_discrete_sequence=px.colors.qualitative.Set3
        )

        fig.update_traces(
            textposition='outside',
            marker=dict(line=dict(width=1, color='DarkSlateGrey'))
        )

        fig.update_layout(
            title='📊 Jumlah Prediksi per Aktivitas',
            xaxis_title='Jumlah',
            yaxis_title='Aktivitas',
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            title_font_size=20
        )

        st.plotly_chart(fig, use_container_width=True)

    # Event Log
    with tab2:
        st.subheader("📋 Event Log")
        selected_activity = st.selectbox("🔍 Filter by Activity", options=["All"] + sorted(df['prediction'].unique()))
        start_date = st.date_input("Start Date", df['timestamp'].min().date())
        end_date = st.date_input("End Date", df['timestamp'].max().date())

        filtered_df = df.copy()
        if selected_activity != "All":
            filtered_df = filtered_df[filtered_df['prediction'] == selected_activity]
        filtered_df = filtered_df[
            (filtered_df['timestamp'].dt.date >= start_date) &
            (filtered_df['timestamp'].dt.date <= end_date)
        ]

        filtered_df = filtered_df[['filename', 'prediction', 'timestamp', 'confidence']]
        filtered_df.columns = ['File Name', 'Activity', 'Timestamp', 'Confidence']

        st.dataframe(filtered_df.sort_values(by='Timestamp', ascending=False), use_container_width=True)

        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Filtered Log as CSV", data=csv, file_name='activity_log.csv', mime='text/csv')

    # Tab 3: Upload to Kafka
    with tab3:
        st.subheader("📤 Upload Gambar ke Kafka")
        uploaded_file = st.file_uploader("Pilih file gambar", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            img_bytes = uploaded_file.read()
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            message = {
                "filename": uploaded_file.name,
                "image": img_b64
            }
            producer.send(TOPIC, value=message)
            st.success(f"📤 Gambar '{uploaded_file.name}' berhasil dikirim ke Kafka!")

# Auto Refresh
time.sleep(REFRESH_RATE_SECONDS)
st.rerun()
