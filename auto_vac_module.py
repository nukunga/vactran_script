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
        # 모든 데스크탑 윈도우를 순회하며 'VacTran' 문자열을 포함하는 창을 찾음
        windows = Desktop(backend="uia").windows(title_re=".*VacTran.*", visible_only=True, enabled_only=True)
        if windows:
            # 여러개가 찾아질 경우, 가장 적합한 것을 선택 (예: PID 비교 등)
            # 여기서는 첫번째 것을 반환
            # print(f"찾은 VacTran 창: {[w.window_text() for w in windows]}")
            try:
                # 간혹 app.window()가 바로 실패하는 경우가 있어 핸들 직접 사용 시도
                return app.connect(handle=windows[0].handle).window(handle=windows[0].handle)
            except Exception: # connect 실패 시 기존 방식 사용
                 return app.window(title_re=".*VacTran.*")
        time.sleep(1)
    raise RuntimeError("VacTran 메인 윈도우를 찾지 못했습니다. 프로그램이 정상적으로 실행되었는지 확인하세요.")

def run_vactran_automation(input_dir_path, output_dir_path):
    """
    VacTran 자동화 프로세스를 실행합니다.
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
        out_path = os.path.join(output_dir_path, os.path.splitext(fname)[0] + '.txt')
        
        print(f"  파일 처리 중: {fname}")

        app = None # app 변수 초기화
        try:
            # 1) 파일 인수로 VacTran 실행
            # 따옴표로 경로를 감싸서 공백이 있는 경로도 처리
            app = Application(backend="uia").start(f'"{VACTRAN_PATH}" "{in_path}"')
            time.sleep(3) # VacTran 초기 로딩 시간 (충분히 길게)

            main_win = find_main_window(app) # 메인 윈도우 찾기
            main_win.set_focus() # 창 활성화
            time.sleep(2) # 창 포커스 및 내부 로딩 대기

            # 2) Window 메뉴 -> 6. Series Text Window (ALT+W, 6, ENTER)
            keyboard.send_keys('%W') # Alt + W
            time.sleep(0.5)
            keyboard.send_keys('6')
            time.sleep(0.2)
            keyboard.send_keys('{ENTER}')
            time.sleep(1.5) # 창 전환 및 로딩 대기

            # 3) Graph 메뉴 -> 19. Conductance vs Pressure (ALT+G, 아래로 18번, ENTER)
            keyboard.send_keys('%G') # Alt + G
            time.sleep(0.5)
            for _ in range(18): # "Conductance vs Pressure" 항목으로 이동 (1부터 시작하면 18번)
                keyboard.send_keys('{DOWN}')
                time.sleep(0.1)
            keyboard.send_keys('{ENTER}')
            time.sleep(10) # 그래프 생성 및 표시 대기 (매우 중요, 시스템에 따라 조절)

            # 4) Window 메뉴 -> 2. Main Text Window (ALT+W, 2, ENTER)
            main_win.set_focus() # 메인 윈도우 다시 활성화 (중요)
            time.sleep(0.5)
            keyboard.send_keys('%W') # Alt + W
            time.sleep(0.5)
            keyboard.send_keys('2')
            time.sleep(0.2)
            keyboard.send_keys('{ENTER}')
            time.sleep(1.5) # Main Text Window 활성화 및 내용 로드 대기

            # 5) Main Text Window 내용 복사 (Ctrl+A, Ctrl+C)
            time.sleep(1) # 확실한 포커스를 위해 추가 대기
            keyboard.send_keys('^a') # Ctrl + A (전체 선택)
            time.sleep(0.3)
            keyboard.send_keys('^c') # Ctrl + C (복사)
            time.sleep(0.5)
            
            text_content = clipboard.paste() # 클립보드에서 내용 가져오기

            # 6) 텍스트 파일로 저장
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            print(f"    -> 저장 완료: {out_path}")

        except Exception as e:
            print(f"    !!! 오류 발생 ({fname} 처리 중): {e}")
            print(f"    !!! 이 파일 처리를 건너뜁니다: {fname}")
        finally:
            # 7) VacTran 종료 (ALT+F4)
            if app and app.is_process_running():
                try:
                    if 'main_win' in locals() and main_win.exists():
                        main_win.close() # 정상 종료 시도
                        time.sleep(1)
                        if app.is_process_running(): # 그래도 실행 중이면 강제 종료
                           app.kill()
                    else: # 메인 윈도우를 못찾았거나 이미 닫혔으면
                        app.kill() # 프로세스 강제 종료
                except Exception as e_close:
                    print(f"      VacTran 종료 중 오류: {e_close}")
                    if app.is_process_running():
                        app.kill() # 최후의 수단
            time.sleep(1) # 다음 파일 처리 전 잠시 대기

    print(f"VacTran 자동화 완료. 결과는 '{output_dir_path}'에 저장됨.")

if __name__ == "__main__":
    # 이 스크립트를 직접 실행할 때를 위한 CLI 인터페이스
    parser = argparse.ArgumentParser(description="VacTran 자동화 실행 모듈")
    parser.add_argument("input_dir", help="VTSER 파일들이 있는 입력 디렉터리")
    parser.add_argument("output_dir", help="생성된 TXT 파일들을 저장할 출력 디렉터리")
    cli_args = parser.parse_args()
    
    run_vactran_automation(cli_args.input_dir, cli_args.output_dir)