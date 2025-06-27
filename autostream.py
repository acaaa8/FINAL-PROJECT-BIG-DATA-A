import subprocess
import time
import platform

commands = [
    ["python", "kafka-consumer.py"],
    ["python", "kafka-producer.py"],
    ["streamlit", "run", "dashboard.py"]
]

processes = []

print("🚀 Memulai semua layanan stream...")

try:
    for cmd in commands:
        print(f"   -> Memulai: {' '.join(cmd)}")
        
        if platform.system() == "Windows":
            creationflags = subprocess.CREATE_NO_WINDOW
            if "streamlit" not in cmd[0]:
                 creationflags = subprocess.CREATE_NEW_CONSOLE
        else:
            creationflags = 0

        proc = subprocess.Popen(cmd, creationflags=creationflags)
        processes.append(proc)
        time.sleep(2)

    print("\n✅ Semua layanan telah dimulai.")
    print("Tekan Ctrl+C di terminal ini untuk menghentikan SEMUA layanan.")

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n🛑 Menerima sinyal shutdown (Ctrl+C)...")
    
finally:
    print("👋 Menghentikan semua proses...")
    for proc in processes:
        print(f"   -> Menghentikan proses {proc.pid}...")
        proc.terminate()

    print("✅ Semua layanan telah dihentikan.")
