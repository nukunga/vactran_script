import argparse
import os
import subprocess
import sys
import shutil
from datetime import datetime # datetime 모듈 추가
import time # time 모듈 추가
import pandas as pd # CSV 주석 추가를 위해 pandas import

# 프로젝트 루트 디렉터리 설정
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# auto_vac_module.py가 프로젝트 루트에 있다고 가정하고 경로 추가
sys.path.append(PROJECT_ROOT)
try:
    from auto_vac_module import run_vactran_automation
except ImportError:
    print("오류: auto_vac_module.py를 찾을 수 없거나 run_vactran_automation 함수가 없습니다.")
    print("auto_vac.py를 auto_vac_module.py로 이름을 변경하고, 제공된 내용으로 수정해주세요.")
    sys.exit(1)

def run_script(script_path_segments, args_list, script_cwd=None):
    """
    지정된 스크립트를 subprocess로 실행하고 완료될 때까지 기다립니다.
    """
    script_full_path = os.path.join(PROJECT_ROOT, *script_path_segments)
    if not script_cwd:
        script_cwd = os.path.dirname(script_full_path)

    # cwd 경로를 절대 경로로 만들고, 존재 여부 및 디렉터리 여부 확인
    effective_cwd = os.path.abspath(script_cwd)

    command = [sys.executable, script_full_path] + args_list
    print(f"실행: {' '.join(command)}")
    print(f"  Subprocess CWD: {effective_cwd}")
    print(f"  CWD exists: {os.path.exists(effective_cwd)}")
    print(f"  CWD is directory: {os.path.isdir(effective_cwd)}")
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=True, cwd=effective_cwd, encoding='utf-8', errors='replace') # errors='replace' 추가
        print(f"--- {os.path.basename(script_full_path)} 실행 성공 ---")
        if process.stdout:
            print("STDOUT:")
            print(process.stdout)
        if process.stderr: # 일부 스크립트는 stderr로 진행 상황을 출력할 수 있음
            print(f"--- {os.path.basename(script_full_path)} STDERR ---")
            print(process.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"!!! {os.path.basename(script_full_path)} 실행 중 오류 발생 !!!")
        print(f"Return code: {e.returncode}")
        print(f"Output (stdout):\n{e.stdout}")
        print(f"Error (stderr):\n{e.stderr}")
        return False
    except FileNotFoundError:
        print(f"!!! 오류: 스크립트 파일을 찾을 수 없습니다 - {script_full_path} !!!")
        return False

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
            "angle_p45_prob": 0.5,             # 45도 각도가 선택될 확률.
            "quantity": 1,                     # VTSER 파일에 기록될 수량.
        },
        "reducer": { # D1_cm > D2_cm, D2_cm < 0.7 * D1_cm (내부 cm 변환 후 조건)
            "D1_inch_range": (1.0, 10.0),       # Reducer 큰 쪽 직경(D1) 범위 (단위: inch). 내부 cm 변환.
            "D1_bin_width_inch": 1.0,           # D1 직경 샘플링 bin 너비 (단위: inch).
            "D2_inch_min_overall": 0.5,       # Reducer 작은 쪽 직경(D2) 전체 최소값 (단위: inch). 내부 cm 변환.
            "D2_inch_max_overall": 9.5,       # Reducer 작은 쪽 직경(D2) 전체 최대값 (단위: inch). 내부 cm 변환. (D1 최대값의 70% 고려)
            "length_cm_range": (5.0, 100.0),   # Reducer 길이 범위 (단위: cm). VACTRAN 입력 기준.
        },
        "expander": { # D2_cm > D1_cm, D1_cm < 0.7 * D2_cm (내부 cm 변환 후 조건)
            "D1_inch_range": (1.0, 10.0),      # Expander 작은 쪽 직경(D1) 범위 (단위: inch). 내부 cm 변환. (D2 최대값의 70% 고려)
            "D1_bin_width_inch": 1.0,           # D1 직경 샘플링 bin 너비 (단위: inch).
            "D2_inch_min_overall": 2.0,       # Expander 큰 쪽 직경(D2) 전체 최소값 (단위: inch). 내부 cm 변환.
            "D2_inch_max_overall": 10.0,      # Expander 큰 쪽 직경(D2) 전체 최대값 (단위: inch). 내부 cm 변환.
            "length_cm_range": (5.0, 100.0),   # Expander 길이 범위 (단위: cm). VACTRAN 입력 기준.
        }
    }

    params = base_params.get(item_type)

    if not params:
        return {"description": "N/A - Unknown item type"}

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
            f"Angles ({', '.join(map(str, params['angles_deg']))} deg "
            f"with {params['angles_deg'][-1]}deg >= {params['angle_p45_prob']*100:.0f}% prob). "
            f"Quantity={params['quantity']}."
        )
    elif item_type == "reducer":
        params["description"] = (
            f"Reducer (D1_cm > D2_cm, D2_cm < 0.7*D1_cm after internal cm conversion): "
            f"D1 {params['D1_inch_range'][0]}-{params['D1_inch_range'][1]} inches (binned by {params['D1_bin_width_inch']} inch), "
            f"D2 {params['D2_inch_min_overall']}-{params['D2_inch_max_overall']} inches, "
            f"Length {params['length_cm_range'][0]}-{params['length_cm_range'][1]} cm."
        )
    elif item_type == "expander":
        params["description"] = (
            f"Expander (D2_cm > D1_cm, D1_cm < 0.7*D2_cm after internal cm conversion): "
            f"D1 {params['D1_inch_range'][0]}-{params['D1_inch_range'][1]} inches (binned by {params['D1_bin_width_inch']} inch), "
            f"D2 {params['D2_inch_min_overall']}-{params['D2_inch_max_overall']} inches, "
            f"Length {params['length_cm_range'][0]}-{params['length_cm_range'][1]} cm."
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
        elif item_type in ["reducer", "expander"]:
            d1_rng_in = params.get("D1_inch_range", ("N/A","N/A"))
            d2_min_in = params.get("D2_inch_min_overall", "N/A") # inch로 변경
            d2_max_in = params.get("D2_inch_max_overall", "N/A") # inch로 변경
            l_rng_cm = params.get("length_cm_range", ("N/A","N/A"))
            return f"D1_{d1_rng_in[0]}-{d1_rng_in[1]}in_D2_{d2_min_in}-{d2_max_in}in_L{l_rng_cm[0]}-{l_rng_cm[1]}cm" # D2 단위 in으로 변경
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
            f"# - Angles deg: {params.get('angles_deg', 'N/A')}",
            f"# - Angle P45 prob: {params.get('angle_p45_prob', 'N/A')}",
            f"# - Quantity: {params.get('quantity', 'N/A')}"
        ])
    elif item_type in ["reducer", "expander"]:
        param_details.extend([
            f"# - D1 inch range (for binning): {params.get('D1_inch_range', 'N/A')}",
            f"# - D1 bin width inch: {params.get('D1_bin_width_inch', 'N/A')}",
            f"# - D2 inch min overall: {params.get('D2_inch_min_overall', 'N/A')}", # cm -> inch
            f"# - D2 inch max overall: {params.get('D2_inch_max_overall', 'N/A')}", # cm -> inch
            f"# - Length cm range (VACTRAN input): {params.get('length_cm_range', 'N/A')}"
        ])
    else:
        for key, value in params.items():
            if key != "description":
                param_details.append(f"# - {key.replace('_', ' ').capitalize()}: {value}")
    
    header_lines.extend(param_details)
    header_lines.append(f"# Description: {params.get('description', 'N/A')}")
    header_lines.append("# Note: All geometric dimensions in the final CSV file are in 'cm'.")
    header_lines.append("# Pressure is in 'Torr', Conductance is in 'L/min'.")
    header_lines.append("# This CSV is generated by processing VACTRAN output.")
    return "\n".join(header_lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="데이터 생성 및 처리 파이프라인")
    parser.add_argument("item_type", choices=["pipe", "elbow", "reducer", "expander"], help="처리할 항목 타입 (pipe, elbow, reducer, expander)")
    parser.add_argument("num_samples", type=int, help="생성할 샘플 데이터 수량")
    parser.add_argument("--seed", type=int, default=42, help="데이터 생성 시 사용할 난수 시드 (기본값: 42)")
    parser.add_argument("--base_output_dir", default=os.path.join(PROJECT_ROOT, "pipeline_output_data"), help="최상위 출력 디렉터리")

    args = parser.parse_args()

    item_type = args.item_type
    num_samples = args.num_samples
    seed = args.seed
    
    generation_params = get_generation_parameters(item_type) # 생성 파라미터 가져오기

    pipeline_start_time = time.time() # 파이프라인 시작 시간 기록
    total_steps = 4 # 전체 단계 수
    
    # --- 고유한 작업 디렉터리 생성 ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 파일명용 스펙 태그 생성
    specs_tag_for_filename = format_specs_for_filename(item_type, generation_params)
    run_dir_name = f"{item_type}_{specs_tag_for_filename}_n{num_samples}_s{seed}_{timestamp}"
    current_run_output_dir = os.path.join(args.base_output_dir, run_dir_name)
    
    # --- 단계별 하위 디렉터리 경로 설정 ---
    excel_output_dir = os.path.join(current_run_output_dir, "01_excel_data")
    vtser_output_dir = os.path.join(current_run_output_dir, "02_vtser_files")
    txt_output_dir = os.path.join(current_run_output_dir, "03_vactran_txt_output")
    csv_output_dir = os.path.join(current_run_output_dir, "04_preprocessed_csv_data")

    # 모든 출력 디렉터리 생성
    os.makedirs(excel_output_dir, exist_ok=True)
    os.makedirs(vtser_output_dir, exist_ok=True)
    os.makedirs(txt_output_dir, exist_ok=True)
    os.makedirs(csv_output_dir, exist_ok=True)

    print(f"--- 파이프라인 시작: {item_type}, 샘플 수: {num_samples}, 시드: {seed} ---")
    print(f"모든 산출물은 다음 디렉터리에 저장됩니다: {current_run_output_dir}")

    # --- 1. sampleDataGen 실행 ---
    print(f"\n[단계 1/{total_steps}] {item_type} 샘플 데이터 생성 중...")
    sample_data_excel_filename = f"{item_type}_samples_n{num_samples}_s{seed}.xlsx"
    sample_data_excel_path = os.path.join(excel_output_dir, sample_data_excel_filename)
    
    data_gen_script_map = {
        "pipe": ["sampleDataGen", "pipeDataGen.py"],
        "elbow": ["sampleDataGen", "elbowDataGen.py"],
        "reducer": ["sampleDataGen", "reducerDataGen.py"],
        "expander": ["sampleDataGen", "expanderDataGen.py"],
    }

    # 기본 인자 구성
    script_args = [str(num_samples), "--output", sample_data_excel_path, "--seed", str(seed)]

    # item_type에 따라 generation_params에서 스펙을 가져와 인자로 추가
    if item_type == "pipe":
        params = generation_params
        script_args.extend([
            "--bin_width_inch", str(params["bin_width_inch"]),
            "--diameter_inch_min", str(params["diameter_inch_range"][0]),
            "--diameter_inch_max", str(params["diameter_inch_range"][1]),
            "--length_mm_min", str(params["length_mm_range"][0]), # mm 단위 유지
            "--length_mm_max", str(params["length_mm_range"][1]), # mm 단위 유지
        ])
    elif item_type == "elbow":
        params = generation_params
        script_args.extend([
            "--bin_width_inch", str(params["bin_width_inch"]),
            "--diameter_inch_min", str(params["diameter_inch_range"][0]),
            "--diameter_inch_max", str(params["diameter_inch_range"][1]),
            "--angles_deg", ",".join(map(str, params["angles_deg"])),
            "--angle_p45_prob", str(params["angle_p45_prob"]),
        ])
    elif item_type in ["reducer", "expander"]:
        params = generation_params
        script_args.extend([
            "--d1_bin_width_inch", str(params["D1_bin_width_inch"]),
            "--d1_inch_min", str(params["D1_inch_range"][0]),
            "--d1_inch_max", str(params["D1_inch_range"][1]),
            "--d2_inch_min_overall", str(params["D2_inch_min_overall"]), # _cm_ -> _inch_
            "--d2_inch_max_overall", str(params["D2_inch_max_overall"]), # _cm_ -> _inch_
            "--length_cm_min", str(params["length_cm_range"][0]),   # Length는 cm 단위 유지
            "--length_cm_max", str(params["length_cm_range"][1]),   # Length는 cm 단위 유지
        ])


    if not run_script(data_gen_script_map[item_type], script_args): # 수정된 script_args 사용
        print("!!! 샘플 데이터 생성 실패. 파이프라인 중단. !!!")
        sys.exit(1)
    print(f"샘플 데이터 생성 완료: {sample_data_excel_path}")
    print(f"--- 단계 1/{total_steps} 완료 ({(1/total_steps)*100:.0f}%) ---")

    # --- 2. Gen_vster 실행 ---
    print(f"\n[단계 2/{total_steps}] {item_type} VTSER 파일 생성 중...")
    gen_vster_script_map = {
        "pipe": ["GEN_vtser", "Pipe_generate.py"],
        "elbow": ["GEN_vtser", "Elbow_generate.py"],
        "reducer": ["GEN_vtser", "Reducer_generate.py"],
        "expander": ["GEN_vtser", "Reducer_generate.py"], 
    }
    if not run_script(gen_vster_script_map[item_type], [sample_data_excel_path, "--output_dir", vtser_output_dir]):
        print("!!! VTSER 파일 생성 실패. 파이프라인 중단. !!!")
        sys.exit(1)
    
    if not os.path.isdir(vtser_output_dir) or not os.listdir(vtser_output_dir):
        print(f"!!! 오류: VTSER 파일이 생성되지 않았거나 폴더를 찾을 수 없습니다: {vtser_output_dir} !!!")
        sys.exit(1)
    print(f"VTSER 파일 생성 완료. 저장 위치: {vtser_output_dir}")
    print(f"--- 단계 2/{total_steps} 완료 ({(2/total_steps)*100:.0f}%) ---")

    # --- 3. auto_vac_module 실행 ---
    print(f"\n[단계 3/{total_steps}] VacTran 자동화 실행 중...")
    try:
        run_vactran_automation(vtser_output_dir, txt_output_dir) 
    except Exception as e:
        print(f"!!! VacTran 자동화 중 오류 발생: {e} !!!")
        print("파이프라인 중단.")
        sys.exit(1)
    print(f"VacTran 자동화 완료. TXT 파일 저장 위치: {txt_output_dir}")
    print(f"--- 단계 3/{total_steps} 완료 ({(3/total_steps)*100:.0f}%) ---")

    # --- 4. dataPreprosessor 실행 ---
    print(f"\n[단계 4/{total_steps}] {item_type} 데이터 전처리 중...")
    # 최종 CSV 파일명 (폴더명에 이미 스펙과 타임스탬프가 있으므로, 여기서는 기본 정보만 포함)
    final_csv_filename_base = f"{item_type}_preprocessed_n{num_samples}_s{seed}"
    final_csv_filename = f"{final_csv_filename_base}.csv" # 스펙 태그는 폴더명에 이미 반영됨
    final_csv_path = os.path.join(csv_output_dir, final_csv_filename)

    preprocessor_script_map = {
        "pipe": ["dataPreprosessor", "pipePrepro.py"],
        "elbow": ["dataPreprosessor", "elbowPrepro.py"],
        "reducer": ["dataPreprosessor", "reducerPrepro.py"],
        "expander": ["dataPreprosessor", "reducerPrepro.py"], 
    }
    if not run_script(preprocessor_script_map[item_type], [txt_output_dir, "--output", final_csv_path]):
        print("!!! 데이터 전처리 실패. 파이프라인 중단. !!!")
        sys.exit(1)
    
    # 전처리 성공 후, CSV 파일에 주석 추가
    try:
        if os.path.exists(final_csv_path) and os.path.getsize(final_csv_path) > 0:
            # 기존 CSV 내용을 읽고, 주석을 추가한 후 다시 저장
            df_temp = pd.read_csv(final_csv_path) 
            
            specs_header_content = generate_csv_header_specs(item_type, num_samples, seed, generation_params)
            
            with open(final_csv_path, 'w', encoding='utf-8', newline='') as f:
                f.write(specs_header_content) # 주석 먼저 쓰기
                df_temp.to_csv(f, index=False, lineterminator='\n') # 그 다음 데이터 쓰기, line_terminator를 lineterminator로 수정
            print(f"CSV 파일에 스펙 주석 추가 완료: {final_csv_path}")
        elif os.path.exists(final_csv_path): # 파일은 존재하나 비어있는 경우
             print(f"경고: 전처리된 CSV 파일이 비어있습니다: {final_csv_path}. 스펙 주석을 추가하지 않습니다.")
        else:
            print(f"경고: 전처리된 CSV 파일을 찾을 수 없습니다: {final_csv_path}. 스펙 주석을 추가할 수 없습니다.")

    except pd.errors.EmptyDataError:
        print(f"경고: 전처리된 CSV 파일이 비어있거나 유효하지 않습니다: {final_csv_path}. 스펙 주석을 추가할 수 없습니다.")
    except Exception as e_spec:
        print(f"!!! CSV 스펙 주석 추가 중 오류 발생: {e_spec} !!!")

    print(f"데이터 전처리 완료: {final_csv_path}")
    print(f"--- 단계 4/{total_steps} 완료 ({(4/total_steps)*100:.0f}%) ---")

    pipeline_end_time = time.time() # 파이프라인 종료 시간 기록
    total_elapsed_time = pipeline_end_time - pipeline_start_time
    print(f"\n--- 모든 프로세스 성공적으로 완료 ---")
    print(f"최종 결과물: {final_csv_path}")
    print(f"모든 산출물 및 최종 결과는 다음 디렉터리에 있습니다: {current_run_output_dir}")
    # print(f"  - 최종 데이터: {final_csv_path}") # 위에서 이미 출력됨
    print(f"총 소요 시간: {total_elapsed_time:.2f}초")

if __name__ == "__main__":
    main()