
import sys
import os
import time
from playwright.sync_api import sync_playwright

UPLOAD_BUTTON_XPATH = '/html/body/app-root/div/app-main-layout/div/div[2]/app-board-view/div/div[2]/div[2]/div/div[1]/div/div[1]/board-task-box[3]/div/div[1]/div[6]/a[5]'

def login(page, username, password):
    LOGIN_URL = "https://sso.earthlink.iq/auth/realms/elcld.ai/protocol/openid-connect/auth?response_type=code&client_id=fms-msp&redirect_uri=https%3A%2F%2Fmsp.go2field.iq%2Fboard%2Fmy-unit-tasks&scope=openid"
    print("Navigating to login page...", flush=True)
    page.goto(LOGIN_URL)
    try:
        print("Waiting for username field to be visible...", flush=True)
        page.wait_for_selector('//*[@id="username"]', timeout=10000)
        print("Filling username...", flush=True)
        page.fill('//*[@id="username"]', username)
        print("Waiting for password field to be visible...", flush=True)
        page.wait_for_selector('//*[@id="password"]', timeout=10000)
        print("Filling password...", flush=True)
        page.fill('//*[@id="password"]', password)
    except Exception as e:
        print(f"[ERROR] Failed to fill username or password: {e}", flush=True)
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        screenshot_path = f"Errors/login_fill_error_{ts}.png"
        try:
            page.screenshot(path=screenshot_path)
            print(f"Screenshot of login error saved to {screenshot_path}", flush=True)
        except Exception as se:
            print(f"Failed to save screenshot: {se}", flush=True)
        raise
    print("Clicking sign in...", flush=True)
    page.click('//*[@id="kc-form-buttons"]')
    print("Waiting for OTP/password page...", flush=True)
    try:
        page.wait_for_url("**/login-actions/authenticate?*", timeout=30000)
        print("Filling OTP/password again...", flush=True)
        page.fill('//*[@id="pi_otp"]', password)
        print("Clicking confirm...", flush=True)
        page.click('//*[@id="kc-login"]')
        print("Waiting for page to load after confirm...", flush=True)
        page.wait_for_timeout(5000)
    except Exception:
        print("No OTP/password page detected.", flush=True)
    print("Login and initial navigation complete.", flush=True)
    max_retries = 4
    for attempt in range(max_retries):
        try:
            print("Navigating to board page after login...", flush=True)
            board_url = "https://msp.go2field.iq/board/a22c39cb-093c-d83e-7dd1-a8c7a5d0fa7b"
            page.goto(board_url)
            page.wait_for_timeout(2000)
            print("Waiting for My Unit Tasks button in sidebar...", flush=True)
            my_unit_tasks_button = page.wait_for_selector('xpath=//*[@id="app_container"]/app-main-layout/div/div[2]/app-board-view/div/div[1]/div[4]/div[3]/a[2]', timeout=15000)
            print("My Unit Tasks button found. Clicking...", flush=True)
            my_unit_tasks_button.click()
            print("My Unit Tasks button clicked. Waiting for columns to appear...", flush=True)
            page.wait_for_selector('.board-col', timeout=15000)
            print("Columns appeared. Waiting for content to load...", flush=True)
            page.wait_for_timeout(6000)
            break
        except Exception as e:
            content = page.content()
            if "403" in content or "permission" in content.lower():
                print(f"403 Permission error detected on attempt {attempt+1}. Aborting login navigation.", flush=True)
                from datetime import datetime
                import os
                os.makedirs("Errors", exist_ok=True)
                ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                screenshot_path = f"Errors/error_403_permission_{ts}.png"
                try:
                    page.screenshot(path=screenshot_path)
                    print(f"Screenshot saved to {screenshot_path}", flush=True)
                except Exception as se:
                    print(f"Failed to save screenshot: {se}", flush=True)
                raise Exception("403 Permission error")
            else:
                print(f"Failed to show columns after My Unit Tasks button click: {e}", flush=True)
                try:
                    from datetime import datetime
                    import os
                    os.makedirs("Errors", exist_ok=True)
                    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    screenshot_path = f"Errors/error_no_columns_attempt{attempt+1}_{ts}.png"
                    page.screenshot(path=screenshot_path)
                    print(f"Screenshot saved as {screenshot_path}", flush=True)
                except Exception:
                    pass
                backoff = 2 ** attempt
                print(f"Waiting {backoff} seconds before retrying...", flush=True)
                time.sleep(backoff)
                if attempt == max_retries - 1:
                    print("Max retries reached. Aborting login navigation.", flush=True)
                    raise Exception("Max retries reached for login navigation")
    print("Navigation to columns complete.", flush=True)

def upload_media(username, password, task_filter, file_path):
    print("[Playwright] Starting Playwright...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login(page, username, password)
        print(f"[Playwright] Filtering tasks with: {task_filter}", flush=True)
        page.fill('input[placeholder="بحث"]', task_filter)
        page.wait_for_timeout(2000)
        print(f"[Playwright] Waiting for upload button (xpath={UPLOAD_BUTTON_XPATH})...", flush=True)
        page.wait_for_selector(f'xpath={UPLOAD_BUTTON_XPATH}', timeout=10000)
        print("[Playwright] Clicking upload button...", flush=True)
        page.click(f'xpath={UPLOAD_BUTTON_XPATH}')
        file_input_selector = 'input[type="file"]'
        print(f"[Playwright] Waiting for file input ({file_input_selector})...", flush=True)
        page.wait_for_selector(file_input_selector, timeout=10000)
        print(f"[Playwright] Setting input files: {file_path}", flush=True)
        page.set_input_files(file_input_selector, file_path)
        print("[Playwright] Waiting for upload to finish...", flush=True)
        page.wait_for_timeout(3000)
        print(f"[Playwright] Uploaded {file_path} to task {task_filter}", flush=True)
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python upload.playwright.py <username> <password> <task_filter> <file_path>")
        sys.exit(1)
    username = sys.argv[1]
    password = sys.argv[2]
    task_filter = sys.argv[3]
    file_path = sys.argv[4]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)
    upload_media(username, password, task_filter, file_path)
