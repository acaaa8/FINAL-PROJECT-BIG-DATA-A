# FINAL-PROJECT-BIG-DATA-A
## Anggota Kelompok:
|             Nama              |     NRP    |
|-------------------------------|------------|
| Fadlillah Cantika Sari Hermawan| 5027231042 |
| Elgracito Iryanda Endia       | 5027231057 |
| Syela Zeruya T. L.      | 5027231076 |

# Human Activity Recognition - Kafka Lakehouse Pipeline

Proyek ini adalah implementasi alur kerja Human Activity Recognition (HAR) berbasis citra menggunakan pendekatan Data Lakehouse dan stream processing dengan Apache Kafka. 
Hasil prediksi dianalisis secara real-time dan divisualisasikan pada dashboard interaktif menggunakan Streamlit.

## Deskripsi Masalah
Dalam dunia kesehatan, pemantauan aktivitas harian individu – terutama lansia atau pasien dalam pengawasan – menjadi hal yang krusial untuk menjaga kualitas hidup, mendeteksi perubahan perilaku, serta mencegah risiko fisik dan mental. Aktivitas pasif berlebihan seperti duduk terlalu lama, tidur di luar waktu normal, atau menatap layar dalam jangka waktu panjang sering dikaitkan dengan peningkatan risiko penyakit kronis, gangguan tidur, dan gangguan psikologis seperti kecemasan atau depresi.

## Tujuan Proyek
- Membangun model klasifikasi aktivitas berbasis citra yang akurat.
- Mengenali perilaku pengguna dari gambar aktivitas secara otomatis.
- Mendeteksi aktivitas tidak sehat (misalnya duduk terlalu lama, menatap layar komputer secara berlebihan, atau pola tidur abnormal) melalui analisis persentase dan log aktivitas yang dilakukan.

## Dataset yang digunakan
https://www.kaggle.com/datasets/meetnagadia/human-action-recognition-har-dataset

Dataset ini berisi gambar-gambar aktivitas manusia yang sudah dilabeli ke dalam 15 kategori, lengkap dengan file metadata. Dataset ini ringan, terstruktur, dan sangat cocok digunakan untuk membangun model klasifikasi citra berbasis deep learning. Selain itu, dataset ini ideal untuk implementasi pipeline data lakehouse dan pemrosesan real-time seperti Kafka dan Streamlit, terutama dalam konteks pemantauan aktivitas untuk keperluan kesehatan atau keamanan.
  
## Arsitektur

![arsitektur FP](https://github.com/user-attachments/assets/25281628-0d15-4913-a356-0dbc4b3d181a)

## Struktur Proyek
```
FINAL-PROJECT-BIG-DATA-A/
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
└── label_map.json           # List label klasifikasi gambar berdasarkan data training
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
python3 kafka-producer.py
```
Producer akan membaca file gambar dari folder dan mengirimkannya ke topic `raw-images`.

![image](https://github.com/user-attachments/assets/58ecaa95-4784-4074-8337-b216aa0f9ad1)

### 2. Jalankan Kafka Consumer
Menerima gambar, menjalankan prediksi dengan model CNN, lalu menyimpan hasil ke `predictions.json`:
```
python3 kafka-consumer.py
```

![image](https://github.com/user-attachments/assets/d9b818ce-a36c-4f97-b63a-a20abf730bf7)

### 3. Jalankan Dashboard Streamlit
Akses dashboard dengan menjalankan *command* berikut:
```
streamlit run dashboard.py
```
Dashboard akan otomatis memuat ulang setiap 10 detik dan menampilkan:

- Distribusi aktivitas (%)

![image](https://github.com/user-attachments/assets/baf2bf10-677c-4686-a757-dd70cb2b148d)

![Cuplikan layar 2025-06-20 120333](https://github.com/user-attachments/assets/017dec16-821f-43ad-9115-0532d0f26139)
  
- Tabel event log: file name, aktivitas, confidence, dan timestamp

![image](https://github.com/user-attachments/assets/4328becb-775d-4e62-b62c-177bd6dbf71b)

![Cuplikan layar 2025-06-20 120423](https://github.com/user-attachments/assets/0344c342-2b5f-4c73-98ae-67d8ec45ee61)

