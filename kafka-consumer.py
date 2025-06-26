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
BATCH_TIMEOUT_SECONDS = 5
TOPIC = 'raw-images'
BUCKET = 'training-images'
OUTPUT_PREFIX = 'output/'

# --- INISIALISASI ---
print("⏳ Memuat model dan konfigurasi...")
model = load_model(MODEL_PATH)
with open(LABEL_MAP_PATH) as f:
    label_map = json.load(f)
idx_to_label = {int(v): k for k, v in label_map.items()}

# Set consumer_timeout_ms agar loop bisa memeriksa waktu secara berkala
consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    consumer_timeout_ms=1000  # Membuat loop tidak blok selamanya, tapi cek setiap 1 detik
)

minio_client = Minio('localhost:9000', access_key='minioadmin', secret_key='minioadmin', secure=False)
if not minio_client.bucket_exists(BUCKET):
    minio_client.make_bucket(BUCKET)

print(f"\n🚀 Memulai proses konsumsi (Mode Hybrid: Batch Size={BATCH_SIZE}, Timeout={BATCH_TIMEOUT_SECONDS}s)...\n")

# Buffer dan timer
img_buf, meta_buf = [], []
batch_start_time = None

# --- FUNGSI UNTUK MEMPROSES BATCH (AGAR TIDAK DUPLIKASI KODE) ---
def process_batch(image_buffer, metadata_buffer):
    if not image_buffer:
        return

    print(f"\n🧠 Memproses batch berisi {len(image_buffer)} gambar...")
    batch = np.array(image_buffer)
    predictions = model.predict(batch)

    for i, pred in enumerate(predictions):
        pred_idx = int(np.argmax(pred))
        label = idx_to_label.get(pred_idx, "tidak dikenal")
        confidence = float(np.max(pred))
        result = {
            'filename': metadata_buffer[i]['filename'],
            'prediction': label,
            'confidence': round(confidence, 4),
            'timestamp': metadata_buffer[i]['timestamp']
        }
        json_bytes = json.dumps(result, indent=2).encode('utf-8')
        json_stream = BytesIO(json_bytes)
        object_name = f"{OUTPUT_PREFIX}{result['filename']}.json"
        minio_client.put_object(BUCKET, object_name, data=json_stream, length=len(json_bytes), content_type='application/json')
        print(f"    ✅ Prediksi untuk '{result['filename']}' ({label}) berhasil diunggah.")
    
    image_buffer.clear()
    metadata_buffer.clear()
    print("...Buffer dikosongkan.\n")


# --- LOOP KONSUMSI UTAMA ---
try:
    while True:
        # Loop ini akan berjalan terus menerus, mengambil pesan jika ada
        for msg in consumer:
            data = msg.value
            filename = data.get('filename', 'unknown.jpg')
            print(f"📥 Diterima: {filename}")

            # Mulai timer jika ini adalah pesan pertama dalam batch
            if not batch_start_time:
                batch_start_time = time.time()

            # Decode dan tambahkan ke buffer
            img_data = base64.b64decode(data['image'])
            img_np = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
            if img is None: continue
            
            img_resized = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
            img_array = img_to_array(img_resized) / 255.0
            img_buf.append(img_array)
            meta_buf.append({'filename': filename, 'timestamp': datetime.now().isoformat()})

            # TRIGGER BERDASARKAN UKURAN: Jika buffer penuh, proses sekarang
            if len(img_buf) >= BATCH_SIZE:
                process_batch(img_buf, meta_buf)
                batch_start_time = None # Reset timer

        # TRIGGER BERDASARKAN WAKTU: Cek setelah loop consumer selesai (atau timeout)
        # Jika ada sesuatu di buffer dan sudah waktunya, proses sekarang
        if batch_start_time and (time.time() - batch_start_time >= BATCH_TIMEOUT_SECONDS):
            process_batch(img_buf, meta_buf)
            batch_start_time = None # Reset timer

except KeyboardInterrupt:
    print("\n🛑 Proses dihentikan oleh pengguna.")
finally:
    # Proses sisa batch terakhir sebelum keluar
    print("⏳ Memproses sisa gambar di buffer sebelum keluar...")
    process_batch(img_buf, meta_buf)
    print("🏁 Consumer berhenti.")