from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time, sys


def open_kutikomi(driver,placeName):

    # Googleのホームページを開く
    driver.get("https://www.google.com/maps")

    # 検索ボックスを見つける
    search_box = driver.find_element(By.NAME, 'q')

    search_box.send_keys(placeName)
    search_box.send_keys(Keys.RETURN)

    time.sleep(5)  # 5秒間待機

    # # クラス名"hh2c6"を持つすべての要素を取得
    # buttons = driver.find_elements(By.CLASS_NAME, "hh2c6")

    # # 二つ目のボタンをクリックする
    # if len(buttons) > 1:  # 要素が2つ以上あることを確認
    #     buttons[1].click()  # インデックスは0から始まるため、2つ目の要素はインデックス1
    # else:
    #     print("対象のボタンが十分に存在しません。")
    #     sys.exit()

    # "class"属性が"hh2c6"のボタン要素を見つける
    search_buttons = driver.find_elements(By.CSS_SELECTOR, "button.hh2c6")

    # 3つ目の要素を抽出
    if len(search_buttons) >= 3:
        search_button = search_buttons[2]
    else:
        raise Exception("該当する要素が3つ以上見つかりませんでした")
    # ボタンをクリック
    search_button.click()

    time.sleep(3)  # 5秒間待機

def search_kutikomi(driver,search_word,forcount):
    if(forcount==0):
        # 虫眼鏡をクリック
        appearinput_elements = driver.find_elements(By.CSS_SELECTOR, "button.g88MCb.S9kvJb")
        # 2つ目の要素虫眼鏡を抽出
        if len(appearinput_elements) >= 2:
            appearinput_element = appearinput_elements[1]
        else:
            raise Exception("該当する要素が2つ以上見つかりませんでした")

        appearinput_element.click()

    time.sleep(3)  # 5秒間待機
    # 指定クラス名を持つinput要素を見つける
    input_element = driver.find_element(By.CSS_SELECTOR, "input.LCTIRd.keSVkf.fontBodyLarge")
    # キーワードを入力
    input_element.send_keys(search_word)
    # Enterキーを押す
    input_element.send_keys(Keys.RETURN)

    time.sleep(4)  # 5秒間待機

    # 特定のクラス名を持つdiv要素をすべて見つける
    elements = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf.fontBodyMedium")

    # 口コミ文を含む要素をすべて検索
    reviews = driver.find_elements(By.CSS_SELECTOR, 'span.wiI7pd')

    # 口コミ文を表示し、それぞれに番号を振る
    for index, review in enumerate(reviews, start=1):
        print(f"{index}. {review.text}")


    input_element.clear()


    return elements


if __name__ == "__main__":
    driver = webdriver.Chrome()
    placeName = "沼部公園"
    search_word = "子供"
    open_kutikomi(driver,placeName)
    search_kutikomi(driver,search_word)