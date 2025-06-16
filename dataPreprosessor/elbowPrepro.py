#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import pandas as pd
from pathlib import Path

# Column definitions
NEW_COLUMNS_ELBOW = [
    "Viscous_K_factor", "Molecular_Transmission_Probability", "Molecular_Conductance_Lpm",
    "Viscous_flow_region_at_pressures", "Molecular_flow_region_at_pressures"
]
BASE_COLUMNS_ELBOW = ["SampleID", "Diameter_cm", "BendAngle_deg", "Quantity", "Pressure_Torr", "Conductance_L_per_min"]
ALL_COLUMNS_ELBOW = BASE_COLUMNS_ELBOW + NEW_COLUMNS_ELBOW

def extract_value(pattern, text, group_index=1, data_type=float, default=None):
    """정규식 패턴을 사용하여 텍스트에서 값을 추출합니다."""
    match = re.search(pattern, text, re.MULTILINE)
    if match:
        try:
            value_str = match.group(group_index)
            if value_str is None or value_str.strip() == "": # 빈 문자열이나 None인 경우 default 반환
                return default
            return data_type(value_str)
        except (ValueError, IndexError):
            return default
    return default

def parse_elbow_block_data(elbow_block_text):
    """단일 'ELBOW' 블록 텍스트에서 추가 데이터를 파싱합니다."""
    data = {}
    # reducerPrepro.py의 Viscous_K_total과 유사하게 Total K factor를 우선적으로 사용
    data["Viscous_K_factor"] = extract_value(r"Viscous flow Total K factor\s*=\s*([\d\.E+-]+)", elbow_block_text, default=None)
    # 만약 Total K factor가 없다면 elbow K factor를 사용 (옵션)
    if data["Viscous_K_factor"] is None:
        data["Viscous_K_factor"] = extract_value(r"Viscous flow elbow K factor\s*=\s*([\d\.E+-]+)", elbow_block_text, default=None)

    data["Molecular_Transmission_Probability"] = extract_value(r"Long tube alpha\s*=\s*([\d\.E+-]+)", elbow_block_text, default=None)
    data["Molecular_Conductance_Lpm"] = extract_value(r"Molecular Flow Conductance=\s*([\d\.E+-]+)\s*Liters/Minute", elbow_block_text, default=None)
    data["Viscous_flow_region_at_pressures"] = extract_value(r"Viscous flow region at pressures\s*>\s*([\d\.E+-]+)\s*Torr", elbow_block_text, default=None)
    data["Molecular_flow_region_at_pressures"] = extract_value(r"Molecular flow region at pressures\s*<\s*([\d\.E+-]+)\s*Torr", elbow_block_text, default=None)
    return data

