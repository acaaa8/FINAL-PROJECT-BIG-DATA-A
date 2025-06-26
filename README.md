# FINAL-PROJECT-BIG-DATA-A

## Anggota Kelompok:

| Nama                            | NRP        |
| ------------------------------- | ---------- |
| Fadlillah Cantika Sari Hermawan | 5027231042 |
| Elgracito Iryanda Endia         | 5027231057 |
| Syela Zeruya T. L.              | 5027231076 |

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
├── train-mode.py            # Melatih model dan disimpan
├── kafka-producer.py        # Mengirim gambar ke Kafka
├── kafka-consumer.py        # Menerima dan memproses gambar
├── dashboard.py             # Menampilkan hasil prediksi
├── model/
│   └── model.h.5            # Model CNN yang telah dilatih
├── data/
│   └── Training_set.csv     # Metadata gambar training
└── requirements.txt
└── label_map.json           # List label klasifikasi gambar berdasarkan data training
```

### Struktur Proyek di MinIO

```
FINAL-PROJECT
├── training/
│   └── image_name.jpg       # File jpg untuk training
├── test/
│   └── image_name.jpg       # File jpg untuk test
├── output/
│   └──image_name.jpg.json   # File hasil prediksi per gambar
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

### 1. Train Model

Sebelum menjalankan pipeline, model dilatih terlebih dahulu. Skrip ini akan membaca data dari MinIO, melatih model, dan menyimpan file model .h5 ke folder model/

### 2. Jalankan Kafka Producer

Skrip ini akan membaca gambar dari MinIO (folder test/) dan mengirimkannya satu per satu ke topic Kafka raw-images sebagai simulasi input data secara real-time

```
python3 kafka-producer.py
```

![image](https://github.com/user-attachments/assets/58ecaa95-4784-4074-8337-b216aa0f9ad1)

### 3. Jalankan Kafka Consumer

Menerima pesan gambar dari Kafka, melakukan preprocessing, menjalankan prediksi dengan model yang sudah dilatih, dan menyimpan hasil prediksi (dalam format JSON) ke MinIO di folder output/

```
python3 kafka-consumer.py
```

![image](https://github.com/user-attachments/assets/d9b818ce-a36c-4f97-b63a-a20abf730bf7)

### 4. Jalankan Dashboard Streamlit

Akses dashboard dengan menjalankan _command_ berikut:

```
streamlit run dashboard.py
```

Dashboard akan otomatis memuat ulang data prediksi dari MinIO setiap beberapa detik dan menampilkan:

- Distribusi aktivitas
![Cuplikan layar 2025-06-27 054623](https://github.com/user-attachments/assets/f03a81aa-7573-4be8-b222-902f11ed93b6)

- Tabel event log: file name, aktivitas, confidence, dan timestamp
![Cuplikan layar 2025-06-27 054813](https://github.com/user-attachments/assets/272938e4-40a0-426a-bfc7-97c637807a9d)

- Upload Gambar: Untuk mengunggah gambar baru secara langsung dari dashboard untuk diproses oleh pipeline
![image](https://github.com/user-attachments/assets/fcd9ca9d-30b8-4f0f-8483-09a48387da36)

## Model yang Digunakan

Proyek ini menggunakan model Convolutional Neural Network (CNN) yang dibangun dengan TensorFlow/Keras. Arsitektur ini dirancang khusus untuk tugas klasifikasi gambar dan terdiri dari beberapa komponen utama:

- **Blok Konvolusi:** Beberapa tumpukan lapisan Conv2D untuk mengekstraksi fitur visual dari gambar, mulai dari tepi dan tekstur sederhana hingga bentuk dan objek yang kompleks.
- **Batch Normalization:** Digunakan setelah setiap lapisan konvolusi untuk menstabilkan dan mempercepat proses training.
- **MaxPooling:** Meringkas fitur dan mengurangi dimensi gambar.
- **Dropout:** Teknik regularisasi yang kuat untuk mencegah model overfitting (terlalu menghafal data training).
- **Classifier Head:** Lapisan Dense untuk membuat keputusan akhir, dengan lapisan output menggunakan aktivasi softmax untuk menghasilkan probabilitas prediksi untuk setiap kelas aktivitas.

Model ini dilatih untuk mengatasi ketidakseimbangan kelas dalam dataset dengan menggunakan class_weight, memastikan model dapat mengenali semua aktivitas dengan baik, bukan hanya yang paling umum.
