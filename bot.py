import os
import time
import uuid
import string
import random
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CAPSOLVER_API_KEY = "CAP-44CA8BA7E128FA814CCA3A5CB0517F65A1C36336E067E149BC7BBA84301F649E"  # <-- PUT YOUR KEY HERE

def solve_captcha_capsolver(site_key, page_url):
    """Use Capsolver to solve reCAPTCHA/hCaptcha"""
    print("      [Capsolver] Sending captcha for solving...")
    
    payload = {
        "clientKey": CAPSOLVER_API_KEY,
        "task": {
            "type": "ReCaptchaV2TaskProxyLess",
            "websiteKey": site_key,
            "websiteURL": page_url
        }
    }
    
    # Create task
    response = requests.post("https://api.capsolver.com/createTask", json=payload)
    result = response.json()
    
    if result.get("errorId") != 0:
        print(f"      [Capsolver] Error: {result}")
        return None
    
    task_id = result["taskId"]
    print(f"      [Capsolver] Task created: {task_id}")
    
    # Wait for solution
    for _ in range(30):  # Wait up to 60 seconds
        time.sleep(2)
        check = requests.post("https://api.capsolver.com/getTaskResult", 
                            json={"clientKey": CAPSOLVER_API_KEY, "taskId": task_id})
        check_result = check.json()
        
        if check_result.get("status") == "ready":
            token = check_result["solution"]["gRecaptchaResponse"]
            print("      [Capsolver] Solved!")
            return token
        
        if check_result.get("status") == "failed":
            print(f"      [Capsolver] Failed: {check_result}")
            return None
    
    return None

def inject_captcha_token(driver, token):
    """Inject the solved token into the page"""
    script = f"""
    document.getElementById('g-recaptcha-response').innerHTML='{token}';
    if(typeof grecaptcha !== 'undefined') {{
        grecaptcha.getResponse = function() {{ return '{token}'; }};
    }}
    """
    driver.execute_script(script)
    print("      [Inject] Token injected")

# Main bot code
profile_dir = "/tmp/chrome_profile_eurodns"
os.makedirs(profile_dir, exist_ok=True)

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument(f"--user-data-dir={profile_dir}")

driver = uc.Chrome(options=options, use_subprocess=True)
driver.set_window_size(1920, 1080)

try:
    print("[1/6] Loading EuroDNS...")
    driver.get("https://eurodns.pxf.io/PzkDy6")
    time.sleep(5)
    
    # Accept cookies
    try:
        btn = driver.find_element(By.XPATH, '//*[@id="cookiescript_accept"]')
        driver.execute_script("arguments[0].click();", btn)
    except:
        pass
    time.sleep(3)
    
    # Navigate to signup
    driver.find_element(By.XPATH, '//*[@id="account-item-logout"]').click()
    time.sleep(3)
    driver.find_element(By.XPATH, '//*[@id="logout-user-section"]/a[2]').click()
    time.sleep(5)
    
    # Check for captcha
    site_key = None
    try:
        captcha_frame = driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
        src = captcha_frame.get_attribute("src")
        # Extract site key from URL
        if "k=" in src:
            site_key = src.split("k=")[1].split("&")[0]
            print(f"      Found site_key: {site_key}")
    except:
        pass
    
    # Fill form
    email = f"user{uuid.uuid4().hex[:10]}@gmail.com"
    password = ''.join(random.choice(string.ascii_letters + string.digits + "!@#$%") for _ in range(16))
    print(f"      Email: {email}")
    
    driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys(email)
    time.sleep(2)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
    time.sleep(2)
    
    # Solve captcha if present
    if site_key:
        token = solve_captcha_capsolver(site_key, driver.current_url)
        if token:
            inject_captcha_token(driver, token)
            time.sleep(2)
    
    # Submit
    driver.find_element(By.XPATH, "//button[contains(., 'Create')]").click()
    print("      Submitted, waiting...")
    time.sleep(30)
    
    # Save results
    with open("credentials.txt", "w") as f:
        f.write(f"Email: {email}\nPassword: {password}\nURL: {driver.current_url}\n")
    print("Done!")

except Exception as e:
    print(f"Error: {e}")
    driver.save_screenshot("error.png")

finally:
    driver.quit()
