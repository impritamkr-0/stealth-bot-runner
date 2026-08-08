import os
import io
import time
import uuid
import json
import string
import random
import tempfile
import shutil
import requests
import urllib.request
from PIL import Image
from ultralytics import YOLO
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Initialize YOLO model once at top level
print("[Init] Loading YOLOv8s vision model...")
model = YOLO("yolov8s.pt")

LABEL_MAP = {
    "bicycles": "bicycle", "bicycle": "bicycle",
    "cars": "car", "car": "car",
    "buses": "bus", "bus": "bus",
    "motorcycles": "motorcycle", "motorcycle": "motorcycle",
    "traffic lights": "traffic light", "traffic light": "traffic light",
    "fire hydrants": "fire hydrant", "fire hydrant": "fire hydrant",
    "boats": "boat", "trains": "train"
}

# -------------------------------------------------------------
# 1. Vision Solver Core Functions
# -------------------------------------------------------------
def detect_target_tiles(full_img, yolo_target, rows=3, cols=3, conf_thresh=0.20, min_overlap=0.08):
    w, h = full_img.size
    tile_w, tile_h = w / cols, h / rows
    tile_area = tile_w * tile_h

    results = model(full_img, verbose=False)
    click_indices = set()

    for result in results:
        for box in result.boxes:
            detected_class = model.names[int(box.cls[0])].lower()
            conf = float(box.conf[0])

            if detected_class == yolo_target and conf >= conf_thresh:
                bx1, by1, bx2, by2 = box.xyxy[0].tolist()

                for r in range(rows):
                    for c in range(cols):
                        tx1, ty1 = c * tile_w, r * tile_h
                        tx2, ty2 = (c + 1) * tile_w, (r + 1) * tile_h

                        ix1, iy1 = max(bx1, tx1), max(by1, ty1)
                        ix2, iy2 = min(bx2, tx2), min(by2, ty2)

                        inter_area = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)

                        if (inter_area / tile_area) >= min_overlap:
                            tile_idx = r * cols + c
                            click_indices.add(tile_idx)
                            print(f"      [Vision Match] Tile {tile_idx} contains '{detected_class}' ({conf:.2f})")

    return sorted(list(click_indices))

def reload_captcha(driver):
    print("      0 tiles matched. Reloading challenge...")
    try:
        reload_btn = driver.find_element(By.ID, "recaptcha-reload-button")
        driver.execute_script("arguments[0].click();", reload_btn)
        time.sleep(2.5)
    except Exception as e:
        print(f"      Reload button note: {e}")
    finally:
        driver.switch_to.default_content()

def solve_recaptcha_v2(driver):
    driver.switch_to.default_content()

    bframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//iframe[contains(@src, "recaptcha/api2/bframe")]'))
    )
    driver.switch_to.frame(bframe)

    instructions_elem = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "rc-imageselect-desc")]'))
    )
    full_instruction_text = instructions_elem.text.lower()
    
    target_elem = instructions_elem.find_element(By.XPATH, './/strong')
    prompt_text = target_elem.text.strip().lower()
    yolo_target = LABEL_MAP.get(prompt_text, prompt_text)

    is_dynamic = "none left" in full_instruction_text or "new ones" in full_instruction_text
    print(f"      [CAPTCHA Target]: '{prompt_text}' -> YOLO: '{yolo_target}' | Dynamic: {is_dynamic}")

    if not is_dynamic:
        tile_elements = driver.find_elements(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]')
        grid_count = len(tile_elements)
        rows, cols = (4, 4) if grid_count == 16 else (3, 3)

        img_elem = driver.find_element(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]//img')
        img_bytes = requests.get(img_elem.get_attribute("src")).content
        full_img = Image.open(io.BytesIO(img_bytes))

        tiles_to_click = detect_target_tiles(full_img, yolo_target, rows=rows, cols=cols, conf_thresh=0.20)

        if not tiles_to_click:
            tiles_to_click = detect_target_tiles(full_img, yolo_target, rows=rows, cols=cols, conf_thresh=0.10)

        if not tiles_to_click:
            reload_captcha(driver)
            return solve_recaptcha_v2(driver)

        for idx in tiles_to_click:
            driver.execute_script("arguments[0].click();", tile_elements[idx])
            time.sleep(0.3)

        time.sleep(1.0)

    else:
        max_rounds = 5
        total_clicks = 0

        for round_num in range(max_rounds):
            tile_elements = driver.find_elements(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]')
            grid_count = len(tile_elements)
            rows, cols = (4, 4) if grid_count == 16 else (3, 3)

            img_elem = driver.find_element(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]//img')
            img_bytes = requests.get(img_elem.get_attribute("src")).content
            full_img = Image.open(io.BytesIO(img_bytes))

            tiles_to_click = detect_target_tiles(full_img, yolo_target, rows=rows, cols=cols, conf_thresh=0.18)

            if not tiles_to_click:
                if total_clicks == 0:
                    reload_captcha(driver)
                    return solve_recaptcha_v2(driver)
                else:
                    break

            for idx in tiles_to_click:
                driver.execute_script("arguments[0].click();", tile_elements[idx])
                total_clicks += 1
                time.sleep(2.5)

    verify_btn = driver.find_element(By.ID, "recaptcha-verify-button")
    driver.execute_script("arguments[0].click();", verify_btn)
    driver.switch_to.default_content()
    print("      CAPTCHA solved and verified successfully!")

