import os
import time
import uuid
import json
import string
import random
import urllib.request
import pydub
import speech_recognition as sr
from playwright.sync_api import sync_playwright

# -------------------------------------------------------------
# Helper: Generate Real Temp Email via mail.tm
# -------------------------------------------------------------
def create_real_temp_email():
    print("      [mail.tm] Querying active domain...")
    req = urllib.request.Request("https://api.mail.tm/domains", headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        domains_data = json.loads(response.read().decode('utf-8'))
    
    active_domain = domains_data['hydra:member'][0]['domain']
    unique_user = f"user_{uuid.uuid4().hex[:8]}"
    email_address = f"{unique_user}@{active_domain}"

    payload = json.dumps({"address": email_address, "password": "TempMailPassword123!"}).encode('utf-8')
    post_req = urllib.request.Request(
        "https://api.mail.tm/accounts",
        data=payload,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(post_req) as response:
        print(f"      [mail.tm] Account created: {email_address}")
        return email_address

def generate_strong_password(length=16):
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*()_+-="
    password = [
        random.choice(lowercase), random.choice(uppercase),
        random.choice(digits), random.choice(symbols)
    ]
    all_chars = lowercase + uppercase + digits + symbols
    password += [random.choice(all_chars) for _ in range(length - 4)]
    random.shuffle(password)
    return "".join(password)

# -------------------------------------------------------------
# Helper: Resilient Click Handler (Bypasses Viewport Offscreen Issues)
# -------------------------------------------------------------
def safe_click(locator):
    """Tries normal click, then forced click, and finally DOM JS click."""
    try:
        locator.scroll_into_view_if_needed(timeout=3000)
        locator.click(timeout=3000)
    except Exception:
        try:
            locator.click(force=True, timeout=3000)
        except Exception:
            locator.evaluate("el => el.click()")

# -------------------------------------------------------------
# Free Audio CAPTCHA Solver
# -------------------------------------------------------------
def solve_audio_recaptcha(page):
    """Detects reCAPTCHA iframe, clicks Audio button, transcribes speech, and submits."""
    print("[CAPTCHA] Checking for reCAPTCHA challenge...")
    try:
        recaptcha_iframe = page.frame_locator('iframe[title*="recaptcha challenge"], iframe[src*="recaptcha"]')
        audio_btn = recaptcha_iframe.locator('#recaptcha-audio-button')
        
        if audio_btn.is_visible(timeout=5000):
            print("      Audio challenge button found. Clicking...")
            audio_btn.click(force=True)
            time.sleep(2)

            audio_source = recaptcha_iframe.locator('#audio-source')
            src_url = audio_source.get_attribute('src')

            if src_url:
                print("      Downloading audio MP3 file...")
                urllib.request.urlretrieve(src_url, "captcha.mp3")

                sound = pydub.AudioSegment.from_mp3("captcha.mp3")
                sound.export("captcha.wav", format="wav")

                recognizer = sr.Recognizer()
                with sr.AudioFile("captcha.wav") as source:
                    audio_data = recognizer.record(source)
                    text_result = recognizer.recognize_google(audio_data)

                print(f"      Transcribed Audio Code: '{text_result}'")

                audio_response_input = recaptcha_iframe.locator('#audio-response')
                audio_response_input.fill(text_result)
                time.sleep(1)

                verify_btn = recaptcha_iframe.locator('#recaptcha-verify-button')
                verify_btn.click(force=True)
                time.sleep(3)
                print("      Audio CAPTCHA submitted.")
                return True
    except Exception as e:
        print(f"      Audio CAPTCHA note: {e}")
    return False

# -------------------------------------------------------------
# Main Execution Workflow
# -------------------------------------------------------------
def run():
    with sync_playwright() as p:
        print("[1/7] Launching Playwright Chromium Browser...")
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        try:
            # Step 1: Navigate to main referral link
            print("[2/7] Navigating to EuroDNS registration page...")
            page.goto("https://eurodns.pxf.io/PzkDy6", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

            # Step 2: Accept Cookies
            print("[3/7] Accepting cookies...")
            try:
                cookie_btn = page.locator('#cookiescript_accept, //*[@id="cookiescript_accept"]').first
                safe_click(cookie_btn)
                print("      Cookies accepted.")
            except Exception as e:
                print(f"      Cookie note: {e}")
            time.sleep(2)

            # Step 3: Open Account menu & click 'New Account'
            print("[4/7] Opening Account menu & clicking 'New Account'...")
            account_btn = page.locator('#account-item-logout, //*[@id="account-item-logout"]').first
            safe_click(account_btn)
            time.sleep(2)

            new_acc_btn = page.locator('#logout-user-section a:nth-child(2), //*[@id="logout-user-section"]/a[2], a[href*="createNewAccount"]').first
            safe_click(new_acc_btn)
            time.sleep(4)

            # Step 4: Fill Credentials
            print("[5/7] Generating real temp email & password...")
            real_email = create_real_temp_email()
            eurodns_pass = generate_strong_password(16)

            print(f"\n==================================================")
            print(f"  REGISTERING WITH:")
            print(f"  EMAIL:    {real_email}")
            print(f"  PASSWORD: {eurodns_pass}")
            print(f"==================================================\n")

            email_field = page.locator("input[type='email'], input[formcontrolname='email'], input[name='email']").first
            email_field.wait_for(state="attached", timeout=15000)
            email_field.fill(real_email)
            time.sleep(1)

            pass_field = page.locator("input[type='password'], input[formcontrolname='password']").first
            pass_field.fill(eurodns_pass)
            time.sleep(1)

            # Newsletter Checkbox
            try:
                chk = page.locator('#subscribe-newsletter-checkbox-input, //*[@id="subscribe-newsletter-checkbox-input"]').first
                safe_click(chk)
            except Exception:
                pass

            page.screenshot(path="screenshot_form_filled.png")

            # Step 5: Click 'Create Account'
            print("[6/7] Clicking 'Create Account' button...")
            create_account_xpath = "/html/body/edns-root/edns-layout/div/div/edns-side-panels/mat-sidenav-container/mat-sidenav-content/div/div[2]/edns-new-account/div/div/form/div[4]/button"
            create_btn = page.locator(f"xpath={create_account_xpath}, edns-new-account button[type='submit'], form button:has-text('Create account')").first
            safe_click(create_btn)
            time.sleep(4)

            # Step 6: Solve CAPTCHA if presented
            solve_audio_recaptcha(page)

            # Secondary submit click post-solve
            try:
                safe_click(create_btn)
            except Exception:
                pass

            time.sleep(10)
            page.screenshot(path="screenshot_after_registration.png")

            # Step 7: Navigating to login page to test registration
            print("[7/7] Navigating to login page to verify credentials...")
            page.goto("https://my.eurodns.com/login", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

            try:
                login_email = page.locator("input[type='email'], input[name='email']").first
                login_email.wait_for(state="attached", timeout=10000)
                login_email.fill(real_email)

                login_pass = page.locator("input[type='password'], input[name='password']").first
                login_pass.fill(eurodns_pass)

                login_btn = page.locator("button[type='submit']").first
                safe_click(login_btn)
                time.sleep(10)
            except Exception as e:
                print(f"      Login verification note: {e}")

            current_url = page.url
            print(f"      Landed URL: {current_url}")
            page.screenshot(path="screenshot.png")

            print("\n==================================================")
            print("Workflow Completed!")
            print(f"Landed URL: {current_url}")
            print(f"Credentials -> Email: {real_email} | Password: {eurodns_pass}")
            print("==================================================\n")

        except Exception as e:
            print(f"\n[X] Error during execution: {e}")
            page.screenshot(path="screenshot.png")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    run()
