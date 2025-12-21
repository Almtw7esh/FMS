import sys
import time
from playwright.sync_api import sync_playwright
try:
    from flask import Flask, jsonify
    import platform

    def get_platform_encoding():
        return 'utf-8-sig' if platform.system() == 'Windows' else 'utf-8'

    app = Flask(__name__)
except ImportError:
    app = None

def login(page, username, password):
    LOGIN_URL = "https://sso.earthlink.iq/auth/realms/elcld.ai/protocol/openid-connect/auth?response_type=code&client_id=fms-msp&redirect_uri=https%3A%2F%2Fmsp.go2field.iq%2Fboard%2Fmy-unit-tasks&scope=openid"
    print("Navigating to login page...", flush=True)
    page.goto(LOGIN_URL)
    print("Filling username...", flush=True)
    page.fill('//*[@id="username"]', username)
    print("Filling password...", flush=True)
    page.fill('//*[@id="password"]', password)
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
            page.wait_for_timeout(6000)  # Increased delay to ensure all content is loaded
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
                print(f"Failed to show columns after Halasat button click: {e}", flush=True)
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

def add_technician(task_uuid, worker_name, username, password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login(page, username, password)
        found = False
        for col_name in ["NEW", "Pending", "In Progress"]:
            col_xpath = f'xpath=//*[@id="board-col-{col_name}"]'
            try:
                page.wait_for_selector(col_xpath, timeout=15000)
                col = page.query_selector(col_xpath)
                card_boxes = col.query_selector_all('board-task-box') if col else []
                for card_el in card_boxes:
                    view_tab_link = card_el.query_selector('a[tooltip="View task in new tab"][target="_blank"]')
                    card_url = None
                    if view_tab_link:
                        href = view_tab_link.get_attribute('href')
                        if href and task_uuid in href:
                            card_url = href
                    if not card_url:
                        continue
                    # Only process the matching task
                    edit_btn = card_el.query_selector('a[tooltip="Open task progress"]')
                    if not edit_btn:
                        continue
                    edit_btn.click()
                    page.wait_for_timeout(1500)
                    try:
                        page.wait_for_selector('.modal-content app-modal-task-progress', timeout=10000)
                    except Exception:
                        continue
                    try:
                        page.wait_for_selector('i-feather#edit-button[name="edit-2"]', timeout=10000)
                        page.click('i-feather#edit-button[name="edit-2"]')
                    except Exception:
                        continue
                    try:
                        page.wait_for_selector('app-team-edit input[placeholder="Search worker"]', timeout=10000)
                    except Exception:
                        continue
                    try:
                        page.fill('app-team-edit input[placeholder="Search worker"]', worker_name)
                        page.wait_for_timeout(1200)
                    except Exception:
                        continue
                    try:
                        worker_row = None
                        rows = page.query_selector_all('app-team-edit table tbody tr')
                        for row in rows:
                            row_text = row.inner_text() if row else ""
                            if worker_name.lower() in row_text.lower():
                                worker_row = row
                                break
                        if not worker_row:
                            continue
                    except Exception:
                        continue
                    # Use exact XPath for checkbox
                    try:
                        checkbox_xpath = '/html/body/modal-container/div[2]/div/app-modal-task-progress/div/div[2]/div/div/div/div[1]/app-task-progress-team/div/app-team-edit/div/div[2]/div/div[3]/div/div/div/div[1]/table/tbody/tr[1]/td[1]/app-checkbox/div/input'
                        checkbox = page.query_selector(f'xpath={checkbox_xpath}')
                        if not checkbox:
                            print('[DEBUG] Checkbox not found by exact XPath.', flush=True)
                            continue
                        print(f"[DEBUG] Checkbox is_checked: {checkbox.is_checked()}", flush=True)
                        print(f"[DEBUG] Checkbox is_enabled: {checkbox.is_enabled()}", flush=True)
                        print(f"[DEBUG] Checkbox is_visible: {checkbox.is_visible()}", flush=True)
                        page.evaluate('(el) => el.scrollIntoView()', checkbox)
                        if not checkbox.is_checked():
                            try:
                                checkbox.click()
                                print('[DEBUG] Checkbox clicked normally.', flush=True)
                            except Exception as e:
                                print(f'[DEBUG] Normal click failed: {e}', flush=True)
                                try:
                                    checkbox.click(force=True)
                                    print('[DEBUG] Checkbox clicked with force=True.', flush=True)
                                except Exception as e2:
                                    print(f'[DEBUG] Force click failed: {e2}', flush=True)
                        if not checkbox.is_checked():
                            print('[DEBUG] Checkbox still not checked after click attempts.', flush=True)
                            continue
                    except Exception as e:
                        print(f'[DEBUG] Exception in checkbox logic: {e}', flush=True)
                        continue
                    try:
                        save_btn_xpath = '/html/body/modal-container/div[2]/div/app-modal-task-progress/div/div[2]/div/div/div/div[1]/app-task-progress-team/div/app-team-edit/div/div[2]/div/div[3]/div/div/div/div[2]/div/div/div[1]/div/div[1]/button'
                        save_btn = page.query_selector(f'xpath={save_btn_xpath}')
                        if not save_btn:
                            print('[DEBUG] Save button not found by exact XPath.', flush=True)
                            continue
                        save_btn_html = save_btn.inner_html() if save_btn else "(none)"
                        save_btn_text = save_btn.inner_text() if save_btn else "(none)"
                        print(f"[DEBUG] Save button HTML: {save_btn_html}", flush=True)
                        print(f"[DEBUG] Save button text: {save_btn_text}", flush=True)
                        print(f"[DEBUG] Save button is_enabled: {save_btn.is_enabled() if save_btn else 'N/A'}", flush=True)
                        print(f"[DEBUG] Save button is_visible: {save_btn.is_visible() if save_btn else 'N/A'}", flush=True)
                        # Scroll Save button into view again after checkbox click and possible UI movement
                        page.wait_for_timeout(500)  # Wait for UI to settle after checkbox click
                        page.evaluate('(el) => el.scrollIntoView()', save_btn)
                        for i in range(10):
                            enabled = save_btn.is_enabled() if save_btn else False
                            visible = save_btn.is_visible() if save_btn else False
                            print(f'[DEBUG] Save button state check {i}: enabled={enabled}, visible={visible}', flush=True)
                            if enabled and visible:
                                break
                            page.wait_for_timeout(200)
                        print('[DEBUG] Attempting to click Save button...', flush=True)
                        try:
                            save_btn.click()
                            print('[DEBUG] Save button clicked normally.', flush=True)
                            from datetime import datetime
                            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                            screenshot_path = f"Errors/save_btn_clicked_{ts}.png"
                            page.screenshot(path=screenshot_path)
                            print(f"[DEBUG] Screenshot after normal click saved: {screenshot_path}", flush=True)
                        except Exception as e:
                            print(f'[DEBUG] Normal click failed: {e}', flush=True)
                            try:
                                save_btn.click(force=True)
                                print('[DEBUG] Save button clicked with force=True.', flush=True)
                                from datetime import datetime
                                ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                                screenshot_path = f"Errors/save_btn_force_clicked_{ts}.png"
                                page.screenshot(path=screenshot_path)
                                print(f"[DEBUG] Screenshot after force click saved: {screenshot_path}", flush=True)
                            except Exception as e2:
                                print(f'[DEBUG] Force click failed: {e2}', flush=True)
                                try:
                                    page.evaluate('(el) => el.click()', save_btn)
                                    print('[DEBUG] Save button clicked via JS evaluate.', flush=True)
                                    from datetime import datetime
                                    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                                    screenshot_path = f"Errors/save_btn_js_clicked_{ts}.png"
                                    page.screenshot(path=screenshot_path)
                                    print(f"[DEBUG] Screenshot after JS click saved: {screenshot_path}", flush=True)
                                except Exception as e3:
                                    print(f'[DEBUG] JS evaluate click failed: {e3}', flush=True)
                    except Exception as e:
                        print(f'[DEBUG] Exception in Save button logic: {e}', flush=True)
                        continue
                    try:
                        close_btn = page.query_selector('.modal-content app-modal-task-progress .close')
                        if close_btn:
                            close_btn.click()
                    except Exception:
                        pass
                    found = True
                    break  # Stop after first successful assignment
                if found:
                    break
            except Exception:
                continue

if __name__ == "__main__":
    # If run as a script with arguments, run add_technician logic
    if len(sys.argv) >= 5:
        task_uuid = sys.argv[1]
        worker_name = sys.argv[2]
        username = sys.argv[3]
        password = sys.argv[4]
        add_technician(task_uuid, worker_name, username, password)
    # If run as a server, run Flask app
    elif app:
        app.run(host="0.0.0.0", port=5000)
    else:
        print("Usage: add_technician.py <task_uuid> <worker_name> <username> <password>", flush=True)
import sys
import time
from playwright.sync_api import sync_playwright

WORKERS = [
    "Amir Laith Samir", "Laith Samir", "Muhammad Jasim", "Muhammad Jasim Muhammad",
    "Khaldoun Adel Mohalhal Zaji", "Adel Mohalhal Zaji", "aysar zaid abbas", "zaid abbas",
    "muhammad baqir hussein", "baqir hussein", "yousif muyad majeed", "muyad majeed",
    "sadiq faaiq Jassim", "faaiq Jassim", "Hussein Nizar Hameed", "Nizar Hameed",
    "Amir Mahdi Muhammad", "Mahdi Muhammad", "Ali Salman Ibrahim", "Salman Ibrahim",
    "Ali Abdul Hussein Abdul Wahid", "Abdul Hussein Abdul Wahid", "Muhammad Omar Hasan", "Omar Hasan"
]

def login(page, username, password):
    LOGIN_URL = "https://sso.earthlink.iq/auth/realms/elcld.ai/protocol/openid-connect/auth?response_type=code&client_id=fms-msp&redirect_uri=https%3A%2F%2Fmsp.go2field.iq%2Fboard%2Fmy-unit-tasks&scope=openid"
    print("Navigating to login page...", flush=True)
    page.goto(LOGIN_URL)
    print("Filling username...", flush=True)
    page.fill('//*[@id="username"]', username)
    print("Filling password...", flush=True)
    page.fill('//*[@id="password"]', password)
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
            print("Waiting for Halasat button in sidebar...", flush=True)
            halasat_button = page.wait_for_selector('xpath=/html/body/app-root/div/app-main-layout/div/div[2]/app-board-view/div/div[1]/div[4]/div[3]/a[4]', timeout=15000)
            print("Halasat button found. Clicking...", flush=True)
            halasat_button.click()
            print("Halasat button clicked. Waiting for columns to appear...", flush=True)
            page.wait_for_selector('.board-col', timeout=15000)
            print("Columns appeared. Waiting for content to load...", flush=True)
            page.wait_for_timeout(3000)
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
                print(f"Failed to show columns after Halasat button click: {e}", flush=True)
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

def add_technician(task_uuid, worker_name, username, password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login(page, username, password)
        found = False
        for col_name in ["NEW", "Pending", "In Progress"]:
            print(f"Processing tasks in {col_name} column...", flush=True)
            col_xpath = f'xpath=//*[@id="board-col-{col_name}"]'
            try:
                page.wait_for_selector(col_xpath, timeout=15000)
                col = page.query_selector(col_xpath)
                card_boxes = col.query_selector_all('board-task-box') if col else []
                print(f"Found {len(card_boxes)} tasks in {col_name} column.", flush=True)
                for card_el in card_boxes:
                    try:
                        card_html = card_el.inner_html() if card_el else None
                        print(f"Card HTML for debugging:\n{card_html}\n---", flush=True)
                        view_tab_link = card_el.query_selector('a[tooltip="View task in new tab"][target="_blank"]')
                        card_url = None
                        if view_tab_link:
                            href = view_tab_link.get_attribute('href')
                            print(f"Extracted href for card: {href}", flush=True)
                            if href and task_uuid in href:
                                card_url = href
                        if not card_url:
                            print(f"Card does not match task_uuid {task_uuid}, skipping.", flush=True)
                            continue
                        print(f"Found card matching task_uuid {task_uuid} in {col_name} column. Proceeding with assignment.", flush=True)
                        # ...existing assignment logic here...
                        # Only click Task Progress button, etc.
                        # ...existing code...
                        # (rest of the assignment logic remains unchanged)
                    except Exception as e:
                        print(f"Error processing a task in {col_name} column: {e}", flush=True)
                        continue
                if found:
                    break
            except Exception as e:
                print(f"Error finding column {col_name}: {e}", flush=True)