import platform

def get_platform_encoding():
    return 'utf-8-sig' if platform.system() == 'Windows' else 'utf-8'
import os
import sys
import time
from playwright.async_api import async_playwright
import json
import asyncio

LOGIN_URL = "https://sso.earthlink.iq/auth/realms/elcld.ai/protocol/openid-connect/auth?response_type=code&client_id=fms-msp&redirect_uri=https%3A%2F%2Fmsp.go2field.iq%2Fboard%2Fmy-unit-tasks&scope=openid"

class ScraperSessionManager:
    def __init__(self):
        self.sessions = {}

    async def scrape_with_session(self, username, password):
        print("\n--- Scraper run started ---", flush=True)
        try:
            print("Starting Playwright...", flush=True)
            async with async_playwright() as p:
                print(f"Creating new session for user: {username}", flush=True)
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                await context.clear_cookies()
                page = await context.new_page()
                await page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9"
                })
                await page.set_viewport_size({"width": 1280, "height": 800})
                print("Navigating to login page...", flush=True)
                await page.goto(LOGIN_URL)
                print("Filling username...", flush=True)
                await page.fill('//*[@id="username"]', username)
                print("Filling password...", flush=True)
                await page.fill('//*[@id="password"]', password)
                print("Clicking sign in...", flush=True)
                await page.click('//*[@id="kc-form-buttons"]')
                print("Waiting for OTP/password page...", flush=True)
                await page.wait_for_url("**/login-actions/authenticate?*", timeout=30000)
                print("Filling OTP/password again...", flush=True)
                await page.fill('//*[@id="pi_otp"]', password)
                print("Clicking confirm...", flush=True)
                await page.click('//*[@id="kc-login"]')
                print("Waiting for page to load after confirm...", flush=True)
                await asyncio.sleep(5)
                print("Login and initial navigation complete.", flush=True)

                max_retries = 4
                for attempt in range(max_retries):
                    try:
                        await page.goto("https://msp.go2field.iq/board/a22c39cb-093c-d83e-7dd1-a8c7a5d0fa7b", wait_until="domcontentloaded", timeout=90000)
                        await asyncio.sleep(2)
                        print("Waiting for My Unit Tasks button in sidebar...", flush=True)
                        my_unit_tasks_button = await page.wait_for_selector('xpath=//*[@id="app_container"]/app-main-layout/div/div[2]/app-board-view/div/div[1]/div[4]/div[3]/a[2]', timeout=15000)
                        print("My Unit Tasks button found. Clicking...", flush=True)
                        async with page.expect_navigation(timeout=20000):
                            await my_unit_tasks_button.click()
                        print("My Unit Tasks button clicked. Waiting for columns to appear...", flush=True)
                        await page.wait_for_selector('.board-col', timeout=15000)
                        print("Columns appeared. Waiting for content to load...", flush=True)
                        await asyncio.sleep(7)
                        break
                    except Exception as e:
                        try:
                            content = await page.content()
                        except Exception:
                            content = ""
                        if "403" in content or "permission" in content.lower():
                            print(f"403 Permission error detected on attempt {attempt+1}. Retrying after backoff...", flush=True)
                            return []
                        else:
                            print(f"Failed to show columns after Halasat button click: {e}", flush=True)
                        try:
                            await page.screenshot(path=f"Errors/error_no_columns_attempt{attempt+1}.png")
                            print(f"Screenshot saved as Errors/error_no_columns_attempt{attempt+1}.png", flush=True)
                        except:
                            pass
                        backoff = 2 ** attempt
                        print(f"Waiting {backoff} seconds before retrying...", flush=True)
                        await asyncio.sleep(backoff)
                        if attempt == max_retries - 1:
                            print("Max retries reached. Aborting scrape.", flush=True)
                            return []
                print("Scraping columns...", flush=True)
                csv_data = []
                try:
                    await page.wait_for_selector('.board-col', timeout=120000)
                    columns = await page.query_selector_all('.board-col')
                    detected_titles = []
                    for c in columns:
                        col_title_el = await c.query_selector('.board-col-title h5')
                        title = await col_title_el.inner_text() if col_title_el else ""
                        detected_titles.append(title)
                    print(f"Detected column titles: {detected_titles}", flush=True)

                    for col_title in ["New", "Pending", "In Progress"]:
                        print(f"Processing column: {col_title}", flush=True)
                        col = None
                        for c in columns:
                            col_title_el = await c.query_selector('.board-col-title h5')
                            title = await col_title_el.inner_text() if col_title_el else ""
                            if title == col_title:
                                col = c
                                break
                        if not col:
                            print(f"Column {col_title} not found.")
                            continue
                        card_els = await col.query_selector_all('board-task-box')
                        print(f"Found {len(card_els)} cards in column {col_title}", flush=True)
                        for idx, card_el in enumerate(card_els):
                            print(f"--- Processing card {idx+1}/{len(card_els)} in column '{col_title}' ---", flush=True)
                            card_html = await card_el.inner_html()
                            print(f"Card HTML for debugging:\n{card_html}\n---", flush=True)
                            case_number_el = await card_el.query_selector('.task-code')
                            case_number = await case_number_el.inner_text() if case_number_el else ""
                            title_el = await card_el.query_selector('.task-name a')
                            card_title = await title_el.inner_text() if title_el else ""
                            fbg_el = await card_el.query_selector('.task-info[title^=\"FBG\"]')
                            fbg_number = await fbg_el.inner_text() if fbg_el else ""
                            if not fbg_number:
                                infos = await card_el.query_selector_all('.task-info')
                                if len(infos) >= 1:
                                    for info in infos:
                                        txt = await info.inner_text()
                                        if txt.strip().startswith("FBG"):
                                            fbg_number = txt.strip()
                                            break
                            card_text = await card_el.inner_text()
                            uuid = None
                            view_tab_link = await card_el.query_selector('.action-buttons a[tooltip=\"View task in new tab\"][target=\"_blank\"]')
                            card_url = None
                            if view_tab_link:
                                href = await view_tab_link.get_attribute('href')
                                print(f"Extracted href for card {case_number}: {href}", flush=True)
                                if href and '/task/' in href:
                                    uuid = href.split('/task/')[-1]
                                    card_url = f"https://msp.go2field.iq/task/{uuid}"
                            meta = {
                                "Column": col_title,
                                "CaseNumber": case_number,
                                "Title": card_title,
                                "FBG": fbg_number,
                                "CardText": card_text,
                                "uuid": uuid
                            }
                            messages = []
                            try:
                                notes_btn_xpath = 'xpath=.//div[contains(@class,\"action-buttons\")]/a[@tooltip=\"Notes\"]'
                                msg_btn = await card_el.query_selector(notes_btn_xpath)
                                if not msg_btn:
                                    action_btns = await card_el.query_selector_all('div.action-buttons a')
                                    if len(action_btns) >= 2:
                                        msg_btn = action_btns[1]
                                if msg_btn:
                                    try:
                                        modal_open = await page.query_selector('.notes-modal-messages-container')
                                        if modal_open:
                                            print(f"Previous notes modal detected, closing before next click.", flush=True)
                                            close_btn = await page.query_selector('.notes-modal-header .close-icon, xpath=/html/body/modal-container/div[2]/div/app-modal-notes/div[1]/button')
                                            if close_btn:
                                                await close_btn.click()
                                                await asyncio.sleep(0.5)
                                                await page.wait_for_selector('.notes-modal-messages-container', state='detached', timeout=5000)
                                    except Exception as e:
                                        print(f"Error closing previous notes modal: {e}", flush=True)
                                    print(f"Clicking Notes button for card {case_number}", flush=True)
                                    await msg_btn.click()
                                    await asyncio.sleep(1)
                                    try:
                                        await page.wait_for_selector('.notes-modal-messages-container', timeout=10000)
                                        msg_container = await page.query_selector('.notes-modal-messages-container')
                                        msg_elems = await msg_container.query_selector_all('.notes-modal-message') if msg_container else []
                                        print(f"Found {len(msg_elems)} messages in popup for card {case_number}", flush=True)
                                        for msg_el in msg_elems:
                                            content_el = await msg_el.query_selector('.message-content')
                                            text = await content_el.inner_text() if content_el else ""
                                            sender_el = await msg_el.query_selector('.message-sender, .highlight')
                                            sender = await sender_el.inner_text() if sender_el else ""
                                            time_el = await msg_el.query_selector('.message-time')
                                            time = await time_el.inner_text() if time_el else ""
                                            extra_text_el = await msg_el.query_selector('.message-text')
                                            extra_text = await extra_text_el.inner_text() if extra_text_el else ""
                                            full_message = f"{text} {extra_text}".strip()
                                            messages.append({
                                                "sender": sender,
                                                "message": full_message,
                                                "date": time
                                            })
                                        if len(msg_elems) == 0:
                                            popup_html = await msg_container.inner_html() if msg_container else ""
                                            print(f"Popup HTML for card {case_number}:\n{popup_html}\n---", flush=True)
                                    except Exception as e:
                                        print(f"Error waiting for message popup for card {case_number}: {e}", flush=True)
                                    try:
                                        close_btn = await page.query_selector('xpath=/html/body/modal-container/div[2]/div/app-modal-notes/div[1]/span/i-feather')
                                        if close_btn:
                                            await close_btn.click()
                                            await asyncio.sleep(0.5)
                                            print(f"Closed notes popup for card {case_number}", flush=True)
                                        else:
                                            print(f"Close button not found for message popup of card {case_number}", flush=True)
                                    except Exception as e:
                                        print(f"Error closing notes popup for card {case_number}: {e}", flush=True)
                                else:
                                    print(f"Notes button not found for card {case_number}", flush=True)
                            except Exception as e:
                                print(f"Error scraping messages for card {case_number}: {e}", flush=True)
                                try:
                                    await page.screenshot(path=f"Errors/error_scraping_messages_{uuid or 'unknown'}.png")
                                    print(f"Screenshot saved for message error on card {uuid or 'unknown'}.", flush=True)
                                except:
                                    pass
                            meta["messages"] = messages
                            csv_data.append(meta)

                    # Save CSV after scraping
                    import csv
                    from datetime import datetime
                    folder = "scraped_results"
                    os.makedirs(folder, exist_ok=True)
                    dt_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    csv_path = os.path.join(folder, f"scraped_{dt_str}.csv")
                    try:
                        with open(csv_path, "w", newline='', encoding=get_platform_encoding()) as f:
                            fieldnames = ["Column", "CaseNumber", "Title", "FBG", "CardText", "uuid", "messages"]
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            for row in csv_data:
                                row = row.copy()
                                row["messages"] = json.dumps(row["messages"], ensure_ascii=False)
                                writer.writerow(row)
                        print(f"Saved scraped data to {csv_path}", flush=True)
                    except Exception as file_err:
                        print(f"[ERROR] Failed to write CSV: {file_err}", flush=True)
                        import traceback
                        traceback.print_exc()
                except Exception as e:
                    print(f"Error scraping columns: {e}", flush=True)
                    try:
                        await page.screenshot(path="Errors/error_scraping_columns.png")
                        print("Screenshot saved as Errors/error_scraping_columns.png", flush=True)
                    except Exception:
                        pass

                # --- TOKEN EXTRACTION LOGIC (always runs after scrape) ---
                print("Extracting token for API use...", flush=True)
                ss_dump = await page.evaluate('''() => {
                    let out = [];
                    for (let k in window.sessionStorage) {
                        out.push({key: k, value: String(window.sessionStorage[k])});
                    }
                    return out;
                }''')
                token = None
                for entry in ss_dump:
                    if entry['key'] == 'formauthtoken' and entry['value'].startswith('eyJ'):
                        token = entry['value']
                        print('Token found in sessionStorage["formauthtoken"]', flush=True)
                        break
                if not token:
                    cookies = await context.cookies()
                    for cookie in cookies:
                        if cookie['name'] == '__auth_token__' and cookie['value'].startswith('eyJ'):
                            token = cookie['value']
                            print('Token found in __auth_token__ cookie', flush=True)
                            break
                if not token:
                    for cookie in cookies:
                        if cookie['name'] == 'KEYCLOAK_IDENTITY' and cookie['value'].startswith('eyJ'):
                            token = cookie['value']
                            print('Token found in KEYCLOAK_IDENTITY cookie', flush=True)
                            break
                if token:
                    token_data = {"token": token}
                    token_path = os.path.join(os.path.dirname(__file__), "token.json")
                    with open(token_path, "w") as f:
                        json.dump(token_data, f)
                    print(f"Token saved to {token_path}", flush=True)
                else:
                    print("Failed to retrieve token.", flush=True)

                try:
                    await browser.close()
                    print(f"Closed browser for {username} after scraping.", flush=True)
                except Exception as e:
                    print(f"Error closing browser for {username}: {e}", flush=True)
                return csv_data
        except Exception as e:
            print(f"Exception in scrape_with_session: {e}", flush=True)
            return []

scraper_manager = ScraperSessionManager()

async def scrape(username, password):
    return await scraper_manager.scrape_with_session(username, password)

if __name__ == "__main__":
    import asyncio
    username = os.environ.get("SCRAPER_USERNAME")
    password = os.environ.get("SCRAPER_PASSWORD")
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
    if not username or not password:
        print("Usage: python scraper.py <username> <password>", flush=True)
        sys.exit(1)
    print(f"Starting periodic scrape for user: {username}", flush=True)
    while True:
        try:
            print("--- Scraper run started ---", flush=True)
            asyncio.run(scrape(username, password))
        except Exception as e:
            print(f"Error in periodic scrape: {e}", flush=True)
        print("Waiting 120 seconds before next scrape...", flush=True)
        time.sleep(120)