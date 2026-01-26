# 既存firebase→スプレッドシートに書き出し。
# スプレッドシートは新規作成。

import sys
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

sys.path.append("../")

from components.SpreadSheet import (
    write_multi_spreadsheet,
    create_new_worksheet,
    excel_column,   # ★列計算を使う
)

SERVICE_ACCOUNT_JSON = "onsenmatching-firebase-adminsdk-qd1mg-ccda745b2d.json"
COLLECTION_V2 = "onsen_data_v2"


# ============================================================
# Firestore
# ============================================================
def get_firestore_client():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_JSON)
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ============================================================
# 口コミの取り出し（Firestoreの格納形式が多少違っても拾う）
# ============================================================
LABELS = [
    (["サウナ"], ["sauna", "サウナ"]),
    (["ロウリュウ", "ロウリュ"], ["rouryu", "ロウリュウ", "ロウリュ"]),
    (["塩サウナ"], ["siosauna", "塩サウナ"]),
    (["泥"], ["doro", "泥"]),
    (["水風呂"], ["mizuburo", "水風呂"]),
    (["天然"], ["tennen", "天然"]),
    (["炭酸風呂", "炭酸泉"], ["tansan", "炭酸風呂", "炭酸泉"]),
    (["漫画"], ["manga", "漫画"]),
    (["Wi-fi", "wifi"], ["wifi", "Wi-fi", "WiFi", "wifi"]),
    (["岩盤浴"], ["ganban", "岩盤浴"]),
    (["洗顔"], ["facewash", "洗顔"]),
]

ADD_LABELS = [
    (["宿泊"], ["syukuhaku", "宿泊"]),
]


def _parse_review_block(block):
    """
    block の想定パターン:
    - list: ["口コミ1", "口コミ2", ...]
    - dict: {"reviews":[...], "count":123, "note":"..."}
    """
    if block is None:
        return {"reviews": [], "count": 0, "note": ""}

    if isinstance(block, list):
        return {"reviews": block, "count": len(block), "note": ""}

    if isinstance(block, dict):
        reviews = block.get("reviews") or block.get("items") or []
        count = block.get("count")
        if count is None:
            count = len(reviews) if isinstance(reviews, list) else 0
        note = block.get("note") or ""
        return {"reviews": reviews if isinstance(reviews, list) else [], "count": count, "note": note}

    return {"reviews": [], "count": 0, "note": ""}


def _find_review_block(data_dict, candidate_keys):
    """
    Firestore内のどこに口コミが入っていても拾えるようにする。
    探索順：
      1) data_dict["kutikomi"][key]
      2) data_dict["reviews"][key]
      3) data_dict[f"{key}_reviews"]
      4) data_dict[key]  （直置きの場合）
    """
    kutikomi = data_dict.get("kutikomi") or {}
    reviews_root = data_dict.get("reviews") or {}

    for k in candidate_keys:
        if k in kutikomi:
            return _parse_review_block(kutikomi.get(k))
        if k in reviews_root:
            return _parse_review_block(reviews_root.get(k))
        if f"{k}_reviews" in data_dict:
            return _parse_review_block(data_dict.get(f"{k}_reviews"))
        if k in data_dict:
            return _parse_review_block(data_dict.get(k))

    return {"reviews": [], "count": 0, "note": ""}


def _pad_to_10(reviews):
    reviews = (reviews or [])[:10]
    while len(reviews) < 10:
        reviews.append("")
    return reviews


def _range_a1(start_col_idx_1based, start_row, end_col_idx_1based, end_row):
    start_col = excel_column(start_col_idx_1based)
    end_col = excel_column(end_col_idx_1based)
    return f"{start_col}{start_row}:{end_col}{end_row}"


