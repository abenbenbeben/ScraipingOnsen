from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys



def RetrieveCost(driver, PlefectureName, PlaceName):
    driver.get("https://www.supersento.com")
    link_prefecture = driver.find_element(By.LINK_TEXT, PlefectureName)
    href_prefecture = link_prefecture.get_attribute('href')

    driver.get(href_prefecture)
    link_OnsenName = driver.find_element(By.LINK_TEXT, PlaceName)
    href_OnsenName = link_OnsenName.get_attribute('href')
    
    driver.get(href_OnsenName)
    # テーブルを見つける
    table = driver.find_element(By.CSS_SELECTOR, 'table.ryokin_box')

    # 各行のデータを取得する
    rows = table.find_elements(By.TAG_NAME, 'tr')

    # 取得したい情報を保存するためのリストを初期化
    data = []

    # 行ごとにループ
    for row in rows:
        # 各セルのテキストを取得
        cells = row.find_elements(By.TAG_NAME, 'td')
        row_data = [cell.text.replace('\n', ' ') for cell in cells]
        data.append(row_data)
    print(data)
    
    return data

if __name__ == "__main__":
    driver = webdriver.Chrome()
    PlaceName = "仙川 湯けむりの里"
    PlefectureName = "東京都"
    RetrieveCost(driver,PlefectureName,PlaceName)