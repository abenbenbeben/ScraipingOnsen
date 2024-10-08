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


# スピプレッドシートから読み込み
def read_spreadsheet(cell):

    # A1セルの読み込み
    value = sheet.acell(cell).value
    return value

# スピプレッドシートから全読み込み
def read_all_spreadsheet(sheetnum=0):
    worksheet = spreadsheet.get_worksheet(sheetnum)
    value = worksheet.get_values()
    return value

# スピプレッドシートから範囲書き込み
def write_multi_spreadsheet(cell, value,sheetnum=0):
    worksheet = spreadsheet.get_worksheet(sheetnum)
    # 指定されたセルに値を書き込み
    worksheet.update(cell, value)

# スピプレッドシートから書き込み
def write_spreadsheet(cell, value, sheetnum=0):
    worksheet = spreadsheet.get_worksheet(sheetnum)
    # 指定されたセルに値を書き込み
    worksheet.update_acell(cell, value)

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
def write_spreadsheet_placeapi_rfd(rownum, placeApiInfo):
    base_index = 13  # Mのアルファベットインデックス (13 -> M)
    data = []
    data_row = []
    # オープン時間とクローズ時間を書き込む
    for day in range(7):
        open_key = f"opentime_day_{day}"
        close_key = f"closetime_day_{day}"
        data_row.append(placeApiInfo[open_key])
        data_row.append(placeApiInfo[close_key])
    data.append(data_row)
    write_multi_spreadsheet(f"M{rownum}:Z{rownum}",data)

    
if __name__ == "__main__":
    cell_to_read = "A1"
    cell_to_write = 'B2'  # 例: 'A1'
    value_to_write = 'Hello, world!'
    comment = "コメントはこれ"
    #read_spreadsheet(cell_to_read)
    write_spreadsheet(cell_to_write,value_to_write,comment)


