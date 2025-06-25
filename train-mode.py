from minio import Minio
import os, cv2, json
import numpy as np, pandas as pd
from tqdm import tqdm
from io import BytesIO
from sklearn.model_selection import train_test_split
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.models import Model
from tensorflow.keras.layers import GlobalAveragePooling2D, Dropout, Dense, Input
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# === CONFIG
IMAGE_SIZE = 96
BUCKET = 'training-images'
FOLDER = 'train/'
CSV_LABELS = 'D:/FINAL-PROJECT-BIG-DATA-A-main/Human Action Recognition/Training_set.csv'
MODEL_PATH = 'model/har_efficientnet_model.h5'
LABEL_MAP_PATH = 'label_map.json'

# === MinIO Client
client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)

# === Load Labels
df_labels = pd.read_csv(CSV_LABELS)
filename_to_label = dict(zip(df_labels['filename'], df_labels['label']))

X, y, used_labels = [], [], []

# === Load Images from MinIO
print("📥 Loading training images from MinIO...")
objects = client.list_objects(BUCKET, prefix=FOLDER, recursive=True)
for obj in tqdm(objects):
    filename = os.path.basename(obj.object_name)
    if filename not in filename_to_label:
        continue

    label = filename_to_label[filename]
    used_labels.append(label)

    try:
        response = client.get_object(BUCKET, obj.object_name)
        img_bytes = np.frombuffer(response.read(), np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
        if img is None: continue

        img = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
        img = img.astype("float32") / 255.0  # Normalisasi
        X.append(img)
        y.append(label)
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")

# === Encode Labels
label_set = sorted(set(used_labels))
label_map = {label: idx for idx, label in enumerate(label_set)}
y_encoded = [label_map[l] for l in y]

X = np.array(X)
y = to_categorical(y_encoded, num_classes=len(label_map))

# === Train-Test Split
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y_encoded, random_state=42)

# === Augmentasi
datagen = ImageDataGenerator(
    rotation_range=15,
    zoom_range=0.15,
    width_shift_range=0.1,
    height_shift_range=0.1,
    horizontal_flip=True,
    brightness_range=(0.8, 1.2),
    fill_mode='nearest'
)

# === EfficientNetB0 + Fine-tune
base_model = EfficientNetB0(include_top=False, weights='imagenet', input_tensor=Input(shape=(IMAGE_SIZE, IMAGE_SIZE, 3)))
x = GlobalAveragePooling2D()(base_model.output)
x = Dropout(0.4)(x)
output = Dense(len(label_map), activation='softmax')(x)
model = Model(inputs=base_model.input, outputs=output)

# Fine-tune hanya layer terakhir
for layer in base_model.layers[:-20]:
    layer.trainable = False

model.compile(optimizer=Adam(1e-4), loss='categorical_crossentropy', metrics=['accuracy'])

# === Callbacks
callbacks = [
    EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
    ModelCheckpoint(MODEL_PATH, monitor='val_accuracy', save_best_only=True, verbose=1)
]

# === Train Model
print("🚀 Starting training...")
model.fit(
    datagen.flow(X_train, y_train, batch_size=32),
    validation_data=(X_val, y_val),
    epochs=30,
    callbacks=callbacks,
    verbose=1
)

# === Save Outputs
model.save(MODEL_PATH)
with open(LABEL_MAP_PATH, 'w') as f:
    json.dump(label_map, f)

print("✅ Model & label_map disimpan.")