# ============================================================
# v2: onsen_data_v2 → シート出力（口コミ列も追加）
# ============================================================
def retrieveFirebase_v2_with_reviews(target_sheetnum: int):
    db = get_firestore_client()
    docs = db.collection(COLLECTION_V2).stream()

    def get_period_time(periods, day, key):
        if not periods:
            return ""
        for p in periods:
            if p.get("day") == day:
                return p.get(key, "")
        return ""

    # -------------------------
    # ヘッダー行（1行目）
    # -------------------------
    header = []

    # 既存の基本列（あなたの現在の順番そのまま）
    header += ["温泉名", "サウナ", "ロウリュ", "塩サウナ", "泥", "水風呂", "天然", "炭酸", "漫画", "wifi", "岩盤", "洗顔"]
    # 営業時間（day=0..6 open/close）
    for d in range(7):
        header += [f"open_day{d}", f"close_day{d}"]
    header += ["緯度", "経度", "住所", "URL", "平日値段", "休日値段", "値段ソース(空)", "駅距離", "駅時間", "最寄駅"]
    header += [f"image{i+1}" for i in range(7)]
    header += ["特徴", "docId", "onsenId", "宿泊フラグ"]

    # 口コミ（LABELS：各ラベル10件）
    for display_group, _keys in LABELS:
        title = display_group[0] if len(display_group) == 1 else ",".join(display_group)
        header += [f"{title}_口コミ{i+1}" for i in range(10)]

    # 追加口コミ（宿泊：count/note + 10件）
    for display_group, _keys in ADD_LABELS:
        title = display_group[0] if len(display_group) == 1 else ",".join(display_group)
        header += [f"{title}_件数", f"{title}_note"]
        header += [f"{title}_口コミ{i+1}" for i in range(10)]

    data_rows = []
    count = 0

    for doc in docs:
        count += 1
        data_dict = doc.to_dict()
        row = []

        # -------------------------
        # 基本情報（あなたのv2出力順）
        # -------------------------
        row.append(data_dict.get("onsen_name", ""))
        row.append(data_dict.get("sauna", ""))
        row.append(data_dict.get("rouryu", ""))
        row.append(data_dict.get("siosauna", ""))
        row.append(data_dict.get("doro", ""))
        row.append(data_dict.get("mizuburo", ""))
        row.append(data_dict.get("tennen", ""))
        row.append(data_dict.get("tansan", ""))
        row.append(data_dict.get("manga", ""))
        row.append(data_dict.get("wifi", ""))
        row.append(data_dict.get("ganban", ""))
        row.append(data_dict.get("facewash", ""))

        periods = data_dict.get("periods", []) or []
        for day in range(7):
            row.append(get_period_time(periods, day, "open"))
            row.append(get_period_time(periods, day, "close"))

        row.append(data_dict.get("latitude", ""))
        row.append(data_dict.get("longitude", ""))
        row.append(data_dict.get("place", ""))
        row.append(data_dict.get("url", ""))
        row.append(data_dict.get("heijitunedan", ""))
        row.append(data_dict.get("kyuzitunedan", ""))
        row.append("")  # 値段ソース(空)

        ekitika = data_dict.get("ekitika") or {}
        row.append(ekitika.get("kyori", ""))
        row.append(ekitika.get("zikan", ""))
        row.append(ekitika.get("moyorieki", ""))

        images = data_dict.get("images", []) or []
        for i in range(7):
            row.append(images[i] if i < len(images) else "")

        row.append(data_dict.get("feature", ""))
        row.append(doc.id)
        row.append(data_dict.get("onsenId", ""))
        row.append(data_dict.get("syukuhaku", ""))  # 宿泊フラグ

        # -------------------------
        # 口コミ（Firestoreから取り出して列に展開）
        # -------------------------
        for _display_group, candidate_keys in LABELS:
            block = _find_review_block(data_dict, candidate_keys)
            row += _pad_to_10(block["reviews"])

        for _display_group, candidate_keys in ADD_LABELS:
            block = _find_review_block(data_dict, candidate_keys)
            row.append(block.get("count", 0))
            row.append(block.get("note", ""))
            row += _pad_to_10(block["reviews"])

        data_rows.append(row)

    # -------------------------
    # 一括書き込み（ヘッダー + データ）
    # 列数は header の長さから自動で範囲計算
    # -------------------------
    all_rows = [header] + data_rows
    last_col_idx = len(header)              # 1-based
    last_row_idx = 1 + count                # ヘッダー行(1) + データ件数

    rng = _range_a1(1, 1, last_col_idx, last_row_idx)  # A1:??{n}
    write_multi_spreadsheet(rng, all_rows, target_sheetnum)


# ============================================================
# main：新規シートを作って、口コミつきで出力
# ============================================================
if __name__ == "__main__":
    new_title = f"onsen_export_v2_with_reviews_{datetime.now():%Y%m%d_%H%M%S}"
    new_sheetnum = create_new_worksheet(title=new_title, rows=5000, cols=200)

    retrieveFirebase_v2_with_reviews(target_sheetnum=new_sheetnum)
