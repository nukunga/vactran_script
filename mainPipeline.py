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
# from autoVacModule import run_vactran_automation # 기존 임포트 라인 주석 처리 또는 삭제

# autoVacModule 임포트 시도 및 clipboard 관련 오류 처리
AUTO_VAC_MODULE_AVAILABLE = False
try:
    from autoVacModule import run_vactran_automation
    AUTO_VAC_MODULE_AVAILABLE = True
except ImportError as e:
    # 에러 메시지에 'clipboard'가 포함되어 있는지 확인 (대소문자 구분 없이)
    if 'clipboard' in str(e).lower():
        print(f"WARNING (mainPipeline.py): Failed to import 'autoVacModule', likely due to missing 'clipboard' module: {e}")
        print("                         VacTran automation (pipeline step 3) will be unavailable if mainPipeline.py is run directly.")
        print("                         To enable it, please install the 'clipboard' module (e.g., 'pip install clipboard') and ensure its dependencies are met in your Python environment.")
        
        # run_vactran_automation을 호출 시 오류를 발생시키는 플레이스홀더 함수로 정의
        def run_vactran_automation(*args, **kwargs):
            error_message = (
                "run_vactran_automation cannot be executed because 'autoVacModule' failed to load "
                "due to a missing 'clipboard' dependency. Please check startup warnings."
            )
            raise ImportError(error_message)
    else:
        # 'clipboard'와 관련 없는 다른 ImportError의 경우, 에러를 다시 발생시켜 파악하도록 함
        print(f"ERROR (mainPipeline.py): Failed to import 'autoVacModule' for a reason other than 'clipboard': {e}")
        raise
except Exception as e_other: # 다른 예외 처리 (예: autoVacModule.py 내부의 구문 오류 등)
    print(f"ERROR (mainPipeline.py): An unexpected error occurred while trying to import 'autoVacModule': {e_other}")
    raise


# 프로젝트 루트 디렉터리 설정
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def get_generation_parameters(item_type):
    """각 아이템 타입별 데이터 생성 파라미터 기본값을 반환합니다."""
    base_params = {
        "pipe": {
            "diameter_inch_spec": (1.0, 10.0, 5), # 파이프 직경 (min_inch, max_inch, num_intervals)
            "length_mm_spec": (100, 20000, 10),   # 파이프 길이 (min_mm, max_mm, num_intervals)
        },
        "elbow": {
            "diameter_inch_spec": (1.0, 5.0, 4),  # 엘보 직경 (min_inch, max_inch, num_intervals)
            "angles_deg": [15, 20, 30, 45],       # 생성될 엘보의 각도 목록.
            "quantity": 1,                        # VTSER 파일에 기록될 수량.
        },
        "reducer": { 
            "d1_inch_spec": (0.8, 12.0, 10),      # Reducer 큰 쪽 직경(D1) (min_inch, max_inch, num_intervals)
            "d2_inch_spec": (0.5, 12.0, 10),       # Reducer 작은 쪽 직경(D2) (min_inch, max_inch, num_intervals)
            "length_mm_spec": (25.0, 1000.0, 10), # Reducer 길이 (min_mm, max_mm, num_intervals)
        },
        "expander": { 
            "d1_inch_spec": (0.5, 12.0, 10),       # Expander 작은 쪽 직경(D1) (min_inch, max_inch, num_intervals)
            "d2_inch_spec": (0.8, 12.0, 10),      # Expander 큰 쪽 직경(D2) (min_inch, max_inch, num_intervals)
            "length_mm_spec": (25.0, 1000.0, 10), # Expander 길이 (min_mm, max_mm, num_intervals)
        }
    }

    params = base_params.get(item_type)
    if not params:
        return {"description": "N/A - Unknown item type"}

    # Descriptions for logging and headers
    if item_type == "pipe":
        dia_spec = params['diameter_inch_spec']
        len_spec = params['length_mm_spec']
        params["description"] = (
            f"Pipe: Diameter {dia_spec[0]}-{dia_spec[1]} inches ({dia_spec[2]} intervals, converted to cm internally), "
            f"Length {len_spec[0]}-{len_spec[1]} mm ({len_spec[2]} intervals, converted to cm internally)."
        )
    elif item_type == "elbow":
        dia_spec = params['diameter_inch_spec']
        params["description"] = (
            f"Elbow: Diameter {dia_spec[0]}-{dia_spec[1]} inches ({dia_spec[2]} intervals, converted to cm internally), "
            f"Angles ({', '.join(map(str, params['angles_deg']))} deg, sampled uniformly per dia_interval-angle combination). "
            f"Quantity={params['quantity']}."
        )
    elif item_type == "reducer":
        d1_spec = params['d1_inch_spec']
        d2_spec = params['d2_inch_spec']
        len_spec = params['length_mm_spec']
        params["description"] = (
            f"Reducer (D1_cm > D2_cm, D1_cm > 1.3*D2_cm after internal cm conversion): "
            f"D1 {d1_spec[0]}-{d1_spec[1]} inches ({d1_spec[2]} intervals), "
            f"D2 {d2_spec[0]}-{d2_spec[1]} inches ({d2_spec[2]} intervals), "
            f"Length {len_spec[0]}-{len_spec[1]} mm ({len_spec[2]} intervals, converted to cm internally)."
        )
    elif item_type == "expander":
        d1_spec = params['d1_inch_spec']
        d2_spec = params['d2_inch_spec']
        len_spec = params['length_mm_spec']
        params["description"] = (
            f"Expander (D2_cm > D1_cm, D2_cm > 1.3*D1_cm after internal cm conversion): "
            f"D1 {d1_spec[0]}-{d1_spec[1]} inches ({d1_spec[2]} intervals), "
            f"D2 {d2_spec[0]}-{d2_spec[1]} inches ({d2_spec[2]} intervals), "
            f"Length {len_spec[0]}-{len_spec[1]} mm ({len_spec[2]} intervals, converted to cm internally)."
        )
    return params

