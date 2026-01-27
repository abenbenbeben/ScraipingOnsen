from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _xpath_literal(s: str) -> str:
    """
    XPathに安全に文字列を埋め込む（シングル/ダブルクォート混在に対応）
    """
    if "'" not in s:
        return f"'{s}'"
    if '"' not in s:
        return f'"{s}"'
    # 両方含む場合: concat('a', '"', 'b', ...)
    parts = s.split("'")
    return "concat(" + ", ".join([f"'{p}'" if i == 0 else f"\"'\", '{p}'" for i, p in enumerate(parts)]) + ")"


def _find_place_link_in_name_table(driver, place_name: str):
    """
    「名称」ヘッダーを含む表の中から place_name のリンクを探す。
    複数表がある場合も最初に一致したものを返す。
    """
    wait = WebDriverWait(driver, 15)

    # 「名称」列を含むtableが出るまで待つ
    wait.until(EC.presence_of_element_located(
        (By.XPATH, "//table[.//th[contains(normalize-space(.),'名称')]]")
    ))

    tables = driver.find_elements(By.XPATH, "//table[.//th[contains(normalize-space(.),'名称')]]")

    lit = _xpath_literal(place_name.strip())

    # 1) 完全一致（推奨）
    for t in tables:
        links = t.find_elements(By.XPATH, f".//a[normalize-space()={lit}]")
        if links:
            return links[0]

    # 2) 部分一致（表記ゆれ保険：例「店」など付く/付かない）
    for t in tables:
        links = t.find_elements(By.XPATH, f".//a[contains(normalize-space(.), {lit})]")
        if links:
            return links[0]

    return None


def RetrieveCost(driver, PlefectureName, PlaceName):
    wait = WebDriverWait(driver, 15)

    driver.get("https://www.supersento.com")

    # 都道府県リンクへ
    link_prefecture = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, PlefectureName)))
    href_prefecture = link_prefecture.get_attribute('href')
    driver.get(href_prefecture)

    # ★ここが修正点：必ず「表内」の施設リンクを拾う
    link_OnsenName = _find_place_link_in_name_table(driver, PlaceName)

    if not link_OnsenName:
        # 最後の保険：どうしても見つからない時だけ従来検索（原因調査用）
        # ここで落としたければ raise にしてもOK
        link_OnsenName = wait.until(EC.presence_of_element_located((By.LINK_TEXT, PlaceName)))

    href_OnsenName = link_OnsenName.get_attribute('href')
    driver.get(href_OnsenName)

    # 料金表テーブル
    table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.ryokin_box")))
    rows = table.find_elements(By.TAG_NAME, "tr")

    data = []
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        row_data = [cell.text.replace('\n', ' ') for cell in cells]
        if row_data:
            data.append(row_data)

    print(data)
    return data


if __name__ == "__main__":
    driver = webdriver.Chrome()
    PlaceName = "仙川 湯けむりの里"
    PlefectureName = "東京都"
    RetrieveCost(driver, PlefectureName, PlaceName)
