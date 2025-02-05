import os
import zipfile
import requests
# Define paths
base_dir = os.path.join(os.getcwd(), "Data", "BAMDataset")
os.makedirs(base_dir, exist_ok=True)  # Create directory if not exists
ZENODO_ID = "13937987"
url = f"https://zenodo.org/api/records/{ZENODO_ID}/files-archive"
zip_path = os.path.join(base_dir, f"{ZENODO_ID}.zip")
# Download the dataset
print(f"Downloading {url} to {zip_path}...")
response = requests.get(url, stream=True)
if response.status_code == 200:
    with open(zip_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024):
            file.write(chunk)
    print("Download completed.")
else:
    print(f"Failed to download: HTTP {response.status_code}")
    exit(1)


# Unzip the file if it exists
if os.path.exists(zip_path):
    print(f"Uncompressing {zip_path}...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(base_dir)
    print("Extraction completed.")
else:
    print(f"File {ZENODO_ID}.zip does not exist.")
print("Process finished.")
