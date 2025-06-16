#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import pandas as pd
from pathlib import Path

# --- 추가된 부분 시작 ---

# Elbow에 대한 추가 컬럼 정의 (항목은 예시이며, 실제 모델 데이터에 맞게 수정 가능)
NEW_COLUMNS_ELBOW = [
    "Viscous_K_factor", "Molecular_Transmission_Probability", "Molecular_Conductance_Lpm",
    "Transition_Alpha_Factor", "Viscous_flow_region_at_pressures", "Molecular_flow_region_at_pressures"
]
BASE_COLUMNS_ELBOW = ["SampleID", "Diameter_cm", "BendAngle_deg", "Quantity", "Pressure_Torr", "Conductance_L_per_min"]
ALL_COLUMNS_ELBOW = BASE_COLUMNS_ELBOW + NEW_COLUMNS_ELBOW

def extract_value(pattern, text, group_index=1, data_type=float, default=None):
    """정규식 패턴을 사용하여 텍스트에서 값을 추출합니다."""
    match = re.search(pattern, text, re.MULTILINE)
    if match:
        try:
            return data_type(match.group(group_index))
        except (ValueError, IndexError):
            return default
    return default

def parse_elbow_block_data(elbow_block_text):
    """단일 'ELBOW(s)' 블록 텍스트에서 추가 데이터를 파싱합니다."""
    data = {}
    data["Viscous_K_factor"] = extract_value(r"Viscous K factor\s*=\s*([\d\.E+-]+)", elbow_block_text)
    data["Molecular_Transmission_Probability"] = extract_value(r"Molecular transmission probability\s*=\s*([\d\.E+-]+)", elbow_block_text)
    data["Molecular_Conductance_Lpm"] = extract_value(r"Molecular Flow Conductance=\s*([\d\.E+-]+)\s*Liters/Minute", elbow_block_text)
    data["Transition_Alpha_Factor"] = extract_value(r"Transition flow alpha factor\s*=\s*([\d\.E+-]+)", elbow_block_text)
    data["Viscous_flow_region_at_pressures"] = extract_value(r"Viscous flow region at pressures\s*>\s*([\d\.E+-]+)\s*Torr", elbow_block_text)
    data["Molecular_flow_region_at_pressures"] = extract_value(r"Molecular flow region at pressures\s*<\s*([\d\.E+-]+)\s*Torr", elbow_block_text)
    return data

# --- 추가된 부분 끝 ---

