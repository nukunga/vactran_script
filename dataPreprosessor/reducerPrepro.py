#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import pandas as pd
from pathlib import Path

# Column definitions
NEW_COLUMNS = [
    "Average dia", "Beta", "Theta_deg", "Zero Angle Cone Factor",
    "Viscous_K_entrance", "Viscous_K_body", "Viscous_K_exit", "Viscous_K_total",
    "Friction_factor", "Molecular flow equivalent diameter", "Sonic_Co",
    "Sonic_Conductance_Lpm", "Equiv pipe length for body loss",
    "Equivalent pipe length for exit loss", "Long tube alpha", "Exit loss alpha",
    "Combined alpha", "Molecular_Conductance_Lpm",
    "Viscous flow region at pressures", "Molecular flow region at pressures"
]
BASE_COLUMNS = ["SampleID", "D1_cm", "D2_cm", "Length_cm", "Pressure_Torr", "Conductance_L_per_min"]
ALL_COLUMNS = BASE_COLUMNS + NEW_COLUMNS

def extract_value(pattern, text, group_index=1, data_type=float, default=None):
    match = re.search(pattern, text, re.MULTILINE)
    if match:
        try:
            return data_type(match.group(group_index))
        except (ValueError, IndexError):
            return default
    return default

def parse_cone_block_data(cone_block_text):
    data = {}
    data["Average dia"] = extract_value(r"Average diameter=\s*([\d\.]+)\s*Cm", cone_block_text)
    data["Beta"] = extract_value(r"Beta \(small diameter/large diameter\)=\s*([\d\.E+-]+)", cone_block_text)
    data["Theta_deg"] = extract_value(r"Theta \(cone angle\)=\s*([\d\.E+-]+)\s*Degrees", cone_block_text)
    data["Zero Angle Cone Factor"] = extract_value(r"Zero Angle Cone Factor=\s*([\d\.E+-]+)", cone_block_text)
    data["Viscous_K_entrance"] = extract_value(r"Viscous flow entrance K factor\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Viscous_K_body"] = extract_value(r"Viscous flow body K factor\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Viscous_K_exit"] = extract_value(r"Viscous flow exit K factor\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Viscous_K_total"] = extract_value(r"Viscous flow Total K factor\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Friction_factor"] = extract_value(r"Friction factor=\s*([\d\.E+-]+)", cone_block_text)
    data["Molecular flow equivalent diameter"] = extract_value(r"Molecular flow equivalent diameter=\s*([\d\.E+-]+)\s*Cm", cone_block_text)
    data["Sonic_Co"] = extract_value(r"Sonic Flow coefficient \(Co\)\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Sonic_Conductance_Lpm"] = extract_value(r"Sonic Flow Conductance\s*=\s*([\d\.E+-]+)\s*Liters/Minute", cone_block_text)
    data["Equiv pipe length for body loss"] = extract_value(r"Equiv pipe length for body loss=\s*([\d\.E+-]+)\s*Cm", cone_block_text)
    data["Equivalent pipe length for exit loss"] = extract_value(r"Equivalent pipe length for exit loss=\s*([\d\.E+-]+)\s*Cm", cone_block_text)
    data["Long tube alpha"] = extract_value(r"Long tube alpha\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Exit loss alpha"] = extract_value(r"Exit loss alpha\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Combined alpha"] = extract_value(r"Combined alpha\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Molecular_Conductance_Lpm"] = extract_value(r"Molecular Flow Conductance=\s*([\d\.E+-]+)\s*Liters/Minute", cone_block_text)
    data["Viscous flow region at pressures"] = extract_value(r"Viscous flow region at pressures\s*>\s*([\d\.E+-]+)\s*Torr", cone_block_text)
    data["Molecular flow region at pressures"] = extract_value(r"Molecular flow region at pressures\s*<\s*([\d\.E+-]+)\s*Torr", cone_block_text)
    return data

