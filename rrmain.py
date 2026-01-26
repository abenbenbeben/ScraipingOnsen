"""
Google口コミ(キーワード検索)を Selenium で取得し、
スプレッドシートへ書き込むスクリプト。

想定:
- read_all_spreadsheet(), write_multi_spreadsheet(), write_spreadsheet()
- open_kutikomi(), search_kutikomi_rr(), search_kutikomi(), search_feature()
などは自作モジュール側に実装済み

主な処理:
1) incorporateReviews_existed(): 既存データ(複数ラベル)の口コミをまとめて取得してDGまで書く
2) incorporateReview_existed(): 既存データ(追加ラベルのみ)の口コミ + 件数 + note を書く
3) incorporateReviews_new():     新規データ(複数ラベル) + 特徴文生成 を書く
"""

from selenium import webdriver
import sys
import pprint

sys.path.append("../")

from components.SpreadSheet import (
    read_all_spreadsheet,
    write_multi_spreadsheet,
    write_spreadsheet,
)
from components.RetrieveKutikomi import (
    open_kutikomi,
    search_kutikomi_rr,
    search_kutikomi,
    search_feature,
)

# ---------------------------------------
# 検索ラベル定義（シート上の「0/1」等に対応）
# labels: 既存/新規で複数カテゴリ分の口コミを集める
# addLabels: 追加でピンポイントに集める（例：宿泊）
# ---------------------------------------
LABELS = [
    ["サウナ"],
    ["ロウリュウ", "ロウリュ"],
    ["塩サウナ"],
    ["泥"],
    ["水風呂"],
    ["天然"],
    ["炭酸風呂", "炭酸泉"],
    ["漫画"],
    ["Wi-fi", "wifi"],
    ["岩盤浴"],
    ["洗顔"],
]
ADD_LABELS = [["宿泊"]]


# ============================================================
# 共通ユーティリティ
# ============================================================
def pad_reviews_to_10(reviews):
    """口コミリストを最大10件に切り、足りない分は空文字で埋める。"""
    reviews = (reviews or [])[:10]
    while len(reviews) < 10:
        reviews.append("")
    return reviews


def choose_best_reviews_by_synonyms(driver, keywords, forcount, use_rr=True):
    """
    同義語(例: ロウリュウ/ロウリュ)で複数検索し、
    「最も長い reviews を返した結果」を採用する。

    use_rr=True  -> search_kutikomi_rr を使う（既存コード踏襲）
    use_rr=False -> search_kutikomi を使う（件数やnoteも返す版）
    """
    best = []
    for kw in keywords:
        if use_rr:
            res = search_kutikomi_rr(driver, kw.strip(), forcount)
            reviews = res.get("reviews", [])
        else:
            res = search_kutikomi(driver, kw.strip(), forcount)
            reviews = res.get("reviews", [])

        # 「レビューが多いほう」を採用（既存ロジック踏襲）
        if len(reviews) > len(best):
            best = reviews

        forcount += 1

    return best, forcount


def build_label_header_row(labels):
    """
    ヘッダー行を生成:
    - "温泉名" + 各ラベル(10列分) を連結
    """
    header = ["温泉名"]
    for label_group in labels:
        # 例: ["ロウリュウ","ロウリュ"] → "ロウリュウ,ロウリュ"
        title = label_group[0] if len(label_group) == 1 else ",".join(label_group)

        # 1つのラベルにつき 10セル分のヘッダ（先頭だけ文字、残り空）
        child = [title] + [""] * 9
        header.extend(child)

    return header


