"""
Firestore(温泉データ) → Googleスプレッドシートへ書き出すスクリプト

- retrieveFirebase_onsen_data(): 旧スキーマ(onsen_data) をシートへ出力
- retrieveFirebase_v2():         新スキーマ(onsen_data_v2) をシートへ出力
- retrievePlaceInfo():           シートの温泉名 → PlaceAPI + 最寄駅検索 を追記

注意:
- firebase_admin.initialize_app() はプロセス内で1回だけ呼ぶ必要があります。
  複数関数を連続実行する可能性があるので、初期化処理を共通化しています。
"""

import sys
import time
import firebase_admin
from firebase_admin import credentials, firestore

sys.path.append("../")

from components.SpreadSheet import (
    read_spreadsheet,
    write_multi_spreadsheet,
    write_spreadsheet_placeapi_rfd,
)

from components.RequestPlacesAPI import get_placeapi_data
from controller.NearStController import SearchNearStatiion


# -----------------------------
# 共通設定
# -----------------------------
SERVICE_ACCOUNT_JSON = "onsenmatching-firebase-adminsdk-qd1mg-ccda745b2d.json"

COLLECTION_V1 = "onsen_data"
COLLECTION_V2 = "onsen_data_v2"


def get_firestore_client():
    """
    Firestoreクライアントを返す（Firebaseアプリ初期化もここで面倒を見る）
    initialize_app は 1プロセス1回だけ必要なので、未初期化なら初期化する。
    """
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_JSON)
        firebase_admin.initialize_app(cred)

    return firestore.client()


# ============================================================
# v1: onsen_data → シート出力
# ============================================================
def retrieveFirebase_onsen_data():
    """
    Firestore の onsen_data コレクションを読み取り、
    スプレッドシートの A列〜BE列へ一括で書き込む。

    ※ v1は途中に「空列」が多く、列合わせのために空文字を挿入している。
    """
    db = get_firestore_client()

    docs = db.collection(COLLECTION_V1).stream()

    data = []
    count = 0

    for doc in docs:
        count += 1
        data_dict = doc.to_dict()
        row = []

        # -------------------------
        # A〜N: 基本情報（v1）
        # -------------------------
        row.append(data_dict.get("onsen_name", ""))          # A: 温泉名
        row.append(data_dict.get("sauna", ""))               # B: サウナ
        row.append(data_dict.get("rouryu", ""))              # C: ロウリュ
        row.append(data_dict.get("siosauna", ""))            # D: 塩サウナ
        row.append(data_dict.get("doro", ""))                # E: 泥
        row.append(data_dict.get("mizuburo", ""))            # F: 水風呂
        row.append(data_dict.get("tennen", ""))              # G: 天然
        row.append(data_dict.get("tansan", ""))              # H: 炭酸風呂
        row.append(data_dict.get("manga", ""))               # I: 漫画
        row.append(data_dict.get("wifi", ""))                # J: wifi
        row.append(data_dict.get("ganban", ""))              # K: 岩盤
        row.append(data_dict.get("facewash", ""))            # L: 洗顔
        row.append(data_dict.get("zikan_heijitu_start", "")) # M: 平日開始
        row.append(data_dict.get("zikan_heijitu_end", ""))   # N: 平日終了

        # O〜V: 旧シート仕様で空欄が必要（列合わせ）
        row.extend([""] * 8)

        # W〜X: 休日
        row.append(data_dict.get("zikan_kyujitu_start", "")) # W: 休日開始
        row.append(data_dict.get("zikan_kyujitu_end", ""))   # X: 休日終了

        # Y〜Z: 空欄（列合わせ）
        row.extend([""] * 2)

        # AA〜AF: 位置/価格など
        row.append(data_dict.get("latitude", ""))            # AA: 緯度
        row.append(data_dict.get("longitude", ""))           # AB: 経度
        row.append(data_dict.get("place", ""))               # AC: 住所
        row.append(data_dict.get("url", ""))                 # AD: URL
        row.append(data_dict.get("heijitunedan", ""))        # AE: 平日値段
        row.append(data_dict.get("kyuzitunedan", ""))        # AF: 休日値段

        # AG〜AJ: 空欄（列合わせ）
        row.extend([""] * 4)

        # -------------------------
        # 画像URL（最大10個）
        # -------------------------
        images = data_dict.get("images", []) or []
        for i in range(10):
            row.append(images[i] if i < len(images) else "")

        # AU〜BE: 追加情報
        row.append(doc.id)                         # AU: Firestore doc.id
        row.append(data_dict.get("feature", ""))   # AV: 特徴
        row.append(data_dict.get("komiguai", ""))  # AW
        row.append(data_dict.get("wadai", ""))     # AX
        row.append(data_dict.get("furosyurui", ""))# AY: お湯の種類
        row.append(data_dict.get("sensituyosa", ""))# AZ: 泉質(強さ?)
        row.append(data_dict.get("senzai", ""))    # BA: 少し良いシャンプー
        row.append(data_dict.get("kodomo", ""))    # BB: 子供も楽しめる
        row.append(data_dict.get("ganbansyurui", ""))# BC
        row.append(data_dict.get("tyusyazyo", "")) # BD: 駐車場
        row.append(data_dict.get("sensitu", ""))   # BE

        data.append(row)

    # -------------------------
    # スプレッドシートへ一括書込
    # -------------------------
    start_row = 2
    write_multi_spreadsheet(f"A{start_row}:BE{start_row + count - 1}", data)


