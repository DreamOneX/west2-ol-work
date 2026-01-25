import logging
import json
import time
import random
import re
from rich.logging import RichHandler
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from zhihu_crawler.utils import setup_driver, load_cookies, handle_login_interrupt, random_sleep, smooth_scroll, check_login_status

logging.basicConfig(
    level=logging.INFO, 
    format="%(message)s", 
    datefmt="[%X]", 
    handlers=[RichHandler(rich_tracebacks=True)]
)

def get_random_topic(json_path="zhihu_topics.json"):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            topics = json.load(f)
        if not topics:
            raise ValueError("Topic list is empty.")
        topic = random.choice(topics)
        return topic
    except FileNotFoundError:
        logging.error(f"{json_path} not found.")
        return None


def normalize_question_url(url):
    """
    Normalize question URL by removing /answer/xxx suffix.
    Example: https://www.zhihu.com/question/609920887/answer/3166683855
    becomes: https://www.zhihu.com/question/609920887
    """
    match = re.match(r'(https://www\.zhihu\.com/question/\d+)', url)
    if match:
        return match.group(1)
    return url


def crawl_question_links(driver, target_count=10):
    """
    Crawl question links from topic page.
    Scrolls to load more items and returns deduplicated URLs.
    """
    question_urls = set()
    attempts = 0
    max_attempts = 30
    last_height = driver.execute_script("return document.body.scrollHeight")

    while len(question_urls) < target_count and attempts < max_attempts:
        handle_login_interrupt(driver)

        if "您当前请求存在异常" in driver.page_source:
            raise PermissionError("403 Forbidden detected")

        links = driver.find_elements(By.CSS_SELECTOR, ".List-item h2 a[href*='/question/']")
        for link in links:
            href = link.get_attribute("href")
            if href:
                question_urls.add(normalize_question_url(href))

        logging.info(f"Found {len(question_urls)} unique question URLs")

        if len(question_urls) >= target_count:
            break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        random_sleep(2, 3)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            random_sleep(5, 6)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                logging.info("Reached bottom of page, no more content to load")
                break

        last_height = new_height
        attempts += 1

    result = list(question_urls)[:target_count]
    logging.info(f"Collected {len(result)} question URLs")
    return result


def crawl_question_detail(driver, question_url):
    """Crawl question details including title, description and answers."""
    driver.get(question_url)
    logging.info(f"Crawling question: {question_url}")
    random_sleep(5, 7)

    if "您当前请求存在异常" in driver.page_source or "403 Forbidden" in driver.page_source:
        logging.warning("Detected 403/Abnormal Request")
        with open("debug_question.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise PermissionError("403 Forbidden detected")

    question_data = {
        "url": question_url,
        "title": "",
        "description": "",
        "answers": []
    }

    for _ in range(5):
        title_els = driver.find_elements(By.CSS_SELECTOR, "h1.QuestionHeader-title")
        title = next((t for e in title_els if (t := e.text.strip())), "")
        if title:
            question_data["title"] = title
            break
        random_sleep(2, 3)
    else:
        raise ValueError("can not get title, maybe modal mismatched")

    logging.info(f"Question title: {question_data['title']}")

    desc_els = driver.find_elements(By.CSS_SELECTOR, ".QuestionRichText")
    if desc_els:
        desc_el = desc_els[0]
        if "QuestionRichText--collapsed" in desc_el.get_attribute("class"):
            more_btns = driver.find_elements(By.CSS_SELECTOR, ".QuestionRichText-more")
            if more_btns:
                more_btns[0].click()
                random_sleep(3, 5)
        question_data["description"] = desc_el.text.strip()

    answers = crawl_answers(driver, target_count=10)
    question_data["answers"] = answers

    return question_data


def crawl_answers(driver, target_count=10):
    """Crawl answers from question page, excluding ads."""
    answers_data = []
    attempts = 0
    max_attempts = 15
    last_height = driver.execute_script("return document.body.scrollHeight")
    no_change_count = 0

    while len(answers_data) < target_count and attempts < max_attempts:
        handle_login_interrupt(driver)

        if "您当前请求存在异常" in driver.page_source:
            raise PermissionError("403 Forbidden detected during scroll")

        items = driver.find_elements(By.CSS_SELECTOR, ".List-item")
        for item in items:
            if len(answers_data) >= target_count:
                break

            content_els = item.find_elements(By.CSS_SELECTOR, ".RichContent-inner")
            if not content_els:
                continue

            text = content_els[0].text.strip()
            if not text:
                continue

            if not any(a["content"][:100] == text[:100] for a in answers_data):
                answers_data.append({"content": text})
                logging.debug(f"Found answer #{len(answers_data)}: {text[:50]}...")

        if len(answers_data) >= target_count:
            break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        random_sleep(2, 3)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            no_change_count += 1
            if no_change_count >= 2:
                logging.info("Reached bottom of page")
                break
            random_sleep(5, 6)
        else:
            no_change_count = 0

        last_height = new_height
        attempts += 1

    logging.info(f"Collected {len(answers_data)} answers")

    if len(answers_data) == 0:
        logging.warning("No answers found! Dumping source to 'debug_question.html'")
        with open("debug_question.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

    return answers_data


def crawl_details(target_questions=5, target_answers_per_question=10):
    """
    Main function to crawl questions and answers from a topic.

    Args:
        target_questions: Number of questions to crawl
        target_answers_per_question: Number of answers per question
    """
    driver = setup_driver()
    try:
        topic = get_random_topic()
        if not topic:
            return

        logging.info(f"Selected Topic: {topic['name']} ({topic['url']})")

        topic_url = topic['url']
        if "/hot" not in topic_url:
            topic_url += "/hot"

        if not load_cookies(driver):
            logging.info("No cookies found. Initiating login flow...")
            driver.get("https://www.zhihu.com/signin")
            time.sleep(3)
            if not handle_login_interrupt(driver):
                if not check_login_status(driver):
                    logging.error("Login failed.")
                    return

        logging.info("Navigating to topic...")
        driver.get(topic_url)
        random_sleep(2, 3)

        logging.info("=== Step 1: Crawling question links ===")
        question_urls = crawl_question_links(driver, target_count=target_questions)

        if not question_urls:
            logging.warning("No questions found! Dumping page source to 'debug_topic.html'")
            with open("debug_topic.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return

        logging.info("=== Step 2: Crawling question details and answers ===")
        all_questions = []

        for i, url in enumerate(question_urls):
            logging.info(f"Processing question {i+1}/{len(question_urls)}: {url}")

            try:
                question_data = crawl_question_detail(driver, url)
                question_data["tags"] = [topic['name']]
                all_questions.append(question_data)

                result = {
                    "topic": topic['name'],
                    "topic_url": topic['url'],
                    "questions": all_questions
                }
                with open("zhihu_topic_details.json", "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

                random_sleep(2, 4)

            except PermissionError:
                logging.warning("403 Detected! Attempting recovery...")
                driver.delete_all_cookies()
                driver.get("https://www.zhihu.com/signin")
                random_sleep(2, 3)
                if not handle_login_interrupt(driver):
                    logging.error("Recovery failed.")
                    break
                driver.get(topic_url)
                random_sleep(2, 3)

            except Exception as e:
                logging.error(f"Failed to crawl question {url}: {e}")
                continue

        logging.info(f"Finished crawling. Total questions: {len(all_questions)}")

    except Exception as e:
        logging.error(f"Unexpected error in crawl_details: {e}")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    crawl_details(target_questions=5, target_answers_per_question=10)