# ============================================================
# 1) 既存データ: 複数ラベル分の口コミをDGまで書く
# ============================================================
def incorporateReviews_existed(driver):
    """
    シート(0)から既存温泉を読み、
    LABELSに対応する列(12列: 温泉名+11フラグ想定)を見て
    フラグが立っているラベルだけ口コミを取得して書き込みする。

    sameNameFlag:
      True  -> 同名施設が検索結果に複数ある想定。placenumで指定する。
      False -> ヘッダー行も書く運用（既存コード踏襲）
    """
    # ===== 同一名称（検索結果の施設が複数ある）対応 =====
    indirecteRow = 258
    placenum = None
    sameNameFlag = True
    # ===============================================

    # --- シート読み込み（先頭行はヘッダー想定なので捨てる） ---
    sheetValue = read_all_spreadsheet(0)
    sheetValue.pop(0)

    # 先頭12列だけ利用（温泉名 + ラベルフラグ列）
    values = [row[:12] for row in sheetValue]

    # 対象を1件だけに絞る（indirecteRowが「シート上の行番号」なので -2）
    values = [values[indirecteRow - 2]]
    start_row = indirecteRow

    insertData = []

    # ヘッダー行（同名運用のときは書かない、という既存ロジック踏襲）
    if sameNameFlag is not True:
        insertData.append(build_label_header_row(LABELS))

    try:
        for _, row in enumerate(values):
            forcount = 0
            output_row = []

            # rowの先頭は温泉名
            placeName = row.pop(0)
            print("================================")
            print(placeName)
            print("================================")

            output_row.append(placeName)

            # 口コミページが開けない場合は温泉名だけ書いて次へ
            if not open_kutikomi(driver, placeName, placenum):
                insertData.append(output_row)
                continue

            # 残りの row は LABELS(11個)に対応するフラグ列想定
            for label_index, flag in enumerate(row):
                if flag != "0":
                    label_group = LABELS[label_index]

                    # 同義語が1つなら単発検索、複数なら「レビュー多い方」を採用
                    if len(label_group) == 1:
                        kw = label_group[0]
                        res = search_kutikomi_rr(driver, kw.strip(), forcount)
                        reviews = res.get("reviews", [])
                        pprint.pprint(reviews)
                        forcount += 1
                    else:
                        reviews, forcount = choose_best_reviews_by_synonyms(
                            driver, label_group, forcount, use_rr=True
                        )
                        pprint.pprint(reviews)

                    # 10件に整形して出力行へ追加
                    output_row.extend(pad_reviews_to_10(reviews))
                else:
                    # フラグが0なら空10セル
                    output_row.extend([""] * 10)

            insertData.append(output_row)

    except Exception as e:
        print(f"エラーが発生しました: {e}")

    # 書き込み範囲（既存コード踏襲）
    # sameNameFlag True の場合はヘッダー無しなので行数計算が1つ違う
    if sameNameFlag is not True:
        write_multi_spreadsheet(f"A{start_row}:DG{start_row + len(values)}", insertData, 1)
    else:
        write_multi_spreadsheet(f"A{start_row}:DG{start_row + len(values) - 1}", insertData, 1)


# ============================================================
# 2) 既存データ: 特定ラベル(ADD_LABELS)だけ追加で取得しDH〜DQへ書く
# ============================================================
def incorporateReview_existed(driver):
    """
    シート(0)の既存温泉に対し、ADD_LABELS(例: 宿泊)の口コミを取得し、
    - 口コミ件数(total_elements) と note を AW列へ書き込み
    - 実際のレビュー10件分を DH〜DQ へ書き込む
    """
    # ===== 同一名称（検索結果の施設が複数ある）対応 =====
    indirecteRow = 237
    placenum = None
    sameNameFlag = True
    # ===============================================

    sheetValue = read_all_spreadsheet(0)
    sheetValue.pop(0)

    # 温泉名だけ取り出す（1列）
    values = [row[:1] for row in sheetValue]

    # 同名運用なら対象行のみ
    if sameNameFlag is True:
        values = [values[indirecteRow - 2]]

    start_row = indirecteRow
    insertData = []

    try:
        for idx, row in enumerate(values):
            forcount = 0

            placeName = row[0]
            print("================================")
            print(placeName)
            print("================================")

            # 口コミページが開けない場合は空行を入れて次へ
            if not open_kutikomi(driver, placeName, placenum):
                insertData.append([])
                continue

            # ADD_LABELS は少数想定なので、ここでは1ラベルずつ
            output_row = []
            for label_group in ADD_LABELS:
                total_elements = 0
                note = None

                if len(label_group) == 1:
                    kw = label_group[0]
                    res = search_kutikomi(driver, kw.strip(), forcount)
                    pprint.pprint(res)

                    total_elements = res.get("count", 0)
                    reviews = res.get("reviews", [])
                    note = res.get("note")

                    forcount += 1
                else:
                    # 同義語対応（count/note も最大を採用しつつ、noteは連結）
                    reviews = []
                    for kw in label_group:
                        res = search_kutikomi(driver, kw.strip(), forcount)
                        r = res.get("reviews", [])
                        c = res.get("count", 0)
                        n = res.get("note")

                        if len(r) > len(reviews):
                            reviews = r

                        total_elements = max(total_elements, c)

                        if n:
                            note = (note + n + "\n\n") if note else (n + "\n\n")

                        forcount += 1

                # 件数とnoteを AW列へ（行ごとに上書き）
                # ※ write_spreadsheet の引数仕様が (range, value, note) 前提で既存コード踏襲
                write_spreadsheet(f"AW{start_row + idx}", total_elements, note)

                output_row.extend(pad_reviews_to_10(reviews))

            insertData.append(output_row)

    except Exception as e:
        print(f"エラーが発生しました: {e}")

    pprint.pprint(insertData)

    # 書き込み範囲（既存コード踏襲）
    if sameNameFlag is not True:
        write_multi_spreadsheet(f"DH{start_row}:DQ{start_row + len(values)}", insertData, 1)
    else:
        write_multi_spreadsheet(f"DH{start_row}:DQ{start_row + len(values) - 1}", insertData, 1)


