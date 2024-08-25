from selenium import webdriver
import time, sys
sys.path.append('../')
from components.SpreadSheet import read_spreadsheet, write_spreadsheet, write_spreadsheet_placeapi
from components.RetrieveKutikomi import open_kutikomi, search_kutikomi
from components.RequestPlacesAPI import *
from controller.CostContoroller import ServeCost
from controller.NearStController import * 
from controller.ImageContoroller import *
driver = webdriver.Chrome()

def scraiping_main(rownum, placenum=None):

    placeName = read_spreadsheet(f"A{rownum}")
    if(not open_kutikomi(driver,placeName, placenum)):
        write_spreadsheet(f"B{rownum}","同一名称あり")
        return
    # スプレッドシートのセル位置リスト
    cells = [chr(i) for i in range(ord('B'), ord('L') + 1)]

    # 各セルからキーワードを読み込み、search_kutikomi関数を実行して結果を表示
    forcount = 0
    
    for cell in cells:
        search_keywords = read_spreadsheet(f"{cell}1").split(",")  # セルからキーワードを読み込む
        total_elements = 0
        note = None
        for keyword in search_keywords:
            result_kutikomi = search_kutikomi(driver,keyword.strip(),forcount)  # strip()を使って前後の余分な空白を削除
            total_elements = max(total_elements,result_kutikomi["count"])
            forcount = forcount + 1
            if(result_kutikomi["note"]):
                if(note is not None):
                    note = note + result_kutikomi["note"] + "\n\n"
                else:
                    note = result_kutikomi["note"] + "\n\n"
        write_spreadsheet(f"{cell}{rownum}",total_elements,note)


    # GooglePlaceApi
    placeApiInfo = get_placeapi_data(placeName)
    write_spreadsheet_placeapi(rownum, placeApiInfo)

    ServeCost(driver, "東京都", placeName, rownum)
    # GoogleAPIで返却された施設名を使用。
    SearchNearStatiion(placeApiInfo["lat"],placeApiInfo["lng"],rownum)

    ServeImage(rownum, placeApiInfo["name"], placeApiInfo["url"])

    

    

if __name__ == "__main__":
    check_firewall()
    placenum = 0 # 同一名称存在している場合に指定
    for value in range(41, 42):
       scraiping_main(value,placenum)
       print("休憩中")
       time.sleep(30)
    # scraiping_main(17)
    # ブラウザを閉じる
    driver.quit()