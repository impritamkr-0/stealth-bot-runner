import os
import sys
import time
import uuid
import json
import string
import random
import tempfile
import shutil
import urllib.request
import urllib.error
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = "."
EXTENSION_PATH = "./nopecha.crx"

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

def generate_fallback_email():
    """Generate a random email using guerrillamail API"""
    try:
        print("      [Fallback] Trying guerrillamail...")
        session = requests.Session()
        # Get session
        r = session.get("https://api.guerrillamail.com/ajax.php?f=get_email_address", timeout=10)
        data = r.json()
        email = data.get("email_addr")
        sid = data.get("sid_token")
        if email:
            print(f"      [Fallback] Got email: {email}")
            return email, sid
    except Exception as e:
        print(f"      [Fallback] Failed: {e}")
    
    # Ultimate fallback - just random
    random_email = f"user{uuid.uuid4().hex[:10]}@sharklasers.com"
    print(f"      [Ultimate Fallback] Using: {random_email}")
    return random_email, None

def create_temp_email():
    """Try mail.tm first, fallback to others"""
    print("      [Email] Trying mail.tm...")
    
    try:
        # Try mail.tm with timeout and better error handling
        req = urllib.request.Request(
            "https://api.mail.tm/domains", 
            headers={'User-Agent': 'Mozilla/5.0'},
            method='GET'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if 'hydra:member' not in data or len(data['hydra:member']) == 0:
            raise Exception("No domains available")
            
        domain = data['hydra:member'][0]['domain']
        unique = f"user{uuid.uuid4().hex[:8]}"
        email = f"{unique}@{domain}"
        
        # Create account
        payload = json.dumps({
            "address": email,
            "password": "TempPass123!"
        }).encode('utf-8')
        
        post_req = urllib.request.Request(
            "https://api.mail.tm/accounts",
            data=payload,
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'},
            method='POST'
        )
        
        with urllib.request.urlopen(post_req, timeout=10) as response:
            print(f"      [Email] Created: {email}")
            return email
            
    except urllib.error.HTTPError as e:
        print(f"      [Email] HTTP Error {e.code}: {e.reason}")
        return generate_fallback_email()[0]
    except urllib.error.URLError as e:
        print(f"      [Email] URL Error: {e.reason}")
        return generate_fallback_email()[0]
    except json.JSONDecodeError as e:
        print(f"      [Email] JSON Error: {e}")
        return generate_fallback_email()[0]
    except Exception as e:
        print(f"      [Email] Error: {e}")
        return generate_fallback_email()[0]

def take_screenshot(driver, name):
    try:
        path = f"{SCREENSHOT_DIR}/{name}.png"
        driver.save_screenshot(path)
        print(f"      [Screenshot] {name}.png")
    except Exception as e:
        print(f"      [Screenshot] Failed: {e}")

# Setup
temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")
print(f"[Setup] Profile: {temp_profile_dir}")

options = uc.ChromeOptions()

if os.path.exists(EXTENSION_PATH):
    print("[Setup] Loading NopeCHA...")
    options.add_extension(EXTENSION_PATH)
else:
    print("[WARNING] Extension not found!")

options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = None

try:
    print("[Setup] Starting Chrome...")
    driver = uc.Chrome(options=options, version_main=None)
    driver.set_window_size(1920, 1080)
    print("[Setup] Chrome started")
    time.sleep(2)
    
    # Step 1: Navigate
    print("\n[1/7] Navigating to EuroDNS...")
    driver.get("https://eurodns.pxf.io/PzkDy6")
    human_delay(3, 5)
    take_screenshot(driver, "01_initial")
    
    # Step 2: Cookies
    print("[2/7] Accepting cookies...")
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiescript_accept"]'))
        )
        driver.execute_script("arguments[0].click();", btn)
        print("      Accepted")
    except Exception as e:
        print(f"      Cookie skip: {e}")
    human_delay(2, 3)
    
    # Step 3: Account menu
    print("[3/7] Opening account menu...")
    btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="account-item-logout"]'))
    )
    driver.execute_script("arguments[0].click();", btn)
    human_delay(2, 3)
    
    # Step 4: New Account
    print("[4/7] Clicking New Account...")
    btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="logout-user-section"]/a[2]'))
    )
    driver.execute_script("arguments[0].click();", btn)
    human_delay(4, 6)
    take_screenshot(driver, "04_form")
    
    # Step 5: Generate credentials
    print("[5/7] Generating credentials...")
    email = create_temp_email()
    password = generate_strong_password()
    print(f"      Email: {email}")
    print(f"      Pass: {password}")
    
    # Fill email
    email_field = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[formcontrolname='email']"))
    )
    email_field.clear()
    for char in email:
        email_field.send_keys(char)
        time.sleep(random.uniform(0.05, 0.1))
    human_delay(1, 2)
    
    # Fill password
    pass_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
    )
    pass_field.clear()
    for char in password:
        pass_field.send_keys(char)
        time.sleep(random.uniform(0.05, 0.1))
    human_delay(2, 3)
    
    # Step 6: Newsletter
    print("[6/7] Unchecking newsletter...")
    try:
        cb = driver.find_element(By.XPATH, '//*[@id="subscribe-newsletter-checkbox-input"]')
        driver.execute_script("arguments[0].click();", cb)
    except Exception as e:
        print(f"      Checkbox: {e}")
    human_delay(2, 3)
    take_screenshot(driver, "06_filled")
    
    # Step 7: Submit
    print("[7/7] Submitting...")
    try:
        btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Create')]")
        driver.execute_script("arguments[0].click();", btn)
    except:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            driver.execute_script("arguments[0].click();", btn)
        except Exception as e:
            raise Exception(f"Cannot find submit button: {e}")
    
    print("      Waiting 25s for captcha...")
    time.sleep(25)
    take_screenshot(driver, "07_after_captcha")
    
    # Check result
    url = driver.current_url
    source = driver.page_source.lower()
    print(f"\nURL: {url}")
    
    success = False
    if "success" in source or "welcome" in source or "dashboard" in url:
        success = True
        print("[SUCCESS] Account created!")
    elif "captcha" in source or "robot" in source:
        print("[FAILED] Captcha still present")
    else:
        print("[CHECK NEEDED] Verify manually")
    
    # Save credentials
    with open("credentials.txt", "w") as f:
        f.write(f"Email: {email}\nPassword: {password}\nSuccess: {success}\nURL: {url}\n")
    print("Saved to credentials.txt")
    
    time.sleep(5)
    take_screenshot(driver, "08_final")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
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
    except:
        pass
    print("\n[Done]")
