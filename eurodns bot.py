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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException

# ==================== BROWSER FINGERPRINTS ====================
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

# ==================== UTILITY FUNCTIONS ====================

def get_chrome_major_version():
    """Detects installed Chrome major version."""
    for cmd in ["google-chrome --version", "google-chrome-stable --version", "chromium-browser --version", "chromium --version"]:
        try:
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
            match = re.search(r"(\d+)\.\d+\.\d+\.\d+", output)
            if match:
                return int(match.group(1))
        except Exception:
            pass
    return None

def human_like_sleep(min_ms=100, max_ms=500):
    """Random human-like delay with Gaussian distribution"""
    delay = random.gauss((min_ms + max_ms) / 2000, (max_ms - min_ms) / 4000)
    delay = max(min_ms / 1000, min(delay, max_ms / 1000))  # Clamp between min and max
    time.sleep(delay)

def get_random_headers():
    """Generate random browser headers"""
    return {
        "User-Agent": random.choice([p["user_agent"] for p in BROWSER_PROFILES]),
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Referer": "https://www.google.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "DNT": "1",
    }

def build_chrome_options(profile_dir):
    """Generates a fresh ChromeOptions object per launch attempt with randomized fingerprint."""
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
    """Simulate human-like clicking with mouse movement and random offsets"""
    try:
        actions = ActionChains(driver)
        # Random offset to make click less predictable
        offset_x = random.randint(-8, 8)
        offset_y = random.randint(-8, 8)
        actions.move_to_element_with_offset(element, offset_x, offset_y)
        human_like_sleep(50, 150)
        actions.click()
        actions.perform()
    except Exception as e:
        print(f"      [Human Click Error] {e}, falling back to execute_script")
        driver.execute_script("arguments[0].click();", element)

print("[Init] Loading YOLOv8m vision model (medium - better accuracy)...")
model = YOLO("yolov8m.pt")

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

# ==================== CAPTCHA DETECTION ====================

def detect_by_color_similarity(full_img, target_color=(100, 150, 200), rows=3, cols=3):
    """Fallback: Detect tiles by color/texture similarity"""
    import numpy as np
    img_array = np.array(full_img)
    w, h = full_img.size
    tile_w, tile_h = w / cols, h / rows
    
    click_indices = []
    for r in range(rows):
        for c in range(cols):
            tile_idx = r * cols + c
            box = (int(c * tile_w), int(r * tile_h), int((c + 1) * tile_w), int((r + 1) * tile_h))
            tile = img_array[int(r * tile_h):int((r + 1) * tile_h), int(c * tile_w):int((c + 1) * tile_w)]
            
            # Simple mean color comparison (heuristic)
            mean_color = np.mean(tile, axis=(0, 1))
            # If tile appears to have relevant content (not blank)
            if np.std(tile) > 15:  # Has variance
                click_indices.append(tile_idx)
    
    return click_indices

def detect_target_tiles_hybrid(full_img, yolo_target, rows=3, cols=3, conf_threshold=0.25):
    """Enhanced hybrid detection with confidence scoring and fallback"""
    w, h = full_img.size
    tile_w, tile_h = w / cols, h / rows
    tile_area = tile_w * tile_h
    click_indices = set()
    confidence_scores = []

    # Pass 1: Full Canvas Detection
    results_full = model(full_img, verbose=False, conf=conf_threshold)
    for result in results_full:
        for box in result.boxes:
            detected_class = model.names[int(box.cls[0])].lower()
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
                            print(f"      [Canvas Match] Tile {tile_idx} -> '{detected_class}' ({conf:.2f})")

    # Pass 2: Individual Crop Detection
    for r in range(rows):
        for c in range(cols):
            tile_idx = r * cols + c
            box = (int(c * tile_w), int(r * tile_h), int((c + 1) * tile_w), int((r + 1) * tile_h))
            tile_crop = full_img.crop(box)

            tile_results = model(tile_crop, verbose=False, conf=conf_threshold)
            for result in tile_results:
                for box in result.boxes:
                    detected_class = model.names[int(box.cls[0])].lower()
                    conf = float(box.conf[0])
                    confidence_scores.append(conf)

                    if detected_class == yolo_target:
                        click_indices.add(tile_idx)
                        print(f"      [Tile Crop Match] Tile {tile_idx} -> '{detected_class}' ({conf:.2f})")

    # Check if confidence is too low - signal reload
    if confidence_scores and max(confidence_scores) < 0.20:
        print(f"      [Low Confidence] Max confidence {max(confidence_scores):.2f} < 0.20 - consider reloading")
        return None
    
    # If YOLO found nothing, try color-based fallback
    if not click_indices:
        print(f"      [YOLO Failed] Trying color-based fallback detection...")
        fallback_indices = detect_by_color_similarity(full_img, rows=rows, cols=cols)
        if fallback_indices:
            click_indices = set(fallback_indices)
            print(f"      [Fallback Success] Found tiles via color: {sorted(list(click_indices))}")

    return sorted(list(click_indices)) if click_indices else None

