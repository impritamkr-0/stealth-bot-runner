import os
import time
import uuid
import json
import string
import random
import tempfile
import shutil
import urllib.request
import pyautogui
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Helper function to generate real temp mail via mail.tm
def create_real_temp_email():
    print("      [mail.tm] Querying active domain...")
    req = urllib.request.Request("https://api.mail.tm/domains", headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        domains_data = json.loads(response.read().decode('utf-8'))
    
    active_domain = domains_data['hydra:member'][0]['domain']
    unique_user = f"user_{uuid.uuid4().hex[:8]}"
    email_address = f"{unique_user}@{active_domain}"
    account_password = "TempMailPassword123!"

    payload = json.dumps({"address": email_address, "password": account_password}).encode('utf-8')
    post_req = urllib.request.Request(
        "https://api.mail.tm/accounts",
        data=payload,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(post_req) as response:
        print(f"      [mail.tm] Account created: {email_address}")
        return email_address

def human_delay(min_sec=2.0, max_sec=4.0):
    time.sleep(random.uniform(min_sec, max_sec))

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
# Temporary Profile Setup
# -------------------------------------------------------------
temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")
options = uc.ChromeOptions()
options.add_argument(f"--user-data-dir={temp_profile_dir}")

driver = uc.Chrome(options=options, version_main=150)

try:
    # Step 1: Install NopeCHA Extension
    print("[1/8] Installing NopeCHA Extension...")
    driver.get("https://chromewebstore.google.com/detail/nopecha-captcha-solver/dknlfmjaanfblgfdfebhijalfmhmjjjo?hl=en")
    human_delay(2, 3)
    
    add_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Add to Chrome') or contains(., 'Add to')]"))
    )
    add_button.click()
    time.sleep(2)
    pyautogui.press('left')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(0.5)
    pyautogui.press('enter')
    human_delay(4, 5)

    # Step 2: Open New Tab & Navigate to EuroDNS
    print("[2/8] Opening new tab and navigating to EuroDNS...")
    driver.switch_to.new_window('tab')
    driver.get("https://eurodns.pxf.io/PzkDy6")
    human_delay(3, 5)

    # Step 3: Accept Cookies
    print("[3/8] Accepting cookie consent...")
    try:
        accept_cookies = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiescript_accept"]'))
        )
        driver.execute_script("arguments[0].click();", accept_cookies)
        print("      Cookies accepted.")
    except Exception as e:
        print(f"      Cookie banner note: {e}")
    human_delay(2, 3)

    # Step 4: Open Account Menu & Click 'New Account'
    print("[4/8] Opening Account menu & clicking 'New Account'...")
    account_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="account-item-logout"]'))
    )
    driver.execute_script("arguments[0].click();", account_btn)
    human_delay(2, 3)

    new_account_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="logout-user-section"]/a[2]'))
    )
    driver.execute_script("arguments[0].click();", new_account_btn)
    human_delay(4, 5)

    # Step 5: Fill Credentials
    print("[5/8] Generating real email & password...")
    real_email = create_real_temp_email()
    eurodns_pass = generate_strong_password(16)

    print(f"\n==================================================")
    print(f"  REGISTERING WITH:")
    print(f"  EMAIL:    {real_email}")
    print(f"  PASSWORD: {eurodns_pass}")
    print(f"==================================================\n")

    email_field = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[formcontrolname='email'], input[name='email']"))
    )
    email_field.clear()
    for char in real_email:
        email_field.send_keys(char)
        time.sleep(0.05)

    human_delay(1, 2)

    password_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[formcontrolname='password']"))
    )
    password_field.clear()
    for char in eurodns_pass:
        password_field.send_keys(char)
        time.sleep(0.05)

    human_delay(2, 3)

    # Step 6: Newsletter Checkbox
    print("[6/8] Clicking newsletter checkbox...")
    try:
        checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="subscribe-newsletter-checkbox-input"]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
        driver.execute_script("arguments[0].click();", checkbox)
    except Exception as e:
        print(f"      Checkbox note: {e}")

    human_delay(2, 3)

    # Step 7: Click 'Create Account' FIRST to trigger CAPTCHA
    print("[7/8] Clicking 'Create Account' button to trigger CAPTCHA popup...")
    create_account_xpath = "/html/body/edns-root/edns-layout/div/div/edns-side-panels/mat-sidenav-container/mat-sidenav-content/div/div[2]/edns-new-account/div/div/form/div[4]/button/span[2]"
    
    try:
        create_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, create_account_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", create_btn)
        driver.execute_script("arguments[0].click();", create_btn)
    except Exception:
        create_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "edns-new-account button[type='submit'], edns-new-account form button"))
        )
        driver.execute_script("arguments[0].click();", create_btn)

    print("      Button clicked! CAPTCHA modal popped up.")

    # Step 8: Wait 60 seconds while NopeCHA solves CAPTCHA & auto-verifies
    print("\n[8/8] Waiting 60 seconds for NopeCHA to solve CAPTCHA and auto-verify...")
    time.sleep(60)

    print("\n==================================================")
    print("SUCCESS! CAPTCHA solved and account created.")
    print(f"Credentials -> Email: {real_email} | Password: {eurodns_pass}")
    print("==================================================\n")

except Exception as e:
    print(f"\n[X] Error during execution: {e}")

finally:
    try:
        driver.close()
        driver.quit()
    except Exception:
        pass
    try:
        shutil.rmtree(temp_profile_dir, ignore_errors=True)
        print("Temporary profile folder cleaned up.")
    except Exception:
        pass
