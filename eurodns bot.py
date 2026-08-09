import os
import io
import re
import time
import uuid
import json
import string
import random
import tempfile
import shutil
import requests
import subprocess
import urllib.request
from PIL import Image
from ultralytics import YOLO
import undetected_chromedriver as uc
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException

def get_chrome_major_version():
    """Detects the exact installed Google Chrome major version."""
    for cmd in ["google-chrome --version", "google-chrome-stable --version", "chromium-browser --version", "chromium --version"]:
        try:
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
            print(f"[Init] Executed '{cmd}': {output.strip()}")
            match = re.search(r"(\d+)\.\d+\.\d+\.\d+", output)
            if match:
                version = int(match.group(1))
                return version
        except Exception:
            pass

    try:
        output = subprocess.check_output(
            r'wmic datafile where name="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" get Version /value',
            shell=True
        ).decode('utf-8')
        match = re.search(r"Version=(\d+)\.", output)
        if match:
            return int(match.group(1))
    except Exception:
        pass

    return None

print("[Init] Loading YOLOv8s vision model...")
model = YOLO("yolov8s.pt")

LABEL_MAP = {
    "bicycles": "bicycle", "bicycle": "bicycle", "a bicycle": "bicycle",
    "cars": "car", "car": "car", "vehicles": "car", "a car": "car",
    "buses": "bus", "bus": "bus", "a bus": "bus",
    "motorcycles": "motorcycle", "motorcycle": "motorcycle",
    "traffic lights": "traffic light", "traffic light": "traffic light", "a traffic light": "traffic light",
    "fire hydrants": "fire hydrant", "fire hydrant": "fire hydrant", "a fire hydrant": "fire hydrant",
    "boats": "boat", "boat": "boat", "trains": "train"
}

UNSUPPORTED_PROMPTS = [
    "crosswalk", "crosswalks", "bridge", "bridges", "chimney", "chimneys",
    "stairs", "palm tree", "palm trees", "mountain", "mountains", "statue"
]

# -------------------------------------------------------------
# 1. High-Speed Vision Solver Core Functions
# -------------------------------------------------------------
def detect_target_tiles_hybrid(full_img, yolo_target, rows=3, cols=3):
    w, h = full_img.size
    tile_w, tile_h = w / cols, h / rows
    tile_area = tile_w * tile_h
    click_indices = set()

    # Pass 1: Full Canvas Detection
    results_full = model(full_img, verbose=False, conf=0.15)
    for result in results_full:
        for box in result.boxes:
            detected_class = model.names[int(box.cls[0])].lower()
            conf = float(box.conf[0])

            if detected_class == yolo_target:
                bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                for r in range(rows):
                    for c in range(cols):
                        tx1, ty1 = c * tile_w, r * tile_h
                        tx2, ty2 = (c + 1) * tile_w, (r + 1) * tile_h

                        inter_w = max(0.0, min(bx2, tx2) - max(bx1, tx1))
                        inter_h = max(0.0, min(by2, ty2) - max(by1, ty1))
                        inter_area = inter_w * inter_h

                        if (inter_area / tile_area) >= 0.08:
                            tile_idx = r * cols + c
                            click_indices.add(tile_idx)
                            print(f"      [Canvas Match] Tile {tile_idx} -> '{detected_class}' ({conf:.2f})")

    if click_indices:
        return sorted(list(click_indices))

    # Pass 2: Fallback Crop Pass
    for r in range(rows):
        for c in range(cols):
            tile_idx = r * cols + c
            box = (int(c * tile_w), int(r * tile_h), int((c + 1) * tile_w), int((r + 1) * tile_h))
            tile_crop = full_img.crop(box)

            tile_results = model(tile_crop, verbose=False, conf=0.12)
            for result in tile_results:
                for box in result.boxes:
                    detected_class = model.names[int(box.cls[0])].lower()
                    conf = float(box.conf[0])

                    if detected_class == yolo_target:
                        click_indices.add(tile_idx)
                        print(f"      [Tile Crop Match] Tile {tile_idx} -> '{detected_class}' ({conf:.2f})")

    return sorted(list(click_indices))

def reload_captcha(driver):
    print("      Reloading challenge for a recognizable prompt...")
    try:
        reload_btn = driver.find_element(By.ID, "recaptcha-reload-button")
        driver.execute_script("arguments[0].click();", reload_btn)
        time.sleep(1.5)
    except Exception as e:
        print(f"      Reload button interaction note: {e}")
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

