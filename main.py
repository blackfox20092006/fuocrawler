import re
import os
import sys
import threading
import json
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from concurrent.futures import ThreadPoolExecutor, as_completed

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

baseurl = 'https://fuoverflow.com'
print_lock = threading.Lock()

EXCLUDE_SUBJECTS_LIST = [
    "BDI301c", "DRS301", "DWB301", "ENM402", "ENW493c", "EPE301", "EPT24", "FRS401", "IAR401", "ITB302c",
    "PLT", "PRE301", "PRN222", "PRX301", "SDN302", "COV111", "COV121", "COV131", "ENT103", "ENT104",
    "ENT203", "ENT303", "ENT304", "ENT403", "ENT404", "ENT503", "EPT202"
]
EXCLUDE_SUBJECTS = {s.replace(" ", "").upper() for s in EXCLUDE_SUBJECTS_LIST}


def filter1(data):
    ans = []
    for i in data:
        ans.append(i.split('/')[-2])
    return ans


def getlink(text, data):
    ans = []
    pattern = r'/[^/\n]+(?:/[^/\n]+)+/?'
    matches = re.findall(pattern, data)
    for i in matches:
        if i.find(f'/{text}/') != -1:
            ans.append(i.split(' ')[0])
    return [i.replace('"', '') for i in ans]


def getlink2(text, html_source):
    pattern = re.compile(
        rf'href=["\'](/(?:{re.escape(text)})/(?:[^/"\'>]+/)+)["\']',
        flags=re.IGNORECASE
    )
    matches = pattern.findall(html_source)
    seen, out = set(), []
    for m in matches:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def get_options():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return options


def select(driver, type, value):
    for _ in range(100):
        try:
            if type == 'id':
                return driver.find_element(By.ID, value)
            elif type == 'xpath':
                return driver.find_element(By.XPATH, value)
            elif type == 'name':
                return driver.find_element(By.NAME, value)
            elif type == 'css':
                return driver.find_element(By.CSS_SELECTOR, value)
            elif type == 'text':
                return driver.find_element(By.PARTIAL_LINK_TEXT, value)
        except:
            sleep(0.1)
    return 'NotFound'


def create_and_login_driver(login_details, thread_id):
    user, password = login_details
    with print_lock:
        print(f"{bcolors.OKBLUE}[Thread-{thread_id}] Initializing Chrome driver for {user}...{bcolors.ENDC}")
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=get_options())
    except Exception as e:
        with print_lock:
            print(f"{bcolors.FAIL}[Thread-{thread_id}] FAILED to initialize driver: {e}{bcolors.ENDC}")
        return None
    try:
        driver.get("https://fuoverflow.com/attachments/q58-webp.231245/")
        with print_lock:
            print(f"{bcolors.WARNING}[Thread-{thread_id}] Attempting login as {user}...{bcolors.ENDC}")
        select(driver, 'name', 'login').send_keys(user)
        select(driver, 'name', 'password').send_keys(password)
        select(driver, 'xpath', '//*[@id="top"]/div[3]/div/div[2]/div/div/div[2]/form/div[1]/dl/dd/div/div[2]/button').click()
        with print_lock:
            print(f"{bcolors.OKGREEN}[Thread-{thread_id}] Login successful for {user}!{bcolors.ENDC}")
        return driver
    except Exception as e:
        with print_lock:
            print(f"{bcolors.FAIL}[Thread-{thread_id}] Login FAILED for {user}: {e}{bcolors.ENDC}")
        driver.quit()
        return None


def worker_scan_threads(driver, subject_link, thread_id):
    if driver is None:
        return subject_link, []
    subject_code = subject_link.split('/')[2]
    with print_lock:
        print(f"{bcolors.OKCYAN}[Thread-{thread_id}] Scanning subject: {bcolors.BOLD}{subject_code}{bcolors.ENDC}")
    tmp2 = []
    try:
        for j in range(1, 6):
            page_url = baseurl + f"{subject_link}page-{j}"
            with print_lock:
                print(f"[Thread-{thread_id}] -> Opening page: {j} ({page_url})")
            driver.get(page_url)
            tmphtml = driver.page_source
            tmp3 = getlink('threads', tmphtml)
            for k in tmp3:
                if k not in tmp2:
                    tmp2.append(k)
        with print_lock:
            print(f"{bcolors.OKGREEN}[Thread-{thread_id}] -> Found {bcolors.BOLD}{len(tmp2)}{bcolors.ENDC}{bcolors.OKGREEN} threads for subject {subject_code}.{bcolors.ENDC}")
    except Exception as e:
        with print_lock:
            print(f"{bcolors.FAIL}[Thread-{thread_id}] -> Error scanning {subject_code}: {e}{bcolors.ENDC}")
    return subject_link, tmp2


