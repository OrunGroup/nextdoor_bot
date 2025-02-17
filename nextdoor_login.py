from config import NEXTDOOR_EMAIL, NEXTDOOR_PASSWORD, HEADLESS_MODE
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def login_to_nextdoor(user_email, user_password, user_agent_list=None, headless=HEADLESS_MODE):
    """Initializes a Chrome WebDriver with stealth settings and logs into Nextdoor."""
    logging.info("Initializing browser...")

    if user_agent_list is None or len(user_agent_list) == 0:
        user_agent_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        ]
    random_user_agent = random.choice(user_agent_list)

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument(f"user-agent={random_user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-crash-reporter")
    chrome_options.add_argument("--disable-features=NetworkService")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    if headless:
        chrome_options.add_argument("--headless")

    try:
        driver = uc.Chrome(options=chrome_options, headless=headless)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        logging.info("Browser stealth mode activated.")
    except Exception as e:
        logging.error(f"Error initializing undetected_chromedriver: {e}")
        return None

    logging.info("Attempting to log in...")
    driver.get("https://nextdoor.com/login/")
    time.sleep(3)

    try:
        logging.info("Entering email...")
        email_input = driver.find_element(By.NAME, "email")
        email_input.send_keys(user_email)
        time.sleep(random.randint(1, 3))

        logging.info("Entering password...")
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys(user_password)
        time.sleep(random.randint(1, 3))

        logging.info("Logging in...")
        password_input.send_keys(Keys.RETURN)
        time.sleep(random.randint(3, 5))

        if check_login_success(driver, attempts=3, delay=4):
            logging.info("Login successful!")
            return driver
        else:
            while True:
                user_input = input("❗ Nextdoor requested 2FA or is slow to load. Complete authentication and type 'yes' when done (or 'no' to exit): ").strip().lower()
                if user_input == "yes":
                    if check_login_success(driver):
                        logging.info("Login successful after 2FA!")
                        return driver
                    else:
                        logging.warning("Still can't find search bar, maybe 2FA isn't done yet...")
                elif user_input == "no":
                    logging.info("Exiting. Complete authentication and restart.")
                    driver.quit()
                    return None
                else:
                    logging.warning("Please type 'yes' or 'no'.")
    except Exception as e:
        logging.error(f"Error during login: {e}")
        driver.quit()
        return None

def check_login_success(driver, attempts=3, delay=3):
    """Checks if login was successful by detecting the search bar."""
    from selenium.common.exceptions import NoSuchElementException

    for attempt in range(attempts):
        try:
            driver.find_element(By.ID, "search-input-field")
            return True
        except NoSuchElementException:
            logging.warning(f"Attempt {attempt+1}/{attempts} failed to find search bar. Waiting {delay} seconds...")
            time.sleep(delay)
        except Exception as e:
            logging.error(f"Unexpected error checking login success: {e}")
            time.sleep(delay)
    return False