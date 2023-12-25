from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service
import time
import os
import re
import sqlite3
import socket
import sys
from dotenv import load_dotenv

try:
    socket.create_connection(("localhost", 4444), timeout=5)
except (socket.timeout, socket.error):
    print(f"An error occurred. Please run selenium stand alone.")
    sys.exit(1)

EMAIL = None
PASS = None
MAIN_GROUP_ID = None

EMAIL = os.environ.get("EMAIL")
PASS = os.environ.get("PASS")
MAIN_GROUP_ID = os.environ.get("MAIN_GROUP_ID")
if load_dotenv():
    EMAIL = os.getenv("EMAIL")
    PASS = os.getenv("PASS")
    MAIN_GROUP_ID = os.getenv("MAIN_GROUP_ID")

if not EMAIL or not PASS or not MAIN_GROUP_ID:
    print(
        "Environment not found. Please check if the env has EMAIL, PASS and MAIN_GROUP_ID."
    )
    sys.exit(1)


options = webdriver.ChromeOptions()
options.add_argument("--disable-notifications")
options.add_argument("--ignore-ssl-errors=yes")
options.add_argument("--ignore-certificate-errors")

driver = webdriver.Remote(
    command_executor="http://localhost:4444/wd/hub", options=options
)

# service = Service(executable_path='../webdriver/chromedriver.exe')
# driver = webdriver.Chrome(service=service, options=options)

print("Logging in")
driver.get("https://mbasic.facebook.com/login.php")

username = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='email']"))
)
password = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='pass']"))
)

username.clear()
username.send_keys(EMAIL)
password.clear()
password.send_keys(PASS)
WebDriverWait(driver, 2).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"]'))
).click()
WebDriverWait(driver, 2).until(
    EC.element_to_be_clickable(
        (By.CSS_SELECTOR, 'tr > td > div > form[method="post"] + div a')
    )
).click()
print("Login completed")

driver.switch_to.window(driver.window_handles[0])

main_group_link = f"https://mbasic.facebook.com/groups/{MAIN_GROUP_ID}/"
driver.get(main_group_link)

with sqlite3.connect("posts.db") as connection:
    cursor = connection.cursor()
    cursor.execute(
        """
      CREATE TABLE IF NOT EXISTS posts (
          id INTEGER PRIMARY KEY,
          post_id INTEGER NOT NULL,
          topic_by TEXT,
          topic TEXT
      )
  """
    )

    cursor.execute(
        """
      CREATE TABLE IF NOT EXISTS comments (
          id INTEGER PRIMARY KEY,
          comment_by TEXT NOT NULL,
          comment TEXT NOT NULL,
          post_id INTEGER NOT NULL,
          FOREIGN KEY (post_id) REFERENCES posts(id)
      )
  """
    )

    cursor.execute(
        """
      CREATE TABLE IF NOT EXISTS replies (
          id INTEGER PRIMARY KEY,
          reply_by TEXT NOT NULL,
          reply_to TEXT,
          reply TEXT NOT NULL,
          reply_order INTEGER NOT NULL,
          comment_id INTEGER NOT NULL,
          FOREIGN KEY (comment_id) REFERENCES comments(id)
      )
  """
    )


def replies_scraping():
    try:
        you_is_block = driver.find_element(
            By.XPATH,
            '//div[@title="You’re Temporarily Blocked"]/h2',
        ).text

        print("You’re Temporarily Blocked from viewing replies.")
        sys.exit(1)
    except:
        None
    
    replies = []
    next_page_btn_id = None

    while True:
        box_replies = driver.find_elements(
            By.XPATH,
            '//div[@id="root"]/div[@class]/div[not(@id)]/div[div]',
        )
        if len(box_replies) > 0:
            for idx, box in enumerate(box_replies):
                reply = dict()
                reply["reply_by"] = box.find_element(By.XPATH, 'div/h3').text
                try:
                    reply["reply_to"] = box.find_element(By.XPATH, 'div/div[1]/a').text
                except:
                    None
                reply_array = box.find_elements(By.XPATH, "div/div[1]")
                reply_comment = ''.join([span.text for span in reply_array])
                if not reply.get("reply_to", None) is None: reply_comment = reply_comment.replace(f'{reply.get("reply_to", None)} ','')
                reply["reply"] = reply_comment
                reply["reply_order"] = idx
                
                print(f"{reply['reply_by']}{ ' To ' + reply.get('reply_to', None) if reply.get('reply_to', None) else None } -> reply: {reply['reply']}")
                replies.append(reply)
                
        if next_page_btn_id is None:
            try:
                next_page_btn_id = driver.find_element(By.XPATH, '//div[@id="root"]//div[starts-with(@id, "comment_replies_more_")]').get_attribute('id')
            except:
                break
        try:
            next_page_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clicskable(
                    (
                        By.XPATH,
                        f'//div[@id="root"]//div[@id="{next_page_btn_id}"]/a',
                    )
                )
            )
            next_page_btn.click()
        except:
            break
    return replies