def worker_scan_attachments(driver, subject_code, thread_links, thread_id):
    if driver is None:
        return subject_code, []
    with print_lock:
        print(f"{bcolors.OKCYAN}[Thread-{thread_id}] Fetching attachments for subject: {bcolors.BOLD}{subject_code}{bcolors.ENDC}")
        print(f"[Thread-{thread_id}] -> Subject {subject_code} has {bcolors.BOLD}{len(thread_links)}{bcolors.ENDC} threads to scan.")
    tmpurl = []
    try:
        for link in thread_links:
            thread_url = baseurl + link
            with print_lock:
                print(f"[Thread-{thread_id}] -> Opening thread: {link}")
            driver.get(thread_url)
            tmphtml = driver.page_source
            attachments_found = getlink2('attachments', tmphtml)
            if attachments_found:
                with print_lock:
                    print(f"{bcolors.OKGREEN}[Thread-{thread_id}] => Crawl Success! Found {len(attachments_found)} attachments.{bcolors.ENDC}")
            tmpurl.extend(attachments_found)
        unique_attachments = []
        for link in tmpurl:
            if link not in unique_attachments:
                unique_attachments.append(link)
        with print_lock:
            print(f"{bcolors.OKBLUE}[Thread-{thread_id}] -> [SUBJECT SUMMARY {subject_code}]: Found {bcolors.BOLD}{len(unique_attachments)}{bcolors.ENDC}{bcolors.OKBLUE} unique attachments.{bcolors.ENDC}")
    except Exception as e:
        with print_lock:
            print(f"{bcolors.FAIL}[Thread-{thread_id}] -> Error fetching attachments for {subject_code}: {e}{bcolors.ENDC}")
        return subject_code, []
    return subject_code, unique_attachments


def worker_take_screenshots(driver, subject_name, url_list, thread_id):
    if driver is None:
        return subject_name, 0
    with print_lock:
        print(f"{bcolors.OKCYAN}[Thread-{thread_id}] Processing subject: {bcolors.BOLD}{subject_name}{bcolors.ENDC}")
    current_directory = os.getcwd()
    subject_path = os.path.join(current_directory, subject_name)
    os.makedirs(subject_path, exist_ok=True)
    if not url_list:
        with print_lock:
            print(f"{bcolors.WARNING}[Thread-{thread_id}] No attachments found for {subject_name}. Skipping.{bcolors.ENDC}")
        return subject_name, 0
    with print_lock:
        print(f"[Thread-{thread_id}] -> {bcolors.BOLD}{len(url_list)}{bcolors.ENDC} attachments found. Starting capture...")
    screenshot_counter = 1
    for attachment_url in url_list:
        full_url = baseurl + attachment_url
        file_name = f"{screenshot_counter}.png"
        save_path = os.path.join(subject_path, file_name)
        try:
            with print_lock:
                print(f"[Thread-{thread_id}] Navigating to: {full_url}")
            driver.get(full_url)
            sleep(1)
            driver.save_screenshot(save_path)
            with print_lock:
                print(f"[Thread-{thread_id}] {bcolors.OKGREEN}SUCCESS: Saved {file_name} to {subject_path}{bcolors.ENDC}")
            screenshot_counter += 1
        except Exception as e:
            with print_lock:
                print(f"[Thread-{thread_id}] {bcolors.FAIL}FAILED to capture {full_url}: {e}{bcolors.ENDC}")
    with print_lock:
        print(f"{bcolors.OKBLUE}[Thread-{thread_id}] Finished processing {subject_name}. Captured {screenshot_counter - 1} images.{bcolors.ENDC}")
    return subject_name, screenshot_counter - 1


