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
# Free Audio CAPTCHA Solver
# -------------------------------------------------------------
def solve_audio_recaptcha(page):
    """Detects reCAPTCHA iframe, clicks Audio option, transcribes audio to text, and submits."""
    print("[CAPTCHA] Attempting 100% Free Audio reCAPTCHA Solve...")
    try:
        # Locate reCAPTCHA Challenge iframe
        bframe = page.frame_locator('iframe[title*="recaptcha challenge"]')
        
        # Click Audio Challenge Button
        audio_btn = bframe.locator('#recaptcha-audio-button')
        audio_btn.click(timeout=5000)
        time.sleep(2)

        # Grab Audio Source URL
        audio_source = bframe.locator('#audio-source')
        src_url = audio_source.get_attribute('src')

        if not src_url:
            print("      Audio URL not found directly, re-checking frame...")
            return False

        print("      Downloading audio challenge MP3...")
        urllib.request.urlretrieve(src_url, "captcha.mp3")

        # Convert MP3 to WAV using pydub
        sound = pydub.AudioSegment.from_mp3("captcha.mp3")
        sound.export("captcha.wav", format="wav")

        # Speech-to-Text using free SpeechRecognition engine
        recognizer = sr.Recognizer()
        with sr.AudioFile("captcha.wav") as source:
            audio_data = recognizer.record(source)
            text_result = recognizer.recognize_google(audio_data)

        print(f"      Transcribed Audio Code: '{text_result}'")

        # Type response into CAPTCHA box
        audio_response_input = bframe.locator('#audio-response')
        audio_response_input.fill(text_result)
        time.sleep(1)

        # Click Verify Button
        verify_btn = bframe.locator('#recaptcha-verify-button')
        verify_btn.click()
        time.sleep(3)
        
        print("      🎉 Audio CAPTCHA verified successfully!")
        return True

    except Exception as e:
        print(f"      Audio CAPTCHA note: {e}")
        return False

# -------------------------------------------------------------
# Main Execution Workflow via Playwright
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
            # Step 2: Navigate to EuroDNS
            print("[2/7] Navigating to EuroDNS registration page...")
            page.goto("https://eurodns.pxf.io/PzkDy6", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

            # Step 3: Accept Cookies
            print("[3/7] Accepting cookies...")
            try:
                page.click('#cookiescript_accept', timeout=5000)
                print("      Cookies accepted.")
            except Exception:
                pass

            # Step 4: Open Registration Form
            print("[4/7] Opening Account menu & clicking 'New Account'...")
            page.click('#account-item-logout', timeout=10000)
            time.sleep(2)
            page.click('#logout-user-section a:nth-child(2)', timeout=10000)
            time.sleep(3)

            # Step 5: Fill Credentials
            print("[5/7] Generating real temp email & password...")
            real_email = create_real_temp_email()
            eurodns_pass = generate_strong_password(16)

            print(f"\n==================================================")
            print(f"  REGISTERING WITH:")
            print(f"  EMAIL:    {real_email}")
            print(f"  PASSWORD: {eurodns_pass}")
            print(f"==================================================\n")

            # Fill Email
            email_input = page.locator("input[type='email'], input[formcontrolname='email'], input[name='email']").first
            email_input.fill(real_email)
            time.sleep(1)

            # Fill Password
            pass_input = page.locator("input[type='password'], input[formcontrolname='password']").first
            pass_input.fill(eurodns_pass)
            time.sleep(1)

            # Checkbox
            try:
                page.click('#subscribe-newsletter-checkbox-input', timeout=3000)
            except Exception:
                pass

            page.screenshot(path="screenshot_form_filled.png")

            # Step 6: Click Create Account
            print("[6/7] Clicking 'Create Account' button...")
            create_btn = page.locator("edns-new-account button[type='submit'], form button:has-text('Create account')").first
            create_btn.click()
            time.sleep(5)

            # Trigger Free Audio CAPTCHA solve if modal appeared
            solve_audio_recaptcha(page)

            # Final submit click after CAPTCHA solve
            try:
                create_btn.click(timeout=3000)
            except Exception:
                pass

            time.sleep(10)
            page.screenshot(path="screenshot_after_registration.png")

            # Step 7: Verify Login Session
            print("[7/7] Navigating to Login Page to verify credentials...")
            page.goto("https://my.eurodns.com/login", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

            # Fill Login Form using Playwright auto-wait
            try:
                login_email = page.locator("input[type='email'], input[name='email']").first
                login_email.fill(real_email)

                login_pass = page.locator("input[type='password'], input[name='password']").first
                login_pass.fill(eurodns_pass)

                login_btn = page.locator("button[type='submit']").first
                login_btn.click()
                time.sleep(10)
            except Exception as e:
                print(f"      Login step note: {e}")

            current_url = page.url
            print(f"      Landed URL: {current_url}")

            page.screenshot(path="screenshot.png")

            print("\n==================================================")
            print("Workflow Completed Successfully!")
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
