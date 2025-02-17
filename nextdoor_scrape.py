# nextdoor_scrape.py

"""
This module holds all the functions needed to:
 1) Search Nextdoor
 2) Extract elements from posts
 3) Convert relative timestamps
 4) Classify posts
 5) Parse multiple posts.

Make sure you:
 - Import or define your "post_exists" and "save_post" functions (database logic)
   if needed, or import them from another module.
 - Define or import "client" for classify_post if it's not in this file.
"""

# -----------------------------
# IMPORTS
# -----------------------------
import time  # For sleep, measuring runtime
import random  # For random sleep intervals
import sqlite3  # Potentially used if referencing a DB directly
import logging  # For structured logging

# For date/time conversion of post timestamps
from utils import convert_relative_time_to_absolute

# For DB logic (checking existence, saving new posts)
from database import post_exists, save_post

# OpenAI API
from openai import OpenAI, RateLimitError, APIError
from config import OPENAI_API_KEY

# Selenium imports
from selenium.webdriver.common.by import By  # For locating elements
from selenium.webdriver.common.keys import Keys  # For sending special keys like ENTER
from selenium.webdriver.support.ui import WebDriverWait  # For waiting until an element is clickable
from selenium.webdriver.support import expected_conditions as EC  # Common conditions (clickable, visible, etc.)
from selenium.webdriver import ActionChains
from selenium.common.exceptions import NoSuchElementException

# Selenium exceptions
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    JavascriptException
)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ---------------------------------------------------------------------------
# 1. Search Nextdoor
# ---------------------------------------------------------------------------
def search_nextdoor(driver, search_query):
    """
    Searches Nextdoor for the given query and applies 'Most Recent' filter.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        search_query (str): The term to search on Nextdoor.

    Returns:
        bool: True if search and filtering were successful, False otherwise.
    """
    if not search_query:
        logging.warning("No search term entered. Exiting search.")
        return False

    logging.info(f"🔍 Searching Nextdoor for '{search_query}'...")

    search_successful = False  # Track success status

    try:
        # Random sleep to simulate human typing delays
        time.sleep(random.randint(1, 3))

        # Find the search bar and click it
        search_bar = driver.find_element(By.ID, "search-input-field")
        search_bar.click()
        time.sleep(random.randint(1, 3))

        # Enter the search query
        search_bar.send_keys(search_query)
        time.sleep(random.randint(1, 3))

        # Press ENTER
        search_bar.send_keys(Keys.RETURN)
        time.sleep(random.randint(3, 5))

        logging.info("✅ Search executed successfully!")
        search_successful = True  # Mark success

    except Exception as e:
        logging.error(f"❌ ERROR: Failed to execute search: {e}")

    finally:
        # Always attempt to apply the "Posts" filter if search was successful
        if search_successful:
            try:
                logging.info("📌 Filtering results to 'Posts'...")
                posts_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-testid='tab-posts']"))
                )
                posts_button.click()
                time.sleep(3)
                logging.info("✅ Filter applied: Now viewing only 'Posts'.")
                return True
            except Exception as e:
                logging.warning(f"⚠️ Could not click 'Posts' tab: {e}")

        logging.info("🛑 Search process completed.")
        return False


# ---------------------------------------------------------------------------
# 2. Extract elements safely
# ---------------------------------------------------------------------------
def extract_element_text(driver, selectors, default_text="Unknown"):
    """
    Extracts text from an element safely, handling exceptions like missing elements or timeouts.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        selectors (list): List of CSS selectors for the element to extract.
        default_text (str, optional): Default text to return if extraction fails. Defaults to "Unknown".

    Returns:
        str: Extracted text or default value if element is not found.
    """
    retries = 3
    for attempt in range(retries):
        for selector in selectors:
            try:
                logging.info(f"Attempting to extract text using selector: {selector}")
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    text = elements[0].text.strip()
                    logging.info(f"Extracted text: {text}")
                    return text if text else default_text
            except Exception as e:
                logging.warning(f"Attempt {attempt+1}: Could not extract '{selector}', error: {e}")
        time.sleep(1)
    logging.warning(f"Giving up on extraction, returning default text.")
    return default_text