def parse_reducer_file(path: Path, start_sample_id: int, model_data_blocks: list):
    rows = []
    assigned_sample_id = start_sample_id
    current_sample_id_in_file = 0

    with path.open('r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        if re.match(r'Data for Conductance\s+\d+', lines[i].strip()):
            header_found, length_cm, d1_cm, d2_cm = False, None, None, None
            
            for j in range(i + 1, min(i + 4, len(lines))):
                m_geom = re.search(r'L=\s*([\d\.E+-]+)\s*Cm,\s*Entrance D=\s*([\d\.E+-]+)\s*,\s*Exit D=\s*([\d\.E+-]+)\s*Cm', lines[j])
                if m_geom:
                    length_cm, d1_cm, d2_cm = float(m_geom.group(1)), float(m_geom.group(2)), float(m_geom.group(3))
                    header_found = True
                    i = j
                    break
            
            if not header_found:
                i += 1
                continue

            additional_data = model_data_blocks[current_sample_id_in_file] if current_sample_id_in_file < len(model_data_blocks) else {col: None for col in NEW_COLUMNS}
            
            data_cursor = i + 1
            data_parsed_this_block = False
            while data_cursor < len(lines) and not re.match(r'Data for Conductance\s+\d+', lines[data_cursor].strip()):
                m_data = re.match(r'\s*\d+\)\s*([\d\.E+-]+),\s*([\d\.E+-]+)', lines[data_cursor].strip())
                if m_data:
                    row_data = {
                        "SampleID": assigned_sample_id, "D1_cm": round(d1_cm, 4), "D2_cm": round(d2_cm, 4),
                        "Length_cm": round(length_cm, 4), "Pressure_Torr": float(m_data.group(1)),
                        "Conductance_L_per_min": float(m_data.group(2))
                    }
                    row_data.update(additional_data)
                    rows.append(row_data)
                    data_parsed_this_block = True
                data_cursor += 1
            
            if data_parsed_this_block:
                assigned_sample_id += 1
                current_sample_id_in_file += 1
            i = data_cursor
        else:
            i += 1
    return rows, assigned_sample_id

def run(input_path_str, output_file):
    """Parses VACTRAN TXT output files for reducers/expanders and generates a final CSV."""
    input_path = Path(input_path_str)
    if input_path.is_dir():
        txt_files = sorted([f for f in input_path.glob('*.txt') if not f.name.endswith('_model.txt')])
    elif input_path.is_file() and not input_path.name.endswith('_model.txt'):
        txt_files = [input_path]
    else:
        print(f"Error: Invalid path provided: {input_path}")
        sys.exit(1)

    all_rows = []
    global_sample_id_counter = 1
    for p_txt in txt_files:
        print(f"Parsing {p_txt.name} …")
        model_file_path = p_txt.with_name(p_txt.stem + "_model.txt")
        current_file_model_data_blocks = []
        if model_file_path.exists():
            with model_file_path.open('r', encoding='utf-8') as mf:
                cone_block_sections = re.finditer(r"(\d+ (?:Cone|PIPE|ELBOW)\(s\).*?)(?=\n\s*\d+ (?:Cone|PIPE|ELBOW)\(s\)|\Z)", mf.read(), re.DOTALL)
                for section_match in cone_block_sections:
                    if "Volume =" in section_match.group(1):
                         current_file_model_data_blocks.append(parse_cone_block_data(section_match.group(1)))
        
        rows, next_start_sample_id = parse_reducer_file(p_txt, global_sample_id_counter, current_file_model_data_blocks)
        all_rows.extend(rows)
        global_sample_id_counter = next_start_sample_id

    if not all_rows:
        print("No data was parsed. Creating empty file.")
        df = pd.DataFrame(columns=ALL_COLUMNS)
    else:
        df = pd.DataFrame(all_rows, columns=ALL_COLUMNS)

    df.to_csv(output_file, index=False)
    print(f"완료: {len(df)}개의 행을 {output_file}에 저장했습니다.")

def main():
    parser = argparse.ArgumentParser(description='Parse REDUCER/EXPANDER series text files into a single CSV.')
    parser.add_argument('input_path', help='Input text file or directory path.')
    parser.add_argument('-o', '--output', default='reducer_output.csv', help='Output CSV filename.')
    args = parser.parse_args()
    run(args.input_path, args.output)

if __name__ == '__main__':
    main()