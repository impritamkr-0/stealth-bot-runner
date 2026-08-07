import os
import time
import uuid
import json
import string
import random
import tempfile
import shutil
import urllib.request
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
ext_path = os.path.abspath("nopecha-chromium")

if not os.path.exists(ext_path):
    raise FileNotFoundError(f"Could not find 'nopecha-chromium' at {ext_path}.")

temp_dir = tempfile.mkdtemp(prefix="stealth_bot_")
profile_dir = os.path.join(temp_dir, "chrome_profile")

try:
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument(f"--load-extension={ext_path}")
    options.add_argument(f"--disable-extensions-except={ext_path}")

    print("[1/8] Launching Chrome with NopeCHA extension...")
    driver = uc.Chrome(options=options, version_main=150)
    time.sleep(5)

    # Step 2: Navigate to EuroDNS
    print("[2/8] Navigating to EuroDNS registration page...")
    driver.get("https://eurodns.pxf.io/PzkDy6")
    human_delay(3, 5)

    # Step 3: Accept Cookies
    print("[3/8] Accepting cookies...")
    try:
        accept_cookies = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiescript_accept"]'))
        )
        driver.execute_script("arguments[0].click();", accept_cookies)
    except Exception:
        pass
    human_delay(2, 3)

    # Step 4: Open Registration Form
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
    print("[5/8] Generating real temp email & password...")
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

    try:
        checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="subscribe-newsletter-checkbox-input"]'))
        )
        driver.execute_script("arguments[0].click();", checkbox)
    except Exception:
        pass

    human_delay(2, 3)

    # Step 6: Click Create Account
    print("[6/8] Clicking 'Create Account' button to trigger CAPTCHA...")
    create_account_xpath = "/html/body/edns-root/edns-layout/div/div/edns-side-panels/mat-sidenav-container/mat-sidenav-content/div/div[2]/edns-new-account/div/div/form/div[4]/button/span[2]"
    
    try:
        create_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, create_account_xpath))
        )
        driver.execute_script("arguments[0].click();", create_btn)
    except Exception:
        create_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "edns-new-account button[type='submit']"))
        )
        driver.execute_script("arguments[0].click();", create_btn)

    print("      Button clicked! Waiting 45s for CAPTCHA solve...")
    time.sleep(45)

    # Secondary click to submit token if form is still active
    try:
        print("      Submitting form with solved CAPTCHA token...")
        driver.execute_script("arguments[0].click();", create_btn)
        time.sleep(15)
    except Exception:
        pass

    driver.save_screenshot("screenshot_after_registration.png")

    # Step 7: Perform Actual Login Verification
    print("[7/8] Navigating to Login Page to test new credentials...")
    driver.get("https://my.eurodns.com/login")
    human_delay(3, 5)

    try:
        login_email = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[formcontrolname='login']"))
        )
        set_angular_input(driver, login_email, real_email)

        login_pass = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[name='password']"))
        )
        set_angular_input(driver, login_pass, eurodns_pass)

        login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        driver.execute_script("arguments[0].click();", login_btn)
        print("      Login form submitted! Waiting 15 seconds...")
        time.sleep(15)
    except Exception as e:
        print(f"      Login attempt note: {e}")

    # Step 8: Verify Final URL
    current_url = driver.current_url
    print(f"[8/8] Landed URL after login: {current_url}")

    driver.save_screenshot("screenshot.png")

    print("\n==================================================")
    print(f"Final Page URL: {current_url}")
    print(f"Credentials -> Email: {real_email} | Password: {eurodns_pass}")
    print("==================================================\n")

except Exception as e:
    print(f"\n[X] Error: {e}")
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
    except Exception:
        pass
