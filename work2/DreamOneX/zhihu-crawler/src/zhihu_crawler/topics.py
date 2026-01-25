from rich.logging import RichHandler
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

import time
import json
import logging

from zhihu_crawler.utils import (
    setup_driver,
    load_cookies,
    handle_login_interrupt,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(message)s", 
    datefmt="[%X]", 
    handlers=[RichHandler(rich_tracebacks=True)]
)

# Crawl limits
MAX_CATEGORIES = 5          # Max number of categories to crawl
MAX_LOAD_MORE_CLICKS = 1    # Max "Load More" clicks per category
MAX_TOTAL_TOPICS = 20      # Stop when reaching this many topics


def click_category(driver, cat_item, cat_name, index):
    """Click a category item using JS to avoid interception issues. Returns True on success."""
    try:
        driver.execute_script("arguments[0].click();", cat_item)
        return True
    except Exception as e:
        logging.warning(f"Failed to click category {cat_name}: {e}")
        return False


def crawl_zhihu_topics():
    driver = setup_driver()
    all_topics = []

    try:
        url = "https://www.zhihu.com/topics"
        logging.info(f"Loading {url}...")
        driver.get(url)

        if load_cookies(driver):
            driver.get(url)
            driver.get(url)
            time.sleep(2)

        wait = WebDriverWait(driver, 10)
        categories_ul = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.zm-topic-cat-main")))

        category_items = driver.find_elements(By.CSS_SELECTOR, "li.zm-topic-cat-item")
        category_count = len(category_items)
        logging.info(f"Found {category_count} categories.")
        
        for i in range(min(category_count, MAX_CATEGORIES)):
            if len(all_topics) >= MAX_TOTAL_TOPICS:
                logging.info(f"Reached max total topics ({MAX_TOTAL_TOPICS}), stopping.")
                break

            handle_login_interrupt(driver)

            category_items = driver.find_elements(By.CSS_SELECTOR, "li.zm-topic-cat-item")
            if i >= len(category_items):
                break

            cat_item = category_items[i]
            cat_name = cat_item.text.strip()
            cat_id = cat_item.get_attribute("data-id")
            logging.info(f"Processing Category {i+1}/{category_count}: {cat_name} (ID: {cat_id})")

            if not click_category(driver, cat_item, cat_name, i):
                continue

            time.sleep(2)

            consecutive_no_growth = 0
            last_item_count = 0
            clicks = 0

            while clicks < MAX_LOAD_MORE_CLICKS:
                handle_login_interrupt(driver)

                items = driver.find_elements(By.CSS_SELECTOR, "div.zh-general-list[style*='block'] div.item")
                current_count = len(items)

                if current_count > 0:
                    if current_count == last_item_count:
                        consecutive_no_growth += 1
                    else:
                        consecutive_no_growth = 0
                    last_item_count = current_count

                if consecutive_no_growth >= 3:
                    logging.info(f"Item count ({current_count}) hasn't changed for 3 clicks. stopping load more.")
                    break

                try:
                    more_btn = driver.find_element(By.CSS_SELECTOR, "a.zu-button-more")
                    if not more_btn.is_displayed():
                        break
                    logging.info(f"Found 'Load More' button, clicking... ({clicks+1}/{MAX_LOAD_MORE_CLICKS})")
                    driver.execute_script("arguments[0].click();", more_btn)
                    clicks += 1
                    time.sleep(2)
                except NoSuchElementException:
                    logging.warning("'Load More' button not found, may be a page issue")
                    break

            topic_items = driver.find_elements(By.CSS_SELECTOR, "div.zh-general-list[style*='block'] div.item")
            logging.info(f"Found {len(topic_items)} topics in category '{cat_name}'")

            for item in topic_items:
                link_els = item.find_elements(By.CSS_SELECTOR, "a[target='_blank']")
                if not link_els:
                    continue

                link_el = link_els[0]
                topic_url = link_el.get_attribute("href")
                name_els = link_el.find_elements(By.TAG_NAME, "strong")
                topic_name = name_els[0].text.strip() if name_els else link_el.text.strip()

                topic_data = {
                    "category": cat_name,
                    "name": topic_name,
                    "url": topic_url
                }
                if topic_data not in all_topics:
                    all_topics.append(topic_data)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        driver.quit()

    output_file = "zhihu_topics.json"
    logging.info(f"Saving {len(all_topics)} topics to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_topics, f, ensure_ascii=False, indent=2)
    logging.info("Done.")


if __name__ == "__main__":
    crawl_zhihu_topics()
