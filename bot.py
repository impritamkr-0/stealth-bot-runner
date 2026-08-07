import os
import time
import uuid
import json
import string
import random
import tempfile
import shutil
import urllib.request
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -------------------------------------------------------------
# Configuration
# -------------------------------------------------------------
SCREENSHOT_DIR = "."
EXTENSION_PATH = "./nopecha.crx"

# -------------------------------------------------------------
# mail.tm API Integration
# -------------------------------------------------------------
def create_real_temp_email():
    """Dynamically creates a real temporary email account using mail.tm API."""
    print("      [mail.tm] Querying active domain...")
    
    try:
        req = urllib.request.Request(
            "https://api.mail.tm/domains", 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
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

        with urllib.request.urlopen(post_req, timeout=10) as response:
            print(f"      [mail.tm] Account created: {email_address}")
            return email_address, account_password
            
    except Exception as e:
        print(f"      [mail.tm] Error: {e}")
        # Fallback to random email
        fallback = f"test_{uuid.uuid4().hex[:8]}@example.com"
        print(f"      [mail.tm] Using fallback: {fallback}")
        return fallback, "password123"

def human_delay(min_sec=2.0, max_sec=5.0):
    delay = random.uniform(min_sec, max_sec)
    print(f"      [Delay] {delay:.2f}s...")
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

def take_screenshot(driver, name):
    try:
        path = f"{SCREENSHOT_DIR}/{name}.png"
        driver.save_screenshot(path)
        print(f"      [Screenshot] Saved: {name}.png")
    except Exception as e:
        print(f"      [Screenshot] Failed: {e}")

# -------------------------------------------------------------
# Main Bot
# -------------------------------------------------------------
temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")
print(f"[Setup] Created profile: {temp_profile_dir}")

options = uc.ChromeOptions()

# Load extension if available
if os.path.exists(EXTENSION_PATH):
    print(f"[Setup] Loading NopeCHA extension...")
    options.add_extension(EXTENSION_PATH)
else:
    print(f"[WARNING] Extension not found at {EXTENSION_PATH}")

# Additional stealth options
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-web-security")
options.add_argument("--disable-features=IsolateOrigins,site-per-process")

driver = None

try:
    print("[Setup] Starting Chrome...")
    driver = uc.Chrome(options=options, version_main=None)
    driver.set_window_size(1920, 1080)
    print("[Setup] Chrome started successfully")
    
    # Wait for extension to load
    time.sleep(3)
    
    # -------------------------------------------------------------
    # Step 1: Navigate to EuroDNS
    # -------------------------------------------------------------
    print("\n[1/7] Navigating to EuroDNS...")
    target_url = "https://eurodns.pxf.io/PzkDy6"
    driver.get(target_url)
    human_delay(3, 5)
    take_screenshot(driver, "01_initial_page")

    # -------------------------------------------------------------
    # Step 2: Accept Cookies
    # -------------------------------------------------------------
    print("[2/7] Accepting cookies...")
    try:
        accept_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiescript_accept"]'))
        )
        driver.execute_script("arguments[0].click();", accept_btn)
        print("      Cookies accepted")
    except Exception as e:
        print(f"      Cookie banner: {e}")
    
    human_delay(2, 3)
    take_screenshot(driver, "02_after_cookies")

    # -------------------------------------------------------------
    # Step 3: Open Account Menu
    # -------------------------------------------------------------
    print("[3/7] Opening account menu...")
    account_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="account-item-logout"]'))
    )
    driver.execute_script("arguments[0].click();", account_btn)
    human_delay(2, 3)

    # -------------------------------------------------------------
    # Step 4: Click New Account
    # -------------------------------------------------------------
    print("[4/7] Clicking 'New Account'...")
    new_account_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="logout-user-section"]/a[2]'))
    )
    driver.execute_script("arguments[0].click();", new_account_btn)
    human_delay(4, 6)
    take_screenshot(driver, "04_registration_form")

    # -------------------------------------------------------------
    # Step 5: Generate Credentials
    # -------------------------------------------------------------
    print("[5/7] Generating credentials...")
    real_email, _ = create_real_temp_email()
    random_password = generate_strong_password(16)
    
    print(f"      Email: {real_email}")
    print(f"      Password: {random_password}")

    # Fill Email
    email_field = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[formcontrolname='email'], input[name='email']"))
    )
    email_field.clear()
    for char in real_email:
        email_field.send_keys(char)
        time.sleep(random.uniform(0.05, 0.12))
    
    human_delay(1, 2)

    # Fill Password
    password_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[formcontrolname='password'], input[id*='password']"))
    )
    password_field.clear()
    for char in random_password:
        password_field.send_keys(char)
        time.sleep(random.uniform(0.05, 0.12))

    human_delay(2, 3)

    # -------------------------------------------------------------
    # Step 6: Handle Newsletter Checkbox
    # -------------------------------------------------------------
    print("[6/7] Handling newsletter checkbox...")
    try:
        checkbox = driver.find_element(By.XPATH, '//*[@id="subscribe-newsletter-checkbox-input"]')
        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
        driver.execute_script("arguments[0].click();", checkbox)
        print("      Checkbox clicked")
    except Exception as e:
        print(f"      Checkbox note: {e}")

    human_delay(2, 3)
    take_screenshot(driver, "06_form_filled")

    # -------------------------------------------------------------
    # Step 7: Submit Form
    # -------------------------------------------------------------
    print("[7/7] Submitting form...")
    
    # Try multiple XPaths for create button
    create_btn = None
    xpaths = [
        "/html/body/edns-root/edns-layout/div/div/edns-side-panels/mat-sidenav-container/mat-sidenav-content/div/div[2]/edns-new-account/div/div/form/div[4]/button/span[2]",
        "//button[contains(text(), 'Create')]",
        "//button[@type='submit']",
        "//edns-new-account//button"
    ]
    
    for xpath in xpaths:
        try:
            create_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            break
        except:
            continue
    
    if create_btn:
        driver.execute_script("arguments[0].scrollIntoView(true);", create_btn)
        driver.execute_script("arguments[0].click();", create_btn)
        print("      Form submitted")
    else:
        raise Exception("Could not find Create Account button")

    # Wait for captcha solve
    print("\n" + "="*60)
    print("Waiting for NopeCHA to solve captcha...")
    print("This may take 15-30 seconds...")
    print("="*60)
    
    time.sleep(20)  # Give NopeCHA time
    
    take_screenshot(driver, "07_after_captcha_wait")
    
    # Check current URL
    current_url = driver.current_url
    print(f"\nCurrent URL: {current_url}")
    
    # Check for success indicators
    page_source = driver.page_source.lower()
    
    if "success" in page_source or "welcome" in page_source or "dashboard" in current_url:
        print("\n[✓] SUCCESS! Account appears to be created!")
        print(f"Email: {real_email}")
        print(f"Password: {random_password}")
        
        # Save credentials
        with open("credentials.txt", "a") as f:
            f.write(f"{real_email}:{random_password}\n")
            
    elif "captcha" in page_source or "robot" in page_source:
        print("\n[✗] FAILED: Captcha still present")
        
        # Wait a bit more
        print("Waiting 20 more seconds...")
        time.sleep(20)
        take_screenshot(driver, "08_extended_wait")
        
    else:
        print("\n[?] UNKNOWN: Check screenshots manually")
        print(f"Page title: {driver.title}")
    
    # Keep open for final screenshot
    time.sleep(5)
    take_screenshot(driver, "09_final")

    # Save credentials regardless for manual check
    with open("credentials.txt", "a") as f:
        f.write(f"{real_email}:{random_password}\n")
    print(f"\nCredentials saved to credentials.txt")

except Exception as e:
    print(f"\n[ERROR] {e}")
    if driver:
        take_screenshot(driver, "ERROR")

finally:
    if driver:
        try:
            driver.quit()
        except:
            pass
    
    try:
        shutil.rmtree(temp_profile_dir, ignore_errors=True)
        print("[Cleanup] Profile removed")
    except:
        pass
    
    print("\n[Done] Check screenshots and credentials.txt")
