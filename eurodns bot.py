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
    }
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8,en-US;q=0.7"
]

def get_chrome_major_version():
    for cmd in ["google-chrome --version", "google-chrome-stable --version", "chromium-browser --version"]:
        try:
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode("utf-8")
            match = re.search(r"(\d+)\.\d+\.\d+\.\d+", output)
            if match:
                return int(match.group(1))
        except Exception:
            pass
    return None

def human_like_sleep(min_ms=200, max_ms=600):
    time.sleep(random.uniform(min_ms / 1000.0, max_ms / 1000.0))

def get_random_headers():
    return {
        "User-Agent": random.choice([p["user_agent"] for p in BROWSER_PROFILES]),
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Referer": "https://www.google.com/",
    }

def build_chrome_options(profile_dir):
    opts = uc.ChromeOptions()
    profile = random.choice(BROWSER_PROFILES)
    opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(f"user-agent={profile['user_agent']}")
    return opts, profile

def human_click(driver, element):
    try:
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(element, random.randint(-4, 4), random.randint(-4, 4))
        human_like_sleep(100, 250)
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

model = None
if YOLO is not None:
    try:
        model_path = os.path.join(os.path.dirname(__file__), "yolov8m.pt")
        if os.path.exists(model_path):
            model = YOLO(model_path)
            print("[Init] Loaded YOLO model from yolov8m.pt")
        else:
            model = YOLO("yolov8m.pt")
            print("[Init] Loaded YOLO model via name 'yolov8m.pt'")
    except Exception:
        model = None

LABEL_MAP = {
    "bicycles": "bicycle", "bicycle": "bicycle", "a bicycle": "bicycle",
    "cars": "car", "car": "car", "vehicles": "car", "a car": "car",
    "buses": "bus", "bus": "bus", "a bus": "bus",
    "motorcycles": "motorcycle", "motorcycle": "motorcycle",
    "traffic lights": "traffic light", "traffic light": "traffic light", "a traffic light": "traffic light",
    "fire hydrants": "fire hydrant", "fire hydrant": "fire hydrant", "a fire hydrant": "fire hydrant"
}

UNSUPPORTED_PROMPTS = ["crosswalk", "crosswalks", "bridge", "bridges", "chimney", "chimneys", "stairs"]

def detect_target_tiles_hybrid(full_img, yolo_target, rows=3, cols=3, conf_threshold=0.15):
    w, h = full_img.size
    tile_w, tile_h = w / cols, h / rows
    tile_area = tile_w * tile_h
    click_indices = set()

    if model is not None:
        try:
            results_full = model(full_img, verbose=False, conf=conf_threshold)
            for result in results_full:
                for box in getattr(result, 'boxes', []):
                    detected_class = model.names[int(box.cls[0])].lower()
                    if detected_class == yolo_target:
                        bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                        for r in range(rows):
                            for c in range(cols):
                                tx1, ty1 = c * tile_w, r * tile_h
                                tx2, ty2 = (c + 1) * tile_w, (r + 1) * tile_h
                                inter_w = max(0.0, min(bx2, tx2) - max(bx1, tx1))
                                inter_h = max(0.0, min(by2, ty2) - max(by1, ty1))
                                if ((inter_w * inter_h) / tile_area) >= 0.02:
                                    click_indices.add(r * cols + c)
        except Exception:
            pass

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

def solve_recaptcha_v2(driver, max_attempts=6):
    for attempt in range(max_attempts):
        if is_recaptcha_solved(driver):
            print("[reCAPTCHA] Green checkmark verified!")
            return True

        try:
            driver.switch_to.default_content()
        except Exception:
            pass

        print(f"\n      --- CAPTCHA Solving Round {attempt + 1}/{max_attempts} ---")

        try:
            bframe = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//iframe[contains(@src, "recaptcha/api2/bframe")]'))
            )
            driver.switch_to.frame(bframe)

            instructions_elem = WebDriverWait(driver, 5).until(
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
                human_like_sleep(150, 300)
            except Exception:
                break

        human_like_sleep(500, 800)

        try:
            verify_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-verify-button"))
            )
            human_click(driver, verify_btn)
            print("      [Verify Button Clicked]")
        except Exception as e:
            print(f"      Verify click failed/skipped: {e}")

try:
            driver.switch_to.default_content()
        except Exception:
            pass
        human_like_sleep(1500, 2500)

    # Return result only AFTER all attempts complete
    return is_recaptcha_solved(driver)

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")
    installed_chrome_version = get_chrome_major_version()

    uc_cache = os.path.expanduser("~/.local/share/undetected_chromedriver")
    shutil.rmtree(uc_cache, ignore_errors=True)

    print("[1/6] Launching Chrome...")
    driver = None
    
# Force alignment with installed Chrome version
    target_version = installed_chrome_version if installed_chrome_version else 150

    try:
        opts, profile = build_chrome_options(temp_profile_dir)
        driver = uc.Chrome(options=opts, version_main=target_version)
    except Exception as e:
        print(f"      Primary launch attempt with version_main={target_version} failed: {e}")
        shutil.rmtree(uc_cache, ignore_errors=True)
        opts, profile = build_chrome_options(temp_profile_dir)
        driver = uc.Chrome(options=opts, version_main=150)
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

        email_addr = f"user_{uuid.uuid4().hex[:8]}@emalupe.com"
        pwd = generate_strong_password(16)
        print(f"      Generated Email: {email_addr}")

print("[5/6] Filling form fields...")
        email_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email' or @name='email' or contains(@id, 'email')]"))
        )
        email_field.clear()
        driver.execute_script("""
            var el = arguments[0];
            el.value = arguments[1];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, email_field, email_addr)

        password_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password' or @name='password' or contains(@id, 'password')]"))
        )
        password_field.clear()
        driver.execute_script("""
            var el = arguments[0];
            el.value = arguments[1];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, password_field, pwd)

        print("[6/6] Submitting registration form...")
        submit_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.mat-mdc-button-touch-target, button[type='submit']"))
        )
        human_click(driver, submit_btn)
        human_like_sleep(2000, 3000)

        # Solve CAPTCHA
        solve_recaptcha_v2(driver, max_attempts=6)

        # Final submission click
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
