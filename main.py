from selenium import webdriver
import time, sys
sys.path.append('../')
from components.SpreadSheet import read_spreadsheet, write_spreadsheet, write_spreadsheet_placeapi
from components.RetrieveKutikomi import open_kutikomi, search_kutikomi
from components.RequestPlacesAPI import *
from controller.CostContoroller import ServeCost
from controller.NearStController import * 
driver = webdriver.Chrome()

def scraiping_main():
    rownum = 2


    placeName = read_spreadsheet(f"A{rownum}")
    open_kutikomi(driver,placeName)
    # スプレッドシートのセル位置リスト
    cells = [chr(i) for i in range(ord('B'), ord('L') + 1)]

    # 各セルからキーワードを読み込み、search_kutikomi関数を実行して結果を表示
    forcount = 0
    for cell in cells:
        search_keywords = read_spreadsheet(f"{cell}1").split(",")  # セルからキーワードを読み込む
        total_elements = 0
        for keyword in search_keywords:
            elements = search_kutikomi(driver,keyword.strip(),forcount)  # strip()を使って前後の余分な空白を削除
            total_elements = max(total_elements,len(elements))
            forcount = forcount + 1
        write_spreadsheet(f"{cell}{rownum}",total_elements)


    # GooglePlaceApi
    placeApiInfo = get_placeapi_data(placeName)
    write_spreadsheet_placeapi(rownum, placeApiInfo)

    ServeCost(driver, "東京都", placeName, rownum)
    SearchNearStatiion(placeApiInfo["lat"],placeApiInfo["lng"],rownum)

    # ブラウザを閉じる
    driver.quit()

    

if __name__ == "__main__":
    scraiping_main()