def parse_elbow_file(path: Path, start_sample_id: int, model_data_blocks: list):
    """
    ELBOW 텍스트 파일을 파싱하고, model_data_blocks의 해당 Elbow 데이터와 결합합니다.
    """
    rows = []
    assigned_sample_id = start_sample_id
    current_sample_id_in_file = 0

    with path.open('r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        current_line_stripped = lines[i].strip()
        if re.match(r'Data for Conductance\s+\d+', current_line_stripped):
            conductance_block_start_line_idx = i
            header_found = False
            geom_details_line_idx = -1
            angle_deg, diameter_cm, quantity = None, None, 1

            temp_search_idx = conductance_block_start_line_idx + 1
            for _ in range(3):
                if temp_search_idx < len(lines):
                    header_candidate = lines[temp_search_idx].strip()
                    if not header_candidate:
                        temp_search_idx += 1
                        continue
                    m_geom = re.search(
                        r'\d+\s+ELBOW\(s\),\s*(\d+)\s+Degrees,\s*D=\s*([\d\.E+-]+)\s*Cm',
                        header_candidate
                    )
                    if m_geom:
                        angle_deg   = int(m_geom.group(1))
                        diameter_cm = float(m_geom.group(2))
                        header_found = True
                        geom_details_line_idx = temp_search_idx
                        break
                    else: 
                        break 
                else: 
                    break
                temp_search_idx += 1

            if not header_found:
                i = conductance_block_start_line_idx + 1
                while i < len(lines) and not re.match(r'Data for Conductance\s+\d+', lines[i].strip()):
                    i += 1
                continue

            additional_data = {}
            if current_sample_id_in_file < len(model_data_blocks):
                additional_data = model_data_blocks[current_sample_id_in_file]
            else:
                for col in NEW_COLUMNS_ELBOW:
                    additional_data[col] = None

            data_cursor = geom_details_line_idx + 1
            data_parsed_this_block = False
            
            while data_cursor < len(lines):
                line_content = lines[data_cursor].strip()
                if not line_content: 
                    data_cursor += 1
                    continue
                if re.match(r'Data for Conductance\s+\d+', line_content): 
                    break

                m_data = re.match(r'\s*\d+\)\s*([\d\.E+-]+),\s*([\d\.E+-]+)', line_content)
                if m_data:
                    pressure = float(m_data.group(1))
                    conductance_val = float(m_data.group(2))
                    
                    row_data = {
                        "SampleID":      assigned_sample_id,
                        "Diameter_cm":   round(diameter_cm, 4),
                        "BendAngle_deg": angle_deg,
                        "Quantity":      quantity,
                        "Pressure_Torr": pressure,
                        "Conductance_L_per_min": conductance_val
                    }
                    row_data.update(additional_data)
                    rows.append(row_data)
                    data_parsed_this_block = True
                else: 
                    break 
                data_cursor += 1
            
            if data_parsed_this_block:
                assigned_sample_id += 1
                current_sample_id_in_file += 1
            
            i = data_cursor
        
        else: 
            i += 1
            
    return rows, assigned_sample_id


def main():
    parser = argparse.ArgumentParser(description='ELBOW 시리즈 텍스트 파일들을 파싱하여 CSV로 저장')
    parser.add_argument('input_path', help='텍스트 파일(.txt) 또는 디렉터리 경로')
    parser.add_argument('-o', '--output', default='elbow_output.csv', help='출력 CSV 파일명')
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if input_path.is_dir():
        txt_files = sorted([f for f in input_path.glob('*.txt') if not f.name.endswith('_model.txt')])
    elif input_path.is_file() and not input_path.name.endswith('_model.txt'):
        txt_files = [input_path]
    else:
        print(f"Error: 유효하지 않은 경로이거나 _model.txt 파일입니다: {input_path}")
        sys.exit(1)

    all_rows = []
    global_sample_id_counter = 1
    for p_txt in txt_files:
        print(f"Parsing {p_txt.name} …")
        
        model_file_path = p_txt.with_name(p_txt.stem + "_model.txt")
        current_file_model_data_blocks = []
        if model_file_path.exists():
            with model_file_path.open('r', encoding='utf-8') as mf:
                model_content = mf.read()
                elbow_block_sections = re.finditer(r"(\d+ ELBOW\(s\).*?)(?=\n\s*\d+ ELBOW\(s\)|\Z)", model_content, re.DOTALL)
                for section_match in elbow_block_sections:
                    block_text = section_match.group(1)
                    if "Viscous K factor" in block_text:
                         current_file_model_data_blocks.append(parse_elbow_block_data(block_text))
        else:
            print(f"Warning: Model file not found: {model_file_path}. Additional data for {p_txt.name} will be empty.")

        rows, next_start_sample_id = parse_elbow_file(p_txt, global_sample_id_counter, current_file_model_data_blocks)
        all_rows.extend(rows)
        global_sample_id_counter = next_start_sample_id

    if not all_rows:
        print("파싱된 데이터가 없습니다.")
        df_empty = pd.DataFrame(columns=ALL_COLUMNS_ELBOW)
        df_empty.to_csv(args.output, index=False)
        print(f"헤더만 있는 빈 파일 생성: {args.output}")
        sys.exit(0)

    df = pd.DataFrame(all_rows, columns=ALL_COLUMNS_ELBOW)
    df.to_csv(args.output, index=False)
    print(f"완료: {len(df)}개의 행을 {args.output}에 저장했습니다.")

if __name__ == '__main__':
    main()