from minio import Minio
from kafka import KafkaProducer
import json, base64, os, time
from tqdm import tqdm

BUCKET = 'training-images'
PREFIX = 'test/'
TOPIC = 'raw-images'
MINIO_CLIENT = Minio('localhost:9000', access_key='minioadmin', secret_key='minioadmin', secure=False)

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

try:
    print("🚀 Mengirim gambar dari MinIO ke Kafka...")

    objects = list(MINIO_CLIENT.list_objects(BUCKET, prefix=PREFIX, recursive=True))

    for obj in tqdm(objects):
        if not obj.object_name.lower().endswith(('.jpg', '.jpeg', '.png')): continue

        response = MINIO_CLIENT.get_object(BUCKET, obj.object_name)
        img_bytes = response.read()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        filename = os.path.basename(obj.object_name)

        message = {
            "filename": filename,
            "image": img_b64
        }

        producer.send(TOPIC, value=message)
        time.sleep(0.1)

finally:
    print("\n -> Memastikan semua pesan terkirim dan menutup koneksi producer...")
    producer.flush()
    producer.close()
    print("✅ Semua gambar sudah dikirim dan koneksi ditutup.")

print("\n--- Producer selesai dengan tugasnya dan sekarang dalam mode idle. ---")
try:
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    print("\n--- Producer dihentikan. ---")
