import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_peta():
    file_path = 'brands.json'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            brands = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        brands = []

    existing_names = {b['name'] for b in brands}
    new_brands_count = 0

    options = Options()
    # Usunięto "--headless=new", aby okno przeglądarki było widoczne
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    print("Uruchamianie przeglądarki...")
    driver = webdriver.Chrome(options=options)

    try:
        for page in range(1, 2):
            url = f"https://crueltyfree.peta.org/companies-do-test/?per_page=1000"
            driver.get(url)
            
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul.search-results li"))
                )
            except Exception as e:
                print(f"Błąd/Timeout na stronie {page}. Sprawdzam kolejną...")
                continue

            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            items = soup.select('ul.search-results li')
            
            print(f" -> Znaleziono {len(items)} elementów na stronie {page}.")
            
            for item in items:
                a_tag = item.select_one('a.link')
                if not a_tag:
                    continue
                    
                name = a_tag.text.strip()
                
                left_div = item.select_one('div.left')
                is_cf = True

                if is_cf and name not in existing_names:
                    brands.append({
                        "name": name,
                        "cruelty_free": False
                    })
                    existing_names.add(name)
                    new_brands_count += 1

                    
    finally:
        driver.quit()

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("[\n")
        for i, brand in enumerate(brands):
            line = json.dumps(brand, ensure_ascii=False, separators=(', ', ': '))
            if i < len(brands) - 1:
                f.write(f"  {line},\n")
            else:
                f.write(f"  {line}\n")
        f.write("]\n")

    print(f"Zakończono! Dodano {new_brands_count} nowych marek cruelty-free.")

if __name__ == '__main__':
    scrape_peta()