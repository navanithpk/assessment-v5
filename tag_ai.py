import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ================= CONFIG =================
START_ID = 1344
END_ID = 600
BASE_URL = "http://127.0.0.1:8000/questions/edit/{}"

SUCCESS_TEXT = "✓ Suggested:"
TIMEOUT = 40
MAX_RETRIES = 3
# =========================================


def wait_for_new_success(driver, previous_count):
    WebDriverWait(driver, TIMEOUT).until(
        lambda d: d.page_source.count(SUCCESS_TEXT) > previous_count
    )


def ai_click_with_retry(driver, button, label):
    """
    Click AI button and wait for a NEW success toast.
    Retry up to MAX_RETRIES times.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            prev = driver.page_source.count(SUCCESS_TEXT)
            WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable(button))
            button.click()
            wait_for_new_success(driver, prev)
            print(f"✅ {label} succeeded (attempt {attempt})")
            return True
        except Exception:
            print(f"⚠️ {label} failed (attempt {attempt})")
            time.sleep(1)

    print(f"❌ {label} failed after {MAX_RETRIES} retries")
    return False


def wait_for_los_to_render(driver, timeout=15):
    """
    Wait until LO checkboxes are rendered OR placeholder disappears.
    """
    WebDriverWait(driver, timeout).until(
        lambda d: (
            len(d.find_elements(By.CSS_SELECTOR, "#loBox input[type='checkbox']")) > 0
            or "Select a topic to load learning objectives" not in d.page_source
        )
    )


def los_already_exist(driver):
    """
    Checks if any Learning Objective checkbox is already checked.
    MUST be called only after wait_for_los_to_render.
    """
    checked = driver.find_elements(
        By.CSS_SELECTOR,
        "#loBox input[type='checkbox']:checked"
    )
    return len(checked) > 0



def main():
    options = webdriver.ChromeOptions()
    options.debugger_address = "127.0.0.1:9222"

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, TIMEOUT)

    print("✅ Attached to existing Chrome")

    current_tab = driver.current_window_handle

    for qid in range(START_ID, END_ID - 1, -1):
        print(f"\n➡️ Processing Question {qid}")

        driver.switch_to.window(current_tab)
        driver.get(BASE_URL.format(qid))

        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "aiTopicBtn")))
        time.sleep(0.5)

        # 1️⃣ Remove iframe focus
        driver.execute_script("""
            document.elementFromPoint(
                window.innerWidth / 2,
                window.innerHeight / 2
            ).click();
        """)
        time.sleep(0.3)

        # 2️⃣ AI Suggest Topic (always)
        topic_btn = driver.find_element(By.ID, "aiTopicBtn")
        print("🤖 AI Suggest Topic")
        if not ai_click_with_retry(driver, topic_btn, "Topic AI"):
            print("🚫 Skipping question due to Topic AI failure")
            continue

        time.sleep(0.7)  # allow topic → LO dependency settle

        # 3️⃣ AI Suggest Learning Objectives (only if needed)
        if los_already_exist(driver):
            print("⏭️ LOs already exist — skipping LO AI")
        else:
            lo_btn = driver.find_element(By.ID, "aiLOBtn")
            print("🤖 AI Suggest Learning Objectives")
            if not ai_click_with_retry(driver, lo_btn, "LO AI"):
                print("🚫 Skipping save due to LO AI failure")
                continue

        time.sleep(0.5)

        # 4️⃣ Save
        save_btn = driver.find_element(By.CSS_SELECTOR, "button.btn.green")
        WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable(save_btn))
        save_btn.click()
        print("💾 Saved")

        time.sleep(1.2)  # allow close / redirect

    print("✅ Finished")


if __name__ == "__main__":
    main()
