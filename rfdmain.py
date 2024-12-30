from selenium import webdriver
import time, sys, pprint
import firebase_admin
from firebase_admin import credentials, firestore
sys.path.append('../')
from components.SpreadSheet import read_spreadsheet, write_spreadsheet, write_multi_spreadsheet, write_spreadsheet_placeapi_rfd
from components.RequestPlacesAPI import *
from controller.NearStController import * 

# firebaseの既存データを全て引っ張ってくる関数
def retrieveFirebase_onsen_data():
    # -------------------------------
    collectionName = "onsen_data"
    # -------------------------------

    # サービスアカウントキーのパスを指定してFirebaseアプリを初期化
    cred = credentials.Certificate('onsenmatching-firebase-adminsdk-qd1mg-ccda745b2d.json')
    firebase_admin.initialize_app(cred)

    # Firestoreクライアントの初期化
    db = firestore.client()

    # コレクションからデータを取得
    collection_ref = db.collection(collectionName)# onsen_dataに置換
    docs = collection_ref.stream()

    rownum = 2
    data = []
    count = 0
        
        # データの表示
    for doc in docs:
        count = count + 1
        data_dict = doc.to_dict()
        row_data = []

        # 各項目の追加（存在しない場合は空文字を追加）
        row_data.append(data_dict.get("onsen_name", ""))  # A列 温泉名
        row_data.append(data_dict.get("sauna", ""))  # B列 サウナ
        row_data.append(data_dict.get("rouryu", ""))  # C列 ロウリュ
        row_data.append(data_dict.get("siosauna", ""))  # D列 塩サウナ
        row_data.append(data_dict.get("doro", ""))  # E列 泥
        row_data.append(data_dict.get("mizuburo", ""))  # F列 水風呂
        row_data.append(data_dict.get("tennen", ""))  # G列 天然
        row_data.append(data_dict.get("tansan", ""))  # H列 炭酸風呂
        row_data.append(data_dict.get("manga", ""))  # I列 漫画
        row_data.append(data_dict.get("wifi", ""))  # J列 wifi
        row_data.append(data_dict.get("ganban", ""))  # K列 岩盤
        row_data.append(data_dict.get("facewash", ""))  # L列 洗顔
        row_data.append(data_dict.get("zikan_heijitu_start", ""))  # M列 平日開始時間
        row_data.append(data_dict.get("zikan_heijitu_end", ""))  # N列 平日終了時間

        # OからV列は空列なので、空文字を追加
        row_data.extend([""] * 8)

        row_data.append(data_dict.get("zikan_kyujitu_start", ""))  # W列 休日開始時間
        row_data.append(data_dict.get("zikan_kyujitu_end", ""))  # X列 休日終了時間

        # YからZ列は空列なので、空文字を追加
        row_data.extend([""] * 2)

        row_data.append(data_dict.get("latitude", ""))  # AA列 緯度
        row_data.append(data_dict.get("longitude", ""))  # AB列 経度
        row_data.append(data_dict.get("place", ""))  # AC列 住所
        row_data.append(data_dict.get("url", ""))  # AD列 URL
        row_data.append(data_dict.get("heijitunedan", ""))  # AE列 平日値段
        row_data.append(data_dict.get("kyuzitunedan", ""))  # AF列 休日値段

        # AGからAJ列は空列なので、空文字を追加
        row_data.extend([""] * 4)

        # 画像URLの追加（最大10個）
        images_count = len(data_dict.get("images", []))
        for i in range(10):
            if i < images_count:
                row_data.append(data_dict["images"][i])
            else:
                row_data.append("")  # 画像が不足している場合、空欄を追加

        row_data.append(doc.id)  # AU列 id
        row_data.append(data_dict.get("feature", ""))  # AV列 特徴
        row_data.append(data_dict.get("komiguai", ""))  # AW列 
        row_data.append(data_dict.get("wadai", ""))  # AX列 
        row_data.append(data_dict.get("furosyurui", ""))  # AY列 お湯の種類
        row_data.append(data_dict.get("sensituyosa", ""))  # AZ列 泉質
        row_data.append(data_dict.get("senzai", ""))  # BA列 少し良いシャンプー
        row_data.append(data_dict.get("kodomo", ""))  # BB列 子供も楽しめる
        row_data.append(data_dict.get("ganbansyurui", ""))  # BC列 
        row_data.append(data_dict.get("tyusyazyo", ""))  # BD列 駐車場
        row_data.append(data_dict.get("sensitu", ""))  # BE列

        # 書き込み用のデータを更新
        data.append(row_data)

    # データを一括でスプレッドシートに書き込む
    start_row = 2
    write_multi_spreadsheet(f"A{start_row}:BE{start_row + count - 1}", data)

