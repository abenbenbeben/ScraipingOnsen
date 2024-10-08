from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time, sys, pprint
import spacy
sys.path.append('../')
from components.SentenceBert import SentenceBertService
from components.ConnectChatGpt import requestGpt
from components.SpreadSheet import write_spreadsheet

def open_kutikomi(driver,placeName, placenum=None):

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

    if placenum is not None:
        search_links = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
        search_links[placenum].click()
        time.sleep(3)
    

    search_buttons = driver.find_elements(By.CSS_SELECTOR, "button.hh2c6")
    print("search_buttons: " + str(len(search_buttons)))
    filtered_buttons = [button for button in search_buttons if "クチコミ" in button.get_attribute("aria-label")]

    # 3つ目or4つ目の要素を抽出
    # if len(search_buttons) == 3:
    #     search_button = search_buttons[1]
    # elif len(search_buttons) == 4:
    #     search_button = search_buttons[2]
    # elif len(search_buttons) >= 5: # ホテルタイプ用
    #     search_button = search_buttons[3]
    # else:
    #     print(placeName + " : 同一名称あり")
    #     return False

    # ボタンをクリック
    if(len(filtered_buttons)==0):
        print(placeName + " : 同一名称あり")
        return False
    else:
        filtered_buttons[0].click()
        
    time.sleep(3)  # 5秒間待機

    return True

def search_kutikomi(driver,search_word,forcount):
    if(forcount==0):
        # 虫眼鏡をクリック
        appearinput_elements = driver.find_elements(By.CSS_SELECTOR, "button.g88MCb.S9kvJb[data-value='クチコミを検索']")
        # 2つ目の要素虫眼鏡を抽出
        print(len(appearinput_elements))
        if len(appearinput_elements) == 1:
            appearinput_element = appearinput_elements[0]
            appearinput_element.click()
        else:
            print("虫眼鏡がありませんでした。")

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


    reviews = driver.find_elements(By.CSS_SELECTOR, 'span.wiI7pd')
    no_item_div = driver.find_elements(By.CSS_SELECTOR, 'div.AA3gcf')

    print(f"review: {len(reviews)}")
    print(f"no_item_div: {len(no_item_div)}")


    # 口コミ文を含む要素をすべて検索
    while(len(reviews)==0 and len(no_item_div)<1):
        print("ロード中、再取得")
        time.sleep(4)
        reviews = driver.find_elements(By.CSS_SELECTOR, 'span.wiI7pd')
        no_item_div = driver.find_elements(By.CSS_SELECTOR, 'div.AA3gcf')

    # 含まれている口コミの数をカウントする変数
    count = 0
    note = None
    search_word_lower = search_word.lower()

    nlp = spacy.load("ja_core_news_sm")

    # 類似度を計算する文のリスト
    sentences_to_compare = []
    temp_sentences = []
    temp_sentences.append(f"{search_word}は無し")
        
    for index, review in enumerate(reviews, start=1):
        review_text = review.text
        review_text_lower = review_text.lower()
        doc = nlp(review_text_lower)

        contains_word = "No"
        if search_word_lower in review_text_lower:
            # 否定的な文脈があるかチェック
            negative_context = False
            
            for sentence in doc.sents:
                if search_word_lower in sentence.text:
                    temp_sentences.append(sentence.text)
            sentences_to_compare.append((temp_sentences, negative_context))
        
        # print(f"{index}. {review_text_lower} (Contains '{search_word_lower}': {contains_word})")


    if(len(temp_sentences)==1):
        count = 0
    elif(len(temp_sentences) >= 2 and len(temp_sentences) <= 3):
        temp_sentences.pop(0)
        systemContent = f"以下の口コミを参考に、{search_word}がある場合は1ない場合は0と回答して。回答例を遵守。"
        data_string = "\n口コミ:".join(f"{x}" for x in temp_sentences)
        print("口コミ:" + data_string)
        userContent = "回答例: {'result': 1}\n\n" + "口コミ:" + data_string

        raw_result = requestGpt(systemContent,userContent)

        print(raw_result)

        note = ",\n".join(f"{x}" for x in temp_sentences)
        try:
            # 辞書型に変換を試みる
            result_gpt = eval(raw_result)
            pprint.pprint(result_gpt["result"])
            count = result_gpt["result"]
        except (SyntaxError, ValueError):
            result_gpt = raw_result
            count = 0
        

    else:
        result = SentenceBertService(temp_sentences)
        result.pop(0) # 最初の文章を除外
        for item in result:
            if item["sim"]>=0.5:
                count = count - 1
            else:
                count = count + 1


    input_element.clear()

    result = {
        "count": count,
        "note": note if note is not None else None,
        "reviews": temp_sentences.pop(0),
    }

    return result