def main():
    print(f"{bcolors.OKBLUE}Starting crawl process...{bcolors.ENDC}")
    try:
        with open('login.txt', 'r') as f:
            logins = [line.strip().split('|') for line in f if line.strip()]
        if not logins:
            print(f"{bcolors.FAIL}login.txt is empty. Exiting.{bcolors.ENDC}")
            return
        N = len(logins)
        print(f"{bcolors.OKGREEN}Found {N} user accounts in login.txt.{bcolors.ENDC}")
    except FileNotFoundError:
        print(f"{bcolors.FAIL}login.txt not found. Exiting.{bcolors.ENDC}")
        return
    except Exception as e:
        print(f"{bcolors.FAIL}Error reading login.txt: {e}{bcolors.ENDC}")
        return
    print(f"\n{bcolors.HEADER}--- INITIALIZING AND LOGGING IN {N} DRIVERS ---{bcolors.ENDC}")
    driver_pool = []
    with ThreadPoolExecutor(max_workers=N) as executor:
        futures = [executor.submit(create_and_login_driver, logins[i], i) for i in range(N)]
        for future in as_completed(futures):
            driver = future.result()
            if driver:
                driver_pool.append(driver)
    if not driver_pool:
        print(f"{bcolors.FAIL}No drivers were successfully created. Exiting.{bcolors.ENDC}")
        return
    N_success = len(driver_pool)
    print(f"{bcolors.OKGREEN}Successfully created and logged in {N_success} drivers.{bcolors.ENDC}")
    print(f"\n{bcolors.OKCYAN}Fetching subject list using first available driver...{bcolors.ENDC}")
    try:
        driver_pool[0].get('https://fuoverflow.com/categories/subjects/')
        output = driver_pool[0].page_source
        all_subjects_links = [i for i in getlink('forums', output) if len(i.split('/')[2]) in (6, 7)]
        print(f"{bcolors.OKGREEN}Found {bcolors.BOLD}{len(all_subjects_links)}{bcolors.ENDC}{bcolors.OKGREEN} total subjects.{bcolors.ENDC}")
        print(f"\n{bcolors.HEADER}--- FILTERING SUBJECTS ---{bcolors.ENDC}")
        filtered_subject_links = []
        for link in all_subjects_links:
            subject_code = link.split('/')[2].upper()
            if subject_code in EXCLUDE_SUBJECTS:
                print(f"{bcolors.WARNING}-> Filtering out excluded subject (from list): {subject_code}{bcolors.ENDC}")
            elif 'TRANS' in link.upper():
                print(f"{bcolors.WARNING}-> Filtering out excluded subject (contains 'TRANS'): {link}{bcolors.ENDC}")
            else:
                filtered_subject_links.append(link)
        tmp = filtered_subject_links
        print(f"{bcolors.OKGREEN}After filtering, {bcolors.BOLD}{len(tmp)}{bcolors.ENDC}{bcolors.OKGREEN} subjects remaining for scan.{bcolors.ENDC}")
    except Exception as e:
        print(f"{bcolors.FAIL}Failed to fetch subject list: {e}. Exiting.{bcolors.ENDC}")
        for driver in driver_pool:
            driver.quit()
        return
    if not tmp:
        print(f"{bcolors.WARNING}No subjects left to scan after filtering. Exiting.{bcolors.ENDC}")
        for driver in driver_pool:
            driver.quit()
        return
    data = {}
    print(f"\n{bcolors.HEADER}--- STARTING THREAD SCAN (STAGE 1 OF 3) ---{bcolors.ENDC}")
    with ThreadPoolExecutor(max_workers=N_success) as executor:
        futures = []
        for i, subject_link in enumerate(tmp):
            driver_to_use = driver_pool[i % N_success]
            thread_id = i % N_success
            futures.append(executor.submit(worker_scan_threads, driver_to_use, subject_link, thread_id))
        for future in as_completed(futures):
            subject_link, tmp2 = future.result()
            data[subject_link] = tmp2
    main_data = {}
    for i in data.keys():
        main_data[i.split('/')[2]] = []
    tmpkey = "/forums/{}/"
    total_attachments_all_subjects = 0
    print(f"\n{bcolors.HEADER}--- STARTING ATTACHMENT SCAN (STAGE 2 OF 3) ---{bcolors.ENDC}")
    with ThreadPoolExecutor(max_workers=N_success) as executor:
        futures = []
        subject_keys = list(main_data.keys())
        for i, subject_code in enumerate(subject_keys):
            driver_to_use = driver_pool[i % N_success]
            thread_id = i % N_success
            thread_links = data.get(tmpkey.format(subject_code), [])
            futures.append(executor.submit(worker_scan_attachments, driver_to_use, subject_code, thread_links, thread_id))
        for future in as_completed(futures):
            subject_code, unique_attachments = future.result()
            main_data[subject_code] = unique_attachments
            total_attachments_all_subjects += len(unique_attachments)
    print(f"\n{bcolors.HEADER}--- BACKING UP DATA ---{bcolors.ENDC}")
    try:
        with open('main_data_backup.json', 'w', encoding='utf-8') as f:
            json.dump(main_data, f, indent=4, ensure_ascii=False)
        print(f"{bcolors.OKGREEN}Successfully saved backup to main_data_backup.json{bcolors.ENDC}")
    except Exception as e:
        print(f"{bcolors.FAIL}Failed to save backup file: {e}{bcolors.ENDC}")
    print(f"\n{bcolors.BOLD}{bcolors.OKBLUE}GRAND TOTAL: Found {total_attachments_all_subjects} attachments across all scanned subjects.{bcolors.ENDC}")
    print(f"\n{bcolors.HEADER}--- STARTING SCREENSHOT CAPTURE (STAGE 3 OF 3) ---{bcolors.ENDC}")
    with ThreadPoolExecutor(max_workers=N_success) as executor:
        futures = []
        i = 0
        for subject_name, url_list in main_data.items():
            driver_to_use = driver_pool[i % N_success]
            thread_id = i % N_success
            futures.append(executor.submit(worker_take_screenshots, driver_to_use, subject_name, url_list, thread_id))
            i += 1
        for future in as_completed(futures):
            subject_name, count = future.result()
    print(f"\n{bcolors.HEADER}--- ALL STAGES COMPLETE ---{bcolors.ENDC}")
    print(f"{bcolors.OKBLUE}Shutting down all {N_success} drivers...{bcolors.ENDC}")
    for driver in driver_pool:
        try:
            driver.quit()
        except Exception as e:
            with print_lock:
                print(f"{bcolors.WARNING}Error quitting a driver: {e}{bcolors.ENDC}")
    print(f"{bcolors.OKGREEN}All processes finished.{bcolors.ENDC}")


if __name__ == "__main__":
    main()
