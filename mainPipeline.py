import argparse
import os
import sys
import time
from datetime import datetime
import pandas as pd

# --- 프로젝트 모듈 임포트 ---
# 각 단계별 스크립트에서 로직을 수행하는 함수를 직접 임포트합니다.
from sampleDataGen import pipeDataGen, elbowDataGen, reducerDataGen, expanderDataGen
from genVtser import pipeGenerate, elbowGenerate, reducerGenerate
from dataPreprosessor import pipePrepro, elbowPrepro, reducerPrepro
from autoVacModule import run_vactran_automation

# 프로젝트 루트 디렉터리 설정
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def get_generation_parameters(item_type):
    """각 아이템 타입별 데이터 생성 파라미터 기본값을 반환합니다."""
    base_params = {
        "pipe": {
            "diameter_inch_range": (1.0, 10.0), # 파이프 직경 범위 (단위: inch). 내부적으로 cm로 변환.
            "length_mm_range": (100, 20000),   # 파이프 길이 범위 (단위: mm). 내부적으로 cm로 변환.
            "bin_width_inch": 1.0,             # 직경 샘플링 시 사용될 bin의 너비 (단위: inch).
        },
        "elbow": {
            "diameter_inch_range": (1.0, 5.0), # 엘보 직경 범위 (단위: inch). 내부적으로 cm로 변환.
            "bin_width_inch": 1.0,             # 직경 샘플링 시 사용될 bin의 너비 (단위: inch).
            "angles_deg": [15, 20, 30, 45],    # 생성될 엘보의 각도 목록.
            "quantity": 1,                     # VTSER 파일에 기록될 수량.
        },
        "reducer": { # D2 기준으로 샘플링, D1_cm > D2_cm, D2_cm < 0.7 * D1_cm
            "D2_inch_range": (1.0, 10.0),       # Reducer 작은 쪽 직경(D2) 샘플링 범위 (단위: inch). 내부 cm 변환.
            "D2_bin_width_inch": 1.0,           # D2 직경 샘플링 bin 너비 (단위: inch).
            "D1_inch_min_overall": 0.5,       # Reducer 큰 쪽 직경(D1) 전체 최소값 (단위: inch). 내부 cm 변환.
            "D1_inch_max_overall": 14.3,      # Reducer 큰 쪽 직경(D1) 전체 최대값 (단위: inch). (D2 최대값 10인치 / 0.7 고려). 내부 cm 변환.
            "length_mm_range": (50.0, 10000.0), # Reducer 길이 범위 (단위: mm). VACTRAN 입력 기준 cm 변환.
        },
        "expander": { # D1 기준으로 샘플링, D2_cm > D1_cm, D1_cm < 0.7 * D2_cm
            "D1_inch_range": (1.0, 10.0),       # Expander 작은 쪽 직경(D1) 샘플링 범위 (단위: inch). 내부 cm 변환.
            "D1_bin_width_inch": 1.0,           # D1 직경 샘플링 bin 너비 (단위: inch).
            "D2_inch_min_overall": 0.5,       # Expander 큰 쪽 직경(D2) 전체 최소값 (단위: inch). 내부 cm 변환.
            "D2_inch_max_overall": 14.3,      # Expander 큰 쪽 직경(D2) 전체 최대값 (단위: inch). (D1 최대값 10인치 / 0.7 고려). 내부 cm 변환.
            "length_mm_range": (50.0, 10000.0), # Expander 길이 범위 (단위: mm). VACTRAN 입력 기준 cm 변환.
        }
    }

    params = base_params.get(item_type)
    if not params:
        return {"description": "N/A - Unknown item type"}

    # Descriptions for logging and headers, no change from original
    if item_type == "pipe":
        params["description"] = (
            f"Pipe: Diameter {params['diameter_inch_range'][0]}-{params['diameter_inch_range'][1]} inches "
            f"(binned by {params['bin_width_inch']} inch, converted to cm internally), "
            f"Length {params['length_mm_range'][0]}-{params['length_mm_range'][1]} mm (converted to cm internally)."
        )
    elif item_type == "elbow":
        params["description"] = (
            f"Elbow: Diameter {params['diameter_inch_range'][0]}-{params['diameter_inch_range'][1]} inches "
            f"(binned by {params['bin_width_inch']} inch, converted to cm internally), "
            f"Angles ({', '.join(map(str, params['angles_deg']))} deg, sampled uniformly). " # 수정: angle_p45_prob 제거
            f"Quantity={params['quantity']}."
        )
    elif item_type == "reducer":
        params["description"] = ( # D2 기준으로 샘플링 설명 변경
            f"Reducer (D2 binned, D1_cm > D2_cm, D2_cm < 0.7*D1_cm after internal cm conversion): "
            f"D2 {params['D2_inch_range'][0]}-{params['D2_inch_range'][1]} inches (binned by {params['D2_bin_width_inch']} inch), "
            f"D1 {params['D1_inch_min_overall']}-{params['D1_inch_max_overall']} inches (overall range for D2 sampling), "
            f"Length {params['length_mm_range'][0]}-{params['length_mm_range'][1]} mm (converted to cm internally)." # cm -> mm
        )
    elif item_type == "expander":
        params["description"] = ( # D1 기준으로 샘플링 설명 변경
            f"Expander (D1 binned, D2_cm > D1_cm, D1_cm < 0.7*D2_cm after internal cm conversion): "
            f"D1 {params['D1_inch_range'][0]}-{params['D1_inch_range'][1]} inches (binned by {params['D1_bin_width_inch']} inch), "
            f"D2 {params['D2_inch_min_overall']}-{params['D2_inch_max_overall']} inches (overall range for D1 sampling), "
            f"Length {params['length_mm_range'][0]}-{params['length_mm_range'][1]} mm (converted to cm internally)." # cm -> mm
        )
    return params

