import cv2
from pathlib import Path

# Adjust this path if needed
FIXTURES_DIR = Path("C:/Users/hailo/Desktop/ShakeChecker-Fork/tests/fixtures/crop")

def main():
    print(f"Looking for pngs in {FIXTURES_DIR}...")
    count = 0
    for img_path in FIXTURES_DIR.glob("*.png"):
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"Failed to read {img_path.name}")
            continue
            
        # Crop the top 48 pixels (the Windows title bar)
        cropped = img[2:, :, :]
        
        # Overwrite the original image
        cv2.imwrite(str(img_path), cropped)
        print(f"Cropped {img_path.name}")
        count += 1
        
    print(f"Done! Cropped {count} fixtures.")

if __name__ == "__main__":
    main()
