
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
    print("Navigating to login page...")
    page.goto(LOGIN_URL)
    page.wait_for_selector('input[name="username"]', timeout=60000)
    page.fill('input[name="username"]', username)
    print("Filling username...")
    page.fill('input[name="password"]', password)
    print("Filling password...")
    page.click('button[type="submit"]')
    print("Clicking sign in...")
    page.wait_for_timeout(3000)
    # Wait for OTP/password page if present
    try:
        page.wait_for_selector('input[type="password"]', timeout=10000)
        print("Waiting for OTP/password page...")
        page.fill('input[type="password"]', password)
        print("Filling OTP/password again...")
        page.click('button[type="submit"]')
        print("Clicking confirm...")
        page.wait_for_timeout(3000)
    except Exception:
        print("No OTP/password page detected.")
    # Wait for board page to load
    page.wait_for_selector('.board-col', timeout=120000)
    print("Logged in and board loaded.")

def add_technician(task_uuid, worker_name, username, password):
    url = f"https://msp.go2field.iq/task/{task_uuid}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login(page, username, password)
        print(f"Navigating to task page: {url}")
        page.goto(url)
        page.wait_for_selector('#edit-button', timeout=120000)
        page.click('#edit-button')
        page.wait_for_timeout(2000)
        # Wait for worker input and enter worker name
        worker_input_xpath = '//*[@id="app_container"]/app-main-layout/div/div[2]/app-task-view/div/div[3]/div/div[2]/tabset/div/tab[1]/div/div[1]/app-task-progress-team/div/app-team-edit/div/div[2]/div/div[2]/div/div/div[1]//input'
        page.wait_for_selector(worker_input_xpath, timeout=20000)
        page.fill(worker_input_xpath, worker_name)
        page.wait_for_timeout(3000)
        # Select worker checkbox
        checkbox_xpath = '//*[@id="app_container"]/app-main-layout/div/div[2]/app-task-view/div/div[3]/div/div[2]/tabset/div/tab[1]/div/div[1]/app-task-progress-team/div/app-team-edit/div/div[2]/div/div[3]/div/div/div/div[1]/table/tbody/tr/td[1]/app-checkbox/div/input'
        page.wait_for_selector(checkbox_xpath, timeout=20000)
        page.check(checkbox_xpath)
        # Click save button
        save_btn_xpath = '//*[@id="app_container"]/app-main-layout/div/div[2]/app-task-view/div/div[3]/div/div[2]/tabset/div/tab[1]/div/div[1]/app-task-progress-team/div/app-team-edit/div/div[2]/div/div[3]/div/div/div/div[2]/div/div/div[1]/div/div[1]/button'
        page.wait_for_selector(save_btn_xpath, timeout=20000)
        page.click(save_btn_xpath)
        print(f"Worker '{worker_name}' added to task {task_uuid} and saved.")
        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python add_technician.py <task_uuid> <worker_name> <username> <password>")
        print("Available workers:", WORKERS)
        sys.exit(1)
    task_uuid = sys.argv[1]
    worker_name = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]
    add_technician(task_uuid, worker_name, username, password)
