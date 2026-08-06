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

# -------------------------------------------------------------
# mail.tm API Integration
# -------------------------------------------------------------
def create_real_temp_email():
    """Dynamically creates a real temporary email account using mail.tm API."""
    print("      [mail.tm] Querying active domain...")
    
    # 1. Fetch available domain from mail.tm
    req = urllib.request.Request(
        "https://api.mail.tm/domains", 
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req) as response:
        domains_data = json.loads(response.read().decode('utf-8'))
    
    active_domain = domains_data['hydra:member'][0]['domain']
    
    # 2. Generate username and password for mail.tm account
    unique_user = f"user_{uuid.uuid4().hex[:8]}"
    email_address = f"{unique_user}@{active_domain}"
    account_password = "TempMailPassword123!"

    # 3. Register account on mail.tm
    payload = json.dumps({
        "address": email_address,
        "password": account_password
    }).encode('utf-8')

    post_req = urllib.request.Request(
        "https://api.mail.tm/accounts",
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }
    )

    try:
        with urllib.request.urlopen(post_req) as response:
            print(f"      [mail.tm] Account created successfully: {email_address}")
            return email_address, account_password
    except Exception as e:
        print(f"      [mail.tm] Error creating account: {e}")
        raise e

# Helper function to insert randomized human-like delays
def human_delay(min_sec=2.0, max_sec=5.0):
    delay = random.uniform(min_sec, max_sec)
    print(f"      [Human Delay] Pausing for {delay:.2f} seconds...")
    time.sleep(delay)

# Helper function to generate a compliant 16-character password for EuroDNS
def generate_strong_password(length=16):
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*()_+-="
    
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(symbols)
    ]
    all_chars = lowercase + uppercase + digits + symbols
    password += [random.choice(all_chars) for _ in range(length - 4)]
    random.shuffle(password)
    return "".join(password)

# -------------------------------------------------------------
# 1. Temporary Profile Setup
# -------------------------------------------------------------
temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")
print(f"[1/8] Created fresh temporary profile: {temp_profile_dir}")

options = uc.ChromeOptions()
options.add_argument(f"--user-data-dir={temp_profile_dir}")

driver = uc.Chrome(options=options, version_main=150)

try:
    # -------------------------------------------------------------
    # Step 1: Install NopeCHA Extension (Tab 1)
    # -------------------------------------------------------------
    print("[1/8] Opening NopeCHA Web Store page in Tab 1...")
    driver.get("https://chromewebstore.google.com/detail/nopecha-captcha-solver/dknlfmjaanfblgfdfebhijalfmhmjjjo?hl=en")
    human_delay(2, 4)
    
    print("      Installing extension...")
    add_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Add to Chrome') or contains(., 'Add to')]"))
    )
    add_button.click()
    time.sleep(2)
    
    # Confirm security dialog
    pyautogui.press('left')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(0.5)
    pyautogui.press('enter')
    
    print("      NopeCHA successfully installed!")
    human_delay(3, 5)

    # -------------------------------------------------------------
    # Step 2: Open a NEW TAB natively (keeps Tab 1 open)
    # -------------------------------------------------------------
    print("\n[2/8] Opening new tab natively for EuroDNS workflow...")
    driver.switch_to.new_window('tab')
    print("      New tab opened successfully!")
    human_delay(1, 2)
    
    target_url = "https://eurodns.pxf.io/PzkDy6"
    print(f"      Navigating to: {target_url}")
    driver.get(target_url)
    human_delay(3, 5)

    # -------------------------------------------------------------
    # Step 3: Click 'Accept All' cookie button
    # -------------------------------------------------------------
    print("[3/8] Accepting cookie consent...")
    try:
        accept_cookies = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiescript_accept"]'))
        )
        driver.execute_script("arguments[0].click();", accept_cookies)
        print("      Cookies accepted successfully.")
    except Exception as e:
        print(f"      Cookie banner note: {e}")
    
    human_delay(2, 4)

    # -------------------------------------------------------------
    # Step 4: Click 'My Account' button
    # -------------------------------------------------------------
    print("[4/8] Opening Account menu...")
    account_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="account-item-logout"]'))
    )
    driver.execute_script("arguments[0].click();", account_btn)
    human_delay(2, 4)

    # -------------------------------------------------------------
    # Step 5: Click 'New Account' button
    # -------------------------------------------------------------
    print("[5/8] Clicking 'New Account'...")
    new_account_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="logout-user-section"]/a[2]'))
    )
    driver.execute_script("arguments[0].click();", new_account_btn)
    
    human_delay(4, 6)

    # -------------------------------------------------------------
    # Step 6: Generate Real mail.tm Email & EuroDNS Password
    # -------------------------------------------------------------
    print("[6/8] Generating real temporary email via mail.tm API...")
    real_email, _ = create_real_temp_email()
    random_password = generate_strong_password(16)
    
    print(f"      Real Temp Email:   {real_email}")
    print(f"      EuroDNS Password:  {random_password}")

    # Locate Email input field
    email_field = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((
            By.CSS_SELECTOR, 
            "input[type='email'], input[formcontrolname='email'], input[name='email'], input[id*='email']"
        ))
    )
    email_field.clear()
    
    # Type email with a human rhythm
    for char in real_email:
        email_field.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))
        
    human_delay(2, 3)

    # Locate Password input field
    password_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.CSS_SELECTOR, 
            "input[type='password'], input[formcontrolname='password'], input[id*='password']"
        ))
    )
    password_field.clear()
    
    # Type password with a human rhythm
    for char in random_password:
        password_field.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))

    human_delay(2, 4)

    # -------------------------------------------------------------
    # Step 7: Click Newsletter Checkbox
    # -------------------------------------------------------------
    print("[7/8] Clicking newsletter checkbox...")
    try:
        checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="subscribe-newsletter-checkbox-input"]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
        driver.execute_script("arguments[0].click();", checkbox)
    except Exception as e:
        print(f"      Checkbox click note: {e}")

    human_delay(2, 4)

    # -------------------------------------------------------------
    # Step 8: Click 'Create Account' Button & Wait for NopeCHA
    # -------------------------------------------------------------
    print("[8/8] Submitting registration form...")
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

    print("\n" + "="*60)
    print("Form submitted successfully!")
    print(f"Email used: {real_email}")
    print("Keeping browser open for 60 seconds to allow NopeCHA to solve CAPTCHA...")
    print("="*60 + "\n")
    
    time.sleep(60)

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
        print("Temporary profile folder cleaned up successfully.")
    except Exception:
        pass
