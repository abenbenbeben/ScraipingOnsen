import time, pprint, json, sys
sys.path.append('../')
from components.ConnectGemini import requestGemini
from components.ScraipeSite import RetrieveCost
from components.SpreadSheet import write_spreadsheet, get_col_by_header


def ServeCost(driver, PlefectureName, PlaceName, rownum, sheetnum=0):
    """
    sheetnum: 書き込み先シート番号（0-based）
    ヘッダー名から列を引くので、列順が変わっても壊れない
    """
    data = RetrieveCost(driver, PlefectureName, PlaceName)

    systemContent = "以下の料金表を参考に、平日と休日の大人料金を教えて。時間記載がある場合2時間利用した際の料金を想定。回答例を遵守。"
    data_string = '\n'.join([': '.join(item) for item in data])
    userContent = "回答例: {'heijitu': 1000, 'kyujitu': 1200}\n\n" + data_string

    raw_result = requestGemini(systemContent, userContent)

    # ★ヘッダー名から列取得（見つからない場合は従来列へフォールバック）
    col_heijitu = get_col_by_header("平日値段", sheetnum=sheetnum, fallback="AE")
    col_kyujitu = get_col_by_header("休日値段", sheetnum=sheetnum, fallback="AF")
    col_source  = get_col_by_header("値段ソース(空)", sheetnum=sheetnum, fallback="AG")

    try:
        result_gpt = eval(raw_result)
        heijitu = result_gpt.get("heijitu", "")
        kyujitu = result_gpt.get("kyujitu", "")

        write_spreadsheet(f"{col_heijitu}{rownum}", heijitu, sheetnum=sheetnum)
        write_spreadsheet(f"{col_kyujitu}{rownum}", kyujitu, sheetnum=sheetnum)

    except (SyntaxError, ValueError):
        # パースできない場合は平日欄に raw_result を入れる（従来挙動）
        write_spreadsheet(f"{col_heijitu}{rownum}", raw_result, sheetnum=sheetnum)
        result_gpt = raw_result

    # 値段ソース
    write_spreadsheet(f"{col_source}{rownum}", data_string, sheetnum=sheetnum)

    return result_gpt


if __name__ == "__main__":
    from selenium import webdriver
    driver = webdriver.Chrome()
    placeName = "第一金乗湯"
    rownum = 8
    ServeCost(driver, "東京都", placeName, rownum, sheetnum=0)
