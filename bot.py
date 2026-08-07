import os
import sys
import time
import uuid
import string
import random
import tempfile
import shutil
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = "."
BUSTER_PATH = "./buster.crx"

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

def check_for_captcha(driver):
    """Check if captcha is present on page"""
    captcha_indicators = [
        "//iframe[contains(@src, 'recaptcha')]",
        "//iframe[contains(@src, 'hcaptcha')]",
        "//div[@class='g-recaptcha']",
        "//div[contains(@class, 'captcha')]",
        "//input[@id='g-recaptcha-response']",
        "//textarea[@id='g-recaptcha-response']"
    ]
    
    for indicator in captcha_indicators:
        try:
            elements = driver.find_elements(By.XPATH, indicator)
            if elements and len(elements) > 0:
                return True
        except:
            continue
    return False

def solve_with_buster(driver):
    """Use Buster extension to solve captcha"""
    print("      [Buster] Attempting to solve captcha...")
    
    try:
        # Look for the audio challenge button (Buster clicks this)
        # First check if we're on a reCAPTCHA iframe
        iframes = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
        
        if len(iframes) > 0:
            print("      [Buster] Found reCAPTCHA iframe")
            # Switch to recaptcha iframe
            driver.switch_to.frame(iframes[0])
            
            # Click the audio challenge button
            try:
                audio_btn = driver.find_element(By.XPATH, "//button[@id='recaptcha-audio-button']")
                audio_btn.click()
                print("      [Buster] Clicked audio button")
                time.sleep(3)
            except:
                pass
            
            # Switch back to main
            driver.switch_to.default_content()
        
        # Wait for Buster to solve (it auto-clicks when ready)
        print("      [Buster] Waiting 20s for solve...")
        time.sleep(20)
        
        # Check if solved
        if not check_for_captcha(driver):
            print("      [Buster] Captcha appears solved!")
            return True
        else:
            print("      [Buster] Still present, may need more time")
            time.sleep(15)
            return not check_for_captcha(driver)
            
    except Exception as e:
        print(f"      [Buster] Error: {e}")
        return False

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
options.add_argument("--disable-site-isolation-trials")
options.add_argument("--disable-features=InterestFeedContentSuggestions")
options.add_argument("--disable-features=TranslateUI")
options.add_argument("--disable-features=PrivacySandboxSettings")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0")

options.add_argument(f"--user-data-dir={profile_dir}")
options.add_argument("--window-size=1920,1080")

# Load Buster extension
if os.path.exists(BUSTER_PATH):
    print("[Setup] Loading Buster extension...")
    options.add_extension(BUSTER_PATH)
else:
    print("[WARNING] Buster not found!")

driver = None

try:
    print("[Setup] Starting Chrome...")
    driver = uc.Chrome(options=options, use_subprocess=True)
    print("[Setup] Chrome started")
    human_delay(2, 4)
    
    # Navigate
    print("\n[1/7] Loading EuroDNS...")
    driver.get("https://eurodns.pxf.io/PzkDy6")
    human_delay(4, 6)
    take_screenshot(driver, "01_start")
    
    # Check if captcha appears immediately
    if check_for_captcha(driver):
        print("[ALERT] Captcha detected on landing page!")
        solve_with_buster(driver)
    
    # Cookies
    print("[2/7] Accepting cookies...")
    try:
        btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiescript_accept"]'))
        )
        human_delay(1, 2)
        driver.execute_script("arguments[0].click();", btn)
    except:
        pass
    human_delay(3, 5)
    
    # Account menu
    print("[3/7] Opening account menu...")
    btn = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="account-item-logout"]'))
    )
    human_delay(1, 3)
    driver.execute_script("arguments[0].click();", btn)
    human_delay(3, 5)
    
    # New Account
    print("[4/7] Clicking New Account...")
    btn = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="logout-user-section"]/a[2]'))
    )
    human_delay(2, 4)
    driver.execute_script("arguments[0].click();", btn)
    human_delay(5, 8)
    take_screenshot(driver, "04_form")
    
    # Check for captcha on form
    if check_for_captcha(driver):
        print("[ALERT] Captcha on form!")
        solve_with_buster(driver)
    
    # Generate credentials
    print("[5/7] Filling form...")
    email = create_temp_email()
    password = generate_strong_password()
    print(f"      Email: {email}")
    print(f"      Pass: {password}")
    
    # Fill email
    email_field = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
    )
    email_field.click()
    human_delay(0.5, 1)
    for char in email:
        email_field.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3))
    human_delay(2, 4)
    
    # Fill password
    pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pass_field.click()
    human_delay(0.5, 1)
    for char in password:
        pass_field.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3))
    human_delay(3, 5)
    
    # Uncheck newsletter
    try:
        cb = driver.find_element(By.XPATH, '//*[@id="subscribe-newsletter-checkbox-input"]')
        driver.execute_script("arguments[0].scrollIntoView(true);", cb)
        human_delay(1, 2)
        driver.execute_script("arguments[0].click();", cb)
    except:
        pass
    take_screenshot(driver, "05_filled")
    
    # Submit
    print("[6/7] Submitting...")
    create_btn = None
    
    selectors = [
        "//button[contains(., 'Create Account')]",
        "//button[contains(., 'Create')]",
        "//edns-new-account//button",
        "/html/body/edns-root/edns-layout/div/div/edns-side-panels/mat-sidenav-container/mat-sidenav-content/div/div[2]/edns-new-account/div/div/form/div[4]/button"
    ]
    
    for selector in selectors:
        try:
            create_btn = driver.find_element(By.XPATH, selector)
            print(f"      Found button: {selector}")
            break
        except:
            continue
    
    if not create_btn:
        form = driver.find_element(By.TAG_NAME, "form")
        create_btn = form.find_element(By.TAG_NAME, "button")
    
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", create_btn)
    human_delay(2, 4)
    driver.execute_script("arguments[0].click();", create_btn)
    print("      Submitted")
    
    # Wait and check for captcha
    print("[7/7] Checking for captcha...")
    time.sleep(5)
    take_screenshot(driver, "07_after_submit")
    
    if check_for_captcha(driver):
        print("[ALERT] Captcha appeared after submit!")
        solved = solve_with_buster(driver)
        if solved:
            print("      [OK] Captcha solved!")
        else:
            print("      [WARN] Buster may have failed")
        time.sleep(10)
    
    # Final check
    time.sleep(5)
    take_screenshot(driver, "08_final")
    
    url = driver.current_url
    print(f"\nFinal URL: {url}")
    
    success = "success" in url.lower() or "welcome" in url.lower() or "dashboard" in url.lower() or not check_for_captcha(driver)
    
    with open("credentials.txt", "w") as f:
        f.write(f"Email: {email}\nPassword: {password}\nSuccess: {success}\nURL: {url}\n")
    print(f"Success: {success}")

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
    print("\n[Done]")
