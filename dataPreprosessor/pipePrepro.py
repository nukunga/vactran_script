#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import pandas as pd
from pathlib import Path

# --- 추가된 부분 시작 ---

# Pipe에 대한 추가 컬럼 정의 (항목은 예시이며, 실제 모델 데이터에 맞게 수정 가능)
NEW_COLUMNS_PIPE = [
    "Viscous_K_total", "Friction_factor", "Molecular_Conductance_Lpm",
    "Long_tube_alpha", "Combined_alpha", "Viscous_flow_region_at_pressures", 
    "Molecular_flow_region_at_pressures"
]
BASE_COLUMNS_PIPE = ["SampleID", "Diameter_cm", "Length_cm", "Pressure_Torr", "Conductance_L_per_min"]
ALL_COLUMNS_PIPE = BASE_COLUMNS_PIPE + NEW_COLUMNS_PIPE

def extract_value(pattern, text, group_index=1, data_type=float, default=None):
    """정규식 패턴을 사용하여 텍스트에서 값을 추출합니다."""
    match = re.search(pattern, text, re.MULTILINE)
    if match:
        try:
            return data_type(match.group(group_index))
        except (ValueError, IndexError):
            return default
    return default

def parse_pipe_block_data(pipe_block_text):
    """단일 'PIPE' 블록 텍스트에서 추가 데이터를 파싱합니다."""
    data = {}
    data["Viscous_K_total"] = extract_value(r"Viscous flow Total K factor\s*=\s*([\d\.E+-]+)", pipe_block_text)
    data["Friction_factor"] = extract_value(r"Friction factor=\s*([\d\.E+-]+)", pipe_block_text)
    data["Molecular_Conductance_Lpm"] = extract_value(r"Molecular Flow Conductance=\s*([\d\.E+-]+)\s*Liters/Minute", pipe_block_text)
    data["Long_tube_alpha"] = extract_value(r"Long tube alpha\s*=\s*([\d\.E+-]+)", pipe_block_text)
    data["Combined_alpha"] = extract_value(r"Combined alpha\s*=\s*([\d\.E+-]+)", pipe_block_text)
    data["Viscous_flow_region_at_pressures"] = extract_value(r"Viscous flow region at pressures\s*>\s*([\d\.E+-]+)\s*Torr", pipe_block_text)
    data["Molecular_flow_region_at_pressures"] = extract_value(r"Molecular flow region at pressures\s*<\s*([\d\.E+-]+)\s*Torr", pipe_block_text)
    return data

# --- 추가된 부분 끝 ---

def parse_pipe_file(path, start_sample_id, model_data_blocks: list):
    """
    주어진 Pipe 파일을 파싱하고, model_data_blocks의 해당 Pipe 데이터와 결합합니다.
    """
    rows = []
    assigned_sample_id = start_sample_id
    current_sample_id_in_file = 0

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        m = re.match(r'Data for Conductance\s+(\d+)', lines[i])
        if m:
            header_line_index = i + 1
            header_found = False
            diameter_cm, length_cm = None, None
            
            # 헤더 정보 찾기 (최대 2줄까지 탐색)
            for j in range(header_line_index, min(header_line_index + 2, len(lines))):
                header = lines[j]
                m2 = re.search(r'\d+\s*PIPE,\s*L=\s*([\d\.E+-]+)\s*Cm,\s*D=\s*([\d\.E+-]+)\s*Cm', header)
                if m2:
                    length_cm = float(m2.group(1))
                    diameter_cm = float(m2.group(2))
                    header_found = True
                    i = j # 데이터 시작 위치를 위해 인덱스 업데이트
                    break

            if not header_found:
                i += 1
                continue

            additional_data = {}
            if current_sample_id_in_file < len(model_data_blocks):
                additional_data = model_data_blocks[current_sample_id_in_file]
            else:
                for col in NEW_COLUMNS_PIPE:
                    additional_data[col] = None

            data_cursor = i + 1
            data_parsed_this_block = False
            while data_cursor < len(lines):
                line_content = lines[data_cursor].strip()
                if not line_content:
                    data_cursor += 1
                    continue
                if re.match(r'Data for Conductance\s+\d+', line_content):
                    break

                m3 = re.match(r'\s*\d+\)\s*([\d\.E+-]+),\s*([\d\.E+-]+)', line_content)
                if m3:
                    pressure = float(m3.group(1))
                    conductance = float(m3.group(2))
                    
                    row_data = {
                        'SampleID': assigned_sample_id,
                        'Diameter_cm': diameter_cm,
                        'Length_cm': length_cm,
                        'Pressure_Torr': pressure,
                        'Conductance_L_per_min': conductance,
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

def main():
    parser = argparse.ArgumentParser(description='PIPE 시리즈 텍스트 파일들을 파싱하여 CSV로 저장합니다.')
    parser.add_argument('input_path', help='입력할 텍스트 파일 또는 디렉터리 경로')
    parser.add_argument('-o', '--output', default='pipe_output.csv', help='출력 CSV 파일명')
    args = parser.parse_args()

    input_path_obj = Path(args.input_path)
    if input_path_obj.is_dir():
        txt_files = sorted([f for f in input_path_obj.glob('*.txt') if not f.name.endswith('_model.txt')])
    elif input_path_obj.is_file() and not input_path_obj.name.endswith('_model.txt'):
        txt_files = [input_path_obj]
    else:
        print(f"Error: 유효하지 않은 경로이거나 _model.txt 파일입니다: {args.input_path}")
        sys.exit(1)

    if not txt_files:
        print("처리할 .txt 파일을 찾을 수 없습니다.")
        df_empty = pd.DataFrame(columns=ALL_COLUMNS_PIPE)
        df_empty.to_csv(args.output, index=False)
        print(f"헤더만 있는 빈 파일 생성: {args.output}")
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
                pipe_block_sections = re.finditer(r"(\d+ PIPE\(s\).*?)(?=\n\s*\d+ PIPE\(s\)|\Z)", model_content, re.DOTALL)
                for section_match in pipe_block_sections:
                    block_text = section_match.group(1)
                    if "Friction factor" in block_text:
                        current_file_model_data_blocks.append(parse_pipe_block_data(block_text))
        else:
            print(f"Warning: Model file not found: {model_file_path}. Additional data for {p_txt.name} will be empty.")

        rows, next_start_sample_id = parse_pipe_file(p_txt, global_sample_id_counter, current_file_model_data_blocks)
        all_rows.extend(rows)
        global_sample_id_counter = next_start_sample_id

    if not all_rows:
        print("파싱된 데이터가 없습니다.")
        df_empty = pd.DataFrame(columns=ALL_COLUMNS_PIPE)
        df_empty.to_csv(args.output, index=False)
        print(f"헤더만 있는 빈 파일 생성: {args.output}")
        return

    df = pd.DataFrame(all_rows, columns=ALL_COLUMNS_PIPE)
    df.to_csv(args.output, index=False)
    print(f"완료: {args.output}에 저장되었습니다.")

if __name__ == '__main__':
    main()