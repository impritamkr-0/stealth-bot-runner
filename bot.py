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
ext_path = os.path.abspath("nopecha-chromium")
manifest_path = os.path.join(ext_path, "manifest.json")

if not os.path.exists(manifest_path):
    raise FileNotFoundError(
        f"Could not find 'nopecha-chromium' folder at {ext_path}. "
        "Please ensure the 'nopecha-chromium' folder is committed to your GitHub repository!"
    )

print(f"[Extension] Found local NopeCHA extension folder at: {ext_path}")

temp_dir = tempfile.mkdtemp(prefix="stealth_bot_")
profile_dir = os.path.join(temp_dir, "chrome_profile")

try:
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument(f"--load-extension={ext_path}")
    options.add_argument(f"--disable-extensions-except={ext_path}")

    print("[1/8] Launching Chrome with unpacked NopeCHA pre-loaded...")
    driver = uc.Chrome(options=options, version_main=150)

    # ---------------------------------------------------------
    # WAKE UP & INITIALIZE NOPECHA SERVICE WORKER
    # ---------------------------------------------------------
    print("      Locating NopeCHA Extension ID via CDP...")
    time.sleep(2)
    ext_id = None
    try:
        targets = driver.execute_cdp_cmd('Target.getTargets', {})
        for target in targets.get('targetInfos', []):
            url = target.get('url', '')
            if 'chrome-extension://' in url:
                ext_id = url.split('/')[2]
                break
    except Exception as e:
        print(f"      CDP target lookup note: {e}")

    if ext_id:
        print(f"      Found NopeCHA Extension ID: {ext_id}")
        options_url = f"chrome-extension://{ext_id}/options.html"
        print(f"      Opening options page to initialize session: {options_url}")
        driver.get(options_url)
        time.sleep(3)
    else:
        print("      Could not locate Extension ID directly; proceeding with 5s pause...")
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
        print("      Cookies accepted.")
    except Exception as e:
        print(f"      Cookie banner note: {e}")
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

    # Newsletter Checkbox
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

    driver.save_screenshot("screenshot_before_submit.png")

    # Step 6: Click Create Account
    print("[6/8] Clicking 'Create Account' button to trigger CAPTCHA...")
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

    print("      Button clicked! Monitoring CAPTCHA solving progress...")
    
    # ---------------------------------------------------------
    # SMART CAPTCHA MONITORING LOOP
    # ---------------------------------------------------------
    captcha_solved = False
    for i in range(12):  # Check every 5 seconds for up to 60 seconds
        time.sleep(5)
        print(f"      [Check {i+1}/12] Checking CAPTCHA status...")
        
        token_found = driver.execute_script("""
            let el = document.querySelector('[name="g-recaptcha-response"], [name="h-captcha-response"], textarea[id*="g-recaptcha"]');
            return el ? el.value.length > 10 : false;
        """)
        
        if token_found:
            print("      🎉 CAPTCHA Token populated by NopeCHA!")
            captcha_solved = True
            break

    driver.save_screenshot("screenshot_captcha_phase.png")

    if captcha_solved:
        print("      Submitting form with solved CAPTCHA token...")
        try:
            driver.execute_script("arguments[0].click();", create_btn)
        except Exception:
            pass
        time.sleep(10)

    # Step 7: Redirect to Account Summary Page
    account_summary_url = "https://my.eurodns.com/account-summary"
    print(f"[7/8] Navigating to account summary: {account_summary_url}")
    driver.get(account_summary_url)
    time.sleep(10)

    current_url = driver.current_url
    print(f"      Landed URL: {current_url}")

    driver.save_screenshot("screenshot.png")
    print("      Saved 'screenshot.png' of final summary landing page.")

    print("\n==================================================")
    print("Workflow finished.")
    print(f"Final Page URL: {current_url}")
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