def parse_elbow_file(path: Path, start_sample_id: int, model_data_blocks: list):
    rows = []
    assigned_sample_id = start_sample_id
    current_model_data_idx = 0 # 현재 파일 내 _model.txt 블록 인덱스

    with path.open('r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        m_conductance_header = re.match(r'Data for Conductance\s+(\d+)', lines[i].strip())
        if m_conductance_header:
            header_line_index = i + 1
            header_found = False
            angle_deg, diameter_cm, quantity = None, None, 1
            
            for j in range(header_line_index, min(header_line_index + 3, len(lines))):
                header_text = lines[j].strip()
                m_geom = re.search(r'\d+\s+ELBOW\(s\),\s*([\d\.]+)\s+Degrees,\s*D=\s*([\d\.E+-]+)\s*Cm', header_text, re.IGNORECASE)
                if m_geom:
                    angle_deg = float(m_geom.group(1)) # 각도도 float으로 처리 후 int 변환 가능
                    diameter_cm = float(m_geom.group(2))
                    header_found = True
                    i = j 
                    break
            
            if not header_found:
                i += 1
                continue
            
            additional_data = model_data_blocks[current_model_data_idx] if current_model_data_idx < len(model_data_blocks) else {col: None for col in NEW_COLUMNS_ELBOW}

            data_cursor = i + 1
            data_parsed_this_block = False
            while data_cursor < len(lines):
                line_content = lines[data_cursor].strip()
                if not line_content:
                    data_cursor += 1
                    continue
                if re.match(r'Data for Conductance\s+\d+', line_content):
                    break

                m_data_line = re.match(r'\s*\d+\)\s*([\d\.E+-]+),\s*([\d\.E+-]+)', line_content)
                if m_data_line:
                    row_data = {
                        "SampleID": assigned_sample_id, 
                        "Diameter_cm": round(diameter_cm, 4) if diameter_cm is not None else None,
                        "BendAngle_deg": int(angle_deg) if angle_deg is not None else None, 
                        "Quantity": quantity,
                        "Pressure_Torr": float(m_data_line.group(1)), 
                        "Conductance_L_per_min": float(m_data_line.group(2))
                    }
                    row_data.update(additional_data)
                    rows.append(row_data)
                    data_parsed_this_block = True
                data_cursor += 1
            
            if data_parsed_this_block:
                assigned_sample_id += 1
                current_model_data_idx += 1
            i = data_cursor
        else:
            i += 1
            
    return rows, assigned_sample_id

def run(input_path_str, output_file):
    input_path_obj = Path(input_path_str)
    if input_path_obj.is_dir():
        txt_files = sorted([f for f in input_path_obj.glob('*.txt') if not f.name.endswith('_model.txt')])
    elif input_path_obj.is_file() and input_path_obj.suffix == '.txt' and not input_path_obj.name.endswith('_model.txt'):
        txt_files = [input_path_obj]
    else:
        print(f"Error: Invalid input path. Must be a directory or a .txt file (not _model.txt): {input_path_str}")
        sys.exit(1)

    if not txt_files:
        print("No .txt files found to process.")
        pd.DataFrame(columns=ALL_COLUMNS_ELBOW).to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Empty CSV with headers created: {output_file}")
        return

    all_rows = []
    global_sample_id_counter = 1
    for p_txt in txt_files:
        print(f"Parsing {p_txt.name} …")
        model_file_path = p_txt.with_name(p_txt.stem + "_model.txt")
        current_file_model_data_blocks = []
        if model_file_path.exists():
            with model_file_path.open('r', encoding='utf-8') as mf:
                model_content = mf.read()
                # 각 "N ELBOW(s)"로 시작하는 블록을 찾음 (대소문자 무시)
                elbow_block_sections = re.finditer(r"(\d+\s*ELBOW\(s\).*?)(?=\n\s*\d+\s*ELBOW\(s\)|\Z)", model_content, re.DOTALL | re.IGNORECASE)
                for section_match in elbow_block_sections:
                    block_text = section_match.group(1)
                    # 블록 내에 Elbow의 주요 식별 정보가 있는지 확인
                    if "Diameter =" in block_text and "Bend Angle =" in block_text:
                         parsed_block_data = parse_elbow_block_data(block_text)
                         current_file_model_data_blocks.append(parsed_block_data)
                    # else:
                    # print(f"Skipping a block in {model_file_path.name} as it doesn't seem to be a valid Elbow model block.")
        else:
            print(f"Warning: Model file not found for {p_txt.name}: {model_file_path}")
        
        rows, next_start_sample_id = parse_elbow_file(p_txt, global_sample_id_counter, current_file_model_data_blocks)
        all_rows.extend(rows)
        global_sample_id_counter = next_start_sample_id

    if not all_rows:
        print("No data was parsed from any file.")
        df = pd.DataFrame(columns=ALL_COLUMNS_ELBOW)
    else:
        df = pd.DataFrame(all_rows, columns=ALL_COLUMNS_ELBOW)

    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"Completed: {len(df)} rows saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Parse ELBOW series text files into a single CSV.')
    parser.add_argument('input_path', help='Input text file or directory path containing VACTRAN .txt output files (excluding _model.txt).')
    parser.add_argument('-o', '--output', default='elbow_preprocessed_output.csv', help='Output CSV filename.')
    args = parser.parse_args()
    run(args.input_path, args.output)

if __name__ == '__main__':
    main()