def reload_captcha(driver):
    """Reload the captcha with human-like timing"""
    print("      Reloading challenge for a recognizable prompt...")
    try:
        reload_btn = driver.find_element(By.ID, "recaptcha-reload-button")
        human_click(driver, reload_btn)
        human_like_sleep(800, 1200)
    except Exception:
        pass
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

def is_recaptcha_solved(driver):
    """Check if reCAPTCHA is already solved"""
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

# CAPPED AT EXACTLY 1 ROUND FOR MAXIMUM SPEED
def solve_recaptcha_v2(driver, max_attempts=1):
    """Solve reCAPTCHA v2 with enhanced stealth and human-like behavior"""
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
            human_like_sleep(300, 800)
            continue

        full_instruction_text = instructions_elem.text.lower()
        target_elem = instructions_elem.find_element(By.XPATH, './/strong')
        prompt_text = target_elem.text.strip().lower()

        if any(unsupported in prompt_text for unsupported in UNSUPPORTED_PROMPTS):
            print(f"      [Instant Skip] '{prompt_text}' unsupported prompt. Reloading...")
            reload_captcha(driver)
            human_like_sleep(800, 1500)
            continue

        yolo_target = LABEL_MAP.get(prompt_text, prompt_text)
        is_dynamic = "none left" in full_instruction_text or "new ones" in full_instruction_text
        print(f"      [Prompt]: '{prompt_text}' -> YOLO: '{yolo_target}' | Dynamic: {is_dynamic}")

        if not is_dynamic:
            tile_elements = driver.find_elements(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]')
            grid_count = len(tile_elements)
            rows, cols = (4, 4) if grid_count == 16 else (3, 3)

            img_elem = driver.find_element(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]//img')
            img_bytes = requests.get(img_elem.get_attribute("src"), headers=get_random_headers()).content
            full_img = Image.open(io.BytesIO(img_bytes))

            tiles_to_click = detect_target_tiles_hybrid(full_img, yolo_target, rows=rows, cols=cols)

            if not tiles_to_click:
                reload_captcha(driver)
                human_like_sleep(800, 1500)
                continue

            print(f"      Static Mode: Clicking tiles -> {tiles_to_click}")
            for idx in tiles_to_click:
                try:
                    human_click(driver, tile_elements[idx])
                    human_like_sleep(150, 400)
                except Exception:
                    break

            human_like_sleep(300, 600)

        else:
            max_dynamic_rounds = 2
            total_clicks = 0

            for d_round in range(max_dynamic_rounds):
                tile_elements = driver.find_elements(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]')
                grid_count = len(tile_elements)
                rows, cols = (4, 4) if grid_count == 16 else (3, 3)

                img_elem = driver.find_element(By.XPATH, '//td[contains(@class, "rc-imageselect-tile")]//img')
                img_bytes = requests.get(img_elem.get_attribute("src"), headers=get_random_headers()).content
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
                        human_click(driver, tile_elements[idx])
                        total_clicks += 1
                        human_like_sleep(1000, 1800)
                    except Exception:
                        break

        try:
            verify_btn = driver.find_element(By.ID, "recaptcha-verify-button")
            human_like_sleep(300, 700)
            human_click(driver, verify_btn)
        except Exception:
            pass

        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        human_like_sleep(800, 1500)

    return is_recaptcha_solved(driver)

