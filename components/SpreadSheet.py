import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os, requests, json

# 環境変数をロードする
load_dotenv()

scope = ['https://www.googleapis.com/auth/spreadsheets']

# サービスアカウントキーファイルへのパス
creds = ServiceAccountCredentials.from_json_keyfile_name('/Users/abeyuichi/スクレイピング/onsenscraiping-010c634e8f24.json', scope)

# 認証
client = gspread.authorize(creds)

# スプレッドシートのIDを使って開く（スプレッドシートのURLから取得可能）
spreadsheet = client.open_by_key('1xnWPdkeu-ouaSYuDSKDK_MFMpxyEeH_hKjkFFTFI1kM')
sheet = spreadsheet.get_worksheet(0)  # 0は最初のシートを意味します

# -----------------------------
# 追加：新規シート（タブ）作成
# -----------------------------
def create_new_worksheet(title=None, rows=5000, cols=200):
    """
    新しい worksheet(タブ) を作成し、その sheetnum(0-based index) を返す
    """
    from datetime import datetime

    if title is None:
        title = f"export_{datetime.now():%Y%m%d_%H%M%S}"

    ws = spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

    # worksheets.index(ws) は失敗することがあるので、id で探す
    worksheets = spreadsheet.worksheets()
    for i, w in enumerate(worksheets):
        if w.id == ws.id:
            return i

    # 念のため：タイトルから取り直して再検索
    ws2 = spreadsheet.worksheet(title)
    worksheets = spreadsheet.worksheets()
    for i, w in enumerate(worksheets):
        if w.id == ws2.id:
            return i

    raise RuntimeError(f"Created worksheet '{title}' but failed to resolve sheet index.")



# スピプレッドシートから読み込み
def read_spreadsheet(cell, sheetnum=0):
    worksheet = spreadsheet.get_worksheet(sheetnum)
    return worksheet.acell(cell).value

# スピプレッドシートから全読み込み
def read_all_spreadsheet(sheetnum=0):
    worksheet = spreadsheet.get_worksheet(sheetnum)
    return worksheet.get_values()

# スピプレッドシートから範囲書き込み
def write_multi_spreadsheet(cell, value, sheetnum=0):
    worksheet = spreadsheet.get_worksheet(sheetnum)
    worksheet.update(cell, value)

# スピプレッドシートから書き込み
def write_spreadsheet(cell, value, note=None, sheetnum=0):
    worksheet = spreadsheet.get_worksheet(sheetnum)
    worksheet.update_acell(cell, value)

    if note:
        url = "https://script.google.com/macros/s/AKfycbx9u3FzZ7Vnu6wo39bJYMH5Oh-Pj0sPUNixlEjHGcYmT6Cys7-y6xlspaoZ13Rq97j9Ig/exec"
        data = {
            'cell': cell,
            'note': note
        }
        response = requests.post(url, data=json.dumps(data))
        print(response.text)

# Excelのカラム計算関数
def excel_column(index):
    column = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        column = chr(65 + remainder) + column
    return column

# 開始時間〜urlの書き込み補助関数
def write_spreadsheet_placeapi(rownum, placeApiInfo):
    base_index = 13  # Mのアルファベットインデックス (13 -> M)
    # オープン時間とクローズ時間を書き込む
    for day in range(7):
        open_key = f"opentime_day_{day}"
        close_key = f"closetime_day_{day}"
        write_spreadsheet(f"{excel_column(base_index)}{rownum}", placeApiInfo[open_key])
        base_index += 1
        write_spreadsheet(f"{excel_column(base_index)}{rownum}", placeApiInfo[close_key])
        base_index += 1

    # 追加のデータ
    additional_data = ["lat", "lng", "address", "url"]
    for data_key in additional_data:
        write_spreadsheet(f"{excel_column(base_index)}{rownum}", placeApiInfo[data_key])
        base_index += 1

# 開始時間〜urlの書き込み補助関数
def write_spreadsheet_placeapi_rfd(rownum, placeApiInfo, sheetnum=0):
    data_row = []
    for day in range(7):
        open_key = f"opentime_day_{day}"
        close_key = f"closetime_day_{day}"
        data_row.append(placeApiInfo[open_key])
        data_row.append(placeApiInfo[close_key])

    write_multi_spreadsheet(f"M{rownum}:Z{rownum}", [data_row], sheetnum)

    
if __name__ == "__main__":
    cell_to_read = "A1"
    cell_to_write = 'B2'  # 例: 'A1'
    value_to_write = 'Hello, world!'
    comment = "コメントはこれ"
    #read_spreadsheet(cell_to_read)
    write_spreadsheet(cell_to_write,value_to_write,comment)