# ============================================================
# v2: onsen_data_v2 → シート出力
# ============================================================
def retrieveFirebase_v2():
    """
    Firestore の onsen_data_v2 コレクションを読み取り、
    スプレッドシートへ一括で書き込む（v2の構造に合わせた列展開）

    注意:
    - periods の要素が欠ける可能性があるので安全に取り出す
    - ekitika が存在しない/空の場合もあるので get で安全に取り出す
    """
    db = get_firestore_client()

    docs = db.collection(COLLECTION_V2).stream()

    data = []
    count = 0

    def get_period_time(periods, day, key):
        """
        periods: [{"day":0,"open":"...","close":"..."}, ...] を想定
        指定dayの open/close を返す。無ければ空文字。
        """
        if not periods:
            return ""
        for p in periods:
            if p.get("day") == day:
                return p.get(key, "")
        return ""

    for doc in docs:
        count += 1
        data_dict = doc.to_dict()
        row = []

        # -------------------------
        # A〜L: 基本情報
        # -------------------------
        row.append(data_dict.get("onsen_name", ""))  # A: 温泉名
        row.append(data_dict.get("sauna", ""))       # B
        row.append(data_dict.get("rouryu", ""))      # C
        row.append(data_dict.get("siosauna", ""))    # D
        row.append(data_dict.get("doro", ""))        # E
        row.append(data_dict.get("mizuburo", ""))    # F
        row.append(data_dict.get("tennen", ""))      # G
        row.append(data_dict.get("tansan", ""))      # H
        row.append(data_dict.get("manga", ""))       # I
        row.append(data_dict.get("wifi", ""))        # J
        row.append(data_dict.get("ganban", ""))      # K
        row.append(data_dict.get("facewash", ""))    # L

        # -------------------------
        # M〜Z: 曜日ごとの営業時間（day=0〜6）
        # ここでは「open, close」を順に並べて列へ展開
        # day=0: M,N / day=1: O,P / ... / day=6: Y,Z
        # -------------------------
        periods = data_dict.get("periods", []) or []
        for day in range(7):
            row.append(get_period_time(periods, day, "open"))
            row.append(get_period_time(periods, day, "close"))

        # -------------------------
        # AA〜AF: 位置/URL/価格
        # -------------------------
        row.append(data_dict.get("latitude", ""))    # AA: 緯度
        row.append(data_dict.get("longitude", ""))   # AB: 経度
        row.append(data_dict.get("place", ""))       # AC: 住所
        row.append(data_dict.get("url", ""))         # AD: URL
        row.append(data_dict.get("heijitunedan", ""))# AE: 平日値段
        row.append(data_dict.get("kyuzitunedan", ""))# AF: 休日値段

        # AG: 値段ソース（将来用の空列）
        row.append("")

        # -------------------------
        # AH〜AJ: 駅近情報（存在しない場合があるので安全に）
        # -------------------------
        ekitika = data_dict.get("ekitika") or {}
        row.append(ekitika.get("kyori", ""))         # AH: 駅からの距離
        row.append(ekitika.get("zikan", ""))         # AI: 駅からの時間
        row.append(ekitika.get("moyorieki", ""))     # AJ: 最寄駅

        # -------------------------
        # 画像URL（最大7個）
        # ※元コードでは AW〜 など列コメントがズレていたので「順番」を優先
        # -------------------------
        images = data_dict.get("images", []) or []
        for i in range(7):
            row.append(images[i] if i < len(images) else "")

        # -------------------------
        # 追加フィールド（v2）
        # -------------------------
        row.append(data_dict.get("feature", ""))     # (続きの列) 特徴
        row.append(doc.id)                           # Firestore doc.id
        row.append(data_dict.get("onsenId", ""))     # 温泉id
        row.append(data_dict.get("syukuhaku", ""))   # 宿泊

        data.append(row)

    # ここは「シートの列範囲」と row の長さが一致している必要あり
    # ※元コードは A..BE を指定していましたが、row の実長と一致しているか要確認
    start_row = 2
    write_multi_spreadsheet(f"A{start_row}:BE{start_row + count - 1}", data)


# ============================================================
# シートの温泉名 → PlaceAPI → シート追記 + 最寄駅検索
# ============================================================
def retrievePlaceInfo(rownum: int):
    """
    スプレッドシート A列にある施設名（温泉名）を読み、
    Google Place API から緯度経度などを取得 → シートへ書込
    その後、取得した lat/lng で最寄駅検索してシートへ書込
    """
    place_name = read_spreadsheet(f"A{rownum}")

    # Google Place API で施設情報を取得
    place_info = get_placeapi_data(place_name)

    # PlaceAPI結果を指定行へ反映
    write_spreadsheet_placeapi_rfd(rownum, place_info)

    # PlaceAPIの lat/lng を使って最寄駅情報を検索して反映
    SearchNearStatiion(place_info["lat"], place_info["lng"], rownum)


# ============================================================
# エントリーポイント
# ============================================================
if __name__ == "__main__":
    # Place API を複数行に対して回す例（API制限回避でsleep）
    # for row in range(66, 260):
    #     retrievePlaceInfo(row)
    #     print("休憩中...")
    #     time.sleep(10)

    # Firestore(v2) → シートへ出力
    retrieveFirebase_v2()
