import time, pprint, json, sys
sys.path.append('../')
from components.ConnectChatGpt import requestGpt
from components.ScraipeSite import RetrieveCost
from components.SpreadSheet import write_spreadsheet


def ServeCost(driver, PlefectureName, PlaceName, rownum):
    data = RetrieveCost(driver, PlefectureName, PlaceName)

    systemContent = "以下の料金表を参考に、平日と休日の大人料金を教えて。時間記載がある場合2時間利用した際の料金を想定。回答例を遵守。"
    data_string = '\n'.join([f"{item[0]}: {item[1]}" for item in data])
    userContent = "回答例: {'heijitu': 1000, 'kyujitu': 1200}\n\n" + data_string

    raw_result = requestGpt(systemContent,userContent)
    try:
        # 辞書型に変換を試みる
        result_gpt = eval(raw_result)
        pprint.pprint(result_gpt["heijitu"])
        pprint.pprint(result_gpt["kyujitu"])
        write_spreadsheet(f"AE{rownum}",result_gpt["heijitu"])
        write_spreadsheet(f"AF{rownum}",result_gpt["kyujitu"])
    except (SyntaxError, ValueError):
        write_spreadsheet(f"AE{rownum}",raw_result)
        result_gpt = raw_result
    

    
    write_spreadsheet(f"AG{rownum}",data_string)


    return result_gpt

if __name__ == "__main__":
    from selenium import webdriver
    driver = webdriver.Chrome()
    placeName = "第一金乗湯"
    rownum = 8
    ServeCost(driver, "東京都", placeName, rownum)




