import sys
sys.path.append('../')

from components.RequestPlacesAPI import get_nearby_placeapi
from components.SpreadSheet import _ws  # 既存
import gspread

# ★追加：ヘッダーindexのキャッシュ（sheetnumごと）
_HEADER_IDX_CACHE = {}

def _build_header_index(sheetnum=0, header_row=1):
    cache_key = (sheetnum, header_row)
    if cache_key in _HEADER_IDX_CACHE:
        return _HEADER_IDX_CACHE[cache_key]

    ws = _ws(sheetnum)
    headers = ws.row_values(header_row)
    idx = {}
    for i, h in enumerate(headers, start=1):
        h = (h or "").strip()
        if h:
            idx[h] = i

    _HEADER_IDX_CACHE[cache_key] = idx
    return idx

def _col_letter(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

def SearchNearStatiion(lat, long, rownum, sheetnum=0):
    result = get_nearby_placeapi(lat, long)
    header_idx = _build_header_index(sheetnum=sheetnum, header_row=1)
    ws = _ws(sheetnum)

    targets = {
        "駅距離": result.get("distance_text", ""),
        "駅時間": result.get("duration_text", ""),
        "最寄駅": result.get("station_name", ""),
    }

    data = []
    for header_name, value in targets.items():
        col_num = header_idx.get(header_name)
        if not col_num:
            print(f"⚠️ header not found: {header_name} (sheetnum={sheetnum})")
            continue
        cell = f"{_col_letter(col_num)}{rownum}"
        data.append({"range": cell, "values": [[value]]})

    if data:
        # ★3セルまとめて1回のAPIで更新
        ws.batch_update(data)