def is_recaptcha_solved(driver):
    try:
        driver.switch_to.default_content()
        anchor_frame = driver.find_element(By.XPATH, '//iframe[contains(@src, "recaptcha/api2/anchor")]')
        driver.switch_to.frame(anchor_frame)
        checkbox = driver.find_element(By.ID, "recaptcha-anchor")
        checked = checkbox.get_attribute("aria-checked")
        driver.switch_to.default_content()
        return checked == "true"
    except Exception:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        return False

def solve_recaptcha_v2(driver, max_attempts=8):
    for attempt in range(max_attempts):
        if is_recaptcha_solved(driver):
            print("      [reCAPTCHA] Green checkmark verified!")
            return True

        try:
            driver.switch_to.default_content()
        except Exception:
            pass

        print(f"\n      --- CAPTCHA Solving Round {attempt + 1}/{max_attempts} ---")

        try:
            bframe = WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.XPATH, '//iframe[contains(@src, "recaptcha/api2/bframe")]'))
            )
            driver.switch_to.frame(bframe)

            instructions_elem = WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "rc-imageselect-desc")]'))
            )
        except (TimeoutException, NoSuchElementException):
            if is_recaptcha_solved(driver):
                return True
            time.sleep(1.0)
            continue

        full_instruction_text = instructions_elem.text.lower()
        target_elem = instructions_elem.find_element(By.XPATH, './/strong')
        prompt_text = target_elem.text.strip().lower()

        if any(unsupported in prompt_text for unsupported in UNSUPPORTED_PROMPTS):
            print(f"      [Instant Skip] '{prompt_text}' is not in standard YOLO COCO dataset. Reloading...")
            reload_captcha(driver)
            time.sleep(1.5)
            continue

        yolo_target = LABEL_MAP.get(prompt_text, prompt_text)
        is_dynamic = "none left" in full_instruction_text or "new ones" in full_instruction_text
        print(f"      [Prompt]: '{prompt_text}' -> YOLO: '{yolo_target}' | Dynamic: {is_dynamic}")

        if not is_dynamic:
            tile_elements = driver.find_elements(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]')
            grid_count = len(tile_elements)
            rows, cols = (4, 4) if grid_count == 16 else (3, 3)

            img_elem = driver.find_element(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]//img')
            img_bytes = requests.get(img_elem.get_attribute("src")).content
            full_img = Image.open(io.BytesIO(img_bytes))

            tiles_to_click = detect_target_tiles_hybrid(full_img, yolo_target, rows=rows, cols=cols)

            if not tiles_to_click:
                reload_captcha(driver)
                time.sleep(1.5)
                continue

            print(f"      Static Mode: Clicking tiles -> {tiles_to_click}")
            for idx in tiles_to_click:
                try:
                    driver.execute_script("arguments[0].click();", tile_elements[idx])
                    time.sleep(0.15)
                except (NoSuchElementException, StaleElementReferenceException):
                    break

            time.sleep(0.5)

        else:
            max_dynamic_rounds = 4
            total_clicks = 0
            previous_click_set = None

            for d_round in range(max_dynamic_rounds):
                tile_elements = driver.find_elements(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]')
                grid_count = len(tile_elements)
                rows, cols = (4, 4) if grid_count == 16 else (3, 3)

                img_elem = driver.find_element(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]//img')
                img_bytes = requests.get(img_elem.get_attribute("src")).content
                full_img = Image.open(io.BytesIO(img_bytes))

                tiles_to_click = detect_target_tiles_hybrid(full_img, yolo_target, rows=rows, cols=cols)

                if tiles_to_click == previous_click_set and len(tiles_to_click) == 1 and d_round >= 2:
                    print("      [Stuck Tile Detected] Challenge is looping on a single tile. Reloading...")
                    reload_captcha(driver)
                    break

                previous_click_set = tiles_to_click

                if not tiles_to_click:
                    if total_clicks == 0:
                        reload_captcha(driver)
                        break
                    else:
                        print(f"      No remaining '{yolo_target}' tiles found.")
                        break

                print(f"      Dynamic Sub-Round {d_round + 1}: Clicking -> {tiles_to_click}")
                for idx in tiles_to_click:
                    try:
                        driver.execute_script("arguments[0].click();", tile_elements[idx])
                        total_clicks += 1
                        time.sleep(1.8)
                    except (NoSuchElementException, StaleElementReferenceException):
                        break

        try:
            verify_btn = driver.find_element(By.ID, "recaptcha-verify-button")
            driver.execute_script("arguments[0].click();", verify_btn)
        except Exception:
            pass

        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        time.sleep(1.5)

    return is_recaptcha_solved(driver)