def retrieveFirebase_v2():
    # -------------------------------
    collectionName = "onsen_data_v2"
    # -------------------------------

    # サービスアカウントキーのパスを指定してFirebaseアプリを初期化
    cred = credentials.Certificate('onsenmatching-firebase-adminsdk-qd1mg-ccda745b2d.json')
    firebase_admin.initialize_app(cred)

    # Firestoreクライアントの初期化
    db = firestore.client()

    # コレクションからデータを取得
    collection_ref = db.collection(collectionName)
    docs = collection_ref.stream()

    rownum = 2
    data = []
    count = 0
        
        # データの表示
    for doc in docs:
        count = count + 1
        data_dict = doc.to_dict()
        row_data = []

        # 各項目の追加（存在しない場合は空文字を追加）
        row_data.append(data_dict.get("onsen_name", ""))  # A列 温泉名
        row_data.append(data_dict.get("sauna", ""))  # B列 サウナ
        row_data.append(data_dict.get("rouryu", ""))  # C列 ロウリュ
        row_data.append(data_dict.get("siosauna", ""))  # D列 塩サウナ
        row_data.append(data_dict.get("doro", ""))  # E列 泥
        row_data.append(data_dict.get("mizuburo", ""))  # F列 水風呂
        row_data.append(data_dict.get("tennen", ""))  # G列 天然
        row_data.append(data_dict.get("tansan", ""))  # H列 炭酸風呂
        row_data.append(data_dict.get("manga", ""))  # I列 漫画
        row_data.append(data_dict.get("wifi", ""))  # J列 wifi
        row_data.append(data_dict.get("ganban", ""))  # K列 岩盤
        row_data.append(data_dict.get("facewash", ""))  # L列 洗顔
        row_data.append([item for item in data_dict["periods"] if item["day"] == 0][0]["open"]) # M列 
        row_data.append([item for item in data_dict["periods"] if item["day"] == 0][0]["close"]) # N列
        row_data.append([item for item in data_dict["periods"] if item["day"] == 1][0]["open"])# O列 
        row_data.append([item for item in data_dict["periods"] if item["day"] == 1][0]["close"]) # P列
        row_data.append([item for item in data_dict["periods"] if item["day"] == 2][0]["open"]) # Q列
        row_data.append([item for item in data_dict["periods"] if item["day"] == 2][0]["close"]) # R列
        row_data.append([item for item in data_dict["periods"] if item["day"] == 3][0]["open"]) # S列
        row_data.append([item for item in data_dict["periods"] if item["day"] == 3][0]["close"]) # T列
        row_data.append([item for item in data_dict["periods"] if item["day"] == 4][0]["open"]) # U列
        row_data.append([item for item in data_dict["periods"] if item["day"] == 4][0]["close"]) # V列
        row_data.append([item for item in data_dict["periods"] if item["day"] == 5][0]["open"]) # W列
        row_data.append([item for item in data_dict["periods"] if item["day"] == 5][0]["close"]) # X列
        row_data.append([item for item in data_dict["periods"] if item["day"] == 6][0]["open"]) # Y列
        row_data.append([item for item in data_dict["periods"] if item["day"] == 6][0]["close"]) # Z列
        row_data.append(data_dict.get("latitude", ""))  # AA列 緯度
        row_data.append(data_dict.get("longitude", ""))  # AB列 経度
        row_data.append(data_dict.get("place", ""))  # AC列 住所
        row_data.append(data_dict.get("url", ""))  # AD列 URL
        row_data.append(data_dict.get("heijitunedan", ""))  # AE列 平日値段
        row_data.append(data_dict.get("kyuzitunedan", ""))  # AF列 休日値段
        row_data.append("") # AG列 値段ソース（今後追加する可能性あるため残し）
        row_data.append(data_dict.get("ekitika", "")["kyori"])  # AH列 駅からの距離
        row_data.append(data_dict.get("ekitika", "")["zikan"])  # AI列 駅からの時間
        row_data.append(data_dict.get("ekitika", "")["moyorieki"])  # AJ列 最寄駅

        # 画像URLの追加（最大7個）
        images_count = len(data_dict.get("images", []))
        for i in range(7):
            if i < images_count:
                row_data.append(data_dict["images"][i])
            else:
                row_data.append("")  # 画像が不足している場合、空欄を追加

        row_data.append(data_dict.get("feature", ""))  # AV列 特徴
        row_data.append(doc.id)  # AU列 id
        row_data.append(data_dict.get("onsenId", ""))  # AV列 特徴

        

        # 書き込み用のデータを更新
        data.append(row_data)

    # データを一括でスプレッドシートに書き込む
    start_row = 2
    write_multi_spreadsheet(f"A{start_row}:BE{start_row + count - 1}", data)


def retrievePlaceInfo(rownum):
    placeName = read_spreadsheet(f"A{rownum}")
    # GooglePlaceApi
    placeApiInfo = get_placeapi_data(placeName)
    write_spreadsheet_placeapi_rfd(rownum, placeApiInfo)

    # GoogleAPIで返却された施設名を使用。
    SearchNearStatiion(placeApiInfo["lat"],placeApiInfo["lng"],rownum)



if __name__ == "__main__":
    # for value in range(66, 260):
    #    retrievePlaceInfo(value)
    #    print("休憩中")
    #    time.sleep(10)
    retrieveFirebase_v2()