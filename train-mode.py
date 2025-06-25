from minio import Minio
import os, cv2, json
import numpy as np, pandas as pd
from tqdm import tqdm
from io import BytesIO
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Reshape, LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# CONFIG
IMAGE_SIZE = 64
BUCKET = 'training-images'
FOLDER = 'train/'
CSV_LABELS = 'D:/FINAL-PROJECT-BIG-DATA-A-main/data/Training_set.csv'
MODEL_PATH = 'model/har_cnn_lstm_model.h5'
LABEL_MAP_PATH = 'label_map.json'

# MinIO Client 
client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)

# Load Labels
df = pd.read_csv(CSV_LABELS)
filename_to_label = dict(zip(df['filename'], df['label']))

X, y = [], []

# Load Images from MinIO
print("📥 Loading training images from MinIO...")
objects = client.list_objects(BUCKET, prefix=FOLDER, recursive=True)
for obj in tqdm(objects):
    filename = os.path.basename(obj.object_name)
    if filename not in filename_to_label:
        continue

    label = filename_to_label[filename]
    try:
        response = client.get_object(BUCKET, obj.object_name)
        img_bytes = np.frombuffer(response.read(), np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
        if img is None: continue

        img = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
        img = img.astype("float32") / 255.0
        X.append(img)
        y.append(label)
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")

X = np.array(X)

# Encode Labels 
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
y_onehot = to_categorical(y_encoded)
label_map = {label: int(idx) for idx, label in enumerate(label_encoder.classes_)}

# Split Data 
X_train, X_val, y_train, y_val = train_test_split(X, y_onehot, test_size=0.2, stratify=y_encoded, random_state=42)

# Augmentasi
datagen = ImageDataGenerator(
    rotation_range=10,
    zoom_range=0.15,
    width_shift_range=0.1,
    height_shift_range=0.1,
    horizontal_flip=True,
    brightness_range=(0.8, 1.2)
)

# CNN + LSTM MODEL 
model = Sequential([
    Conv2D(32, (3, 3), activation='relu', input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3)),
    MaxPooling2D((2, 2)),
    Conv2D(64, (3, 3), activation='relu'),
    MaxPooling2D((2, 2)),
    Reshape((-1, 64)),  # e.g., (16x16x64) → (256, 64)
    LSTM(64),
    Dense(64, activation='relu'),
    Dense(len(label_map), activation='softmax')
])

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# Callbacks 
callbacks = [
    EarlyStopping(patience=5, monitor='val_loss', restore_best_weights=True),
    ModelCheckpoint(MODEL_PATH, save_best_only=True, monitor='val_accuracy', verbose=1)
]

# Train 
print("🚀 Training CNN + LSTM model...")
model.fit(
    datagen.flow(X_train, y_train, batch_size=32),
    validation_data=(X_val, y_val),
    epochs=50,
    callbacks=callbacks,
    verbose=1
)

# Save 
model.save(MODEL_PATH)
with open(LABEL_MAP_PATH, 'w') as f:
    json.dump(label_map, f)

print("✅ Model & label_map saved.")
