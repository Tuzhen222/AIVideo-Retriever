import csv
import json
import os
from pathlib import Path

def extract_fps_from_csv(csv_path):
    """Extract fps value from a CSV file"""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Read first row to get fps value
            first_row = next(reader, None)
            if first_row and 'fps' in first_row:
                return float(first_row['fps'])
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        return None
    return None

def create_fps_mapping():
    """Create JSON mapping of video IDs to their fps values"""
    base_dir = Path(__file__).parent.parent / 'data'
    
    fps_map = {}
    
    # Process map-keyframes-b1
    b1_dir = base_dir / 'map-keyframes-b1' / 'map-keyframes'
    if b1_dir.exists():
        for csv_file in sorted(b1_dir.glob('*.csv')):
            video_id = csv_file.stem  # e.g., "L01_V001"
            fps = extract_fps_from_csv(csv_file)
            if fps is not None:
                fps_map[video_id] = fps
                print(f"Processed {video_id}: {fps} fps")
    
    # Process map-keyframes-b2
    b2_dir = base_dir / 'map-keyframes-b2' / 'map-keyframes'
    if b2_dir.exists():
        for csv_file in sorted(b2_dir.glob('*.csv')):
            video_id = csv_file.stem  # e.g., "L13_V011"
            fps = extract_fps_from_csv(csv_file)
            if fps is not None:
                fps_map[video_id] = fps
                print(f"Processed {video_id}: {fps} fps")
    
    return fps_map

if __name__ == '__main__':
    print("Extracting fps values from CSV files...")
    fps_mapping = create_fps_mapping()
    
    # Save to JSON file
    output_path = Path(__file__).parent.parent / 'data' / 'fps_mapping.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(fps_mapping, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Created fps_mapping.json with {len(fps_mapping)} entries")
    print(f"Output file: {output_path}")

