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
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
import numpy as np

# --- Configuration ---
MAX_RECAPTCHA_ATTEMPTS = 3
YOLO_MODEL_PATH = "yolov8s.pt"
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
    "stairs", "palm tree", "palm trees", "mountain", "mountains", "statue",
    "zebra", "zebras", "horse", "horses", "cow", "cows", "sheep", "dogs", "cats"
]

def get_chrome_major_version():
    """
    Detects the EXACT installed Chrome major version.
    Returns an integer, e.g., 150.
    """
    chrome_cmds = [
        ["google-chrome-stable", "--version"],
        ["google-chrome", "--version"],
        ["chromium-browser", "--version"],
        ["chromium", "--version"]
    ]
    
    for cmd in chrome_cmds:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            output = result.stdout.strip()
            if not output:
                output = result.stderr.strip()
            
            # Regex to match "Google Chrome 150.0.7871.0" or "150.0.7871.0"
            match = re.search(r'(\d+)\.\d+\.\d+\.\d+', output)
            if match:
                version = int(match.group(1))
                print(f"[Init] Detected Chrome Version: {version}")
                return version
        except Exception:
            continue
            
    # Fallback if detection fails
    print("[Init] Chrome version detection failed, defaulting to 150")
    return 150

def build_chrome_options(profile_dir):
    """Generates a fresh ChromeOptions object per launch attempt."""
    opts = uc.ChromeOptions()
    opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--headless=new")
    opts.add_argument("--lang=en-US")
    opts.add_argument("--timezone=America/New_York")
    return opts

print("[Init] Loading YOLOv8s vision model...")
model = YOLO(YOLO_MODEL_PATH)

def detect_target_tiles_optimized(full_img, yolo_target, rows=3, cols=3):
    """
    Optimized detection:
    1. Crop each tile individually.
    2. Run YOLO on the crop.
    """
    w, h = full_img.size
    tile_w, tile_h = w / cols, h / rows
    click_indices = set()

    for r in range(rows):
        for c in range(cols):
            tile_idx = r * cols + c
            # Crop the specific tile
            left = int(c * tile_w)
            top = int(r * tile_h)
            right = int((c + 1) * tile_w)
            bottom = int((r + 1) * tile_h)
            
            tile_crop = full_img.crop((left, top, right, bottom))
            
            # Run YOLO on the crop with HIGHER confidence (0.35) to reduce false positives
            results = model(tile_crop, verbose=False, conf=0.35, iou=0.7)
            
            for result in results:
                for box in result.boxes:
                    detected_class = model.names[int(box.cls[0])].lower()
                    
                    if detected_class == yolo_target:
                        click_indices.add(tile_idx)
                        break # Found in this tile, move to next
    
    return sorted(list(click_indices))

def reload_captcha(driver):
    print(" [Reloading Captcha]")
    try:
        driver.execute_script("""
            var btn = document.getElementById('recaptcha-reload-button');
            if (btn) btn.click();
        """)
        time.sleep(1.5)
    except Exception as e:
        print(f" [Reload Error]: {e}")

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
        return False

def solve_recaptcha_v2(driver):
    for attempt in range(MAX_RECAPTCHA_ATTEMPTS):
        if is_recaptcha_solved(driver):
            print(" [SUCCESS] Captcha solved!")
            return True

        print(f" --- Captcha Attempt {attempt + 1}/{MAX_RECAPTCHA_ATTEMPTS} ---")
        
        try:
            driver.switch_to.default_content()
            bframe = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//iframe[contains(@src, "recaptcha/api2/bframe")]'))
            )
            driver.switch_to.frame(bframe)

            instructions_elem = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "rc-imageselect-desc")]'))
            )
            full_instruction_text = instructions_elem.text.lower()
            
            try:
                target_elem = instructions_elem.find_element(By.XPATH, './/strong')
                prompt_text = target_elem.text.strip().lower()
            except:
                prompt_text = full_instruction_text.split('select all squares with ')[1].split('.')[0]

            if any(unsupported in prompt_text for unsupported in UNSUPPORTED_PROMPTS):
                print(f" [SKIP] Unsupported prompt: '{prompt_text}'")
                reload_captcha(driver)
                continue

            yolo_target = LABEL_MAP.get(prompt_text, prompt_text)
            print(f" [Target]: '{prompt_text}' -> YOLO: '{yolo_target}'")

            tile_elements = driver.find_elements(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]')
            grid_count = len(tile_elements)
            rows, cols = (4, 4) if grid_count == 16 else (3, 3)

            full_grid_imgs = []
            for i in range(grid_count):
                try:
                    img_elem = driver.find_elements(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]//img')[i]
                    src = img_elem.get_attribute("src")
                    response = requests.get(src, timeout=5)
                    img = Image.open(io.BytesIO(response.content))
                    full_grid_imgs.append(img)
                except Exception as e:
                    print(f" [Img Load Error]: {e}")
                    break
            
            if not full_grid_imgs:
                reload_captcha(driver)
                continue

            sample_img = full_grid_imgs[0]
            tile_w, tile_h = sample_img.size
            
            full_grid_img = Image.new('RGB', (tile_w * cols, tile_h * rows))
            for r in range(rows):
                for c in range(cols):
                    idx = r * cols + c
                    if idx < len(full_grid_imgs):
                        full_grid_img.paste(full_grid_imgs[idx], (c * tile_w, r * tile_h))

            tiles_to_click = detect_target_tiles_optimized(full_grid_img, yolo_target, rows, cols)

            if not tiles_to_click:
                print(" [NO TILES FOUND] Reloading...")
                reload_captcha(driver)
                continue

            print(f" [CLICKING] Tiles: {tiles_to_click}")
            
            for idx in tiles_to_click:
                try:
                    current_tiles = driver.find_elements(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]')
                    if idx < len(current_tiles):
                        driver.execute_script("arguments[0].click();", current_tiles[idx])
                        time.sleep(0.2)
                except Exception as e:
                    print(f" [Click Error]: {e}")
                    break

            try:
                verify_btn = driver.find_element(By.ID, "recaptcha-verify-button")
                driver.execute_script("arguments[0].click();", verify_btn)
                time.sleep(2.0)
            except Exception:
                pass

            if is_recaptcha_solved(driver):
                return True
            else:
                print(" [FAILED] Reloading for next attempt...")
                reload_captcha(driver)

        except Exception as e:
            print(f" [Exception]: {e}")
            reload_captcha(driver)

    return False

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

