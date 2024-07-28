import requests , os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from urllib.parse import urljoin
load_dotenv()

# webスクレイピングで画像を取得する方法
def get_photos_from_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    photos = []
    for img in soup.find_all('img'):
        photo_url = img.get('src')
        if photo_url:
            # 相対URLを絶対URLに変換
            absolute_url = urljoin(url, photo_url)
            photos.append(absolute_url)
    return photos



def search_photos(query, website_url):
    cse_id = 'e710a5adbb57440b4'
    api_key = os.getenv("PLACES_API_KEY")
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&cx={cse_id}&key={api_key}&searchType=image"
    response = requests.get(url)
    results = response.json()
    
    if 'error' in results and results['error']['code'] == 403:
        print(results)
        raise Exception("IPアドレスエラー")
    else:
        items = results.get('items', [])
        if website_url is not None:
            website_links = [item['link'] for item in items if item['link'].startswith(website_url)]
            other_links = [item['link'] for item in items if not item['link'].startswith(website_url)]
            sorted_links = website_links + other_links
        else:
            sorted_links = [item['link'] for item in items]
            
        return sorted_links





# webスクレイピングで画像取得する場合の実行関数
if __name__ == "__main__":
    #driver = webdriver.Chrome()
    website_url = 'https://saunarium-lava.com/'  # スーパー銭湯のURLを指定
    # photos = get_photos_from_website(website_url)
    query = 'サウナリウム高円寺'
    photos = search_photos(query, website_url)
    for photo in photos:
        print(photo)



