import os
import cv2
import numpy as np
import pandas as pd
from tqdm import tqdm
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.utils import to_categorical
from sklearn.model_selection import train_test_split
import json

# CONFIG
IMAGE_SIZE = 64
IMAGE_FOLDER = '/home/iryandae/kafka_2.13-3.7.0/FP/data/Training_set'
CSV_LABELS = '/home/iryandae/kafka_2.13-3.7.0/FP/data/Training_set.csv'
MODEL_NAME = '/home/iryandae/kafka_2.13-3.7.0/FP/model/har_cnn_model.h5'

# Load dataset from CSV
def load_dataset_from_csv(image_folder, csv_file):
    df = pd.read_csv(csv_file)
    X = []
    y = []
    label_set = sorted(df['label'].unique())
    label_map = {label: idx for idx, label in enumerate(label_set)}

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Loading images"):
        img_path = os.path.join(image_folder, row['filename'])
        label = row['label']
        if not os.path.exists(img_path):
            continue
        img = cv2.imread(img_path)
        if img is None:
            continue
        img = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
        X.append(img)
        y.append(label_map[label])

    X = np.array(X) / 255.0
    y = to_categorical(y, num_classes=len(label_map))
    return X, y, label_map

# Build CNN Model
def build_model(num_classes):
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3)),
        MaxPooling2D((2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        Flatten(),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model

# Main pipeline
X, y, label_map = load_dataset_from_csv(IMAGE_FOLDER, CSV_LABELS)
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

model = build_model(num_classes=y.shape[1])
model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=10, batch_size=32)

# Save model and label map
model.save(MODEL_NAME)
with open('label_map.json', 'w') as f:
    json.dump(label_map, f)

print(f"✅ Model saved to {MODEL_NAME}")
print(f"✅ Label map saved to label_map.json")