def format_specs_for_filename(item_type, params):
    """파일명에 포함될 스펙 태그를 생성합니다."""
    if not isinstance(params, dict): return ""
    try:
        if item_type == "pipe":
            d_rng_in = params.get("diameter_inch_range", ("N/A","N/A"))
            l_rng_mm = params.get("length_mm_range", ("N/A","N/A"))
            return f"D{d_rng_in[0]}-{d_rng_in[1]}in_L{l_rng_mm[0]}-{l_rng_mm[1]}mm"
        elif item_type == "elbow":
            d_rng_in = params.get("diameter_inch_range", ("N/A","N/A"))
            a_rng = params.get("angles_deg", ["N/A"])
            return f"D{d_rng_in[0]}-{d_rng_in[1]}in_Ang{min(a_rng)}-{max(a_rng)}deg"
        elif item_type == "reducer": # D2 기준으로 변경, 길이 mm
            d2_rng_in = params.get("D2_inch_range", ("N/A","N/A"))
            d1_min_in = params.get("D1_inch_min_overall", "N/A")
            d1_max_in = params.get("D1_inch_max_overall", "N/A")
            l_rng_mm = params.get("length_mm_range", ("N/A","N/A")) # cm -> mm
            return f"D2_{d2_rng_in[0]}-{d2_rng_in[1]}in_D1_{d1_min_in}-{d1_max_in}in_L{l_rng_mm[0]}-{l_rng_mm[1]}mm" # cm -> mm
        elif item_type == "expander": # D1 기준으로 변경, 길이 mm
            d1_rng_in = params.get("D1_inch_range", ("N/A","N/A"))
            d2_min_in = params.get("D2_inch_min_overall", "N/A")
            d2_max_in = params.get("D2_inch_max_overall", "N/A")
            l_rng_mm = params.get("length_mm_range", ("N/A","N/A")) # cm -> mm
            return f"D1_{d1_rng_in[0]}-{d1_rng_in[1]}in_D2_{d2_min_in}-{d2_max_in}in_L{l_rng_mm[0]}-{l_rng_mm[1]}mm" # cm -> mm
    except Exception:
        return "SpecError"
    return "UnknownSpec"


