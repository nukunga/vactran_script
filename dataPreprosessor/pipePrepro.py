#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import pandas as pd
from pathlib import Path

# Column definitions
NEW_COLUMNS_PIPE = [
    "Viscous_K_total", "Friction_factor", "Molecular_Conductance_Lpm",
    "Long_tube_alpha", "Viscous_flow_region_at_pressures", 
    "Molecular_flow_region_at_pressures"
]
BASE_COLUMNS_PIPE = ["SampleID", "Diameter_cm", "Length_cm", "Pressure_Torr", "Conductance_L_per_min"]
ALL_COLUMNS_PIPE = BASE_COLUMNS_PIPE + NEW_COLUMNS_PIPE

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

def parse_pipe_block_data(pipe_block_text):
    """단일 'PIPE' 블록 텍스트에서 추가 데이터를 파싱합니다."""
    data = {}
    data["Viscous_K_total"] = extract_value(r"Viscous flow Total K factor\s*=\s*([\d\.E+-]+)", pipe_block_text, default=None)
    data["Friction_factor"] = extract_value(r"Friction factor=\s*([\d\.E+-]+)", pipe_block_text, default=None)
    data["Molecular_Conductance_Lpm"] = extract_value(r"Molecular Flow Conductance=\s*([\d\.E+-]+)\s*Liters/Minute", pipe_block_text, default=None)
    data["Long_tube_alpha"] = extract_value(r"Long tube alpha\s*=\s*([\d\.E+-]+)", pipe_block_text, default=None)
    data["Viscous_flow_region_at_pressures"] = extract_value(r"Viscous flow region at pressures\s*>\s*([\d\.E+-]+)\s*Torr", pipe_block_text, default=None)
    data["Molecular_flow_region_at_pressures"] = extract_value(r"Molecular flow region at pressures\s*<\s*([\d\.E+-]+)\s*Torr", pipe_block_text, default=None)
    return data
    
def parse_pipe_file(path: Path, start_sample_id: int, model_data_blocks: list):
    rows = []
    assigned_sample_id = start_sample_id
    current_model_data_idx = 0 # 현재 파일 내 _model.txt 블록 인덱스

    with path.open('r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        # "Data for Conductance X" 패턴으로 각 샘플 블록 시작을 감지
        m_conductance_header = re.match(r'Data for Conductance\s+(\d+)', lines[i].strip())
        if m_conductance_header:
            # 기하학적 정보 파싱 (L, D)
            header_line_index = i + 1
            header_found = False
            diameter_cm, length_cm = None, None
            
            # 다음 몇 줄에서 기하학적 정보 라인을 찾음
            for j in range(header_line_index, min(header_line_index + 3, len(lines))): # 검색 범위 약간 확장
                header_text = lines[j].strip()
                # "1 PIPE, L= X Cm, D= Y Cm" 형식의 라인 검색
                m_geom = re.search(r'\d+\s*PIPE,\s*L=\s*([\d\.E+-]+)\s*Cm,\s*D=\s*([\d\.E+-]+)\s*Cm', header_text)
                if m_geom:
                    length_cm = float(m_geom.group(1))
                    diameter_cm = float(m_geom.group(2))
                    header_found = True
                    i = j # 현재 위치를 기하 정보 라인으로 업데이트
                    break
            
            if not header_found:
                i += 1 # 다음 라인으로 이동하여 계속 검색
                continue

            # 현재 샘플에 해당하는 모델 데이터 가져오기
            additional_data = model_data_blocks[current_model_data_idx] if current_model_data_idx < len(model_data_blocks) else {col: None for col in NEW_COLUMNS_PIPE}
            
            data_cursor = i + 1
            data_parsed_this_block = False
            while data_cursor < len(lines):
                line_content = lines[data_cursor].strip()
                if not line_content: # 빈 줄은 건너뛰기
                    data_cursor += 1
                    continue
                # 다음 "Data for Conductance" 블록이 시작되면 현재 블록 종료
                if re.match(r'Data for Conductance\s+\d+', line_content):
                    break

                # 압력 및 컨덕턴스 데이터 파싱 ("N) P, C" 형식)
                m_data_line = re.match(r'\s*\d+\)\s*([\d\.E+-]+),\s*([\d\.E+-]+)', line_content)
                if m_data_line:
                    row_data = {
                        'SampleID': assigned_sample_id, 
                        'Diameter_cm': round(diameter_cm, 4) if diameter_cm is not None else None, 
                        'Length_cm': round(length_cm, 4) if length_cm is not None else None,
                        'Pressure_Torr': float(m_data_line.group(1)), 
                        'Conductance_L_per_min': float(m_data_line.group(2)),
                    }
                    row_data.update(additional_data) # 파싱된 모델 데이터 병합
                    rows.append(row_data)
                    data_parsed_this_block = True
                
                data_cursor += 1
            
            if data_parsed_this_block:
                assigned_sample_id += 1
                current_model_data_idx += 1 # 다음 모델 데이터 블록으로 이동
            
            i = data_cursor # 다음 검색 시작 위치 업데이트
        else:
            i += 1 # "Data for Conductance" 헤더가 아니면 다음 줄로

    return rows, assigned_sample_id

def run(input_path_str, output_file):
    """Parses VACTRAN TXT output files and generates a final CSV."""
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
        # 헤더만 있는 빈 CSV 파일 생성
        pd.DataFrame(columns=ALL_COLUMNS_PIPE).to_csv(output_file, index=False, encoding='utf-8-sig')
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
                # 각 "N Pipe(s)"로 시작하는 블록을 찾음 (공백 유연하게 처리)
                # 블록은 다음 "N Pipe(s)" 또는 파일 끝까지 이어짐
                pipe_block_sections = re.finditer(r"(\d+\s*Pipe\(s\).*?)(?=\n\s*\d+\s*Pipe\(s\)|\Z)", model_content, re.DOTALL)
                for section_match in pipe_block_sections:
                    block_text = section_match.group(1)
                    # 블록 내에 특정 키워드가 있는지 확인하여 유효한 파이프 모델 데이터인지 검증 (선택 사항)
                    if "Friction factor=" in block_text and "Molecular Flow Conductance=" in block_text:
                         current_file_model_data_blocks.append(parse_pipe_block_data(block_text))
        else:
            print(f"Warning: Model file not found for {p_txt.name}: {model_file_path}")
            # 모델 파일이 없으면 빈 모델 데이터로 처리하거나, 에러 처리할 수 있음
            # 여기서는 빈 리스트를 전달하여 additional_data가 None으로 채워지도록 함

        rows, next_start_sample_id = parse_pipe_file(p_txt, global_sample_id_counter, current_file_model_data_blocks)
        all_rows.extend(rows)
        global_sample_id_counter = next_start_sample_id

    if not all_rows:
        print("No data was parsed from any file.")
        df = pd.DataFrame(columns=ALL_COLUMNS_PIPE)
    else:
        df = pd.DataFrame(all_rows, columns=ALL_COLUMNS_PIPE)

    df.to_csv(output_file, index=False, encoding='utf-8-sig') # Excel 호환성을 위해 utf-8-sig 사용
    print(f"Completed: {len(df)} rows saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Parse PIPE series text files into a single CSV.')
    parser.add_argument('input_path', help='Input text file or directory path containing VACTRAN .txt output files (excluding _model.txt).')
    parser.add_argument('-o', '--output', default='pipe_preprocessed_output.csv', help='Output CSV filename.')
    args = parser.parse_args()
    run(args.input_path, args.output)

if __name__ == '__main__':
    main()