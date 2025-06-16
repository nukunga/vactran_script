#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import pandas as pd
from pathlib import Path

# --- 추가된 부분 시작 ---

# 추가될 컬럼 및 기본 컬럼 정의
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
    """정규식 패턴을 사용하여 텍스트에서 값을 추출합니다."""
    match = re.search(pattern, text, re.MULTILINE)
    if match:
        try:
            return data_type(match.group(group_index))
        except (ValueError, IndexError):
            return default
    return default

def parse_cone_block_data(cone_block_text):
    """단일 'Cone(s)' 블록 텍스트에서 추가 데이터를 파싱합니다."""
    data = {}
    data["Average dia"] = extract_value(r"Average diameter=\s*([\d\.]+)\s*Cm", cone_block_text)
    data["Beta"] = extract_value(r"Beta \(small diameter/large diameter\)=\s*([\d\.E+-]+)", cone_block_text)
    data["Theta_deg"] = extract_value(r"Theta \(cone angle\)=\s*([\d\.E+-]+)\s*Degrees", cone_block_text)
    data["Zero Angle Cone Factor"] = extract_value(r"Zero Angle Cone Factor=\s*([\d\.E+-]+)", cone_block_text)
    data["Viscous_K_entrance"] = extract_value(r"Viscous flow entrance K factor\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Viscous_K_body"] = extract_value(r"Viscous flow body K factor\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Viscous_K_exit"] = extract_value(r"Viscous flow exit K factor\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Viscous_K_total"] = extract_value(r"Viscous flow Total K factor\s*=\s*([\d\.E+-]+)", cone_block_text) # fT 제거
    data["Friction_factor"] = extract_value(r"Friction factor=\s*([\d\.E+-]+)", cone_block_text)
    data["Molecular flow equivalent diameter"] = extract_value(r"Molecular flow equivalent diameter=\s*([\d\.E+-]+)\s*Cm", cone_block_text)
    data["Sonic_Co"] = extract_value(r"Sonic Flow coefficient \(Co\)\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Sonic_Conductance_Lpm"] = extract_value(r"Sonic Flow Conductance\s*=\s*([\d\.E+-]+)\s*Liters/Minute", cone_block_text)
    data["Equiv pipe length for body loss"] = extract_value(r"Equiv pipe length for body loss=\s*([\d\.E+-]+)\s*Cm", cone_block_text)
    data["Equivalent pipe length for exit loss"] = extract_value(r"Equivalent pipe length for exit loss=\s*([\d\.E+-]+)\s*Cm", cone_block_text)
    data["Long tube alpha"] = extract_value(r"Long tube alpha\s*=\s*([\d\.E+-]+)", cone_block_text) # (included) 제거
    data["Exit loss alpha"] = extract_value(r"Exit loss alpha\s*=\s*([\d\.E+-]+)", cone_block_text) # (included) 제거
    data["Combined alpha"] = extract_value(r"Combined alpha\s*=\s*([\d\.E+-]+)", cone_block_text)
    data["Molecular_Conductance_Lpm"] = extract_value(r"Molecular Flow Conductance=\s*([\d\.E+-]+)\s*Liters/Minute", cone_block_text)
    data["Viscous flow region at pressures"] = extract_value(r"Viscous flow region at pressures\s*>\s*([\d\.E+-]+)\s*Torr", cone_block_text)
    data["Molecular flow region at pressures"] = extract_value(r"Molecular flow region at pressures\s*<\s*([\d\.E+-]+)\s*Torr", cone_block_text)
    return data

# --- 추가된 부분 끝 ---

def parse_reducer_file(path: Path, start_sample_id: int, model_data_blocks: list):
    """
    REDUCER(.txt) 파일을 파싱하고, model_data_blocks의 해당 Cone 데이터와 결합합니다.
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
            length_cm, d1_cm, d2_cm = None, None, None

            temp_search_idx = conductance_block_start_line_idx + 1
            for _ in range(3): # 다음 3줄까지 확인
                if temp_search_idx < len(lines):
                    header_candidate = lines[temp_search_idx].strip()
                    if not header_candidate:
                        temp_search_idx += 1
                        continue
                    m_geom = re.search(
                        r'L=\s*([\d\.E+-]+)\s*Cm,\s*Entrance D=\s*([\d\.E+-]+)\s*,\s*Exit D=\s*([\d\.E+-]+)\s*Cm',
                        header_candidate
                    )
                    if m_geom:
                        length_cm = float(m_geom.group(1))
                        d1_cm     = float(m_geom.group(2))
                        d2_cm     = float(m_geom.group(3))
                        header_found = True
                        geom_details_line_idx = temp_search_idx
                        break
                    else:
                        break
                else:
                    break
                temp_search_idx += 1

            if not header_found:
                # 헤더 파싱 실패 시 다음 블록으로 이동
                i = conductance_block_start_line_idx + 1
                while i < len(lines) and not re.match(r'Data for Conductance\s+\d+', lines[i].strip()):
                    i += 1
                continue

            # --- 추가된 부분: 모델 데이터 매칭 ---
            additional_data = {}
            if current_sample_id_in_file < len(model_data_blocks):
                additional_data = model_data_blocks[current_sample_id_in_file]
            else:
                # 모델 데이터가 부족할 경우 빈 데이터로 채움
                for col in NEW_COLUMNS:
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
                        "SampleID": assigned_sample_id,
                        "D1_cm": round(d1_cm, 4),
                        "D2_cm": round(d2_cm, 4),
                        "Length_cm": round(length_cm, 4),
                        "Pressure_Torr": pressure,
                        "Conductance_L_per_min": conductance_val
                    }
                    row_data.update(additional_data) # 병합
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
    parser = argparse.ArgumentParser(description='REDUCER/EXPANDER 시리즈 텍스트 파일들을 파싱하여 CSV로 저장')
    parser.add_argument('input_path', help='텍스트 파일(.txt) 또는 디렉터리 경로')
    parser.add_argument('-o', '--output', default='reducer_output.csv', help='출력 CSV 파일명')
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
                # "1 Cone(s)" 또는 "1 PIPE(s)" 등 일반적인 패턴으로 블록 분리
                cone_block_sections = re.finditer(r"(\d+ (?:Cone|PIPE|ELBOW)\(s\).*?)(?=\n\s*\d+ (?:Cone|PIPE|ELBOW)\(s\)|\Z)", model_content, re.DOTALL)
                for section_match in cone_block_sections:
                    block_text = section_match.group(1)
                    if "Volume =" in block_text:
                         current_file_model_data_blocks.append(parse_cone_block_data(block_text))
        else:
            print(f"Warning: Model file not found: {model_file_path}. Additional data for {p_txt.name} will be empty.")

        rows, next_start_sample_id = parse_reducer_file(p_txt, global_sample_id_counter, current_file_model_data_blocks)
        all_rows.extend(rows)
        global_sample_id_counter = next_start_sample_id

    if not all_rows:
        print("파싱된 데이터가 없습니다.")
        df_empty = pd.DataFrame(columns=ALL_COLUMNS)
        df_empty.to_csv(args.output, index=False)
        print(f"헤더만 있는 빈 파일 생성: {args.output}")
        sys.exit(0)

    df = pd.DataFrame(all_rows, columns=ALL_COLUMNS)
    df.to_csv(args.output, index=False)
    print(f"완료: {len(df)}개의 행을 {args.output}에 저장했습니다.")

if __name__ == '__main__':
    main()