# --- Main Execution ---
temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")

# Get the installed Chrome version
chrome_version = get_chrome_major_version()

driver = None
driver_error = None

# Try to launch with the detected version, then fallback to -1, -2, etc.
# This handles the case where Chrome is 150 but UC tries to grab 151
for version_offset in range(0, 5):
    try_version = chrome_version - version_offset
    if try_version < 100:
        break
        
    print(f"[Init] Attempting to launch ChromeDriver for Chrome version {try_version}")
    try:
        fresh_options = build_chrome_options(temp_profile_dir)
        # version_main forces UC to download/use the specific major version
        driver = uc.Chrome(options=fresh_options, version_main=try_version)
        print(f"[Init] Success! Driver initialized using version {try_version}")
        driver_error = None
        break
    except Exception as e:
        driver_error = e
        print(f"[Init] Failed for version {try_version}: {str(e)[:100]}...")
        # Clean up failed driver instance if any
        try:
            driver.quit()
        except:
            pass
        driver = None

if not driver:
    print(f"[Init] All version attempts failed. Last error: {driver_error}")
    raise Exception("Failed to initialize Chrome Driver")

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
    time.sleep(1.0)

    try:
        accept_cookies = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "cookiescript_accept"))
        )
        driver.execute_script("arguments[0].click();", accept_cookies)
    except Exception:
        pass

    my_account_btn = WebDriverWait(driver, 4).until(
        EC.presence_of_element_located((By.ID, "account-item-logout"))
    )
    driver.execute_script("arguments[0].click();", my_account_btn)

    new_account_btn = WebDriverWait(driver, 4).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a.btn.btn-secondary[href*='createNewAccount']"))
    )
    driver.execute_script("arguments[0].click();", new_account_btn)

    email, _ = create_real_temp_email()
    pwd = generate_strong_password(16)
    print(f" Generated Email: {email}")

    email_field = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[id*='email']"))
    )
    email_field.clear()
    email_field.send_keys(email)

    password_field = WebDriverWait(driver, 4).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[name='password'], input[id*='password']"))
    )
    password_field.clear()
    password_field.send_keys(pwd)

    try:
        checkbox = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "subscribe-newsletter-checkbox-input"))
        )
        driver.execute_script("arguments[0].click();", checkbox)
    except Exception:
        pass

    create_account_target = WebDriverWait(driver, 4).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "span.mat-mdc-button-touch-target, button[type='submit']"))
    )
    driver.execute_script("""
        var target = arguments[0];
        var button = target.tagName === 'BUTTON' ? target : target.closest('button');
        if (button) { button.click(); } else { target.click(); }
    """, create_account_target)
    time.sleep(1.5)

    # Solve CAPTCHA
    solve_recaptcha_v2(driver)

    # Trigger final submit
    try:
        remaining_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button.mat-mdc-raised-button")
        for btn in remaining_btns:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                break
    except Exception:
        pass

    # Wait 12 seconds for registration processing and redirect
    print("\nWaiting 12 seconds for account creation and redirect...")
    time.sleep(12.0)

    # Fetch and log current landed URL
    try:
        landed_url = driver.current_url
        print(f"Landed URL: {landed_url}")
    except Exception as e:
        print(f"Landed URL retrieval note: {e}")

    print("\n" + "="*50)
    print("Registration Workflow Completed Successfully!")
    print(f"Email used: {email}")
    print("="*50 + "\n")

finally:
    try:
        driver.quit()
    except Exception:
        pass
    shutil.rmtree(temp_profile_dir, ignore_errors=True)
    print("[Clean exit] Chrome closed.")
