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
from PIL import Image

# Optional vision model - ultralytics YOLOv8 (best-effort)
try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

import undetected_chromedriver as uc
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException

# ==================== CONFIG / FINGERPRINTS ====================
BROWSER_PROFILES = [
    {
        "vendor": "Google Inc.",
        "renderer": "Intel(R) UHD Graphics 620",
        "platform": "Win32",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    },
    {
        "vendor": "NVIDIA",
        "renderer": "ANGLE (NVIDIA GeForce GTX 1080)",
        "platform": "Win32",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    },
    {
        "vendor": "Intel Inc.",
        "renderer": "Intel Iris OpenGL Engine",
        "platform": "MacIntel",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    },
    {
        "vendor": "Google Inc.",
        "renderer": "ANGLE (AMD Radeon RX 580 Series)",
        "platform": "Win32",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    },
    {
        "vendor": "Google Inc.",
        "renderer": "Mesa Intel(R) UHD Graphics",
        "platform": "Linux x86_64",
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8,en-US;q=0.7",
    "en-US,en;q=0.95",
    "en;q=0.9,en-US;q=0.8"
]

MAILTM_BASE = "https://api.mail.tm"

# ==================== UTILITIES ====================

def get_chrome_major_version():
    """Detects installed Chrome major version (best effort)."""
    for cmd in [
        "google-chrome --version",
        "google-chrome-stable --version",
        "chromium-browser --version",
        "chromium --version",
    ]:
        try:
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode("utf-8")
            match = re.search(r"(\d+)\.\d+\.\d+\.\d+", output)
            if match:
                return int(match.group(1))
        except Exception:
            pass
    return None


def human_like_sleep(min_ms=100, max_ms=500):
    """Random human-like delay in seconds."""
    delay = random.uniform(min_ms / 1000.0, max_ms / 1000.0)
    time.sleep(delay)


def get_random_headers():
    """Generate plausible browser headers for HTTP requests."""
    return {
        "User-Agent": random.choice([p["user_agent"] for p in BROWSER_PROFILES]),
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Referer": "https://www.google.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "DNT": "1",
    }


def build_chrome_options(profile_dir):
    opts = uc.ChromeOptions()
    profile = random.choice(BROWSER_PROFILES)

    opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-popup-blocking")
    opts.add_argument("--start-maximized")
    opts.add_argument(f"user-agent={profile['user_agent']}")

    return opts, profile


def human_click(driver, element):
    try:
        actions = ActionChains(driver)
        offset_x = random.randint(-8, 8)
        offset_y = random.randint(-8, 8)
        actions.move_to_element_with_offset(element, offset_x, offset_y)
        human_like_sleep(50, 150)
        actions.click()
        actions.perform()
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
        except Exception:
            pass


def generate_strong_password(length=16):
    chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + "!@#$%^&*()"
    return "".join(random.choice(chars) for _ in range(length))

# ==================== OPTIONAL YOLO MODEL ====================
model = None
if YOLO is not None:
    try:
        # attempt to load a local model file if present, otherwise skip
        model_path = os.path.join(os.path.dirname(__file__), "yolov8m.pt")
        if os.path.exists(model_path):
            model = YOLO(model_path)
            print("[Init] Loaded YOLO model from yolov8m.pt")
        else:
            # try default model name (may attempt to download or fail)
            try:
                model = YOLO("yolov8m.pt")
                print("[Init] Loaded YOLO model via name 'yolov8m.pt'")
            except Exception:
                print("[Init] YOLO model not available; falling back to non-vision detection")
                model = None
    except Exception:
        model = None
else:
    print("[Init] ultralytics not installed; vision features disabled")

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

# ==================== CAPTCHA DETECTION HELPERS ====================

def detect_by_color_similarity(full_img, rows=3, cols=3):
    try:
        import numpy as np
    except Exception:
        return []

    img_array = np.array(full_img)
    w, h = full_img.size
    tile_w, tile_h = w / cols, h / rows

    click_indices = []
    for r in range(rows):
        for c in range(cols):
            tile_idx = r * cols + c
            tile = img_array[int(r * tile_h):int((r + 1) * tile_h), int(c * tile_w):int((c + 1) * tile_w)]
            if tile.size == 0:
                continue
            if np.std(tile) > 10:
                click_indices.append(tile_idx)
    return click_indices


def detect_target_tiles_hybrid(full_img, yolo_target, rows=3, cols=3, conf_threshold=0.25):
    w, h = full_img.size
    tile_w, tile_h = w / cols, h / rows
    tile_area = tile_w * tile_h
    click_indices = set()
    confidence_scores = []

    # If vision model is available, try it; otherwise fallback
    if model is not None:
        try:
            results_full = model(full_img, verbose=False, conf=conf_threshold)
            for result in results_full:
                for box in getattr(result, 'boxes', []):
                    cls_i = int(box.cls[0])
                    detected_class = model.names[cls_i].lower()
                    conf = float(box.conf[0])
                    confidence_scores.append(conf)
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
        except Exception:
            # model inference failed; continue to fallback
            pass

    # Per-tile crop detection if model available
    if model is not None:
        try:
            for r in range(rows):
                for c in range(cols):
                    tile_idx = r * cols + c
                    box = (int(c * tile_w), int(r * tile_h), int((c + 1) * tile_w), int((r + 1) * tile_h))
                    tile_crop = full_img.crop(box)
                    tile_results = model(tile_crop, verbose=False, conf=conf_threshold)
                    for result in tile_results:
                        for box in getattr(result, 'boxes', []):
                            cls_i = int(box.cls[0])
                            detected_class = model.names[cls_i].lower()
                            conf = float(box.conf[0])
                            confidence_scores.append(conf)
                            if detected_class == yolo_target:
                                click_indices.add(tile_idx)
        except Exception:
            pass

    # If nothing found or model not available, try color fallback
    if not click_indices:
        fallback = detect_by_color_similarity(full_img, rows=rows, cols=cols)
        if fallback:
            click_indices.update(fallback)

    if not click_indices:
        return None
    return sorted(list(click_indices))


def reload_captcha(driver):
    try:
        reload_btn = driver.find_element(By.ID, "recaptcha-reload-button")
        human_click(driver, reload_btn)
        human_like_sleep(800, 1200)
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


def solve_recaptcha_v2(driver, max_attempts=1):
    for attempt in range(max_attempts):
        if is_recaptcha_solved(driver):
            print("[reCAPTCHA] Already solved")
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
            human_like_sleep(300, 600)
            continue

        full_instruction_text = instructions_elem.text.lower()
        target_elem = instructions_elem.find_element(By.XPATH, './/strong')
        prompt_text = target_elem.text.strip().lower()

        if any(unsupported in prompt_text for unsupported in UNSUPPORTED_PROMPTS):
            print(f"      [Instant Skip] '{prompt_text}' unsupported prompt. Reloading...")
            reload_captcha(driver)
            continue

        yolo_target = LABEL_MAP.get(prompt_text, prompt_text)
        is_dynamic = "none left" in full_instruction_text or "new ones" in full_instruction_text
        print(f"      [Prompt]: '{prompt_text}' -> Target: '{yolo_target}' | Dynamic: {is_dynamic}")

        tile_elements = driver.find_elements(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]')
        grid_count = len(tile_elements)
        rows, cols = (4, 4) if grid_count == 16 else (3, 3)

        try:
            img_elem = driver.find_element(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]//img')
            img_bytes = requests.get(img_elem.get_attribute("src"), headers=get_random_headers()).content
            full_img = Image.open(io.BytesIO(img_bytes))
        except Exception as e:
            print(f"      Image capture failed: {e}")
            reload_captcha(driver)
            continue

        tiles_to_click = detect_target_tiles_hybrid(full_img, yolo_target, rows=rows, cols=cols)

        if not tiles_to_click:
            print("      No matching tiles identified. Reloading...")
            reload_captcha(driver)
            continue

        print(f"      Clicking tiles -> {tiles_to_click}")
        for idx in tiles_to_click:
            try:
                human_click(driver, tile_elements[idx])
            except Exception:
                break

        try:
            verify_btn = driver.find_element(By.ID, "recaptcha-verify-button")
            human_click(driver, verify_btn)
        except Exception:
            pass

        try:
            driver.switch_to.default_content()
        except Exception:
            pass

        human_like_sleep(1000, 1500)

    return is_recaptcha_solved(driver)

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")
    installed_chrome_version = get_chrome_major_version()

    # Clear undetected_chromedriver cache to prevent driver locks
    uc_cache = os.path.expanduser("~/.local/share/undetected_chromedriver")
    shutil.rmtree(uc_cache, ignore_errors=True)

    opts, profile = build_chrome_options(temp_profile_dir)

    print("[1/6] Launching Chrome...")
    try:
        driver = uc.Chrome(options=opts, version_main=installed_chrome_version)
    except Exception:
        driver = uc.Chrome(options=opts)

    stealth(
        driver,
        languages=["en-US", "en"],
        vendor=profile["vendor"],
        platform=profile["platform"],
        webgl_vendor=profile["vendor"],
        renderer=profile["renderer"],
        fix_hairline=True,
    )

    try:
        print("[2/6] Navigating to EuroDNS...")
        driver.get("https://eurodns.pxf.io/PzkDy6")
        human_like_sleep(1500, 2500)

        print("[3/6] Clicking 'My account'...")
        try:
            my_account_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "account-item-logout"))
            )
            human_click(driver, my_account_btn)
        except Exception as e:
            print(f"      Account button note: {e}")

        print("[4/6] Clicking 'New account'...")
        try:
            new_account_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.btn.btn-secondary[href*='createNewAccount']"))
            )
            human_click(driver, new_account_btn)
        except Exception as e:
            print(f"      New account button note: {e}")

        human_like_sleep(2000, 3000)

        # Generate credentials
        email_addr = f"user_{uuid.uuid4().hex[:8]}@emalupe.com"
        pwd = generate_strong_password(16)
        print(f"      Generated Email: {email_addr}")

        print("[5/6] Filling form fields...")
        email_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email' or @name='email' or contains(@id, 'email')]"))
        )
        email_field.clear()
        email_field.send_keys(email_addr)

        password_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password' or @name='password' or contains(@id, 'password')]"))
        )
        password_field.clear()
        password_field.send_keys(pwd)

        # Submit form to trigger CAPTCHA
        print("[6/6] Submitting registration form...")
        submit_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.mat-mdc-button-touch-target, button[type='submit']"))
        )
        human_click(driver, submit_btn)
        human_like_sleep(2000, 3000)

        # Solve CAPTCHA challenge
        solve_recaptcha_v2(driver, max_attempts=1)

        # Trigger final submission step
        try:
            remaining_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button.mat-mdc-raised-button")
            for btn in remaining_btns:
                if btn.is_displayed():
                    human_click(driver, btn)
                    break
        except Exception:
            pass

        time.sleep(10.0)
        print(f"Final Landed URL: {driver.current_url}")

    finally:
        try:
            driver.quit()
        except Exception:
            pass
        shutil.rmtree(temp_profile_dir, ignore_errors=True)
        print("[Clean exit] Chrome closed.")
