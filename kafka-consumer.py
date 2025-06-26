import json
import base64
import cv2
import numpy as np
import os
from kafka import KafkaConsumer
from datetime import datetime
from minio import Minio
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from io import BytesIO

MODEL_PATH = 'D:\\fp big data\\FINAL-PROJECT-BIG-DATA-A\\model\\model.h5'
LABEL_MAP_PATH = 'D:\\fp big data\\FINAL-PROJECT-BIG-DATA-A\\label_map.json'
IMAGE_SIZE = 64
BATCH_SIZE = 100
TOPIC = 'raw-images'
BUCKET = 'training-images'
OUTPUT_PREFIX = 'output/'

# --- INISIALISASI ---

print("⏳ Memuat model dan konfigurasi...")
try:
    # Memuat model Keras yang sudah dilatih
    model = load_model(MODEL_PATH)

    # Memuat mapping dari indeks ke label kelas
    with open(LABEL_MAP_PATH) as f:
        label_map = json.load(f)
    idx_to_label = {v: k for k, v in label_map.items()}
    print(f"✅ Model '{MODEL_PATH}' dan label map berhasil dimuat.")
except Exception as e:
    print(f"❌ Gagal memuat model atau label map: {e}")
    exit()

# Inisialisasi Kafka Consumer
print("⏳ Menghubungkan ke Kafka...")
consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest', # Membaca dari pesan paling awal jika consumer baru
    consumer_timeout_ms=30000 # Timeout setelah 30 detik jika tidak ada pesan baru
)
print(f"✅ Terhubung ke Kafka dan memantau topic '{TOPIC}'.")

# Inisialisasi MinIO Client
print("⏳ Menghubungkan ke MinIO...")
minio_client = Minio(
    'localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False
)

# Pastikan bucket tujuan ada, jika tidak, buat bucket baru
if not minio_client.bucket_exists(BUCKET):
    minio_client.make_bucket(BUCKET)
    print(f"✅ Bucket '{BUCKET}' berhasil dibuat di MinIO.")
else:
    print(f"✅ Terhubung ke MinIO dan bucket '{BUCKET}' sudah ada.")

# Buffer untuk menampung gambar dan metadata sebelum diproses secara batch
img_buf, meta_buf = [], []

print("\n🚀 Memulai proses konsumsi pesan dari Kafka...\n")

# --- LOOP KONSUMSI PESAN ---

for msg in consumer:
    try:
        data = msg.value
        
        # 1. Decode gambar dari base64
        img_data = base64.b64decode(data['image'])
        img_np = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

        if img is None:
            print(f"⚠️ Gagal decode gambar: {data.get('filename', 'unknown')}")
            continue

        # 2. Preprocessing gambar agar sesuai dengan input model
        img_resized = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
        img_array = img_to_array(img_resized) / 255.0

        # 3. Tambahkan gambar dan metadatanya ke buffer
        img_buf.append(img_array)
        meta_buf.append({
            'filename': data.get('filename', 'unknown.jpg'),
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"📥 Diterima: {data.get('filename', 'unknown.jpg')}, Ukuran batch saat ini: {len(img_buf)}/{BATCH_SIZE}")

        # 4. Jika buffer sudah penuh, lakukan prediksi secara batch
        if len(img_buf) >= BATCH_SIZE:
            print(f"\n🧠 Buffer penuh. Melakukan prediksi untuk {len(img_buf)} gambar...")
            batch = np.array(img_buf)
            predictions = model.predict(batch)

            # 5. Proses setiap hasil prediksi dalam batch
            for i, pred in enumerate(predictions):
                # Dapatkan label dan confidence score
                pred_idx = int(np.argmax(pred))
                label = idx_to_label.get(pred_idx, "tidak dikenal")
                confidence = float(np.max(pred))

                # Siapkan hasil dalam format JSON
                result = {
                    'filename': meta_buf[i]['filename'],
                    'prediction': label,
                    'confidence': round(confidence, 4),
                    'timestamp': meta_buf[i]['timestamp']
                }

                # 6. Upload hasil prediksi ke MinIO secara efisien (in-memory)
                json_bytes = json.dumps(result, indent=2).encode('utf-8')
                json_stream = BytesIO(json_bytes)
                
                # Nama file output di MinIO (contoh: output/image_01.jpg.json)
                object_name = f"{OUTPUT_PREFIX}{result['filename']}.json"

                minio_client.put_object(
                    bucket_name=BUCKET,
                    object_name=object_name,
                    data=json_stream,
                    length=len(json_bytes),
                    content_type='application/json'
                )
                print(f"    ✅ Prediksi untuk '{result['filename']}' ({label}) berhasil diunggah ke MinIO.")

            # Kosongkan buffer setelah batch diproses
            img_buf.clear()
            meta_buf.clear()
            print(" emptied.\n")

    except json.JSONDecodeError:
        print("❌ Error: Pesan bukan format JSON yang valid.")
    except Exception as e:
        print(f"❌ Terjadi error tak terduga: {e}")

print("\n🏁 Consumer berhenti (timeout atau diinterupsi).")
