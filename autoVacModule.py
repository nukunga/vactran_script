import os
import time
import clipboard
from pywinauto import Application, Desktop, keyboard
import argparse

# === 환경 설정 ===
VACTRAN_PATH = r"C:\Program Files (x86)\PEC\VacTran 3\VacTran.exe" # VacTran 설치 경로 확인 필요

def find_main_window(app):
    """VacTran 메인 윈도우를 찾습니다."""
    for _ in range(20): # 탐색 시간 증가 (최대 20초)
        windows = Desktop(backend="uia").windows(title_re=".*VacTran.*", visible_only=True, enabled_only=True)
        if windows:
            try:
                return app.connect(handle=windows[0].handle).window(handle=windows[0].handle)
            except Exception:
                 return app.window(title_re=".*VacTran.*")
        time.sleep(1)
    raise RuntimeError("VacTran 메인 윈도우를 찾지 못했습니다. 프로그램이 정상적으로 실행되었는지 확인하세요.")

def run_vactran_automation(input_dir_path, output_dir_path):
    """
    VacTran 자동화 프로세스를 실행하여 Conductance 데이터(.txt)와 모델 데이터(_model.txt)를 저장합니다.
    :param input_dir_path: VTSER 파일들이 있는 입력 디렉터리 경로.
    :param output_dir_path: 생성된 TXT 파일들을 저장할 출력 디렉터리 경로.
    """
    print(f"VacTran 자동화 시작: 입력 폴더 '{input_dir_path}', 출력 폴더 '{output_dir_path}'")
    os.makedirs(output_dir_path, exist_ok=True)

    if not os.path.isdir(input_dir_path):
        print(f"오류: VTSER 입력 디렉터리 '{input_dir_path}'를 찾을 수 없습니다.")
        return

    vtser_files = [f for f in sorted(os.listdir(input_dir_path)) if f.lower().endswith('.vtser')]
    if not vtser_files:
        print(f"경고: 입력 디렉터리 '{input_dir_path}'에 VTSER 파일이 없습니다.")
        return

    for fname in vtser_files:
        in_path = os.path.join(input_dir_path, fname)
        base_fname_no_ext = os.path.splitext(fname)[0]
        out_path = os.path.join(output_dir_path, base_fname_no_ext + '.txt')
        model_out_path = os.path.join(output_dir_path, base_fname_no_ext + '_model.txt') # 모델 데이터 저장 경로

        print(f"  파일 처리 중: {fname}")

        app = None
        main_win = None
        try:
            # 1) 파일 인수로 VacTran 실행
            app = Application(backend="uia").start(f'"{VACTRAN_PATH}" "{in_path}"')
            time.sleep(3)

            main_win = find_main_window(app)
            main_win.set_focus()
            time.sleep(2)

            # 2) 그래프 생성을 위한 초기 작업 (Conductance vs Pressure)
            keyboard.send_keys('%W') # Alt + W
            time.sleep(0.5)
            keyboard.send_keys('6')
            time.sleep(0.2)
            keyboard.send_keys('{ENTER}')
            time.sleep(1.0)

            keyboard.send_keys('%G') # Alt + G
            time.sleep(0.5)
            for _ in range(18):
                keyboard.send_keys('{DOWN}')
                time.sleep(0.1)
            keyboard.send_keys('{ENTER}')
            time.sleep(5) # 그래프 생성 대기 (중요)

            # 3) Main Text Window (Conductance 데이터) 저장
            main_win.set_focus()
            time.sleep(0.5)
            keyboard.send_keys('%W')
            time.sleep(0.5)
            keyboard.send_keys('2')
            time.sleep(0.2)
            keyboard.send_keys('{ENTER}')
            time.sleep(1.5)

            keyboard.send_keys('^a')
            time.sleep(0.3)
            keyboard.send_keys('^c')
            time.sleep(0.5)
            text_content_main = clipboard.paste()

            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(text_content_main)
            print(f"    -> Conductance 데이터 저장 완료: {out_path}")

            # 4) Series Text Window (모델 데이터) 저장
            if main_win and main_win.exists():
                 main_win.set_focus()
            else:
                main_win = find_main_window(app)
                main_win.set_focus()
            time.sleep(0.5)
            keyboard.send_keys('%W')
            time.sleep(0.5)
            keyboard.send_keys('6')
            time.sleep(0.2)
            keyboard.send_keys('{ENTER}')
            time.sleep(0.2) # 엔터 키 입력 전 짧은 대기
            keyboard.send_keys('{ENTER}') # 엔터 키 입력
            time.sleep(0.2) # 오른쪽 화살표 키 입력 전 짧은 대기
            keyboard.send_keys('{RIGHT}') # 오른쪽 화살표 키 입력
            time.sleep(0.2) # 탭 키 입력 전 짧은 대기
            keyboard.send_keys('{TAB}') # 탭 키 입력
            time.sleep(1.0) # Series Text Window 활성화 및 내용 로드 대기

            # 7) Series Text Window 내용 복사 (Ctrl+A, Ctrl+C) 및 저장
            time.sleep(1)
            keyboard.send_keys('^a')
            time.sleep(0.3)
            keyboard.send_keys('^c')
            time.sleep(0.5)
            text_content_model = clipboard.paste()

            with open(model_out_path, 'w', encoding='utf-8') as f:
                f.write(text_content_model)
            print(f"    -> 모델 데이터 저장 완료: {model_out_path}")

        except Exception as e:
            print(f"    !!! 오류 발생 ({fname} 처리 중): {e}")
            print(f"    !!! 이 파일 처리를 건너뜁니다: {fname}")
        finally:
            # 5) VacTran 종료
            if app and app.is_process_running():
                try:
                    if main_win and main_win.exists():
                        main_win.close()
                        time.sleep(1)
                    if app.is_process_running():
                       app.kill()
                except Exception as e_close:
                    print(f"      VacTran 종료 중 오류: {e_close}")
                    if app.is_process_running():
                        app.kill()
            time.sleep(1)

    print(f"VacTran 자동화 완료. 결과는 '{output_dir_path}'에 저장됨.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VacTran 자동화 실행 모듈")
    parser.add_argument("input_dir", help="VTSER 파일들이 있는 입력 디렉터리")
    parser.add_argument("output_dir", help="생성된 TXT 파일들을 저장할 출력 디렉터리")
    cli_args = parser.parse_args()
    
    run_vactran_automation(cli_args.input_dir, cli_args.output_dir)