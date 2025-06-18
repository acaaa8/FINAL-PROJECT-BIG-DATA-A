# FINAL-PROJECT-BIG-DATA-A

# Human Activity Recognition - Kafka Lakehouse Pipeline

Proyek ini adalah implementasi alur kerja Human Activity Recognition (HAR) berbasis citra menggunakan pendekatan Data Lakehouse dan stream processing dengan Apache Kafka. 
Hasil prediksi dianalisis secara real-time dan divisualisasikan pada dashboard interaktif menggunakan Streamlit.

## Arsitektur

![arsitektur FP](https://github.com/user-attachments/assets/25281628-0d15-4913-a356-0dbc4b3d181a)

## Strukture Proyek
project-root/
├── kafka-producer.py        # Mengirim gambar ke Kafka
├── kafka-consumer.py        # Menerima dan memproses gambar
├── dashboard.py             # Menampilkan hasil prediksi
├── output/
│   └── predictions.json     # File hasil prediksi
├── model/
│   └── cnn_model.pth        # Model CNN yang telah dilatih
├── data/                    
│   └── Training_set.csv     # Metadata gambar training 
│   └── Training_set/        # Folder gambar training
│   └── Test/                # Folder gambar test
└── requirements.txt
