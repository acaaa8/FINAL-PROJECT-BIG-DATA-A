# FINAL-PROJECT-BIG-DATA-A

# Human Activity Recognition - Kafka Lakehouse Pipeline

Proyek ini adalah implementasi alur kerja Human Activity Recognition (HAR) berbasis citra menggunakan pendekatan Data Lakehouse dan stream processing dengan Apache Kafka. 
Hasil prediksi dianalisis secara real-time dan divisualisasikan pada dashboard interaktif menggunakan Streamlit.

## Arsitektur

![arsitektur FP](https://github.com/user-attachments/assets/25281628-0d15-4913-a356-0dbc4b3d181a)

## Struktur Proyek
```
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
```

## Prasyarat
### Buat Virtual Environment dan Install Dependensi
```
python3 -m venv venv-kafka
source venv-kafka/bin/activate
pip install -r requirements.txt
```

### Jalankan Kafka dan Zookeeper
```
# Start Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# Start Kafka broker
bin/kafka-server-start.sh config/server.properties

# Buat Kafka topic
bin/kafka-topics.sh --create --topic raw-images --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

## Langkah Eksekusi Program

### 1. Jalankan Kafka Producer
Mengirim gambar dari folder dataset ke Kafka secara bertahap sebagai simulasi input dari kamera:
```
python kafka-producer.py
```
Producer akan membaca file gambar dari folder dan mengirimkannya ke topic `raw-images`.

### 2. Jalankan Kafka Consumer
Menerima gambar, menjalankan prediksi dengan model CNN, lalu menyimpan hasil ke `predictions.json`:
```
python kafka-consumer.py
```

### 3. Jalankan Dashboard Streamlit
Akses dashboard dengan menjalankan *command* berikut:
```
streamlit run dashboard.py
```
Dashboard akan otomatis memuat ulang setiap 10 detik dan menampilkan:

- Distribusi aktivitas (%)
- Tabel event log: file name, aktivitas, confidence, dan timestamp
