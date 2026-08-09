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
from selenium.common.exceptions import (
    NoSuchElementException, 
    TimeoutException, 
    StaleElementReferenceException,
    SessionNotCreatedException
)

def get_chrome_major_version():
    """Detects installed Google Chrome major version via shell commands."""
    for cmd in ["google-chrome --version", "google-chrome-stable --version", "chromium-browser --version", "chromium --version"]:
        try:
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
            match = re.search(r"(\d+)\.\d+\.\d+\.\d+", output)
            if match:
                return int(match.group(1))
        except Exception:
            pass
    return None

def build_chrome_options(profile_dir):
    """Generates an isolated ChromeOptions object per launch attempt."""
    opts = uc.ChromeOptions()
    opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    return opts

def safe_js_click(driver, by_type, selector, timeout=12):
    """Dynamic retry click helper resilient to Angular re-renders and stale elements."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            elem = driver.find_element(by_type, selector)
            driver.execute_script("arguments[0].click();", elem)
            return True
        except (NoSuchElementException, StaleElementReferenceException):
            time.sleep(0.4)
        except Exception:
            time.sleep(0.4)
    return False

def switch_to_latest_tab(driver):
    """Switches driver context if EuroDNS opens registration in a new window/tab."""
    try:
        handles = driver.window_handles
        if len(handles) > 1:
            driver.switch_to.window(handles[-1])
            print("      [Tab Control] Switched to newly opened browser tab.")
    except Exception as e:
        print(f"      Tab switch note: {e}")

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

def detect_target_tiles_hybrid(full_img, yolo_target, rows=3, cols=3):
    w, h = full_img.size
    tile_w, tile_h = w / cols, h / rows
    tile_area = tile_w * tile_h
    click_indices = set()

    # Pass 1: Full Canvas Detection
    results_full = model(full_img, verbose=False, conf=0.10)
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

                        if (inter_area / tile_area) >= 0.02:
                            tile_idx = r * cols + c
                            click_indices.add(tile_idx)
                            print(f"      [Canvas Match] Tile {tile_idx} -> '{detected_class}' ({conf:.2f})")

    # Pass 2: Individual Tile Crop Detection
    for r in range(rows):
        for c in range(cols):
            tile_idx = r * cols + c
            box = (int(c * tile_w), int(r * tile_h), int((c + 1) * tile_w), int((r + 1) * tile_h))
            tile_crop = full_img.crop(box)

            tile_results = model(tile_crop, verbose=False, conf=0.10)
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
        time.sleep(1.0)
    except Exception:
        pass
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

def solve_recaptcha_v2(driver, max_attempts=3):
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
            time.sleep(0.5)
            continue

        full_instruction_text = instructions_elem.text.lower()
        target_elem = instructions_elem.find_element(By.XPATH, './/strong')
        prompt_text = target_elem.text.strip().lower()

        if any(unsupported in prompt_text for unsupported in UNSUPPORTED_PROMPTS):
            print(f"      [Instant Skip] '{prompt_text}' unsupported prompt. Reloading...")
            reload_captcha(driver)
            time.sleep(1.0)
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
                time.sleep(1.0)
                continue

            print(f"      Static Mode: Clicking tiles -> {tiles_to_click}")
            for idx in tiles_to_click:
                try:
                    driver.execute_script("arguments[0].click();", tile_elements[idx])
                    time.sleep(0.15)
                except Exception:
                    break

            time.sleep(0.3)

        else:
            max_dynamic_rounds = 3
            total_clicks = 0

            for d_round in range(max_dynamic_rounds):
                tile_elements = driver.find_elements(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]')
                grid_count = len(tile_elements)
                rows, cols = (4, 4) if grid_count == 16 else (3, 3)

                img_elem = driver.find_element(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]//img')
                img_bytes = requests.get(img_elem.get_attribute("src")).content
                full_img = Image.open(io.BytesIO(img_bytes))

                tiles_to_click = detect_target_tiles_hybrid(full_img, yolo_target, rows=rows, cols=cols)

                if not tiles_to_click:
                    if total_clicks == 0:
                        reload_captcha(driver)
                        break
                    else:
                        break

                print(f"      Dynamic Sub-Round {d_round + 1}: Clicking -> {tiles_to_click}")
                for idx in tiles_to_click:
                    try:
                        driver.execute_script("arguments[0].click();", tile_elements[idx])
                        total_clicks += 1
                        time.sleep(1.2)
                    except Exception:
                        break

        try:
            verify_btn = driver.find_element(By.ID, "recaptcha-verify-button")
            driver.execute_script("arguments[0].click();", verify_btn)
            print("      [Verify Clicked]")
        except Exception as e:
            print(f"      Verify click note: {e}")

        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        time.sleep(1.5)

    return is_recaptcha_solved(driver)

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
    chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + "!@#$%^&*()"
    return "".join(random.choice(chars) for _ in range(length))

temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")
installed_chrome_version = get_chrome_major_version()

# Purge undetected_chromedriver cache directory to clear stale binary locks
uc_cache = os.path.expanduser("~/.local/share/undetected_chromedriver")
shutil.rmtree(uc_cache, ignore_errors=True)

driver = None
version_candidates = [installed_chrome_version, 150, 151, None]

for ver in version_candidates:
    try:
        shutil.rmtree(uc_cache, ignore_errors=True)
        fresh_options = build_chrome_options(temp_profile_dir)
        if ver:
            driver = uc.Chrome(options=fresh_options, version_main=ver)
        else:
            driver = uc.Chrome(options=fresh_options)
        print(f"[Init] Driver initialized using version_main={ver}")
        break
    except Exception as e:
        print(f"[Init] Launch attempt failed for version {ver}: {e}")

if not driver:
    shutil.rmtree(uc_cache, ignore_errors=True)
    fresh_options = build_chrome_options(temp_profile_dir)
    driver = uc.Chrome(options=fresh_options)

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
    time.sleep(2.0)

    try:
        safe_js_click(driver, By.ID, "cookiescript_accept", timeout=5)
    except Exception:
        pass

    print("[2/6] Clicking 'My account'...")
    safe_js_click(driver, By.ID, "account-item-logout", timeout=10)
    time.sleep(1.5)

    print("[3/6] Clicking 'New account'...")
    safe_js_click(driver, By.CSS_SELECTOR, "a.btn.btn-secondary[href*='createNewAccount']", timeout=12)
    time.sleep(2.5)

    # Context switch check if EuroDNS loaded the form in a new tab
    switch_to_latest_tab(driver)

    email, _ = create_real_temp_email()
    pwd = generate_strong_password(16)
    print(f"      Generated Email:    {email}")

    print("[4/6] Filling email & password fields...")
    # Resilient XPath queries matching any variations of EuroDNS form input attributes
    email_xpath = "//input[@type='email' or @name='email' or contains(@id, 'email') or contains(@placeholder, 'email')]"
    password_xpath = "//input[@type='password' or @name='password' or contains(@id, 'password') or contains(@placeholder, 'password')]"

    email_field = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, email_xpath))
    )
    email_field.clear()
    email_field.send_keys(email)

    password_field = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, password_xpath))
    )
    password_field.clear()
    password_field.send_keys(pwd)

    print("[5/6] Subscribing to newsletter...")
    try:
        safe_js_click(driver, By.ID, "subscribe-newsletter-checkbox-input", timeout=5)
    except Exception:
        pass

    print("[6/6] Triggering reCAPTCHA popup...")
    safe_js_click(driver, By.CSS_SELECTOR, "span.mat-mdc-button-touch-target, button[type='submit']", timeout=8)
    time.sleep(2.0)

    # Execute CAPTCHA solver
    solve_recaptcha_v2(driver, max_attempts=3)

    # Form submission
    print("\n[Form Submission] Triggering final EuroDNS registration submit button...")
    try:
        remaining_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button.mat-mdc-raised-button")
        for btn in remaining_btns:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                break
    except Exception as e:
        print(f"      Post-CAPTCHA submit note: {e}")

    # Poll URL for dashboard redirect
    redirected = False
    for _ in range(10):
        time.sleep(1.0)
        current_url = driver.current_url
        if "createNewAccount" not in current_url:
            redirected = True
            print(f"      Redirected to: {current_url}")
            break

    final_url = driver.current_url
    print(f"\nFinal Landed URL: {final_url}")

    print("\n" + "="*50)
    print("Registration Workflow Completed!")
    print(f"Email used: {email}")
    print(f"Landed URL: {final_url}")
    print("="*50 + "\n")

finally:
    try:
        driver.quit()
    except Exception:
        pass
    shutil.rmtree(temp_profile_dir, ignore_errors=True)
    print("[Clean exit] Chrome closed.")