# ---------------------------------------------------------------------------
# 3. Classify a post using OpenAI (Simple 'yes'/'no' approach)
# ---------------------------------------------------------------------------
def classify_post(content, author):
    """
    Uses OpenAI to classify whether a post is a service request.
    If 'yes', extracts the type of service and generates a custom message.

    Args:
        content (str): The text content of the Nextdoor post.
        author (str): The name of the user who posted.

    Returns:
        (bool, str): (True, custom_message) if the post is requesting a service, otherwise (False, None).
    """
    if not content or not content.strip():
        return (False, None)

    try:
        # Step 1: Classify if the post is a service request
        classification_response = client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a classifier that determines if a post is requesting a service, make sure  "
                        "that aligns with Moku's service list (lawn care, snow blowing, landscaping, waste removal, power washing, etc.).\n"
                        "Answer only 'yes' or 'no'."
                    )
                },
                {
                    "role": "user",
                    "content": f"Is this post a request for our services?\n\n{content}"
                }
            ]
        )

        classification = classification_response.choices[0].message.content.strip().lower()
        if classification != "yes":
            return (False, None)

        # Step 2: Extract the type of service requested
        service_extraction_response = client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a service extraction tool. Analyze the post and identify the type of service being requested. "
                        "Respond with only the type of service (e.g., 'lawn care', 'snow removal', 'landscaping')."
                    )
                },
                {
                    "role": "user",
                    "content": f"What type of service is being requested in this post?\n\n{content}"
                }
            ]
        )

        service_type = service_extraction_response.choices[0].message.content.strip()

        # Step 3: Generate a custom comment
        custom_message_response = client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that generates polite and professional comments "
                        "offering services to users on Nextdoor. Include the user's first name and the type of service they are requesting. "
                        "Keep the message concise and friendly and do not sign off with anything like Warm Regards or leave my name at the end"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Generate a comment offering your services to {author}. "
                        f"They are requesting help with {service_type}. "
                        "Include your contact information (808-987-6065 cj@mokunebraska.com)."
                    )
                }
            ]
        )

        custom_message = custom_message_response.choices[0].message.content.strip()
        return (True, custom_message)

    except Exception as e:
        logging.error(f"Error classifying post: {e}")
        return (False, None)


