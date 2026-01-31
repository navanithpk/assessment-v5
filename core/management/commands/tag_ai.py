import time
import threading
import logging
import keyboard

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
START_ID = 1544
END_ID = 600
BASE_URL = "http://127.0.0.1:8000/questions/edit/{}"

MAX_RETRIES = 3
WAIT_TIMEOUT = 20  # seconds

SUCCESS_TEXT = "✓ Suggested:"
FAILURE_TEXT = "All AI services failed."

# =========================================


# ---------- Logging ----------
logging.basicConfig(
    filename="ai_tagging_failures.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

# ---------- Control Flags ----------
paused = True
stopped = False


def listen_keys():
    global paused, stopped
    print("\nControls: [S] Start/Resume | [P] Pause | [Q] Quit\n")

    while not stopped:
        if keyboard.is_pressed("s"):
            paused = False
            print("▶️  Running")
            time.sleep(0.5)

        elif keyboard.is_pressed("p"):
            paused = True
            print("⏸️  Paused")
            time.sleep(0.5)

        elif keyboard.is_pressed("q"):
            stopped = True
            print("🛑 Stopping gracefully…")
            break


def wait_for_result(driver):
    """Wait until success or failure message appears"""
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        lambda d: SUCCESS_TEXT in d.page_source or FAILURE_TEXT in d.page_source
    )

    if SUCCESS_TEXT in driver.page_source:
        return True
    return False


def click_with_retry(driver, button_text, question_id):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            button = WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//button[contains(., '{button_text}')]")
                )
            )
            button.click()

            success = wait_for_result(driver)
            if success:
                return True

            print(f"⚠️  {button_text} failed (attempt {attempt})")

        except Exception as e:
            print(f"❌ Error clicking {button_text}: {e}")

        time.sleep(2)

    logging.info(f"Question {question_id} | {button_text} FAILED after {MAX_RETRIES} retries")
    return False


def main():
    global paused, stopped

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install())
    )
    driver.maximize_window()

    print("🔐 Please log in to Django once, then press S to start.")
    driver.get("http://127.0.0.1:8000/accounts/login/")

    for qid in range(START_ID, END_ID - 1, -1):
        if stopped:
            break

        while paused:
            time.sleep(0.2)

        url = BASE_URL.format(qid)
        print(f"\n➡️  Processing Question {qid}")
        driver.get(url)

        time.sleep(1)

        ok_topic = click_with_retry(driver, "🤖 AI Suggest Topic", qid)
        ok_lo = click_with_retry(driver, "🤖 AI Suggest Learning Objectives", qid)

        if ok_topic and ok_lo:
            try:
                save_btn = WebDriverWait(driver, WAIT_TIMEOUT).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(., '💾 Save')]")
                    )
                )
                save_btn.click()
                print("💾 Saved")

            except Exception as e:
                logging.info(f"Question {qid} | SAVE FAILED | {e}")
        else:
            print("🚫 Skipped save due to failures")

        time.sleep(1)

    driver.quit()
    print("✅ Done")


# ---------- Run ----------
key_thread = threading.Thread(target=listen_keys, daemon=True)
key_thread.start()

main()