def comments_scraping():
    post_id = re.search(r"/permalink/(\d+)", driver.current_url).group(1)
    comments = []
    next_page_btn_id = None

    while True:
        box_comments = driver.find_elements(
            By.XPATH,
            '//*[@id="m_story_permalink_view"]/div[@id]/div/div[not(@id)]/div[div]',
        )
        if len(box_comments) > 0:
            for box_comment in box_comments:
                comment = dict()
                comment["comment_by"] = box_comment.find_element(By.XPATH, "div/h3").text
                comment["comment"] = box_comment.find_element(By.XPATH, "div/div[1]").text
                print(f"{comment['comment_by']} -> comment: {comment['comment']}")

                replies_href = None
                try:
                    replies_href = box_comment.find_element(
                        By.XPATH, 
                        'div[last()]/div/div//a[contains(text(), "replied")]').get_attribute('href')
                except:
                    None
                if not replies_href is None:
                    driver.execute_script(f"window.open('{replies_href}', '_blank')")
                    time.sleep(1)
                    driver.switch_to.window(driver.window_handles[2])
                    replies = replies_scraping()
                    if len(replies) != 0:
                        comment["replies"] = replies
                    driver.close()
                    time.sleep(1)
                    driver.switch_to.window(driver.window_handles[1])    
                comments.append(comment)

        if next_page_btn_id is None:
            try:
                next_page_btn_id = driver.find_element(
                    By.XPATH,
                    '//*[@id="m_story_permalink_view"]/div[last()]/div/div[not(@id)]/div[a]'
                ).get_attribute('id')
            except:
                break
        try:
            next_page_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, f'//div[@id="root"]//div[@id="{next_page_btn_id}"]/a'))
            )
            next_page_btn.click()
        except:
            break
    print(f"Complete post_id: {post_id}")
    return comments

def post_scraping():
    post_id = re.search(r"/permalink/(\d+)", driver.current_url).group(1)
    post = dict()
    post["post_id"] = post_id
    post["topic"] = driver.find_element(
        By.CSS_SELECTOR,
        "#m_story_permalink_view div:not([id]) > div > div > div",
    ).text
    post["topic_by"] = driver.find_element(
        By.CSS_SELECTOR, "td > header > h3 > span > strong:first-child > a"
    ).text
    post["comments"] = comments_scraping()
    return post


def reset_tab():
    print("Program is restarting.")
    for idx, tab in enumerate(driver.window_handles):
        if idx == 0:
            continue
        driver.switch_to.window(tab)
        driver.close()
    driver.switch_to.window(driver.window_handles[0])
    driver.get(main_group_link)
    print("Restart finished.")


while True:
    anchor_all = driver.find_elements(
        By.XPATH, '//article/footer/div[last()]/a[contains(text(), "Full Story")]'
    )
    anchor_all = [a.get_attribute("href") for a in anchor_all]
    anchor_post_shares = driver.find_elements(
        By.XPATH,
        '//article[descendant::article]/footer/div[last()]/a[contains(text(), "Full Story")]',
    )
    anchor_post_shares = [a.get_attribute("href") for a in anchor_post_shares]
    anchors = list(set(anchor_all) - set(anchor_post_shares))
    if len(anchors) > 0:
        for a in anchors:
            post_id = re.search(r"/permalink/(\d+)", a).group(1)
            with sqlite3.connect("posts.db") as connection:
                cursor = connection.cursor()
                rows = cursor.execute(
                    "SELECT post_id FROM posts WHERE post_id=?", (post_id,)
                ).fetchall()
                if len(rows) != 0:
                    print(f"Already have post_id : {post_id}")
                    continue
            driver.execute_script(f"window.open('{a}', '_blank')")
            time.sleep(1)
            driver.switch_to.window(driver.window_handles[1])
            print(f"Start scraping post_id: {post_id}.")

            post = post_scraping()

            with sqlite3.connect("posts.db") as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO posts (post_id, topic_by, topic) VALUES (?, ?, ?)",
                    (post["post_id"], post["topic_by"], post["topic"]),
                )
                post_id1 = cursor.lastrowid
                comments = post.get("comments", [])
                if len(comments) == 0:
                    continue
                for comment in comments:
                    cursor.execute(
                        "INSERT INTO comments (comment_by, comment, post_id) VALUES (?, ?, ?)",
                        (comment["comment_by"], comment["comment"], post_id1),
                    )
                    comment_id = cursor.lastrowid
                    replies = comment.get("replies", [])
                    if len(replies) == 0:
                        continue
                    for reply in replies:
                        cursor.execute(
                            "INSERT INTO replies (reply_by, reply_to, reply, reply_order, comment_id) VALUES (?, ?, ?, ?, ?)",
                            (reply["reply_by"], reply.get("reply_to", None), reply["reply"], reply['reply_order'], comment_id),
                        )
                connection.commit()
            print(f"Save to database complated as post_id: {post_id}.")

            driver.close()
            time.sleep(1)
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(1)
    try:
        see_more_posts_btn = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    "section + div > a:has(span)",
                )
            )
        )
        see_more_posts_btn.click()
    except:
        print("An error occurred.")
        print(f"Error URL: {driver.current_url}")
        reset_tab()