# ---------------------------------------------------------------------------
# 4. Parse multiple posts from search results
# ---------------------------------------------------------------------------
def parse_posts(driver, max_posts=50, max_runtime=1200, verify_links=False):
    """
    Extracts posts from the search results page, processes each post, and saves them.
    If a post is identified as a service request, generates a custom comment and prompts the user for approval.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        max_posts (int, optional): Maximum number of posts to extract. Defaults to 50.
        max_runtime (int, optional): Maximum runtime in seconds before stopping. Defaults to 1200.
        verify_links (bool, optional): Unused in current logic, but can be used if you want additional link checks.

    Returns:
        bool: True if the parsing completed successfully, False otherwise.
    """
    logging.info("Extracting posts from the search results...")

    start_time = time.time()
    processed_posts = 0
    seen_posts = set()  # Track processed post links

    while processed_posts < max_posts and (time.time() - start_time) < max_runtime:
        try:
            logging.info("Fetching post elements...")
            post_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-testid^='dwell-tracker-searchFeedItem']")
            post_count = len(post_elements)
            logging.info(f"Found {post_count} posts on the page.")

            new_posts_found = False

            for i in range(post_count):
                try:
                    # Refresh elements each loop to avoid stale references
                    post_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-testid^='dwell-tracker-searchFeedItem']")
                    if i >= len(post_elements):
                        logging.warning(f"Skipping post {i+1}: Index out of range.")
                        continue

                    logging.info(f"Processing post {i+1} of {post_count}...")

                    # Extract post link
                    link_element = post_elements[i].find_element(By.CSS_SELECTOR, "a.BaseLink__kjvg670")
                    post_link = link_element.get_attribute("href")

                    # Skip if we've already processed this link
                    if post_link in seen_posts:
                        logging.warning(f"Skipping post {i+1}: Already processed.")
                        continue

                    seen_posts.add(post_link)
                    new_posts_found = True

                    # Check if post already exists in DB
                    if post_exists(post_link):
                        logging.warning(f"Skipping duplicate post: {post_link}")
                        continue

                    logging.info("Clicking on post...")
                    driver.execute_script("arguments[0].click();", link_element)
                    time.sleep(random.randint(2, 5))

                    # Wait for content to load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.blocks-uj7zvs span div span span"))
                    )

                    # Extract post details
                    author = extract_element_text(driver, ["a._3I7vNNNM.E7NPJ3WK"], "Unknown Author")
                    location = extract_element_text(driver, ["a.post-byline-redesign.post-byline-truncated"], "Unknown Location")
                    date = extract_element_text(driver, ["a.post-byline-redesign:not(.post-byline-truncated)"], "Unknown Date")
                    content = extract_element_text(driver, ["div.blocks-uj7zvs span div span span"], "Content not found")

                    absolute_date = convert_relative_time_to_absolute(date)

                    logging.info(f"Author: {author}")
                    logging.info(f"Location: {location}")
                    logging.info(f"Date: {absolute_date}")
                    logging.info(f"Content: {content[:100]}...")

                    # Classify the post and generate a custom comment
                    is_service_request, custom_message = classify_post(content, author)
                    service_request_label = "yes" if is_service_request else "no"
                    logging.info(f"Service Request? {'Yes' if is_service_request else 'No'}")

                    # Save the post
                    if save_post(post_link, author, absolute_date, location, content, service_request_label):
                        processed_posts += 1
                        logging.info(f"Post saved! Total processed: {processed_posts}/{max_posts}")

                        # If it's a service request, prompt the user to approve the comment
                        if is_service_request and custom_message:
                            if prompt_for_approval(custom_message):
                                logging.info("Posting the comment...")
                                post_comment(driver, custom_message)
                            else:
                                logging.info("Comment not posted.")

                        if processed_posts >= max_posts:
                            logging.info(f"Reached max posts limit ({max_posts}). Stopping extraction.")
                            return True

                    logging.info("Returning to search results page...")
                    driver.back()
                    time.sleep(random.randint(2, 5))

                except (StaleElementReferenceException, NoSuchElementException, TimeoutException) as e:
                    logging.warning(f"Skipping post {i+1} due to element issues: {e}")
                    continue
                except Exception as e:
                    logging.error(f"Error processing post {i+1}: {e}")
                    continue

            # If no new posts were found, we can stop scrolling
            if not new_posts_found:
                logging.info("No new posts found, stopping scrolling.")
                break

            logging.info("Scrolling down to load more posts...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.randint(3, 6))

        except Exception as e:
            logging.error(f"General error in post parsing: {e}")
            break

    logging.info(f"Completed parsing. {processed_posts}/{max_posts} new posts extracted.")
    return True
# ---------------------------------------------------------------------------
# 5. Post a comment if a service request is identified 
# ---------------------------------------------------------------------------
def post_comment(driver, comment_text):
    """
    Finds the correct form, activates the comment box, types a comment, and submits.
    """

    try:
        logging.info("📜 Scrolling to the bottom of the page...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1, 2))

        # Step 1: Locate the form
        logging.info("🔎 Searching for the correct comment form...")
        comment_form = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "form.comment-body-container"))
        )

        logging.info("✅ Found the comment form!")

        # Step 2: Click the form to ensure it's active
        driver.execute_script("arguments[0].click();", comment_form)
        time.sleep(random.uniform(0.5, 1.5))

        # Step 3: Locate the textarea inside the form
        logging.info("🔎 Searching for the textarea inside the form...")
        comment_box = comment_form.find_element(By.CSS_SELECTOR, "textarea[data-testid='comment-add-reply-input']")

        # Step 4: Click inside the textarea to ensure activation
        logging.info("🖱 Clicking inside the textarea...")
        comment_box.click()
        time.sleep(random.uniform(0.5, 1.5))

        # Step 5: Type the comment
        logging.info("⌨️ Typing comment: " + comment_text)
        for char in comment_text:
            comment_box.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))  # Mimic human typing

        # Step 6: Trigger an input event to enable the submit button
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", comment_box)
        time.sleep(random.uniform(1, 2))

        # Step 7: Locate and click the submit button inside the form
        logging.info("🚀 Searching for submit button...")
        submit_button = comment_form.find_element(By.CSS_SELECTOR, "button[data-testid='inline-composer-reply-button']")

        # Ensure the submit button is enabled before clicking
        if submit_button.get_attribute("aria-disabled") == "true":
            logging.warning("⚠️ Submit button is still disabled! Trying another input event...")
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", comment_box)
            time.sleep(random.uniform(1, 2))

        logging.info("✅ Clicking submit button...")
        submit_button.click()
        time.sleep(random.uniform(3, 5))

        logging.info("✅ Comment posted successfully!")
        return True

    except TimeoutException:
        logging.error("🚫 ERROR: Comment form or textarea not found. The method may need adjustments.")
    except NoSuchElementException:
        logging.error("🚫 ERROR: Submit button not found.")
    except Exception as e:
        logging.error(f"🚫 ERROR: Unexpected issue - {e}")

        # Debugging: Save a screenshot for troubleshooting
        driver.save_screenshot("comment_error.png")

    return False
    


    

# ---------------------------------------------------------------------------
# 6. Prompt user to approval drafted comment 
# ---------------------------------------------------------------------------
def prompt_for_approval(comment):
    """
    Prompts the user in the terminal to approve or reject a comment.

    Args:
        comment (str): The comment to be approved.

    Returns:
        bool: True if the user approves, False otherwise.
    """
    print("\nGenerated Comment:")
    print(comment)
    response = input("\nDo you want to post this comment? (yes/no): ").strip().lower()
    return response == "yes"




def verify_login(driver):
    """
    Checks if the bot is still logged in by looking for a profile picture or logout button.
    Returns True if logged in, False if logged out.
    """
    try:
        # Look for the user's profile picture (sign of a logged-in session)
        driver.find_element(By.CSS_SELECTOR, "img[alt*='Profile picture']")
        logging.info("✅ Login verified: User is still logged in.")
        return True
    except NoSuchElementException:
        logging.warning("⚠️ Login verification failed: Not logged in.")
        return False
