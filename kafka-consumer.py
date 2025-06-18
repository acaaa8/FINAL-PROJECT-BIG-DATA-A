import json
import base64
import cv2
import numpy as np
from kafka import KafkaConsumer
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
import os
from datetime import datetime

# CONFIG
TOPIC_NAME = 'raw-images'
MODEL_PATH = '/home/iryandae/kafka_2.13-3.7.0/FP/model/har_cnn_model.h5'
LABEL_MAP_PATH = '/home/iryandae/kafka_2.13-3.7.0/FP/label_map.json'
OUTPUT_FILE = '/home/iryandae/kafka_2.13-3.7.0/FP/output/predictions.json'
IMAGE_SIZE = 64
os.makedirs('output', exist_ok=True)

# Load CNN model and label map
model = load_model(MODEL_PATH)
with open(LABEL_MAP_PATH, 'r') as f:
    label_map = json.load(f)
idx_to_label = {v: k for k, v in label_map.items()}

# Initialize Kafka Consumer
consumer = KafkaConsumer(
    TOPIC_NAME,
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

print("🎯 Kafka Consumer is running and listening...")

# Process stream
for message in consumer:
    try:
        data = message.value
        img_bytes = base64.b64decode(data['image'])
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
        img = img_to_array(img) / 255.0
        img = np.expand_dims(img, axis=0)

        # Predict
        predictions = model.predict(img)
        predicted_class = int(np.argmax(predictions))
        label = idx_to_label[predicted_class]
        confidence = float(np.max(predictions))

        result = {
            'filename': data.get('filename', 'unknown'),
            'prediction': label,
            'confidence': round(confidence, 4),
            'timestamp': datetime.now().isoformat()
        }

        print(f"✅ {result['filename']}: {label} ({confidence:.2f})")

        # Simpan ke file JSON (append mode)
        with open('output/predictions.json', 'a') as f:
            f.write(json.dumps(result) + '\n')

    except Exception as e:
        print(f"❌ Error processing message: {e}")