def generate_csv_header_specs(item_type, num_samples, seed, params):
    """CSV 파일 상단에 추가할 주석 형태의 스펙 문자열을 생성합니다."""
    header_lines = [
        f"# Item Type: {item_type}",
        f"# Number of Samples Requested (for initial Excel generation): {num_samples}",
        f"# Seed Used (for initial Excel generation): {seed}",
        f"# Generation Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "# --- Data Generation Parameters (inch/mm inputs are converted to cm internally for VACTRAN) ---"
    ]
    if not isinstance(params, dict):
        params = {"description": "Parameters not available."}

    param_details = []
    if item_type == "pipe":
        param_details.extend([
            f"# - Diameter inch range (for binning): {params.get('diameter_inch_range', 'N/A')}",
            f"# - Length mm range: {params.get('length_mm_range', 'N/A')}",
            f"# - Bin width inch: {params.get('bin_width_inch', 'N/A')}"
        ])
    elif item_type == "elbow":
        param_details.extend([
            f"# - Diameter inch range (for binning): {params.get('diameter_inch_range', 'N/A')}",
            f"# - Bin width inch: {params.get('bin_width_inch', 'N/A')}",
            f"# - Angles deg: {params.get('angles_deg', 'N/A')}", # angle_p45_prob 제거
            f"# - Quantity: {params.get('quantity', 'N/A')}"
        ])
    elif item_type == "reducer": # D2 기준, 길이 mm
        param_details.extend([
            f"# - D2 inch range (for binning): {params.get('D2_inch_range', 'N/A')}",
            f"# - D2 bin width inch: {params.get('D2_bin_width_inch', 'N/A')}",
            f"# - D1 inch min overall: {params.get('D1_inch_min_overall', 'N/A')}",
            f"# - D1 inch max overall: {params.get('D1_inch_max_overall', 'N/A')}",
            f"# - Length mm range: {params.get('length_mm_range', 'N/A')}" # cm -> mm
        ])
    elif item_type == "expander": # D1 기준, 길이 mm
        param_details.extend([
            f"# - D1 inch range (for binning): {params.get('D1_inch_range', 'N/A')}",
            f"# - D1 bin width inch: {params.get('D1_bin_width_inch', 'N/A')}",
            f"# - D2 inch min overall: {params.get('D2_inch_min_overall', 'N/A')}",
            f"# - D2 inch max overall: {params.get('D2_inch_max_overall', 'N/A')}",
            f"# - Length mm range: {params.get('length_mm_range', 'N/A')}" # cm -> mm
        ])

    header_lines.extend(param_details)
    header_lines.append(f"# Description: {params.get('description', 'N/A')}")
    header_lines.append("# Note: All geometric dimensions in the final CSV file are in 'cm'.")
    header_lines.append("# Pressure is in 'Torr', Conductance is in 'L/min'.")
    header_lines.append("# This CSV is generated by processing VACTRAN output.")
    return "\n".join(header_lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="데이터 생성 및 처리 파이프라인")
    parser.add_argument("item_type", choices=["pipe", "elbow", "reducer", "expander"], help="처리할 항목 타입")
    parser.add_argument("num_samples", type=int, help="생성할 샘플 데이터 수량")
    parser.add_argument("--seed", type=int, default=42, help="데이터 생성 시 사용할 난수 시드 (기본값: 42)")
    parser.add_argument("--base_output_dir", default=os.path.join(PROJECT_ROOT, "pipeline_output_data"), help="최상위 출력 디렉터리")
    args = parser.parse_args()

    item_type = args.item_type
    num_samples = args.num_samples
    seed = args.seed
    
    generation_params = get_generation_parameters(item_type)
    pipeline_start_time = time.time()
    total_steps = 4

    # --- 고유한 작업 디렉터리 생성 ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    specs_tag_for_filename = format_specs_for_filename(item_type, generation_params)
    run_dir_name = f"{item_type}_{specs_tag_for_filename}_n{num_samples}_s{seed}_{timestamp}"
    current_run_output_dir = os.path.join(args.base_output_dir, run_dir_name)

    # --- 단계별 하위 디렉터리 경로 설정 ---
    excel_output_dir = os.path.join(current_run_output_dir, "01_excel_data")
    vtser_output_dir = os.path.join(current_run_output_dir, "02_vtser_files")
    txt_output_dir = os.path.join(current_run_output_dir, "03_vactran_txt_output")
    csv_output_dir = os.path.join(current_run_output_dir, "04_preprocessed_csv_data")

    for d in [excel_output_dir, vtser_output_dir, txt_output_dir, csv_output_dir]:
        os.makedirs(d, exist_ok=True)

    print(f"--- 파이프라인 시작: {item_type}, 샘플 수: {num_samples}, 시드: {seed} ---")
    print(f"모든 산출물은 다음 디렉터리에 저장됩니다: {current_run_output_dir}")

    # --- 1. sampleDataGen 실행 ---
    print(f"\n[단계 1/{total_steps}] {item_type} 샘플 데이터 생성 중...")
    sample_data_excel_filename = f"{item_type}_samples_n{num_samples}_s{seed}.xlsx"
    sample_data_excel_path = os.path.join(excel_output_dir, sample_data_excel_filename)

    try:
        if item_type == 'pipe':
            params = generation_params
            pipeDataGen.run(
                output_file=sample_data_excel_path,
                total_samples=num_samples,
                bin_width_inch=params["bin_width_inch"],
                diameter_inch_min=params["diameter_inch_range"][0],
                diameter_inch_max=params["diameter_inch_range"][1],
                length_mm_min=params["length_mm_range"][0],
                length_mm_max=params["length_mm_range"][1],
                seed=seed
            )
        elif item_type == 'elbow':
            params = generation_params
            elbowDataGen.run(
                output_file=sample_data_excel_path,
                total_samples=num_samples,
                bin_width_inch=params["bin_width_inch"],
                diameter_inch_min=params["diameter_inch_range"][0],
                diameter_inch_max=params["diameter_inch_range"][1],
                angles_deg_list=params["angles_deg"],
                seed=seed
            )
        elif item_type == 'reducer': # D2 기준, 길이 mm
            params = generation_params
            reducerDataGen.run(
                 output_file=sample_data_excel_path,
                 total_samples=num_samples,
                 d2_bin_width_inch=params["D2_bin_width_inch"],       # D1 -> D2
                 d2_inch_min=params["D2_inch_range"][0],             # D1 -> D2
                 d2_inch_max=params["D2_inch_range"][1],             # D1 -> D2
                 d1_inch_min_overall=params["D1_inch_min_overall"], # D2 -> D1
                 d1_inch_max_overall=params["D1_inch_max_overall"], # D2 -> D1
                 length_mm_min=params["length_mm_range"][0],         # cm -> mm
                 length_mm_max=params["length_mm_range"][1],         # cm -> mm
                 seed=seed
            )
        elif item_type == 'expander': # D1 기준, 길이 mm
            params = generation_params
            expanderDataGen.run(
                output_file=sample_data_excel_path,
                total_samples=num_samples,
                d1_bin_width_inch=params["D1_bin_width_inch"],       # D2 -> D1
                d1_inch_min=params["D1_inch_range"][0],             # D2 -> D1
                d1_inch_max=params["D1_inch_range"][1],             # D2 -> D1
                d2_inch_min_overall=params["D2_inch_min_overall"], # D1 -> D2
                d2_inch_max_overall=params["D2_inch_max_overall"], # D1 -> D2
                length_mm_min=params["length_mm_range"][0],         # cm -> mm
                length_mm_max=params["length_mm_range"][1],         # cm -> mm
                seed=seed
            )
        print(f"샘플 데이터 생성 완료: {sample_data_excel_path}")
        print(f"--- 단계 1/{total_steps} 완료 ({(1/total_steps)*100:.0f}%) ---")
    except Exception as e:
        print(f"!!! 샘플 데이터 생성 실패. 파이프라인 중단: {e} !!!")
        sys.exit(1)

    # --- 2. Gen_vster 실행 ---
    print(f"\n[단계 2/{total_steps}] {item_type} VTSER 파일 생성 중...")
    try:
        if item_type == 'pipe':
            pipeGenerate.run(sample_data_excel_path, vtser_output_dir)
        elif item_type == 'elbow':
            elbowGenerate.run(sample_data_excel_path, vtser_output_dir)
        elif item_type in ['reducer', 'expander']:
            reducerGenerate.run(sample_data_excel_path, vtser_output_dir)
        
        if not os.path.isdir(vtser_output_dir) or not os.listdir(vtser_output_dir):
             raise FileNotFoundError(f"VTSER 파일이 생성되지 않았습니다: {vtser_output_dir}")
        print(f"VTSER 파일 생성 완료. 저장 위치: {vtser_output_dir}")
        print(f"--- 단계 2/{total_steps} 완료 ({(2/total_steps)*100:.0f}%) ---")
    except Exception as e:
        print(f"!!! VTSER 파일 생성 실패. 파이프라인 중단: {e} !!!")
        sys.exit(1)

    # --- 3. auto_vac_module 실행 ---
    print(f"\n[단계 3/{total_steps}] VacTran 자동화 실행 중...")
    try:
        run_vactran_automation(vtser_output_dir, txt_output_dir)
        print(f"VacTran 자동화 완료. TXT 파일 저장 위치: {txt_output_dir}")
        print(f"--- 단계 3/{total_steps} 완료 ({(3/total_steps)*100:.0f}%) ---")
    except Exception as e:
        print(f"!!! VacTran 자동화 중 오류 발생: {e} !!!")
        print("파이프라인 중단.")
        sys.exit(1)

    # --- 4. dataPreprosessor 실행 ---
    print(f"\n[단계 4/{total_steps}] {item_type} 데이터 전처리 중...")
    final_csv_filename = f"{item_type}_preprocessed_n{num_samples}_s{seed}.csv"
    final_csv_path = os.path.join(csv_output_dir, final_csv_filename)

    try:
        if item_type == 'pipe':
            pipePrepro.run(txt_output_dir, final_csv_path)
        elif item_type == 'elbow':
            elbowPrepro.run(txt_output_dir, final_csv_path)
        elif item_type in ['reducer', 'expander']:
            reducerPrepro.run(txt_output_dir, final_csv_path)

        # CSV 파일에 스펙 주석 추가
        if os.path.exists(final_csv_path) and os.path.getsize(final_csv_path) > 0:
            df_temp = pd.read_csv(final_csv_path)
            specs_header_content = generate_csv_header_specs(item_type, num_samples, seed, generation_params)
            with open(final_csv_path, 'w', encoding='utf-8', newline='') as f:
                f.write(specs_header_content)
                df_temp.to_csv(f, index=False, lineterminator='\n')
            print(f"CSV 파일에 스펙 주석 추가 완료: {final_csv_path}")
        
        print(f"데이터 전처리 완료: {final_csv_path}")
        print(f"--- 단계 4/{total_steps} 완료 ({(4/total_steps)*100:.0f}%) ---")
    except Exception as e:
        print(f"!!! 데이터 전처리 실패. 파이프라인 중단: {e} !!!")
        sys.exit(1)

    pipeline_end_time = time.time()
    total_elapsed_time = pipeline_end_time - pipeline_start_time
    print(f"\n--- 모든 프로세스 성공적으로 완료 ---")
    print(f"최종 결과물: {final_csv_path}")
    print(f"모든 산출물 및 최종 결과는 다음 디렉터리에 있습니다: {current_run_output_dir}")
    print(f"총 소요 시간: {total_elapsed_time:.2f}초")


if __name__ == "__main__":
    main()