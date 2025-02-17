import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def initialize_db():
    """Ensures the `posts` table exists with the required structure."""
    try:
        conn = sqlite3.connect("nextdoor_posts.db")
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link TEXT UNIQUE,  
                author TEXT,
                location TEXT,
                date TEXT,
                content TEXT,
                service_request TEXT DEFAULT 'no',  -- Stores AI classification ('yes' or 'no')
                processed BOOLEAN DEFAULT FALSE  
            )
        """)

        # Check if the 'service_request' column exists, and add it if missing
        cursor.execute("PRAGMA table_info(posts);")
        columns = [col[1] for col in cursor.fetchall()]
        if "service_request" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN service_request TEXT DEFAULT 'no'")
            logging.info("Added 'service_request' column to database.")

        conn.commit()
        logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error initializing database: {e}")
    finally:
        conn.close()

def post_exists(link):
    """Checks if a post already exists in the database."""
    try:
        conn = sqlite3.connect("nextdoor_posts.db")
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM posts WHERE link = ?", (link,))
        result = cursor.fetchone()
        exists = result is not None
        logging.info(f"Checking if post exists: {link} -> {'Found' if exists else 'Not Found'}")
        return exists
    except sqlite3.Error as e:
        logging.error(f"Error checking if post exists: {e}")
        return False
    finally:
        conn.close()

def save_post(link, author, date, location, content, service_request):
    """
    Saves a new post to the database if it hasn’t already been seen.

    Args:
        link (str): The post URL.
        author (str): The post author.
        date (str): The post date.
        location (str): The post location.
        content (str): The post content.
        service_request (str): "yes" if AI determines it's a service request, otherwise "no".

    Returns:
        bool: True if the post was saved, False if it was already seen.
    """
    try:
        # Create a new connection for each save operation
        conn = sqlite3.connect("nextdoor_posts.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO posts (link, author, date, location, content, service_request) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (link, author, date, location, content, service_request))

        conn.commit()
        logging.info(f"Successfully saved post: {link} (Service Request: {service_request})")
        return True

    except sqlite3.IntegrityError:
        logging.warning(f"Post already exists in the database: {link}")
        return False
    except sqlite3.OperationalError as e:
        logging.error(f"Database error: {e}")
        return False
    finally:
        # Ensure the connection is always closed
        if conn:
            conn.close()
def mark_post_processed(link):
    """Marks a post as processed, meaning it has been interacted with."""
    try:
        conn = sqlite3.connect("nextdoor_posts.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE posts SET processed = TRUE WHERE link = ?", (link,))
        conn.commit()
        logging.info(f"Marked post as processed: {link}")
    except sqlite3.Error as e:
        logging.error(f"Error marking post as processed: {e}")
    finally:
        conn.close()

def get_unprocessed_posts():
    """Retrieves all posts that haven't been processed yet."""
    try:
        conn = sqlite3.connect("nextdoor_posts.db")
        cursor = conn.cursor()
        cursor.execute("SELECT link FROM posts WHERE processed = FALSE")
        posts = cursor.fetchall()
        post_links = [post[0] for post in posts]
        logging.info(f"Found {len(post_links)} unprocessed posts.")
        return post_links
    except sqlite3.Error as e:
        logging.error(f"Error retrieving unprocessed posts: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    initialize_db()
    logging.info("Database setup complete!")