def search_kutikomi_rr(driver,search_word,forcount):
    if(forcount==0):
        # 虫眼鏡をクリック
        appearinput_elements = driver.find_elements(By.CSS_SELECTOR, "button.g88MCb.S9kvJb[data-value='クチコミを検索']")
        # 2つ目の要素虫眼鏡を抽出
        if len(appearinput_elements) == 1:
            appearinput_element = appearinput_elements[0]
            appearinput_element.click()
        else:
            print("虫眼鏡がありませんでした。")

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


    reviews = driver.find_elements(By.CSS_SELECTOR, 'span.wiI7pd')
    no_item_div = driver.find_elements(By.CSS_SELECTOR, 'div.AA3gcf')


    # 口コミ文を含む要素をすべて検索
    while(len(reviews)==0 and len(no_item_div)<1):
        print("ロード中、再取得")
        time.sleep(4)
        reviews = driver.find_elements(By.CSS_SELECTOR, 'span.wiI7pd')
        no_item_div = driver.find_elements(By.CSS_SELECTOR, 'div.AA3gcf')

    # 含まれている口コミの数をカウントする変数
    count = 0
    note = None
    search_word_lower = search_word.lower()

    nlp = spacy.load("ja_core_news_sm")

    # 類似度を計算する文のリスト
    sentences_to_compare = []
    temp_sentences = []
    temp_sentences.append(f"{search_word}は無し")
        
    for index, review in enumerate(reviews, start=1):
        review_text = review.text
        review_text_lower = review_text.lower()
        doc = nlp(review_text_lower)

        if search_word_lower in review_text_lower:
            # 否定的な文脈があるかチェック
            negative_context = False
            
            for sentence in doc.sents:
                if search_word_lower in sentence.text:
                    temp_sentences.append(sentence.text)
            sentences_to_compare.append((temp_sentences, negative_context))
        
        # print(f"{index}. {review_text_lower} (Contains '{search_word_lower}': {contains_word})")

    input_element.clear()

    temp_sentences.pop(0)

    result = {
        "reviews": temp_sentences,
    }

    return result

def search_feature(driver):

    # 特定のクラス名を持つdiv要素をすべて見つける
    elements = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf.fontBodyMedium")

    reviews = driver.find_elements(By.CSS_SELECTOR, 'span.wiI7pd')
    no_item_div = driver.find_elements(By.CSS_SELECTOR, 'div.AA3gcf')

    # 口コミ文を含む要素をすべて検索
    while(len(reviews)==0 and len(no_item_div)<1):
        print("ロード中、再取得")
        time.sleep(4)
        reviews = driver.find_elements(By.CSS_SELECTOR, 'span.wiI7pd')
        no_item_div = driver.find_elements(By.CSS_SELECTOR, 'div.AA3gcf')

    # 含まれている口コミの数をカウントする変数
    count = 0
    note = None

    nlp = spacy.load("ja_core_news_sm")

    # 口コミ文のリスト
    temp_sentences = []
        
    for index, review in enumerate(reviews, start=1):
        temp_sentences.append(review.text)
        
        # print(f"{index}. {review_text_lower} (Contains '{search_word_lower}': {contains_word})")

    systemContent = f"以下の口コミから、温泉施設のプラスになる情報を取捨選択して3行にまとめて"
    data_string = "\n口コミ:".join(f"{x}" for x in temp_sentences)
    userContent = "口コミ:" + data_string

    gptResult = requestGpt(systemContent,userContent)

    print("=======特徴文章=========================")
    pprint.pprint(gptResult)
    print("======================================")

    return gptResult



if __name__ == "__main__":
    driver = webdriver.Chrome()
    placeName = "湯乃市 鎌ヶ谷店"
    search_word = "サウナ"
    open_kutikomi(driver,placeName)
    # search_kutikomi_rr(driver,search_word,0)
    search_feature(driver)
