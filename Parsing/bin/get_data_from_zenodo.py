import argparse
import os
from pathlib import Path
import zipfile

import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Download and extract BAM dataset from Zenodo.")
    parser.add_argument(
        "--zenodo-id",
        default="13937987",
        help="Zenodo record ID (default: 13937987)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join("Data", "BAMDataset"),
        help="Directory where zip file is saved and extracted (default: Data/BAMDataset)",
    )
    return parser.parse_args()


def download_file(url: str, destination: Path) -> None:
    print(f"Downloading {url} to {destination}...")
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    with destination.open("wb") as file_handle:
        for chunk in response.iter_content(chunk_size=1024 * 64):
            if chunk:
                file_handle.write(chunk)


def extract_zip(zip_path: Path, output_dir: Path) -> None:
    print(f"Uncompressing {zip_path}...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(output_dir)


def main() -> None:
    args = parse_args()

    base_dir = Path(args.output_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    zenodo_id = str(args.zenodo_id)
    url = f"https://zenodo.org/api/records/{zenodo_id}/files-archive"
    zip_path = base_dir / f"{zenodo_id}.zip"

    download_file(url, zip_path)
    print("Download completed.")

    if not zip_path.exists():
        raise FileNotFoundError(f"File does not exist: {zip_path}")

    extract_zip(zip_path, base_dir)
    print("Extraction completed.")
    print(f"Process finished. Dataset available at: {base_dir}")


if __name__ == "__main__":
    main()
