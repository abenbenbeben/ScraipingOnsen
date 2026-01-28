from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, sys, pprint
import spacy
import unicodedata
import re
import difflib
sys.path.append('../')
from components.SentenceBert import SentenceBertService
from components.ConnectGemini import requestGemini
from components.SpreadSheet import write_spreadsheet

# -----------------------
# 追加：自動選択ユーティリティ
# -----------------------
_PLACE_KEYWORDS_BONUS = ["サウナ", "スパ", "温泉", "銭湯", "スーパー銭湯", "岩盤浴", "浴場"]
_AVOID_HINTS_PENALTY = ["スポンサー", "広告", "HOTEL", "ホテル"]  # 必要なら増やす


def _nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "")).strip()


def _norm_for_match(s: str) -> str:
    s = _nfkc(s).lower()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[‐-–—−ー]", "-", s)
    s = re.sub(r"[()（）\[\]【】『』「」]", "", s)
    return s


def _safe_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    try:
        el.click()
    except (ElementClickInterceptedException, StaleElementReferenceException):
        driver.execute_script("arguments[0].click();", el)


def _is_place_detail_page(driver) -> bool:
    # URL /place/ は詳細ページであることが多い
    try:
        if "/place/" in (driver.current_url or ""):
            return True
    except Exception:
        pass

    # 「クチコミ」タブ(button.hh2c6)が出ていれば詳細ページ寄り
    btns = driver.find_elements(By.CSS_SELECTOR, "button.hh2c6")
    for b in btns:
        aria = b.get_attribute("aria-label") or ""
        if "クチコミ" in aria and b.is_displayed():
            return True
    return False


def _has_result_list(driver) -> bool:
    # 検索結果カード（div.Nv2PK）が取れれば一覧
    cards = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
    if any(c.is_displayed() for c in cards):
        return True
    # フォールバック：a.hfpxzc が複数取れれば一覧の可能性
    links = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
    if len([a for a in links if a.is_displayed()]) >= 2:
        return True
    return False


def _collect_candidates(driver):
    """
    候補一覧から (clickable, name, text) を集める
    """
    items = []

    cards = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
    for card in cards:
        if not card.is_displayed():
            continue
        try:
            a = card.find_element(By.CSS_SELECTOR, "a.hfpxzc")
        except Exception:
            continue

        name = _nfkc(a.get_attribute("aria-label") or "")
        if not name:
            # name要素が取れる場合
            try:
                name = _nfkc(card.find_element(By.CSS_SELECTOR, "div.qBF1Pd").text)
            except Exception:
                # 最低限：カード先頭行
                name = _nfkc((card.text or "").split("\n")[0])

        text = _nfkc(card.text or "")
        items.append({"click": a, "name": name, "text": text})

    if items:
        return items

    # 最後の保険：リンクだけ拾う
    links = [a for a in driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc") if a.is_displayed()]
    for a in links:
        items.append({
            "click": a,
            "name": _nfkc(a.get_attribute("aria-label") or a.text or ""),
            "text": _nfkc(a.get_attribute("aria-label") or a.text or ""),
        })
    return items


def _split_query(placeName: str):
    """
    placeName が「施設名 + 市区町村」みたいな場合を想定して分離
    例: "Ledian Spa 麻布十番店 港区" -> name_part="Ledian Spa 麻布十番店", loc_words=["港区"]
    """
    s = _nfkc(placeName)
    parts = re.split(r"\s+", s)
    loc_words = []
    name_words = []

    for p in parts:
        if re.search(r"(都|道|府|県|市|区|町|村)$", p):
            loc_words.append(p)
        else:
            name_words.append(p)

    name_part = " ".join(name_words).strip() if name_words else s
    return name_part, loc_words


def _score_candidate(placeName: str, cand_name: str, cand_text: str) -> float:
    q_name, loc_words = _split_query(placeName)

    qn = _norm_for_match(q_name)
    cn = _norm_for_match(cand_name)

    if not cn:
        return -1e9

    # スポンサーは強く避ける（画像のケース対策）
    if "スポンサー" in cand_text:
        return -1e9

    # ベース：名称の類似度
    sim = difflib.SequenceMatcher(None, qn, cn).ratio()  # 0..1
    score = sim * 100.0

    # クエリ（元placeName）に含まれてた市区町村が、カード文面に出ていれば加点
    for lw in loc_words:
        if lw and lw in cand_text:
            score += 6.0

    # サウナ/温泉っぽいワードがカード内にあれば加点（温浴施設向け）
    for kw in _PLACE_KEYWORDS_BONUS:
        if kw in cand_text:
            score += 4.0

    # 避けたいヒント（ホテル等）に軽い減点（必要なら調整）
    for bad in _AVOID_HINTS_PENALTY:
        if bad in cand_text and bad not in placeName:
            score -= 5.0

    # 完全包含にボーナス
    if qn and qn in cand_name:
        score += 8.0

    return score


def _click_best_candidate(driver, placeName: str, timeout_each=12) -> bool:
    candidates = _collect_candidates(driver)
    if not candidates:
        return False

    scored = []
    for it in candidates:
        s = _score_candidate(placeName, it["name"], it["text"])
        scored.append((s, it))

    scored.sort(key=lambda x: x[0], reverse=True)

    # 上位から試す（最大5件）
    for rank, (s, it) in enumerate(scored[:5], start=1):
        if s < 30:  # 低すぎる候補しかないなら諦め（必要なら調整）
            break

        try:
            # デバッグログ（不要なら消してOK）
            print(f"✅ try candidate#{rank} score={s:.1f} name='{it['name']}'")

            _safe_click(driver, it["click"])

            WebDriverWait(driver, timeout_each).until(lambda d: _is_place_detail_page(d))
            return True
        except Exception as e:
            print(f"⚠️ candidate#{rank} failed: {e}")
            # 一覧へ戻って次を試す
            try:
                driver.back()
                WebDriverWait(driver, 10).until(lambda d: _has_result_list(d) or _is_place_detail_page(d))
            except Exception:
                pass

    return False


def _click_reviews_tab(driver, timeout=12) -> bool:
    """
    詳細ページで「クチコミ」タブ(button.hh2c6)をクリック
    """
    end = time.time() + timeout
    while time.time() < end:
        btns = driver.find_elements(By.CSS_SELECTOR, "button.hh2c6")
        filtered = [
            b for b in btns
            if b.is_displayed() and ("クチコミ" in (b.get_attribute("aria-label") or ""))
        ]
        if filtered:
            _safe_click(driver, filtered[0])
            return True
        time.sleep(0.5)
    return False


# -----------------------
# 差し替え：open_kutikomi（placenumなし）
# -----------------------
def open_kutikomi(driver, placeName):
    driver.get("https://www.google.com/maps")

    search_box = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.NAME, "q"))
    )
    search_box.clear()
    search_box.send_keys(placeName)
    search_box.send_keys(Keys.RETURN)

    # 「詳細ページ」か「一覧」どちらかが出るまで待つ
    try:
        WebDriverWait(driver, 15).until(lambda d: _is_place_detail_page(d) or _has_result_list(d))
    except TimeoutException:
        print(placeName + " : 検索結果が安定せず判定できません")
        return False

    # 一覧なら、自動でベスト候補をクリックして詳細へ
    if not _is_place_detail_page(driver):
        ok = _click_best_candidate(driver, placeName, timeout_each=15)
        if not ok:
            print(placeName + " : 同一名称あり/候補選択失敗")
            return False

    # 詳細ページでクチコミタブを開く
    if not _click_reviews_tab(driver, timeout=12):
        print(placeName + " : クチコミボタンが見つかりません")
        return False

    time.sleep(3)
    return True



