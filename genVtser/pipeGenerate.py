import pandas as pd
import os
import argparse

def write_vtser_chunk(chunk_df, file_index, save_dir):
    lines = ["[General]", f"Total={len(chunk_df)}", "ModelMultiplier=1"]
    for idx, row in chunk_df.iterrows():
        diameter_cm = float(row['Diameter_cm'])
        length_cm = float(row['Length_cm'])
        lines.extend([
            f"[{idx % 50}]", "Description=PIPE", "Quantity=1",
            f"Diameter={diameter_cm:.6f}", f"ModelLength={length_cm:.6f}",
            "Volume=0", "EntranceLoss=0", "ExitLoss=0", "EdgeRadius=0", "Projecting=0"
        ])
    output_filename = f"PIPE_SERIES_{file_index+1:03d}.VTSER"
    output_path = os.path.join(save_dir, output_filename)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Saved: {output_path}")

def run(excel_path, output_dir):
    """Reads an Excel file and generates VTSER files for pipes."""
    os.makedirs(output_dir, exist_ok=True)
    try:
        df = pd.read_excel(excel_path)
    except FileNotFoundError:
        print(f"Error: Input Excel file not found at {excel_path}")
        return

    chunk_size = 50
    chunks = [df[i:i+chunk_size] for i in range(0, len(df), chunk_size)]
    for idx, chunk in enumerate(chunks):
        write_vtser_chunk(chunk.reset_index(drop=True), idx, output_dir)

def main():
    parser = argparse.ArgumentParser(description="Generate VTSER files from Excel for pipes.")
    parser.add_argument("excel_path", help="Path to the input Excel file.")
    parser.add_argument("--output_dir", required=True, help="Directory to save VTSER files.")
    args = parser.parse_args()
    run(args.excel_path, args.output_dir)

if __name__ == '__main__':
    main()