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



def search_photos(query, api_key, cse_id, website_url):
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&cx={cse_id}&key={api_key}&searchType=image"
    response = requests.get(url)
    results = response.json()
    # IPアドレスのエラー時に出力する。
    if 'error' in results and results['error']['code'] == 403:
        print(results)
    else:
        return [item['link'] for item in results.get('items', []) if item['link'].startswith(website_url)]





# webスクレイピングで画像取得する場合の実行関数
if __name__ == "__main__":
    #driver = webdriver.Chrome()
    website_url = 'https://saunarium-lava.com/'  # スーパー銭湯のURLを指定
    # photos = get_photos_from_website(website_url)
    api_key = os.getenv("PLACES_API_KEY")
    cse_id = 'e710a5adbb57440b4'
    query = 'サウナリウム高円寺'
    photos = search_photos(query, api_key, cse_id, website_url)
    for photo in photos:
        print(photo)



