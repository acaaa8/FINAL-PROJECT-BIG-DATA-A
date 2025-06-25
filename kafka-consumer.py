import json, base64, cv2, numpy as np, os
from kafka import KafkaConsumer
from datetime import datetime
from minio import Minio
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array

MODEL_PATH = 'D:\FINAL-PROJECT-BIG-DATA-A-main\model\har_efficientnet_model.h5'
LABEL_MAP_PATH = 'D:\FINAL-PROJECT-BIG-DATA-A-main\label_map.json'
IMAGE_SIZE = 96
BATCH_SIZE = 100
TOPIC = 'raw-images'
BUCKET = 'training-images'
OUTPUT_PREFIX = 'output/'

model = load_model(MODEL_PATH)
with open(LABEL_MAP_PATH) as f:
    label_map = json.load(f)
idx_to_label = {v: k for k, v in label_map.items()}

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)
minio_client = Minio('localhost:9000', access_key='minioadmin', secret_key='minioadmin', secure=False)
if not minio_client.bucket_exists(BUCKET):
    minio_client.make_bucket(BUCKET)

img_buf, meta_buf = [], []

for msg in consumer:
    try:
        data = msg.value
        img_data = base64.b64decode(data['image'])
        img_np = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
        img = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
        img = img_to_array(img) / 255.0

        img_buf.append(img)
        meta_buf.append({
            'filename': data.get('filename', 'unknown'),
            'timestamp': datetime.now().isoformat()
        })

        if len(img_buf) >= BATCH_SIZE:
            batch = np.array(img_buf)
            preds = model.predict(batch)

            for i, pred in enumerate(preds):
                label = idx_to_label[int(np.argmax(pred))]
                conf = float(np.max(pred))
                result = {
                    'filename': meta_buf[i]['filename'],
                    'prediction': label,
                    'confidence': round(conf, 4),
                    'timestamp': meta_buf[i]['timestamp']
                }

                temp = 'temp_result.json'
                with open(temp, 'w') as f: json.dump(result, f)

                object_name = f"{OUTPUT_PREFIX}{result['filename']}.json"
                minio_client.fput_object(BUCKET, object_name, temp)
                print(f"✅ Uploaded {object_name}")

            img_buf.clear()
            meta_buf.clear()

    except Exception as e:
        print("❌ Error:", e)
