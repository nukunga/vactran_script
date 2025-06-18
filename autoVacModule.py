import os
import time
import clipboard
from pywinauto import Application, Desktop, keyboard
import argparse
from typing import List, Dict, Any

# === 환경 설정 ===
VACTRAN_PATH = r"C:\Program Files (x86)\PEC\VacTran 3\VacTran.exe" # VacTran 설치 경로 확인 필요
DEFAULT_CONCURRENCY = 4 # 동시에 실행할 기본 프로세스 수

def find_main_window(app: Application, timeout: int = 20) -> Any:
    """VacTran 메인 윈도우를 찾습니다."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        # 새로 시작된 프로세스에 속한 창만 대상으로 검색하여 정확도 향상
        windows = Desktop(backend="uia").windows(process=app.process, title_re=".*VacTran.*", visible_only=True, enabled_only=True)
        if windows:
            try:
                # connect 호출은 특정 창에 대한 제어권을 더 안정적으로 가져올 수 있습니다.
                return app.connect(handle=windows[0].handle).window(handle=windows[0].handle)
            except Exception:
                # 예외 발생 시 이전 방식으로 재시도
                return app.window(title_re=".*VacTran.*")
        time.sleep(0.5)
    raise RuntimeError(f"VacTran 메인 윈도우를 찾지 못했습니다 (프로세스 ID: {app.process}). 프로그램이 정상적으로 실행되었는지 확인하세요.")


def process_batch(batch_files: List[str], input_dir_path: str, output_dir_path: str):
    """
    하나의 파일 배치(batch)를 동시에 처리합니다.
    1. 모든 인스턴스 실행
    2. 순차적으로 그래프 생성 명령 전송
    3. 데이터 순차적으로 추출 및 저장
    """
    running_processes: List[Dict[str, Any]] = []

    # 단계 1: Launch Phase - 배치 내 모든 VacTran 인스턴스를 시작합니다.
    print(f"--- Launching batch of {len(batch_files)} processes ---")
    for fname in batch_files:
        in_path = os.path.join(input_dir_path, fname)
        base_fname_no_ext = os.path.splitext(fname)[0]
        out_path = os.path.join(output_dir_path, base_fname_no_ext + '.txt')
        model_out_path = os.path.join(output_dir_path, base_fname_no_ext + '_model.txt')

        try:
            app = Application(backend="uia").start(f'"{VACTRAN_PATH}" "{in_path}"')
            # 프로세스가 시작되고 창을 열 충분한 시간을 줍니다.
            time.sleep(1)

            for attempt in range(5):
                try:
                    # 제목에 'Error'가 포함된 창을 찾습니다 (대소문자 무관).
                    # timeout=0.5 로 설정하여 창이 없으면 즉시 다음으로 넘어갑니다.
                    error_window = app.window(title_re=".*[Ee]rror.*", top_level_only=True, timeout=0.5)
                    
                    print(f"  -> Error popup detected: '{error_window.window_text()}'. Pressing ENTER. (Attempt {attempt + 1})")
                    error_window.send_keys('{ENTER}')
                    time.sleep(0.5)  # 팝업이 닫힐 시간을 줍니다.

                except (TimeoutError, NameError): # pywinauto.timings.TimeoutError, pywinauto.findwindows.ElementNotFoundError
                    # 'Error' 창을 찾지 못한 경우로, 정상적인 상황입니다.
                    # 팝업 확인 루프를 중단하고 다음 단계로 진행합니다.
                    break
                except Exception as e:
                    # 예기치 못한 다른 오류가 발생하면 루프를 중단합니다.
                    print(f"  -> An unexpected error occurred while checking for popups: {e}")
                    break

            main_win = find_main_window(app)
            running_processes.append({
                'app': app,
                'main_win': main_win,
                'out_path': out_path,
                'model_out_path': model_out_path,
                'fname': fname,
                'failed': False
            })
            print(f"  -> Launched process for: {fname} (PID: {app.process})")
        except Exception as e:
            print(f"  !!! Failed to launch or find window for {fname}: {e}")

    # 단계 2: Graph Generation Phase - 각 프로세스에 대해 순차적으로 그래프 생성을 시작합니다.
    print("\n--- Initiating graph generation for all processes in batch ---")
    for i, proc_info in enumerate(running_processes):
        main_win = proc_info['main_win']
        fname = proc_info['fname']
        print(f"  -> Sending graph generation commands to: {fname}")
        try:
            main_win.set_focus()

            # 그래프 생성 키 입력
            keyboard.send_keys('%W')  # Alt + W
            time.sleep(0.2)
            keyboard.send_keys('6')
            time.sleep(0.2)
            keyboard.send_keys('{ENTER}')
            time.sleep(0.5)
            keyboard.send_keys('%G')  # Alt + G
            time.sleep(0.5)
            for _ in range(12):
                keyboard.send_keys('{UP}')
                time.sleep(0.02)
            keyboard.send_keys('{ENTER}')
        except Exception as e:
            print(f"  !!! Failed to send commands to {fname}: {e}")
            proc_info['failed'] = True

    # 단계 3: Wait Phase - 모든 그래프 계산 및 렌더링을 위해 5초 대기합니다.
    print("\n--- Waiting 3 seconds for graphs to compute and render... ---")
    time.sleep(3)

    # 단계 4: Data Extraction, Save, and Cleanup Phase - 순차적으로 데이터를 처리하고 종료합니다.
    print("\n--- Extracting data, saving, and closing processes sequentially ---")
    for proc_info in running_processes:
        # 실패 플래그가 설정된 프로세스는 건너뜁니다.
        if proc_info.get('failed'):
            print(f"  -> Skipping failed process for: {proc_info['fname']}")
        else:
            main_win = proc_info['main_win']
            out_path = proc_info['out_path']
            model_out_path = proc_info['model_out_path']
            fname = proc_info['fname']
            print(f"  -> Processing data for: {fname}")

            try:
                main_win.set_focus()

                # a) Main Text Window (Conductance 데이터) 저장
                time.sleep(0.3)
                keyboard.send_keys('%W')
                time.sleep(0.2)
                keyboard.send_keys('2')
                time.sleep(0.2)
                keyboard.send_keys('{ENTER}')
                time.sleep(0.5)

                keyboard.send_keys('^a')
                time.sleep(0.3)
                keyboard.send_keys('^c')
                time.sleep(0.5)
                text_content_main = clipboard.paste()

                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(text_content_main)
                print(f"    -> Conductance data saved: {os.path.basename(out_path)}")

                # b) Series Text Window (모델 데이터) 저장
                main_win.set_focus()
                time.sleep(0.5)
                keyboard.send_keys('%W')
                time.sleep(0.3)
                keyboard.send_keys('6')
                time.sleep(1.0)
                keyboard.send_keys('{ENTER}')
                time.sleep(0.2)
                keyboard.send_keys('{ENTER}')
                time.sleep(0.2)
                keyboard.send_keys('{RIGHT}')
                time.sleep(0.2)
                keyboard.send_keys('{TAB}')
                time.sleep(0.5)

                keyboard.send_keys('^a')
                time.sleep(0.3)
                keyboard.send_keys('^c')
                time.sleep(0.5)
                text_content_model = clipboard.paste()

                with open(model_out_path, 'w', encoding='utf-8') as f:
                    f.write(text_content_model)
                print(f"    -> Model data saved: {os.path.basename(model_out_path)}")

            except Exception as e:
                print(f"    !!! Error during data extraction for {fname}: {e}")

        # c) VacTran 종료 (성공 여부와 관계없이 정리)
        app = proc_info['app']
        if app and app.is_process_running():
            try:
                app.kill()
                print(f"  -> Closed process for: {proc_info['fname']}")
            except Exception as e_close:
                print(f"      Error closing process for {proc_info['fname']}: {e_close}")
        time.sleep(0.5) # 다음 프로세스 처리 전 안정성을 위한 짧은 대기


def run_vactran_automation(input_dir_path: str, output_dir_path: str, concurrency: int = DEFAULT_CONCURRENCY):
    """
    VacTran 자동화 프로세스를 실행하여 .txt 결과 파일을 저장합니다.
    지정된 수의 프로세스를 동시에 실행하여 작업을 병렬 처리합니다.
    
    :param input_dir_path: VTSER 파일들이 있는 입력 디렉터리 경로.
    :param output_dir_path: 생성된 TXT 파일들을 저장할 출력 디렉터리 경로.
    :param concurrency: 동시에 실행할 VacTran 프로세스의 수.
    """
    print(f"VacTran 자동화 시작: 입력 폴더 '{input_dir_path}', 출력 폴더 '{output_dir_path}'")
    print(f"동시 실행 수: {concurrency}")
    os.makedirs(output_dir_path, exist_ok=True)

    if not os.path.isdir(input_dir_path):
        print(f"오류: VTSER 입력 디렉터리 '{input_dir_path}'를 찾을 수 없습니다.")
        return

    vtser_files = [f for f in sorted(os.listdir(input_dir_path)) if f.lower().endswith('.vtser')]
    if not vtser_files:
        print(f"경고: 입력 디렉터리 '{input_dir_path}'에 VTSER 파일이 없습니다.")
        return
    
    total_files = len(vtser_files)
    print(f"총 {total_files}개의 VTSER 파일을 처리합니다.")

    # 파일 목록을 concurrency 크기의 배치로 나눕니다.
    for i in range(0, total_files, concurrency):
        batch = vtser_files[i:i + concurrency]
        batch_num = (i // concurrency) + 1
        total_batches = (total_files + concurrency - 1) // concurrency
        print(f"\n>>> Processing Batch {batch_num} of {total_batches} <<<")
        process_batch(batch, input_dir_path, output_dir_path)

    print(f"\nVacTran 자동화 완료. 모든 결과는 '{output_dir_path}'에 저장됨.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VacTran 자동화 실행 모듈. 여러 프로세스를 동시에 실행합니다.")
    parser.add_argument("input_dir", help="VTSER 파일들이 있는 입력 디렉터리")
    parser.add_argument("output_dir", help="생성된 TXT 파일들을 저장할 출력 디렉터리")
    parser.add_argument("-n", "--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                        help=f"동시에 실행할 프로세스 수 (기본값: {DEFAULT_CONCURRENCY})")
    cli_args = parser.parse_args()
    
    run_vactran_automation(cli_args.input_dir, cli_args.output_dir, cli_args.concurrency)