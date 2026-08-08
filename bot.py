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
from selenium_recaptcha_solver import RecaptchaSolver

# -------------------------------------------------------------
# mail.tm API Integration
# -------------------------------------------------------------
def create_real_temp_email():
    """Dynamically creates a real temporary email account using mail.tm API."""
    print("      [mail.tm] Querying active domain...")
    
    req = urllib.request.Request(
        "https://api.mail.tm/domains", 
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req) as response:
        domains_data = json.loads(response.read().decode('utf-8'))
    
    active_domain = domains_data['hydra:member'][0]['domain']
    unique_user = f"user_{uuid.uuid4().hex[:8]}"
    email_address = f"{unique_user}@{active_domain}"
    account_password = "TempMailPassword123!"

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

def human_delay(min_sec=2.0, max_sec=5.0):
    delay = random.uniform(min_sec, max_sec)
    print(f"      [Human Delay] Pausing for {delay:.2f} seconds...")
    time.sleep(delay)

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
# Chrome & Profile Setup (Linux CI / Xvfb compatible)
# -------------------------------------------------------------
temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")
print(f"[1/8] Created temporary profile: {temp_profile_dir}")

options = uc.ChromeOptions()
options.add_argument(f"--user-data-dir={temp_profile_dir}")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = uc.Chrome(options=options)

try:
    target_url = "https://eurodns.pxf.io/PzkDy6"
    print(f"[2/8] Navigating to target URL: {target_url}")
    driver.get(target_url)
    human_delay(3, 5)

    # -------------------------------------------------------------
    # Step 3: Cookie Banner
    # -------------------------------------------------------------
    print("[3/8] Accepting cookie consent...")
    try:
        accept_cookies = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiescript_accept"]'))
        )
        driver.execute_script("arguments[0].click();", accept_cookies)
        print("      Cookies accepted.")
    except Exception as e:
        print(f"      Cookie banner note: {e}")

    human_delay(2, 4)

    # -------------------------------------------------------------
    # Step 4: My Account
    # -------------------------------------------------------------
    print("[4/8] Opening Account menu...")
    account_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="account-item-logout"]'))
    )
    driver.execute_script("arguments[0].click();", account_btn)
    human_delay(2, 4)

    # -------------------------------------------------------------
    # Step 5: New Account Form
    # -------------------------------------------------------------
    print("[5/8] Clicking 'New Account'...")
    new_account_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="logout-user-section"]/a[2]'))
    )
    driver.execute_script("arguments[0].click();", new_account_btn)
    human_delay(4, 6)

    # -------------------------------------------------------------
    # Step 6: Generate & Fill Credentials
    # -------------------------------------------------------------
    print("[6/8] Generating temp email via mail.tm...")
    real_email, _ = create_real_temp_email()
    random_password = generate_strong_password(16)
    
    print(f"      Email: {real_email}")
    print(f"      Password: {random_password}")

    email_field = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((
            By.CSS_SELECTOR, 
            "input[type='email'], input[formcontrolname='email'], input[name='email'], input[id*='email']"
        ))
    )
    email_field.clear()
    for char in real_email:
        email_field.send_keys(char)
        time.sleep(random.uniform(0.05, 0.12))

    human_delay(1, 2)

    password_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.CSS_SELECTOR, 
            "input[type='password'], input[formcontrolname='password'], input[id*='password']"
        ))
    )
    password_field.clear()
    for char in random_password:
        password_field.send_keys(char)
        time.sleep(random.uniform(0.05, 0.12))

    human_delay(2, 3)

    # Newsletter Checkbox
    try:
        checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="subscribe-newsletter-checkbox-input"]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
        driver.execute_script("arguments[0].click();", checkbox)
    except Exception as e:
        print(f"      Checkbox note: {e}")

    human_delay(2, 3)

    # -------------------------------------------------------------
    # Step 7: Free Audio reCAPTCHA Solver Integration
    # -------------------------------------------------------------
    print("[7/8] Detecting reCAPTCHA v2 frame...")
    try:
        recaptcha_iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//iframe[contains(@src, "recaptcha") or contains(@title, "reCAPTCHA")]'))
        )
        print("      reCAPTCHA iframe found! Invoking Audio Speech Solver...")
        
        # Initialize free solver
        solver = RecaptchaSolver(driver=driver)
        solver.click_recaptcha_v2(iframe=recaptcha_iframe)
        print("      reCAPTCHA solved successfully via Audio Recognition!")
    except Exception as e:
        print(f"      reCAPTCHA solving note/error: {e}")

    human_delay(2, 4)

    # -------------------------------------------------------------
    # Step 8: Submit Form
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
    print("Workflow executed successfully!")
    print(f"Created account email: {real_email}")
    print("="*60 + "\n")
    
    time.sleep(10)

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
