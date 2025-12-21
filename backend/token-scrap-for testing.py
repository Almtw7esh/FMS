
import sys
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

# Usage: python token-scrap.py <username> <password>


def get_token(username, password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
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
        # Navigate to board and wait for columns
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
        # Debug: print all sessionStorage keys and values
        print("--- sessionStorage contents after navigation ---")
        ss_dump = page.evaluate('''() => {
            let out = [];
            for (let k in window.sessionStorage) {
                out.push({key: k, value: String(window.sessionStorage[k])});
            }
            return out;
        }''')
        for entry in ss_dump:
            print(f"{entry['key']}: {entry['value'][:100]}{'...' if len(entry['value']) > 100 else ''}")
        print("--- end sessionStorage dump ---")
        # Debug: print all cookies
        print("--- cookies after navigation ---")
        cookies = page.context.cookies()
        for cookie in cookies:
            print(f"{cookie['name']}: {cookie['value'][:100]}{'...' if len(cookie['value']) > 100 else ''}")
        print("--- end cookies dump ---")
        # Debug: print all localStorage keys and values
        print("--- localStorage contents after navigation ---")
        ls_dump = page.evaluate('''() => {
            let out = [];
            for (let k in window.localStorage) {
                out.push({key: k, value: String(window.localStorage[k])});
            }
            return out;
        }''')
        for entry in ls_dump:
            print(f"{entry['key']}: {entry['value'][:100]}{'...' if len(entry['value']) > 100 else ''}")
        print("--- end localStorage dump ---")
        # Extract token from sessionStorage['formauthtoken'] if present
        token = None
        for entry in ss_dump:
            if entry['key'] == 'formauthtoken' and entry['value'].startswith('eyJ'):
                token = entry['value']
                print('Token found in sessionStorage["formauthtoken"]')
                break
        # Fallback: try __auth_token__ cookie
        if not token:
            for cookie in cookies:
                if cookie['name'] == '__auth_token__' and cookie['value'].startswith('eyJ'):
                    token = cookie['value']
                    print('Token found in __auth_token__ cookie')
                    break
        # Fallback: try KEYCLOAK_IDENTITY cookie
        if not token:
            for cookie in cookies:
                if cookie['name'] == 'KEYCLOAK_IDENTITY' and cookie['value'].startswith('eyJ'):
                    token = cookie['value']
                    print('Token found in KEYCLOAK_IDENTITY cookie')
                    break
        browser.close()
        return token


def main():
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
    else:
        # Try to read from users.json
        users_path = Path(__file__).parent / "users.json"
        if not users_path.exists():
            print("Usage: python token-scrap.py <username> <password> OR ensure users.json exists.")
            sys.exit(1)
        with open(users_path, "r") as f:
            users = json.load(f)
        if not users or 'username' not in users[0] or 'password' not in users[0]:
            print("users.json is missing username or password.")
            sys.exit(1)
        username = users[0]['username']
        password = users[0]['password']
        print(f"Using credentials from users.json: {username}")
    token = get_token(username, password)
    if token:
        token_data = {"token": token}
        token_path = Path(__file__).parent / "token.json"
        with open(token_path, "w") as f:
            json.dump(token_data, f)
        print(f"Token saved to {token_path}")
    else:
        print("Failed to retrieve token.")
        sys.exit(1)

if __name__ == "__main__":
    main()
