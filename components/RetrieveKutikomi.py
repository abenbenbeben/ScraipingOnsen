from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time, sys


def open_kutikomi(driver,placeName):

    # Googleのホームページを開く
    driver.get("https://www.google.com/maps")

    # 検索ボックスを見つける（新しい方法）
    search_box = driver.find_element(By.NAME, 'q')

    # 検索ボックスに"OpenAI"と入力し、Enterキーを押す
    search_box.send_keys(placeName)
    search_box.send_keys(Keys.RETURN)

    time.sleep(5)  # 5秒間待機

    # クラス名"hh2c6"を持つすべての要素を取得
    buttons = driver.find_elements(By.CLASS_NAME, "hh2c6")

    # 二つ目のボタンをクリックする
    if len(buttons) > 1:  # 要素が2つ以上あることを確認
        buttons[1].click()  # インデックスは0から始まるため、2つ目の要素はインデックス1
    else:
        print("対象のボタンが十分に存在しません。")
        sys.exit()

    # "aria-label"属性が"クチコミを検索"のボタンを見つける
    search_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='クチコミを検索']")
    # ボタンをクリック
    search_button.click()

    time.sleep(3)  # 5秒間待機

def search_kutikomi(driver,search_word):
    # 指定クラス名を持つinput要素を見つける
    input_element = driver.find_element(By.CSS_SELECTOR, "input.LCTIRd.keSVkf.fontBodyLarge")
    # キーワードを入力
    input_element.send_keys(search_word)
    # Enterキーを押す
    input_element.send_keys(Keys.RETURN)

    time.sleep(4)  # 5秒間待機

    # 特定のクラス名を持つdiv要素をすべて見つける
    elements = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf.fontBodyMedium")
    input_element.clear()
    return elements