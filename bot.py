import os
import sys
import time
import uuid
import string
import random
import shutil
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = "."

def human_delay(min_sec=3.0, max_sec=7.0):
    delay = random.uniform(min_sec, max_sec)
    print(f"      [Delay] {delay:.2f}s...")
    time.sleep(delay)

def generate_strong_password(length=16):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choice(chars) for _ in range(length))

def create_temp_email():
    return f"user{uuid.uuid4().hex[:10]}@gmail.com"

def take_screenshot(driver, name):
    try:
        driver.save_screenshot(f"{SCREENSHOT_DIR}/{name}.png")
        print(f"      [Screenshot] {name}.png")
    except:
        pass

# Setup
profile_dir = "/tmp/chrome_profile_eurodns"
os.makedirs(profile_dir, exist_ok=True)
print(f"[Setup] Profile: {profile_dir}")

options = uc.ChromeOptions()

# Stealth flags
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-web-security")
options.add_argument("--disable-features=IsolateOrigins,site-per-process")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
options.add_argument(f"--user-data-dir={profile_dir}")
options.add_argument("--window-size=1920,1080")

driver = None

try:
    print("[Setup] Starting Chrome...")
    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.set_window_size(1920, 1080)
    print("[Setup] Chrome started")
    human_delay(2, 4)
    
    # Navigate
    print("\n[1/6] Loading EuroDNS...")
    driver.get("https://eurodns.pxf.io/PzkDy6")
    human_delay(4, 6)
    take_screenshot(driver, "01_start")
    
    # Cookies
    print("[2/6] Cookies...")
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiescript_accept"]'))
        )
        driver.execute_script("arguments[0].click();", btn)
    except:
        pass
    human_delay(3, 5)
    
    # Account menu
    print("[3/6] Account menu...")
    btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="account-item-logout"]'))
    )
    driver.execute_script("arguments[0].click();", btn)
    human_delay(3, 5)
    
    # New Account
    print("[4/6] New Account...")
    btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="logout-user-section"]/a[2]'))
    )
    driver.execute_script("arguments[0].click();", btn)
    human_delay(5, 8)
    take_screenshot(driver, "04_form")
    
    # Fill form
    print("[5/6] Filling form...")
    email = create_temp_email()
    password = generate_strong_password()
    print(f"      Email: {email}")
    print(f"      Pass: {password}")
    
    # Email
    email_field = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
    )
    for char in email:
        email_field.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3))
    human_delay(2, 4)
    
    # Password
    pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    for char in password:
        pass_field.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3))
    human_delay(3, 5)
    
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
        btn = driver.find_element(By.XPATH, "//button[contains(., 'Create')]")
    except:
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    
    driver.execute_script("arguments[0].click();", btn)
    print("      Submitted, waiting 45s...")
    time.sleep(45)
    take_screenshot(driver, "06_after_submit")
    
    # Result
    url = driver.current_url
    print(f"\nFinal URL: {url}")
    
    with open("credentials.txt", "w") as f:
        f.write(f"Email: {email}\nPassword: {password}\nURL: {url}\n")
    print("Saved credentials.txt")

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
    print("\n[Done]")