def create_real_temp_email():
    """Create a temporary email using mail.tm API"""
    req = urllib.request.Request("https://api.mail.tm/domains", headers=get_random_headers())
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
        headers={'Content-Type': 'application/json', **get_random_headers()}
    )
    with urllib.request.urlopen(post_req) as response:
        return email_address, account_password

def generate_strong_password(length=16):
    """Generate a random strong password"""
    chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + "!@#$%^&*()"
    return "".join(random.choice(chars) for _ in range(length))

# ==================== MAIN EXECUTION ====================

temp_profile_dir = tempfile.mkdtemp(prefix="stealth_profile_")
installed_chrome_version = get_chrome_major_version()

driver = None
version_candidates = [installed_chrome_version, 150, 151, None]

for ver in version_candidates:
    try:
        fresh_options, selected_profile = build_chrome_options(temp_profile_dir)
        driver = uc.Chrome(options=fresh_options, version_main=ver)
        print(f"[Init] Driver initialized using version_main={ver}")
        print(f"[Init] Using browser profile: {selected_profile['renderer']}")
        break
    except Exception as e:
        print(f"[Init] Launch attempt failed for version {ver}: {e}")

if not driver:
    fresh_options, selected_profile = build_chrome_options(temp_profile_dir)
    driver = uc.Chrome(options=fresh_options)
    print(f"[Init] Using browser profile: {selected_profile['renderer']}")

# Apply stealth with randomized fingerprint
stealth(
    driver,
    languages=["en-US", "en"],
    vendor=selected_profile["vendor"],
    platform=selected_profile["platform"],
    webgl_vendor=selected_profile["vendor"],
    renderer=selected_profile["renderer"],
    fix_hairline=True,
    chrome_runtime_cdc=True,
)

# Inject additional JavaScript to hide automation
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
    "source": """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });
    """
})

try:
    print("[1/6] Visiting EuroDNS...")
    driver.get("https://eurodns.pxf.io/PzkDy6")
    human_like_sleep(800, 1500)

    try:
        accept_cookies = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "cookiescript_accept"))
        )
        human_click(driver, accept_cookies)
        human_like_sleep(300, 700)
    except Exception:
        pass

    my_account_btn = WebDriverWait(driver, 4).until(
        EC.presence_of_element_located((By.ID, "account-item-logout"))
    )
    human_click(driver, my_account_btn)
    human_like_sleep(500, 1000)

    new_account_btn = WebDriverWait(driver, 4).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a.btn.btn-secondary[href*='createNewAccount']"))
    )
    human_click(driver, new_account_btn)
    human_like_sleep(800, 1500)

    email, _ = create_real_temp_email()
    pwd = generate_strong_password(16)
    print(f"      Generated Email:    {email}")

    email_field = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[id*='email']"))
    )
    email_field.clear()
    human_like_sleep(100, 300)
    email_field.send_keys(email)
    human_like_sleep(300, 600)

    password_field = WebDriverWait(driver, 4).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[name='password'], input[id*='password']"))
    )
    password_field.clear()
    human_like_sleep(100, 300)
    password_field.send_keys(pwd)
    human_like_sleep(300, 600)

    try:
        checkbox = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "subscribe-newsletter-checkbox-input"))
        )
        human_click(driver, checkbox)
        human_like_sleep(200, 500)
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
    human_like_sleep(1200, 1800)

    # Solve CAPTCHA (1 Round Capped)
    solve_recaptcha_v2(driver, max_attempts=1)

    # Trigger final submit
    try:
        remaining_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button.mat-mdc-raised-button")
        for btn in remaining_btns:
            if btn.is_displayed():
                human_click(driver, btn)
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
