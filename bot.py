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
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choice(chars) for _ in range(length))

def create_temp_email():
    """Generate random email"""
    return f"user{uuid.uuid4().hex[:10]}@mail.tm"

def take_screenshot(driver, name):
    try:
        driver.save_screenshot(f"{SCREENSHOT_DIR}/{name}.png")
        print(f"      [Screenshot] {name}.png")
    except:
        pass

# Setup
temp_profile_dir = tempfile.mkdtemp(prefix="stealth_")
print(f"[Setup] Profile: {temp_profile_dir}")

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

if os.path.exists(EXTENSION_PATH):
    print("[Setup] Loading extension...")
    options.add_extension(EXTENSION_PATH)

driver = None

try:
    print("[Setup] Starting Chrome (auto-downloading matching version)...")
    # KEY FIX: Don't specify version_main, let uc download its own Chrome
    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.set_window_size(1920, 1080)
    print("[Setup] Chrome started successfully")
    time.sleep(2)
    
    # Navigate
    print("\n[1/6] Loading EuroDNS...")
    driver.get("https://eurodns.pxf.io/PzkDy6")
    human_delay(3, 5)
    take_screenshot(driver, "01_start")
    
    # Cookies
    print("[2/6] Cookies...")
    try:
        btn = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiescript_accept"]'))
        )
        driver.execute_script("arguments[0].click();", btn)
    except:
        pass
    human_delay(2, 3)
    
    # Account menu
    print("[3/6] Account menu...")
    btn = WebDriverWait(driver, 8).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="account-item-logout"]'))
    )
    driver.execute_script("arguments[0].click();", btn)
    human_delay(2, 3)
    
    # New Account
    print("[4/6] New Account...")
    btn = WebDriverWait(driver, 8).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="logout-user-section"]/a[2]'))
    )
    driver.execute_script("arguments[0].click();", btn)
    human_delay(4, 6)
    take_screenshot(driver, "04_form")
    
    # Generate credentials
    print("[5/6] Filling form...")
    email = create_temp_email()
    password = generate_strong_password()
    print(f"      Email: {email}")
    print(f"      Pass: {password}")
    
    # Fill email
    email_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
    )
    email_field.send_keys(email)
    human_delay(1, 2)
    
    # Fill password
    pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pass_field.send_keys(password)
    human_delay(2, 3)
    
    # Uncheck newsletter
    try:
        cb = driver.find_element(By.XPATH, '//*[@id="subscribe-newsletter-checkbox-input"]')
        driver.execute_script("arguments[0].click();", cb)
    except:
        pass
    take_screenshot(driver, "05_filled")
    
    # Submit
    print("[6/6] Submitting...")
    try:
        btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Create')]")
        driver.execute_script("arguments[0].click();", btn)
    except:
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", btn)
    
    print("      Waiting 30s for captcha solve...")
    time.sleep(30)
    take_screenshot(driver, "06_after_captcha")
    
    # Save results
    url = driver.current_url
    print(f"\nFinal URL: {url}")
    
    with open("credentials.txt", "w") as f:
        f.write(f"Email: {email}\nPassword: {password}\nURL: {url}\n")
    print("Saved credentials.txt")
    
    time.sleep(3)
    take_screenshot(driver, "07_final")

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
    shutil.rmtree(temp_profile_dir, ignore_errors=True)
    print("\n[Done]")
