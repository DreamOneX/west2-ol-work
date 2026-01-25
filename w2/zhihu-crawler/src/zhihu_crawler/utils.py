import logging
import json
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def setup_driver():
    logging.info("Initializing Chromium Driver...")
    options = Options()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    return driver

def save_cookies(driver, path="cookies.json"):
    with open(path, "w") as f:
        json.dump(driver.get_cookies(), f)
    logging.info("Cookies saved.")


def load_cookies(driver, path="cookies.json"):
    try:
        driver.get("https://www.zhihu.com/404")
        with open(path, "r") as f:
            cookies = json.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
        logging.info("Cookies loaded.")
        return True
    except FileNotFoundError:
        logging.info("No cookies found.")
        return False

def check_login_status(driver):
    """Checks if logged in by looking for specific cookies."""
    return driver.get_cookie("z_c0") is not None


def login_with_qrcode(driver):
    """Handles the login flow via QR code."""
    logging.info("Initiating login sequence...")

    switch_btns = driver.find_elements(By.CSS_SELECTOR, "button.SignFlow-qrCodeButton, .SignFlow-tabs .SignFlow-tab:not(.SignFlow-tab--active)")
    if switch_btns:
        logging.info("Switching to QR code login mode...")
        switch_btns[0].click()
        time.sleep(2)

    driver.save_screenshot("qrcode.png")
    logging.info("Saved full page screenshot to 'qrcode.png'.")

    logging.info("Waiting for login...")
    max_retries = 60
    for _ in range(max_retries):
        if check_login_status(driver):
            logging.info("Login successful!")
            save_cookies(driver)
            return True
        time.sleep(2)

    logging.error("Login timed out.")
    return False


def handle_login_interrupt(driver):
    """Checks for login modal and handles it."""
    modals = driver.find_elements(By.CSS_SELECTOR, ".SignFlow-modal, .Modal-wrapper, .SignFlow")
    if not modals:
        return False

    logging.info("Login required (Modal or Inline detected).")
    if check_login_status(driver):
        logging.info("Already logged in. Attempting to close modal.")
        close_btns = driver.find_elements(By.CSS_SELECTOR, "button.Modal-closeButton, .Modal-close")
        if close_btns:
            close_btns[0].click()
            return True
    return login_with_qrcode(driver)

def random_sleep(min_seconds=1.0, max_seconds=3.0):
    """Sleeps for a random duration to mimic human pauses."""
    time.sleep(random.uniform(min_seconds, max_seconds))


def smooth_scroll(driver, direction="down", distance=None):
    """Scrolls the page smoothly to mimic human reading."""
    current_scroll = driver.execute_script("return window.pageYOffset;")
    total_height = driver.execute_script("return document.body.scrollHeight;")
    viewport_height = driver.execute_script("return window.innerHeight;")

    if distance is None:
        distance = int(viewport_height * random.uniform(0.7, 0.9))

    if direction == "down":
        target = current_scroll + distance
    else:
        target = current_scroll - distance

    target = max(0, min(target, total_height))

    steps = random.randint(5, 10)
    step_size = (target - current_scroll) / steps

    for _ in range(steps):
        current_scroll += step_size
        jitter = random.uniform(-5, 5)
        driver.execute_script(f"window.scrollTo(0, {current_scroll + jitter});")
        time.sleep(random.uniform(0.05, 0.2))

    driver.execute_script(f"window.scrollTo(0, {target});")

    if random.random() < 0.3:
        random_sleep(0.5, 1.5)
        if random.random() < 0.5:
            driver.execute_script(f"window.scrollBy(0, -{random.randint(20, 50)});")
            time.sleep(random.uniform(0.2, 0.5))