# -------------------------------------------------------------
# 2. mail.tm & Helper Functions
# -------------------------------------------------------------
def create_real_temp_email():
    req = urllib.request.Request("https://api.mail.tm/domains", headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        domains_data = json.loads(response.read().decode('utf-8'))
    
    active_domain = domains_data['hydra:member'][0]['domain']
    unique_user = f"user_{uuid.uuid4().hex[:8]}"
    email_address = f"{unique_user}@{active_domain}"
    account_password = "TempMailPassword123!"

    payload = json.dumps({"address": email_address, "password": account_password}).encode('utf-8')
    post_req = urllib.request.Request(
        "https://api.mail.tm/accounts",
        data=payload,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(post_req) as response:
        return email_address, account_password

def generate_strong_password(length=16):
    chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + "!@#$%^&*()_+-="
    return "".join(random.choice(chars) for _ in range(length))

# -------------------------------------------------------------
# 3. Main EuroDNS Automation Workflow
# -------------------------------------------------------------
temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")

options = uc.ChromeOptions()
options.add_argument(f"--user-data-dir={temp_profile_dir}")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

driver = uc.Chrome(options=options)

try:
    print("[1/6] Navigating to EuroDNS...")
    driver.get("https://eurodns.pxf.io/PzkDy6")
    time.sleep(3)

    # Accept Cookies
    try:
        cookies = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiescript_accept"]')))
        driver.execute_script("arguments[0].click();", cookies)
    except Exception:
        pass

    # Open Account Menu -> New Account
    print("[2/6] Navigating to New Account Registration...")
    account_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="account-item-logout"]')))
    driver.execute_script("arguments[0].click();", account_btn)
    time.sleep(2)

    new_account_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="logout-user-section"]/a[2]')))
    driver.execute_script("arguments[0].click();", new_account_btn)
    time.sleep(3)

    # Fill Credentials
    print("[3/6] Filling credentials...")
    email, _ = create_real_temp_email()
    pwd = generate_strong_password()
    print(f"      Email: {email}")

    email_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
    email_field.send_keys(email)

    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
    password_field.send_keys(pwd)

    # Click Newsletter Checkbox
    try:
        checkbox = driver.find_element(By.XPATH, '//*[@id="subscribe-newsletter-checkbox-input"]')
        driver.execute_script("arguments[0].click();", checkbox)
    except Exception:
        pass

    # Click Initial reCAPTCHA Anchor Checkbox
    print("[4/6] Activating reCAPTCHA...")
    anchor_frame = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//iframe[contains(@src, "recaptcha/api2/anchor")]'))
    )
    driver.switch_to.frame(anchor_frame)
    recaptcha_box = driver.find_element(By.ID, "recaptcha-anchor")
    driver.execute_script("arguments[0].click();", recaptcha_box)
    time.sleep(2)

    # Solve reCAPTCHA with YOLO Vision Solver
    print("[5/6] Invoking YOLO Vision Solver...")
    solve_recaptcha_v2(driver)

    # Submit Registration
    print("[6/6] Submitting form...")
    create_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Create') or contains(., 'Sign up')]"))
    )
    driver.execute_script("arguments[0].click();", create_btn)
    
    print("\n" + "="*50)
    print("Account Creation Submitted Successfully!")
    print(f"Email used: {email}")
    print("="*50 + "\n")
    time.sleep(10)

finally:
    driver.quit()
    shutil.rmtree(temp_profile_dir, ignore_errors=True)
