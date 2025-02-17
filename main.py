# main.py

import time
import random
import sqlite3
import logging

from nextdoor_login import login_to_nextdoor
from nextdoor_scrape import search_nextdoor, parse_posts
from config import NEXTDOOR_EMAIL, NEXTDOOR_PASSWORD, OPENAI_API_KEY
from database import initialize_db, post_exists, save_post

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    # 1) Initialize the database (create tables/columns if missing)
    initialize_db()

    # 2) Log into Nextdoor and get a Selenium driver
    driver = login_to_nextdoor(
        user_email=NEXTDOOR_EMAIL,
        user_password=NEXTDOOR_PASSWORD,
    )

    if driver is None:
        logging.error("Login failed. Exiting program.")
        return

    logging.info("Successfully logged in.")

    while True:
        # Prompt user for the Nextdoor search term
        search_query = input("\n🔍 Enter the search term for Nextdoor (or type 'exit' to quit): ").strip()

        if not search_query:
            logging.warning("No search term entered. Please try again.")
            continue

        if search_query.lower() == "exit":
            confirm_exit = input("⚠️ Are you sure you want to exit? (yes/no): ").strip().lower()
            if confirm_exit == "yes":
                logging.info("Exiting script as per user request.")
                break
            else:
                logging.info("Continuing script...")
                continue

        max_posts = int(input("Enter the maximum number of posts to extract (default 50): ") or 50)
        max_runtime = int(input("Enter the maximum runtime in seconds (default 1200): ") or 1200)

        logging.info(f"Searching Nextdoor for '{search_query}'...")
        if search_nextdoor(driver, search_query):
            logging.info("Search results are now displayed.")
            # Parse the posts
            result = parse_posts(
                driver,
                max_posts=max_posts,
                max_runtime=max_runtime,
                verify_links=True  # Optional: Add logic for link verification if needed
            )

            if result is None:
                logging.error("An error occurred. Restarting bot...")
                driver.quit()
                time.sleep(5)
                # Re-init driver if you want to keep going
                driver = login_to_nextdoor(NEXTDOOR_EMAIL, NEXTDOOR_PASSWORD)
                if driver is None:
                    logging.error("Could not re-initialize driver. Exiting.")
                    break
                continue
            else:
                logging.info("Post extraction complete.")
        else:
            logging.warning("Search failed or no results found. Try again.")

    # Close everything gracefully
    logging.info("Closing browser session...")
    driver.quit()
    logging.info("Script execution completed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("\nScript interrupted by user. Closing session...")
    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")