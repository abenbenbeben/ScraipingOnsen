# RetrieveReview
from selenium import webdriver
import time, sys, pprint
import firebase_admin
from firebase_admin import credentials, firestore
sys.path.append('../')
from components.SpreadSheet import *
from components.RequestPlacesAPI import *
from controller.NearStController import * 
from components.RetrieveKutikomi import *
driver = webdriver.Chrome()


labels = [["サウナ"],["ロウリュウ","ロウリュ"],["塩サウナ"],["泥"],["水風呂"],["天然"],["炭酸風呂","炭酸泉"],["漫画"],["Wi-fi","wifi"],["岩盤浴"],["洗顔"]]

#既存データに対して、口コミを調べる。
def incorporateReviews_existed():
    # ==同一名称存在時===================================
    indirecteRow = 104
    placenum = None
    sameNameFlag = True
    # =================================================


    sheetValue = read_all_spreadsheet(0)
    sheetValue.pop(0)
    value = [item[:12] for item in sheetValue]

    # value = value[:1]
    # value = value[39:] # 最初の⚪︎個の要素を消す。
    value = [value[indirecteRow - 2]]
    start_row = indirecteRow

    insertData = []
    insertLabel = ["温泉名"]
    if(sameNameFlag is not True):
        for label in labels:
            insertLabel_child = []
            if(len(label)==1):
                insertLabel_child.append(label[0])
            else:
                insertLabel_child.append(",".join(label))
            while len(insertLabel_child) < 10:
                insertLabel_child.append("")
            insertLabel = insertLabel + insertLabel_child
        insertData.append(insertLabel)


    try:
        for index ,items in enumerate(value):
            forcount = 0
            insertData_child = []
            placeName = items.pop(0)
            print("================================")
            print(placeName)
            print("================================")
            insertData_child.append(placeName)
            if(not open_kutikomi(driver, placeName, placenum)):
                insertData.append(insertData_child)
                continue
            for item_index, item in enumerate(items):
                if (item!="0"):
                    if(len(labels[item_index])==1):
                        keyword = labels[item_index][0]
                        result = search_kutikomi_rr(driver,keyword.strip(),forcount)["reviews"]
                        pprint.pprint(result)
                    else:
                        keywords = labels[item_index] 
                        before_result = []
                        for keyword in keywords:
                            result = search_kutikomi_rr(driver,keyword.strip(),forcount)["reviews"]
                            result = before_result if len(before_result) > len(result) else result
                            before_result = result
                            forcount = forcount + 1
                            pprint.pprint(result)
                    forcount = forcount + 1
                    result= result[:10]
                    while len(result) < 10:
                        result.append("")
                    insertData_child = insertData_child + result
                else:
                    empty_list = [""] * 10
                    insertData_child = insertData_child + empty_list
            insertData.append(insertData_child)
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    if(sameNameFlag is not True):
        write_multi_spreadsheet(f"A{start_row}:DG{start_row + len(value)}", insertData,1)
    else:
        write_multi_spreadsheet(f"A{start_row}:DG{start_row + len(value) - 1}", insertData,1)

#新規データに対して、口コミを調べる。特徴を生成する。
def incorporateReviews_new():
    # ==========================================
    readSheetNum = 2 # 読み込みするシートの順番
    writeSheetNum = 3 # 書き込みするシートの順番
    deleteElement = 39 # 最初の⚪︎個の要素を消す。
    start_row = 41 #　書き込み始める行番号
    # ==========================================
    
    sheetValue = read_all_spreadsheet(readSheetNum)
    sheetValue.pop(0)
    value = [item[:12] for item in sheetValue]

    # value = value[:1]
    value = value[deleteElement:] # 最初の⚪︎個の要素を消す。
    

    insertData = []
    insertLabel = ["温泉名"]
    for label in labels:
        insertLabel_child = []
        if(len(label)==1):
            insertLabel_child.append(label[0])
        else:
            insertLabel_child.append(",".join(label))
        while len(insertLabel_child) < 10:
            insertLabel_child.append("")
        insertLabel = insertLabel + insertLabel_child
    insertLabel.append("特徴文章")
    insertData.append(insertLabel)


    try:
        for index ,items in enumerate(value):
            forcount = 0
            insertData_child = []
            rownum = index + 2
            placeName = items.pop(0)
            print("================================")
            print(placeName)
            print("================================")
            insertData_child.append(placeName)
            if(not open_kutikomi(driver,placeName)):
                insertData.append(insertData_child)
                continue
            # 特徴文章を抽出
            feature_sentence = search_feature(driver)
            for item_index, item in enumerate(items):
                if (item!="0"):
                    # ここのkeywordをなんとかするところから。
                    if(len(labels[item_index])==1):
                        keyword = labels[item_index][0]
                        result = search_kutikomi_rr(driver,keyword.strip(),forcount)["reviews"]
                        pprint.pprint(result)
                    else:
                        keywords = labels[item_index] 
                        before_result = []
                        for keyword in keywords:
                            result = search_kutikomi_rr(driver,keyword.strip(),forcount)["reviews"]
                            result = before_result if len(before_result) > len(result) else result
                            before_result = result
                            forcount = forcount + 1
                            pprint.pprint(result)
                    forcount = forcount + 1
                    result= result[:10]
                    while len(result) < 10:
                        result.append("")
                    insertData_child = insertData_child + result
                else:
                    empty_list = [""] * 10
                    insertData_child = insertData_child + empty_list
            insertData_child.append(feature_sentence)
            insertData.append(insertData_child)

    except Exception as e:
        print(f"エラーが発生しました: {e}")
    write_multi_spreadsheet(f"A{start_row}:DH{start_row + len(value)}", insertData, writeSheetNum)   


if __name__ == "__main__":
    incorporateReviews_existed()
    # incorporateReviews_new()

    # ブラウザを閉じる
    driver.quit()