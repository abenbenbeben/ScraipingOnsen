import sys
sys.path.append('../')

from components.RequestPlacesAPI import get_nearby_placeapi
from components.SpreadSheet import _ws  # ★追加: sheetからヘッダー取得のため
import gspread

def _build_header_index(sheetnum=0, header_row=1):
    """
    1行目のヘッダーから {ヘッダー名: 列番号(1-based)} を作る
    """
    ws = _ws(sheetnum)
    headers = ws.row_values(header_row)  # 1行目
    idx = {}
    for i, h in enumerate(headers, start=1):
        h = (h or "").strip()
        if h:
            idx[h] = i
    return idx

def _col_letter(n: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA ..."""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

def SearchNearStatiion(lat, long, rownum, sheetnum=0):
    """
    sheetnum: 書き込み先シート番号（0-based）
    ヘッダー順が変わっても '駅距離','駅時間','最寄駅' に書く
    """
    result = get_nearby_placeapi(lat, long)

    header_idx = _build_header_index(sheetnum=sheetnum, header_row=1)

    # 書き込み先ヘッダー（あなたのOUTPUT_HEADER_TEXTにある名前）
    targets = {
        "駅距離": result.get("distance_text", ""),
        "駅時間": result.get("duration_text", ""),
        "最寄駅": result.get("station_name", ""),
    }

    ws = _ws(sheetnum)

    for header_name, value in targets.items():
        col_num = header_idx.get(header_name)
        if not col_num:
            print(f"⚠️ header not found: {header_name} (sheetnum={sheetnum})")
            continue

        cell = f"{_col_letter(col_num)}{rownum}"
        ws.update_acell(cell, value)