def format_specs_for_filename(item_type, params):
    """파일명에 포함될 스펙 태그를 생성합니다."""
    if not isinstance(params, dict): return ""
    try:
        if item_type == "pipe":
            d_spec = params.get("diameter_inch_spec", ("N/A","N/A","N/A"))
            l_spec = params.get("length_mm_spec", ("N/A","N/A","N/A"))
            return f"D{d_spec[0]}-{d_spec[1]}in({d_spec[2]})_L{l_spec[0]}-{l_spec[1]}mm({l_spec[2]})"
        elif item_type == "elbow":
            d_spec = params.get("diameter_inch_spec", ("N/A","N/A","N/A"))
            a_rng = params.get("angles_deg", ["N/A"])
            return f"D{d_spec[0]}-{d_spec[1]}in({d_spec[2]})_Ang{min(a_rng)}-{max(a_rng)}deg"
        elif item_type == "reducer":
            d1_spec = params.get("d1_inch_spec", ("N/A","N/A","N/A"))
            d2_spec = params.get("d2_inch_spec", ("N/A","N/A","N/A"))
            l_spec = params.get("length_mm_spec", ("N/A","N/A","N/A"))
            return f"D1_{d1_spec[0]}-{d1_spec[1]}in({d1_spec[2]})_D2_{d2_spec[0]}-{d2_spec[1]}in({d2_spec[2]})_L{l_spec[0]}-{l_spec[1]}mm({l_spec[2]})"
        elif item_type == "expander":
            d1_spec = params.get("d1_inch_spec", ("N/A","N/A","N/A"))
            d2_spec = params.get("d2_inch_spec", ("N/A","N/A","N/A"))
            l_spec = params.get("length_mm_spec", ("N/A","N/A","N/A"))
            return f"D1_{d1_spec[0]}-{d1_spec[1]}in({d1_spec[2]})_D2_{d2_spec[0]}-{d2_spec[1]}in({d2_spec[2]})_L{l_spec[0]}-{l_spec[1]}mm({l_spec[2]})"
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
            f"# - Diameter inch spec (min,max,intervals): {params.get('diameter_inch_spec', 'N/A')}",
            f"# - Length mm spec (min,max,intervals): {params.get('length_mm_spec', 'N/A')}",
        ])
    elif item_type == "elbow":
        param_details.extend([
            f"# - Diameter inch spec (min,max,intervals): {params.get('diameter_inch_spec', 'N/A')}",
            f"# - Angles deg list: {params.get('angles_deg', 'N/A')}",
            f"# - Quantity: {params.get('quantity', 'N/A')}"
        ])
    elif item_type == "reducer":
        param_details.extend([
            f"# - D1 inch spec (min,max,intervals): {params.get('d1_inch_spec', 'N/A')}",
            f"# - D2 inch spec (min,max,intervals): {params.get('d2_inch_spec', 'N/A')}",
            f"# - Length mm spec (min,max,intervals): {params.get('length_mm_spec', 'N/A')}"
        ])
    elif item_type == "expander":
        param_details.extend([
            f"# - D1 inch spec (min,max,intervals): {params.get('d1_inch_spec', 'N/A')}",
            f"# - D2 inch spec (min,max,intervals): {params.get('d2_inch_spec', 'N/A')}",
            f"# - Length mm spec (min,max,intervals): {params.get('length_mm_spec', 'N/A')}"
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
    parser.add_argument("--seed", "-s",type=int, default=42, help="데이터 생성 시 사용할 난수 시드 (기본값: 42)")
    parser.add_argument("--base_output_dir", default=os.path.join(PROJECT_ROOT, "pipeline_output_data"), help="최상위 출력 디렉터리")
    # 아래 라인 추가: 동시 실행 개수(n)를 지정하는 옵션
    parser.add_argument("--concurrency","-c" ,type=int, default=4, help="VacTran 동시 실행 프로세스 수 (기본값: 4)")
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
                diameter_inch_spec=params["diameter_inch_spec"],
                length_mm_spec=params["length_mm_spec"],
                seed=seed
            )
        elif item_type == 'elbow':
            params = generation_params
            elbowDataGen.run(
                output_file=sample_data_excel_path,
                total_samples=num_samples,
                diameter_inch_spec=params["diameter_inch_spec"],
                angles_deg_list=params["angles_deg"],
                seed=seed
            )
        elif item_type == 'reducer':
            params = generation_params
            reducerDataGen.run(
                 output_file=sample_data_excel_path,
                 total_samples=num_samples,
                 d1_inch_spec=params["d1_inch_spec"],
                 d2_inch_spec=params["d2_inch_spec"],
                 length_mm_spec=params["length_mm_spec"],
                 seed=seed
            )
        elif item_type == 'expander':
            params = generation_params
            expanderDataGen.run(
                output_file=sample_data_excel_path,
                total_samples=num_samples,
                d1_inch_spec=params["d1_inch_spec"],
                d2_inch_spec=params["d2_inch_spec"],
                length_mm_spec=params["length_mm_spec"],
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
    # 출력 메시지와 함수 호출 부분 수정
    print(f"\n[단계 3/{total_steps}] VacTran 자동화 실행 중 (동시 실행: {args.concurrency})...")
    try:
        if not AUTO_VAC_MODULE_AVAILABLE:
            raise ImportError("VacTran automation (step 3) skipped: 'autoVacModule' could not be loaded, likely due to a missing 'clipboard' dependency. Check startup warnings.")
        
        # concurrency 인자를 전달하도록 함수 호출 수정
        run_vactran_automation(vtser_output_dir, txt_output_dir, concurrency=args.concurrency)
        
        print(f"VacTran 자동화 완료. TXT 파일 저장 위치: {txt_output_dir}")
        print(f"--- 단계 3/{total_steps} 완료 ({(3/total_steps)*100:.0f}%) ---")
    except ImportError as e_imp:
        print(f"!!! VacTran 자동화 중단 (ImportError): {e_imp} !!!")
        print("파이프라인의 이 단계는 건너뛰고 다음 단계로 진행하지 않습니다. 문제를 해결하고 다시 시도해주세요.")
        sys.exit(1)
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