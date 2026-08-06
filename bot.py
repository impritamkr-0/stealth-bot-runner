import os
import time
import uuid
import json
import io
import zipfile
import string
import random
import tempfile
import shutil
import urllib.request
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -------------------------------------------------------------
# Permanent Fix: Download & Unpack NopeCHA Extension
# -------------------------------------------------------------
def get_unpacked_nopecha(target_dir):
    """Downloads official NopeCHA release zip and extracts unpacked extension."""
    abs_dir = os.path.abspath(target_dir)
    manifest_path = os.path.join(abs_dir, "manifest.json")

    if os.path.exists(manifest_path):
        print(f"[Extension] Found existing NopeCHA folder at: {abs_dir}")
        return abs_dir

    print("[Extension] Downloading NopeCHA source zip from official repository...")
    zip_url = "https://github.com/NopeCHA/NopeCHA/releases/latest/download/chrome.zip"
    
    req = urllib.request.Request(zip_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            zip_bytes = resp.read()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            z.extractall(abs_dir)

        print(f"[Extension] Successfully unpacked extension to: {abs_dir}")
        return abs_dir
    except Exception as e:
        print(f"[Extension] Download error: {e}")
        raise e

# Helper: Set Angular Input and Dispatch Events
def set_angular_input(driver, element, value):
    element.clear()
    for char in value:
        element.send_keys(char)
        time.sleep(0.03)
    driver.execute_script("""
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
    """, element)

# Helper: Generate Real Temp Email via mail.tm
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

def human_delay(min_sec=2.0, max_sec=4.0):
    time.sleep(random.uniform(min_sec, max_sec))

# -------------------------------------------------------------
# Main Execution Workflow
# -------------------------------------------------------------
temp_dir = tempfile.mkdtemp(prefix="stealth_bot_")
ext_folder = os.path.join(temp_dir, "nopecha_ext")
profile_dir = os.path.join(temp_dir, "chrome_profile")

try:
    # 1. Download & extract unpacked NopeCHA extension
    ext_path = get_unpacked_nopecha(ext_folder)

    # 2. Configure Chrome with unpacked extension
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument(f"--load-extension={ext_path}")
    options.add_argument(f"--disable-extensions-except={ext_path}")

    print("[1/6] Launching Chrome with NopeCHA pre-loaded...")
    driver = uc.Chrome(options=options, version_main=150)

    # 3. Navigate to EuroDNS
    print("[2/6] Navigating to EuroDNS registration page...")
    driver.get("https://eurodns.pxf.io/PzkDy6")
    human_delay(3, 5)

    # 4. Accept Cookies
    print("[3/6] Accepting cookies...")
    try:
        accept_cookies = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiescript_accept"]'))
        )
        driver.execute_script("arguments[0].click();", accept_cookies)
        print("      Cookies accepted.")
    except Exception as e:
        print(f"      Cookie banner note: {e}")
    human_delay(2, 3)

    # 5. Open Registration Form
    print("[4/6] Opening Account menu & clicking 'New Account'...")
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

    # 6. Fill Credentials
    print("[5/6] Generating real temp email & password...")
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
    set_angular_input(driver, email_field, real_email)
    human_delay(1, 2)

    password_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[formcontrolname='password']"))
    )
    set_angular_input(driver, password_field, eurodns_pass)
    human_delay(2, 3)

    # Checkbox
    print("      Clicking newsletter checkbox...")
    try:
        checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="subscribe-newsletter-checkbox-input"]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
        driver.execute_script("arguments[0].click();", checkbox)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", checkbox)
    except Exception as e:
        print(f"      Checkbox note: {e}")

    human_delay(2, 3)

    # 7. Click Create Account
    print("[6/6] Clicking 'Create Account' button to trigger CAPTCHA...")
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

    print("      Button clicked! Waiting 60 seconds for NopeCHA to solve image CAPTCHA...")
    time.sleep(60)

    # Save screenshot artifact
    driver.save_screenshot("screenshot.png")
    print("      Saved 'screenshot.png' for run verification.")

    print("\n==================================================")
    print("Form submitted post-CAPTCHA solve.")
    print(f"Credentials -> Email: {real_email} | Password: {eurodns_pass}")
    print("==================================================\n")

except Exception as e:
    print(f"\n[X] Error during execution: {e}")
    try:
        driver.save_screenshot("screenshot.png")
    except Exception:
        pass

finally:
    try:
        driver.close()
        driver.quit()
    except Exception:
        pass
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("Temporary folder cleaned up.")
    except Exception:
        pass
