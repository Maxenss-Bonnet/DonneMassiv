import time
from shutil import copyfile

def upload_file():
    while True:
        # Simulate uploading a new file every 5 seconds
        print("Uploading new file...")
        copyfile("sample.txt", "/shared/sample_uploaded.txt")
        time.sleep(5)

if __name__ == "__main__":
    upload_file()
