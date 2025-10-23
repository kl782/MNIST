#!/usr/bin/env python3
"""
Preprocess company data (e.g., convert CSV to JSON).
"""

import argparse
import sys
from pathlib import Path


def preprocess_folder(input_dir: Path, output_dir: Path):
    """Preprocess data files in a folder."""
    print(f"Preprocessing: {input_dir}")
    
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert CSV files to JSON
    csv_files = list(input_dir.glob('*.csv'))
    
    if csv_files:
        try:
            import pandas as pd
        except ImportError:
            print("ERROR: pandas not installed. Install with: pip install pandas")
            sys.exit(1)
        
        for csv_path in csv_files:
            json_path = output_dir / csv_path.with_suffix('.json').name
            print(f"Converting: {csv_path.name} -> {json_path.name}")
            
            try:
                df = pd.read_csv(csv_path)
                df.to_json(json_path, orient='records', indent=2)
                print(f"✓ Converted {csv_path.name}")
            except Exception as e:
                print(f"✗ Failed to convert {csv_path.name}: {e}")
    
    # Copy other supported files
    for ext in ['.txt', '.pdf', '.docx', '.md', '.json']:
        for file_path in input_dir.glob(f'*{ext}'):
            dest = output_dir / file_path.name
            if dest != file_path:  # Don't copy to itself
                import shutil
                shutil.copy2(file_path, dest)
                print(f"✓ Copied {file_path.name}")
    
    print("Preprocessing complete")


def main():
    parser = argparse.ArgumentParser(description="Preprocess company data")
    parser.add_argument("--input", required=True, help="Input directory")
    parser.add_argument("--output", required=True, help="Output directory")
    
    args = parser.parse_args()
    preprocess_folder(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()

