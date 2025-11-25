from playwright.async_api import async_playwright
import json
import asyncio


LOGIN_URL = "https://sso.earthlink.iq/auth/realms/elcld.ai/protocol/openid-connect/auth?response_type=code&client_id=fms-msp&redirect_uri=https%3A%2F%2Fmsp.go2field.iq%2Fboard%2Fmy-unit-tasks&scope=openid"

async def scrape(username, password):
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.clear_cookies()
        page = await context.new_page()
        # Mimic real browser headers and settings
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })
        await page.set_viewport_size({"width": 1280, "height": 800})
        print("Navigating to login page...")
        await page.goto(LOGIN_URL)
        print("Filling username...")
        await page.fill('//*[@id="username"]', username)
        print("Filling password...")
        await page.fill('//*[@id="password"]', password)
        print("Clicking sign in...")
        await page.click('//*[@id="kc-form-buttons"]')
        print("Waiting for OTP/password page...")
        await page.wait_for_url("**/login-actions/authenticate?*", timeout=30000)
        print("Filling OTP/password again...")
        await page.fill('//*[@id="pi_otp"]', password)
        print("Clicking confirm...")
        await page.click('//*[@id="kc-login"]')
        print("Waiting for page to load after confirm...")
        # Wait longer after login confirm to ensure page loads
        await asyncio.sleep(5)
        print("Navigating directly to Halasat board...")
        await page.goto("https://msp.go2field.iq/board/a22c39cb-093c-d83e-7dd1-a8c7a5d0fa7b", wait_until="domcontentloaded", timeout=90000)
        # Wait for document to be fully loaded after navigation
        await asyncio.sleep(2)
        print("Waiting for Halasat button in sidebar...")
        try:
            halasat_button = await page.wait_for_selector('xpath=/html/body/app-root/div/app-main-layout/div/div[2]/app-board-view/div/div[1]/div[4]/div[3]/a[4]', timeout=15000)
            print("Halasat button found. Clicking...")
            async with page.expect_navigation(timeout=20000):
                await halasat_button.click()
            print("Halasat button clicked. Waiting for columns to appear...")
            await page.wait_for_selector('.board-col', timeout=15000)
            print("Columns appeared. Waiting for content to load...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Failed to show columns after Halasat button click: {e}")
            try:
                await page.screenshot(path="Errors/error_no_columns.png")
                print("Screenshot saved as Errors/error_no_columns.png")
            except:
                pass
            await browser.close()
            return []
        print("Scraping columns...")
        try:
            csv_data = []
            card_refs = []
            columns = await page.query_selector_all('.board-col')
            for col in columns:
                col_title_el = await col.query_selector('.board-col-title h5')
                col_title = await col_title_el.inner_text() if col_title_el else ""
                if col_title not in ["New", "Pending", "In Progress"]:
                    continue
                card_els = await col.query_selector_all('board-task-box')
                for card_el in card_els:
                    case_number_el = await card_el.query_selector('.task-code')
                    case_number = await case_number_el.inner_text() if case_number_el else ""
                    title_el = await card_el.query_selector('.task-name a')
                    card_title = await title_el.inner_text() if title_el else ""
                    fbg_el = await card_el.query_selector('.task-info[title^="FBG"]')
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
                    title_link = await card_el.query_selector('.task-name a')
                    if title_link:
                        href = await title_link.get_attribute('href')
                        if href and '/task/' in href:
                            uuid = href.split('/task/')[-1]
                    # Store card info and element reference for later message scraping
                    csv_data.append({
                        "Column": col_title,
                        "CaseNumber": case_number,
                        "Title": card_title,
                        "FBG": fbg_number,
                        "CardText": card_text,
                        "uuid": uuid,
                        "messages": []
                    })
                    card_refs.append(card_el)
            print("Column and card info scraped. Now scraping messages...")
            # Scrape messages for each card after all columns are scraped
            for i, card_el in enumerate(card_refs):
                uuid = csv_data[i]["uuid"]
                messages = []
                try:
                    print(f"Clicking card {uuid} to view details...")
                    async with page.expect_navigation(timeout=30000):
                        await card_el.click()
                    await asyncio.sleep(3)
                    await page.wait_for_selector('xpath=//*[@id=\"app_container\"]/app-main-layout/div/div[2]/app-task-view/div/div[3]/div/app-permission/div/app-task-notes/div/div[2]/app-task-event/div/div/div[2]', timeout=30000)
                    message_elements = await page.query_selector_all('xpath=//*[@id=\"app_container\"]/app-main-layout/div/div[2]/app-task-view/div/div[3]/div/app-permission/div/app-task-notes/div/div[2]/app-task-event/div/div/div[2]')
                    print(f"Found {len(message_elements)} notes/messages for card {uuid}")
                    for el in message_elements:
                        try:
                            msg_text = await el.inner_text()
                            messages.append({"message": msg_text})
                        except Exception as e:
                            print(f"Error reading message text: {e}")
                    if not messages:
                        await page.screenshot(path=f"Errors/error_no_messages_{uuid}.png")
                        print(f"No messages found for card {uuid}, screenshot saved.")
                except Exception as e:
                    print(f"Error scraping messages for card {uuid}: {e}")
                    try:
                        await page.screenshot(path=f"Errors/error_scraping_messages_{uuid}.png")
                        print(f"Screenshot saved for message error on card {uuid}.")
                    except:
                        pass
                finally:
                    # Always go back to board for next card, even if message scraping fails
                    await page.goto("https://msp.go2field.iq/board/a22c39cb-093c-d83e-7dd1-a8c7a5d0fa7b", timeout=120000)
                    await page.wait_for_selector('.board-col', timeout=120000)
                csv_data[i]["messages"] = messages
            print("Scraping complete.")
            # Save to CSV with datetime name
            import csv
            import os
            from datetime import datetime
            folder = "scraped_results"
            os.makedirs(folder, exist_ok=True)
            dt_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            csv_path = os.path.join(folder, f"scraped_{dt_str}.csv")
            with open(csv_path, "w", newline='', encoding='utf-8') as f:
                fieldnames = ["Column", "CaseNumber", "Title", "FBG", "CardText", "uuid", "messages"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in csv_data:
                    # Save messages as JSON string
                    row = row.copy()
                    row["messages"] = json.dumps(row["messages"], ensure_ascii=False)
                    writer.writerow(row)
            print(f"Saved scraped data to {csv_path}")
            await browser.close()
            return csv_data
        except Exception as e:
            print(f"Error scraping columns: {e}")
            await page.screenshot(path="Errors/error_scraping_columns.png")
            print("Screenshot saved as Errors/error_scraping_columns.png")
            await browser.close()
            return []

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        username = sys.argv[1]
        password = sys.argv[2]
        asyncio.run(scrape(username, password))
    else:
        print("Usage: python scraper.py <username> <password>")
