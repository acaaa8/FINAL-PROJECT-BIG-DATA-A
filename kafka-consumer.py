import json, base64, cv2, numpy as np, os, time
from kafka import KafkaConsumer
from datetime import datetime
from minio import Minio
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from io import BytesIO

# --- KONFIGURASI ---
MODEL_PATH = 'D:\\fp big data\\FINAL-PROJECT-BIG-DATA-A\\model\\model.h5'
LABEL_MAP_PATH = 'D:\\fp big data\\FINAL-PROJECT-BIG-DATA-A\\label_map.json'
IMAGE_SIZE = 64
BATCH_SIZE = 100
BATCH_TIMEOUT_SECONDS = 5
TOPIC = 'raw-images'
BUCKET = 'training-images'
OUTPUT_PREFIX = 'output/'

# --- INISIALISASI ---
try:
    print("--- TAHAP 1: INISIALISASI ---")
    print(f"⏳ Memuat model dari: {MODEL_PATH}")
    model = load_model(MODEL_PATH)
    print(f"✅ Model berhasil dimuat.")
    
    print(f"⏳ Memuat label map dari: {LABEL_MAP_PATH}")
    with open(LABEL_MAP_PATH) as f:
        label_map = json.load(f)
    print(f"✅ Label map berhasil dimuat.")
    idx_to_label = {int(v): k for k, v in label_map.items()}

    print("⏳ Menghubungkan ke Kafka di 'localhost:9092'...")
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        consumer_timeout_ms=1000  # Cek pesan setiap 1 detik
    )
    print("✅ Berhasil terhubung ke Kafka.")

    print("⏳ Menghubungkan ke MinIO di 'localhost:9000'...")
    minio_client = Minio('localhost:9000', access_key='minioadmin', secret_key='minioadmin', secure=False)
    if not minio_client.bucket_exists(BUCKET):
        print(f"⚠️ Bucket '{BUCKET}' tidak ada. Membuatnya...")
        minio_client.make_bucket(BUCKET)
    print("✅ Berhasil terhubung ke MinIO.")

except Exception as e:
    print(f"\n❌❌❌ GAGAL PADA TAHAP INISIALISASI ❌❌❌")
    print(f"ERROR: {e}")
    print("Periksa path file model/label atau koneksi ke Kafka/MinIO. Proses dihentikan.")
    exit()

# --- FUNGSI PEMROSESAN BATCH ---
def process_batch(image_buffer, metadata_buffer):
    if not image_buffer:
        return

    print(f"\n--- TAHAP 3: PEMROSESAN BATCH ---")
    print(f"🧠 Memulai prediksi untuk {len(image_buffer)} gambar...")
    try:
        batch = np.array(image_buffer)
        predictions = model.predict(batch)
        print("    -> Prediksi model selesai.")

        for i, pred in enumerate(predictions):
            pred_idx = int(np.argmax(pred))
            label = idx_to_label.get(pred_idx, "tidak dikenal")
            filename = metadata_buffer[i]['filename']
            print(f"    -> Hasil untuk '{filename}': {label}")

            result = {
                'filename': filename,
                'prediction': label,
                'confidence': float(np.max(pred)),
                'timestamp': metadata_buffer[i]['timestamp']
            }
            json_bytes = json.dumps(result, indent=2).encode('utf-8')
            json_stream = BytesIO(json_bytes)
            object_name = f"{OUTPUT_PREFIX}{filename}.json"
            
            print(f"    -> Mengunggah hasil ke MinIO: '{object_name}'...")
            minio_client.put_object(BUCKET, object_name, data=json_stream, length=len(json_bytes), content_type='application/json')
            print(f"    ✅ Unggah untuk '{filename}' berhasil.")

    except Exception as e:
        print(f"\n❌❌❌ GAGAL SAAT MEMPROSES BATCH ❌❌❌")
        print(f"ERROR: {e}")

    image_buffer.clear()
    metadata_buffer.clear()
    print("...Buffer dikosongkan.\n")
    print("--- Menunggu pesan berikutnya... ---")


# --- LOOP KONSUMSI UTAMA ---
img_buf, meta_buf = [], []
batch_start_time = None
print(f"\n--- TAHAP 2: MENUNGGU PESAN ---")
print(f"Menunggu pesan dari topik Kafka '{TOPIC}'...")

try:
    while True:
        for msg in consumer:
            data = msg.value
            filename = data.get('filename', 'unknown.jpg')
            print(f"📥 DITERIMA: Pesan untuk file '{filename}'")

            if not batch_start_time:
                batch_start_time = time.time()

            img_data = base64.b64decode(data['image'])
            img_np = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
            
            if img is None:
                print(f"    ⚠️ GAGAL DECODE gambar '{filename}'. Pesan dilewati.")
                continue
            
            img_resized = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
            img_array = img_to_array(img_resized) / 255.0
            img_buf.append(img_array)
            meta_buf.append({'filename': filename, 'timestamp': datetime.now().isoformat()})
            print(f"    -> Gambar ditambahkan ke buffer. Ukuran buffer: {len(img_buf)}")

            if len(img_buf) >= BATCH_SIZE:
                print("    -> TRIGGER: Ukuran batch tercapai.")
                process_batch(img_buf, meta_buf)
                batch_start_time = None 

        if batch_start_time and (time.time() - batch_start_time >= BATCH_TIMEOUT_SECONDS):
            print(f"    -> TRIGGER: Timeout ({BATCH_TIMEOUT_SECONDS} detik) tercapai.")
            process_batch(img_buf, meta_buf)
            batch_start_time = None 

except KeyboardInterrupt:
    print("\n🛑 Proses dihentikan oleh pengguna.")
finally:
    if img_buf:
        print("⏳ Memproses sisa gambar di buffer sebelum keluar...")
        process_batch(img_buf, meta_buf)
    print("🏁 Consumer berhenti.")
