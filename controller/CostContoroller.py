import time, pprint, json, sys
sys.path.append('../')
from components.ConnectChatGpt import requestGpt
from components.ScraipeSite import RetrieveCost
from components.SpreadSheet import write_spreadsheet


def ServeCost(driver, PlefectureName, PlaceName, rownum):
    data = RetrieveCost(driver, PlefectureName, PlaceName)

    systemContent = "以下の料金表を参考に、大人の平日と休日の料金を教えて。時間の制限がある場合2時間利用を想定。回答例を遵守。"
    data_string = '\n'.join([f"{item[0]}: {item[1]}" for item in data])
    userContent = "回答例: {'heijitu': 1000, 'kyujitu': 1200}\n\n" + data_string

    result_gpt = eval(requestGpt(systemContent,userContent))
    pprint.pprint(result_gpt["heijitu"])
    pprint.pprint(result_gpt["kyujitu"])

    write_spreadsheet(f"AE{rownum}",result_gpt["heijitu"])
    write_spreadsheet(f"AF{rownum}",result_gpt["kyujitu"])
    write_spreadsheet(f"AG{rownum}",data_string)


    return result_gpt

if __name__ == "__main__":
    from selenium import webdriver
    driver = webdriver.Chrome()
    placeName = "久松湯"
    rownum = 4
    ServeCost(driver, "東京都", placeName, rownum)