# ============================================================
# 3) 新規データ: 複数ラベル + 特徴文生成 まで行いA〜DHへ書く
# ============================================================
def incorporateReviews_new(driver):
    """
    新規データ用:
    - readSheetNum の温泉候補を読み
    - LABELSフラグに応じた口コミ(最大10件×11カテゴリ)を取得
    - search_feature() で特徴文章を生成
    - writeSheetNum に書き込む
    """
    # ===== シート設定 =====
    readSheetNum = 2
    writeSheetNum = 3
    deleteElement = 39  # 未使用（既存コード踏襲）
    start_row = 41
    # =====================

    sheetValue = read_all_spreadsheet(readSheetNum)
    sheetValue.pop(0)
    values = [row[:12] for row in sheetValue]

    # デバッグ用：1件だけ
    values = values[:1]
    # values = values[deleteElement:]  # 使う場合

    insertData = []

    # ヘッダー行を作成（最後に特徴文章列を追加）
    header = build_label_header_row(LABELS)
    header.append("特徴文章")
    insertData.append(header)

    try:
        for _, row in enumerate(values):
            forcount = 0
            output_row = []

            placeName = row.pop(0)
            print("================================")
            print(placeName)
            print("================================")

            output_row.append(placeName)

            if not open_kutikomi(driver, placeName):
                insertData.append(output_row)
                continue

            # 特徴文章（口コミページから抽出する想定）
            feature_sentence = search_feature(driver)

            # LABELSに対応するフラグ列を見て口コミを集める
            for label_index, flag in enumerate(row):
                if flag != "0":
                    label_group = LABELS[label_index]

                    if len(label_group) == 1:
                        kw = label_group[0]
                        res = search_kutikomi_rr(driver, kw.strip(), forcount)
                        reviews = res.get("reviews", [])
                        pprint.pprint(reviews)
                        forcount += 1
                    else:
                        reviews, forcount = choose_best_reviews_by_synonyms(
                            driver, label_group, forcount, use_rr=True
                        )
                        pprint.pprint(reviews)

                    output_row.extend(pad_reviews_to_10(reviews))
                else:
                    output_row.extend([""] * 10)

            output_row.append(feature_sentence)
            insertData.append(output_row)

    except Exception as e:
        print(f"エラーが発生しました: {e}")

    # 書き込み範囲（既存コード踏襲）
    write_multi_spreadsheet(
        f"A{start_row}:DH{start_row + len(values)}",
        insertData,
        writeSheetNum,
    )


# ============================================================
# エントリーポイント
# ============================================================
if __name__ == "__main__":
    # ChromeDriver は main で作って最後に必ず quit
    driver = webdriver.Chrome()
    try:
        incorporateReview_existed(driver)
        # incorporateReviews_existed(driver)
        # incorporateReviews_new(driver)
    finally:
        driver.quit()
