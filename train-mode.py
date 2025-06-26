import os
import cv2
import json
import numpy as np
import pandas as pd
from tqdm import tqdm
from minio import Minio
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.optimizers import Adam

# CONFIG
IMAGE_SIZE = 64
BATCH_SIZE = 64
EPOCHS = 50
BUCKET = 'training-images'
FOLDER = 'train/'
CSV_LABELS = 'D:\\fp big data\\FINAL-PROJECT-BIG-DATA-A\\data\\Training_set.csv'
MODEL_PATH = 'D:\\fp big data\\FINAL-PROJECT-BIG-DATA-A\\model\\model.h5'
LABEL_MAP_PATH = 'label_map.json'

# --- INISIALISASI MINIO CLIENT --- #
print("⏳ Menghubungkan ke MinIO...")
client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)
print("✅ Terhubung ke MinIO.")

# --- MEMUAT DATA DAN LABEL ---
print("⏳ Memuat label dari file CSV...")
try:
    df = pd.read_csv(CSV_LABELS)
    filename_to_label = dict(zip(df['filename'], df['label']))
    print(f"✅ Berhasil memuat {len(filename_to_label)} label.")
except FileNotFoundError:
    print(f"❌ Error: File CSV tidak ditemukan di '{CSV_LABELS}'. Pastikan path sudah benar.")
    exit()

X, y = [], []

# Memuat gambar dari MinIO
print(f"📥 Memuat gambar training dari MinIO (Bucket: {BUCKET}, Prefix: {FOLDER})...")
objects = client.list_objects(BUCKET, prefix=FOLDER, recursive=True)
# Mengubah iterator menjadi list agar tqdm bisa menampilkan progress bar total
object_list = list(objects) 

for obj in tqdm(object_list, desc="Processing images"):
    # Pastikan objek adalah file gambar
    if not obj.object_name.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue

    filename = os.path.basename(obj.object_name)
    if filename not in filename_to_label:
        continue

    label = filename_to_label[filename]
    try:
        response = client.get_object(BUCKET, obj.object_name)
        img_bytes = np.frombuffer(response.read(), np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

        if img is None:
            print(f"⚠️ Gagal decode gambar: {filename}")
            continue

        # Preprocessing gambar
        img = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
        img = img.astype("float32") / 255.0
        X.append(img)
        y.append(label)
    except Exception as e:
        print(f"❌ Error saat memuat gambar {filename}: {e}")

X = np.array(X)
print(f"\n✅ Selesai memuat {len(X)} gambar.")

# --- ENCODE LABEL DAN SPLIT DATA ---
print("⏳ Melakukan encoding label dan pemisahan data...")
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
num_classes = len(label_encoder.classes_)
y_onehot = to_categorical(y_encoded, num_classes=num_classes)

# Simpan label map untuk digunakan oleh consumer
label_map = {label: int(idx) for idx, label in enumerate(label_encoder.classes_)}

# Split data menjadi training dan validation set
X_train, X_val, y_train, y_val = train_test_split(
    X, y_onehot, test_size=0.2, stratify=y_encoded, random_state=42
)
print(f"✅ Data siap: {len(X_train)} train, {len(X_val)} validation.")
print(f"Total kelas: {num_classes}")

# --- AUGMENTASI GAMBAR ---
# Membuat lebih banyak variasi data training untuk membuat model lebih robust
datagen = ImageDataGenerator(
    rotation_range=20,
    zoom_range=0.15,
    width_shift_range=0.2,
    height_shift_range=0.2,
    shear_range=0.15,
    horizontal_flip=True,
    fill_mode="nearest"
)

# --- MEMBANGUN MODEL CNN YANG LEBIH BAIK ---
print("🏗️  Membangun model CNN baru...")
model = Sequential([
    # Blok Konvolusi 1
    Conv2D(32, (3, 3), activation='relu', padding='same', input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3)),
    BatchNormalization(),
    Conv2D(32, (3, 3), activation='relu', padding='same'),
    BatchNormalization(),
    MaxPooling2D(pool_size=(2, 2)),
    Dropout(0.25),

    # Blok Konvolusi 2
    Conv2D(64, (3, 3), activation='relu', padding='same'),
    BatchNormalization(),
    Conv2D(64, (3, 3), activation='relu', padding='same'),
    BatchNormalization(),
    MaxPooling2D(pool_size=(2, 2)),
    Dropout(0.25),
    
    # Blok Konvolusi 3
    Conv2D(128, (3, 3), activation='relu', padding='same'),
    BatchNormalization(),
    Conv2D(128, (3, 3), activation='relu', padding='same'),
    BatchNormalization(),
    MaxPooling2D(pool_size=(2, 2)),
    Dropout(0.25),

    # Classifier Head
    Flatten(),
    Dense(512, activation='relu'),
    BatchNormalization(),
    Dropout(0.5),
    Dense(num_classes, activation='softmax') # Output layer
])

model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

model.summary()

# --- CALLBACKS UNTUK TRAINING ---
# Callbacks ini membantu proses training menjadi lebih efisien
callbacks = [
    # Hentikan training jika tidak ada peningkatan di val_loss setelah 5 epoch
    EarlyStopping(patience=10, monitor='val_loss', restore_best_weights=True),
    # Simpan hanya model terbaik berdasarkan val_accuracy
    ModelCheckpoint(MODEL_PATH, save_best_only=True, monitor='val_accuracy', mode='max', verbose=1),
    # Kurangi learning rate jika tidak ada peningkatan
    ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5, min_lr=0.00001)
]

# --- MELATIH MODEL ---
print("\n🚀 Memulai proses training model...")
history = model.fit(
    datagen.flow(X_train, y_train, batch_size=BATCH_SIZE),
    validation_data=(X_val, y_val),
    epochs=EPOCHS,
    callbacks=callbacks,
    verbose=1
)

# --- MENYIMPAN HASIL ---
# Model terbaik sudah disimpan oleh ModelCheckpoint, jadi kita hanya perlu menyimpan label map.
print(f"💾 Menyimpan label map ke '{LABEL_MAP_PATH}'...")
with open(LABEL_MAP_PATH, 'w') as f:
    json.dump(label_map, f, indent=4)

print("\n✅ Proses training selesai! Model terbaik dan label map telah disimpan.")