def click_kutikomi_search_button(driver, timeout=10) -> bool:
    # まずは aria-label / data-value で直指定（最優先）
    xpaths = [
        "//button[@aria-label='クチコミを検索']",
        "//button[@data-value='クチコミを検索']",
        "//button[@data-tooltip='クチコミを検索']",
        "//button[contains(@aria-label,'クチコミ') and contains(@aria-label,'検索')]",
    ]

    for xp in xpaths:
        try:
            btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)

            try:
                btn.click()
            except (ElementClickInterceptedException, StaleElementReferenceException):
                driver.execute_script("arguments[0].click();", btn)

            return True
        except TimeoutException:
            continue

    # フォールバック：S9kvJbの中から aria-label が一致する「表示されているもの」を探してクリック
    buttons = driver.find_elements(By.CSS_SELECTOR, "button.S9kvJb")
    for b in buttons:
        if (b.get_attribute("aria-label") == "クチコミを検索"
            and b.is_displayed()
            and b.is_enabled()):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", b)
            driver.execute_script("arguments[0].click();", b)
            return True

    return False


def search_kutikomi(driver, search_word, forcount):
    if forcount == 0:
        ok = click_kutikomi_search_button(driver, timeout=15)
        if not ok:
            print("虫眼鏡（クチコミを検索）が見つからない / クリックできませんでした")

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
        systemContent = f"以下の口コミを参考に、この施設に、{search_word}がある場合は1ない場合は0と回答して。回答例を遵守。"
        data_string = "\n口コミ:".join(f"{x}" for x in temp_sentences)
        print("口コミ:" + data_string)
        userContent = "回答例: {'result': 1}\n\n" + "口コミ:" + data_string

        raw_result = requestGemini(systemContent, userContent)

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

    temp_sentences.pop(0) # 「〇〇は無し」の文を削除

    result = {
        "count": count,
        "note": note if note is not None else None,
        "reviews": temp_sentences,
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


# 特徴文章の生成
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

    # 口コミ文のリスト
    temp_sentences = []
        
    for index, review in enumerate(reviews, start=1):
        temp_sentences.append(review.text)
        
        # print(f"{index}. {review_text_lower} (Contains '{search_word_lower}': {contains_word})")

    systemContent = f"以下の口コミから、温泉施設のプラスになる情報を取捨選択して3行にまとめて"
    data_string = "\n口コミ:".join(f"{x}" for x in temp_sentences)
    userContent = "口コミ:" + data_string

    gptResult = requestGemini(systemContent, userContent)

    print("=======特徴文章========================")
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
