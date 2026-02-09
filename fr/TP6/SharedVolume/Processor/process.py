import os
import time

WATCH_DIR = "/shared"

def process_file(file_path):
    print(f"Processing file: {file_path}")
    # Simulate file processing
    with open(file_path, "r") as f:
        content = f.read()
    print("File content:")
    print(content)
    # Rename to mark as processed
    os.rename(file_path, file_path + ".processed")

def watch_directory():
    while True:
        files = [f for f in os.listdir(WATCH_DIR) if f.endswith(".txt")]
        for f in files:
            process_file(os.path.join(WATCH_DIR, f))
        time.sleep(2)

if __name__ == "__main__":
    watch_directory()