# -------------------------------------------------------------
# 2. Mail & Compliant Password Generation
# -------------------------------------------------------------
def create_real_temp_email():
    req = urllib.request.Request("https://api.mail.tm/domains", headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        domains_data = json.loads(response.read().decode('utf-8'))
    
    active_domain = domains_data['hydra:member'][0]['domain']
    unique_user = f"user_{uuid.uuid4().hex[:8]}"
    email_address = f"{unique_user}@{active_domain}"
    account_password = generate_strong_password(16)

    payload = json.dumps({"address": email_address, "password": account_password}).encode('utf-8')
    post_req = urllib.request.Request(
        "https://api.mail.tm/accounts",
        data=payload,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(post_req) as response:
        return email_address, account_password

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
# 3. Main Registration Automation Workflow
# -------------------------------------------------------------
temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")

options = uc.ChromeOptions()
options.add_argument(f"--user-data-dir={temp_profile_dir}")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")

installed_chrome_version = get_chrome_major_version()

# Resilient Driver Launch Retry Loop
driver = None
version_candidates = [installed_chrome_version, 150, 151, None]
for ver in version_candidates:
    try:
        print(f"[Init] Launching Chrome driver with version_main={ver}...")
        driver = uc.Chrome(options=options, version_main=ver)
        print(f"[Init] Success! Chrome initialized using version_main={ver}")
        break
    except Exception as e:
        print(f"[Init] Driver launch failed with version_main={ver}: {e}")

if not driver:
    raise RuntimeError("Failed to launch Chrome driver under all candidate versions.")

stealth(
    driver,
    languages=["en-US", "en"],
    vendor="Google Inc.",
    platform="Win32",
    webgl_vendor="Intel Inc.",
    renderer="Intel(R) UHD Graphics 620",
    fix_hairline=True,
)

try:
    print("[1/6] Visiting EuroDNS...")
    driver.get("https://eurodns.pxf.io/PzkDy6")
    time.sleep(1.5)

    try:
        accept_cookies = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "cookiescript_accept"))
        )
        driver.execute_script("arguments[0].click();", accept_cookies)
        print("      Cookies accepted.")
    except Exception as e:
        print(f"      Cookie banner note: {e}")

    time.sleep(1.0)
    print("[2/6] Clicking 'My account'...")

    my_account_btn = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.ID, "account-item-logout"))
    )
    driver.execute_script("arguments[0].click();", my_account_btn)

    print("[3/6] Clicking 'New account' button...")
    new_account_btn = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a.btn.btn-secondary[href*='createNewAccount']"))
    )
    driver.execute_script("arguments[0].click();", new_account_btn)

    time.sleep(1.5)
    print("[4/6] Filling credentials...")

    email, _ = create_real_temp_email()
    pwd = generate_strong_password(16)
    print(f"      Generated Email:    {email}")
    print(f"      Generated Password: {pwd}")

    email_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[id*='email']"))
    )
    email_field.clear()
    email_field.send_keys(email)

    password_field = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[name='password'], input[id*='password']"))
    )
    password_field.clear()
    password_field.send_keys(pwd)

    print("[5/6] Checking newsletter checkbox...")
    try:
        checkbox = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "subscribe-newsletter-checkbox-input"))
        )
        driver.execute_script("arguments[0].click();", checkbox)
    except Exception as e:
        print(f"      Checkbox note: {e}")

    print("[6/6] Triggering CAPTCHA popup...")
    create_account_target = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "span.mat-mdc-button-touch-target, button[type='submit']"))
    )
    driver.execute_script("""
        var target = arguments[0];
        var button = target.tagName === 'BUTTON' ? target : target.closest('button');
        if (button) { button.click(); } else { target.click(); }
    """, create_account_target)
    time.sleep(2.0)

    print("[7/7] Invoking reCAPTCHA solver...")
    is_solved = solve_recaptcha_v2(driver, max_attempts=8)

    if is_solved:
        print("\n[reCAPTCHA Verified] Submitting registration form...")
        try:
            remaining_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button.mat-mdc-raised-button")
            for btn in remaining_btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    break
        except Exception as e:
            print(f"      Post-CAPTCHA submission note: {e}")

        time.sleep(3.0)

        print("\n" + "="*50)
        print("Registration Workflow Completed Successfully!")
        print(f"Email used: {email}")
        print("="*50 + "\n")
    else:
        print("\n[Error] reCAPTCHA challenge was not solved.")
        raise RuntimeError("Registration aborted: reCAPTCHA verification failed.")

finally:
    try:
        driver.quit()
    except Exception:
        pass
    shutil.rmtree(temp_profile_dir, ignore_errors=True)
    print("[Clean exit] Chrome closed and temporary profiles cleared.")
