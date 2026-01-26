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

# ----------------------------------------
# ★ デフォルト（今までのままでも動く）
# ----------------------------------------
_DEFAULT_SPREADSHEET_KEY = '1xnWPdkeu-ouaSYuDSKDK_MFMpxyEeH_hKjkFFTFI1kM'
_default_sheetnum = 0

spreadsheet = client.open_by_key(_DEFAULT_SPREADSHEET_KEY)


def configure_spreadsheet(spreadsheet_key: str, default_sheetnum: int = 0):
    """
    ★ main.py から呼んで「書き込み先スプレッドシート」を切り替える
    """
    global spreadsheet, _default_sheetnum
    spreadsheet = client.open_by_key(spreadsheet_key)
    _default_sheetnum = default_sheetnum

def _ws(sheetnum=None):
    """内部：対象worksheetを返す（指定がなければ default_sheetnum）"""
    if sheetnum is None:
        sheetnum = _default_sheetnum
    return spreadsheet.get_worksheet(sheetnum)

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
def read_spreadsheet(cell, sheetnum=None):
    return _ws(sheetnum).acell(cell).value

# スピプレッドシートから全読み込み
def read_all_spreadsheet(sheetnum=0):
    return _ws(sheetnum).get_values()

# スピプレッドシートから範囲書き込み
def write_multi_spreadsheet(cell, value, sheetnum=0):
    _ws(sheetnum).update(cell, value)

# スピプレッドシートから書き込み
def write_spreadsheet(cell, value, note=None, sheetnum=0):
    ws = _ws(sheetnum)
    ws.update_acell(cell, value)

    if note:
        url = "https://script.google.com/macros/s/AKfycbx9u3FzZ7Vnu6wo39bJYMH5Oh-Pj0sPUNixlEjHGcYmT6Cys7-y6xlspaoZ13Rq97j9Ig/exec"
        data = {'cell': cell, 'note': note}
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
def write_spreadsheet_placeapi(rownum, placeApiInfo, sheetnum=0):
    base_index = 13  # M
    for day in range(7):
        open_key = f"opentime_day_{day}"
        close_key = f"closetime_day_{day}"
        write_spreadsheet(f"{excel_column(base_index)}{rownum}", placeApiInfo[open_key], sheetnum=sheetnum)
        base_index += 1
        write_spreadsheet(f"{excel_column(base_index)}{rownum}", placeApiInfo[close_key], sheetnum=sheetnum)
        base_index += 1

    for data_key in ["lat", "lng", "address", "url"]:
        write_spreadsheet(f"{excel_column(base_index)}{rownum}", placeApiInfo[data_key], sheetnum=sheetnum)
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


