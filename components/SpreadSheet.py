import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os, requests, json
import unicodedata
import re
import unicodedata
import time, random
from gspread.exceptions import APIError

# 環境変数をロードする
load_dotenv()

scope = ['https://www.googleapis.com/auth/spreadsheets']

# サービスアカウントキーファイルへのパス
creds = ServiceAccountCredentials.from_json_keyfile_name(
    '/Users/abeyuichi/スクレイピング/onsenscraiping-010c634e8f24.json',
    scope
)

# 認証
client = gspread.authorize(creds)

# ----------------------------------------
# ★ Worksheet キャッシュ（429対策の本丸）
# ----------------------------------------
_WS_CACHE = {}          # {sheetnum: Worksheet}
_WS_LIST_CACHE = None   # [Worksheet, Worksheet, ...]（順番=sheetnum）

def _is_retryable_api_error(e: Exception) -> bool:
    if not isinstance(e, APIError):
        return False
    code = getattr(getattr(e, "response", None), "status_code", None)
    # 念のため文字列でも判定
    msg = str(e)
    return (code in (429, 500, 503, 504)) or ("[429]" in msg) or ("Quota exceeded" in msg)

def _retry(op_name: str, fn, max_retries: int = 7, base_sleep: float = 1.0, max_sleep: float = 60.0):
    """
    Sheets API の 429 / 503 等を指数バックオフでリトライ
    """
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            if (attempt >= max_retries) or (not _is_retryable_api_error(e)):
                raise
            sleep = min(max_sleep, base_sleep * (2 ** attempt)) + random.random()
            print(f"⚠️ Sheets API retryable error on {op_name}: {e}  -> sleep {sleep:.1f}s")
            time.sleep(sleep)

def _refresh_worksheets_cache():
    """
    worksheets() は1回のメタデータ取得で全WSを取れるので、ここだけ叩いて以降はキャッシュから返す
    """
    global _WS_LIST_CACHE, _WS_CACHE
    _WS_CACHE = {}
    _WS_LIST_CACHE = _retry("spreadsheet.worksheets()", lambda: spreadsheet.worksheets())

def _ws(sheetnum=None):
    """
    内部：対象worksheetを返す（指定がなければ default_sheetnum）
    ★毎回 get_worksheet() を呼ばない（= metadata read を量産しない）
    """
    global _WS_LIST_CACHE

    if sheetnum is None:
        sheetnum = _default_sheetnum

    if sheetnum in _WS_CACHE:
        return _WS_CACHE[sheetnum]

    if _WS_LIST_CACHE is None:
        _refresh_worksheets_cache()

    # sheetnum 範囲外ならキャッシュを更新して再挑戦
    if sheetnum < 0 or sheetnum >= len(_WS_LIST_CACHE):
        _refresh_worksheets_cache()

    ws = _WS_LIST_CACHE[sheetnum]
    _WS_CACHE[sheetnum] = ws
    return ws


# ----------------------------------------
# ★ デフォルト（今までのままでも動く）
# ----------------------------------------
_DEFAULT_SPREADSHEET_KEY = '1xnWPdkeu-ouaSYuDSKDK_MFMpxyEeH_hKjkFFTFI1kM'
_default_sheetnum = 0

spreadsheet = client.open_by_key(_DEFAULT_SPREADSHEET_KEY)
_refresh_worksheets_cache()   # ★追加

# ★追加：ヘッダー -> 列番号 のキャッシュ（sheetnumごと）
_header_cache = {}  # { sheetnum: {"温泉名": 1, "住所": 24, ...} }


def configure_spreadsheet(spreadsheet_key: str, default_sheetnum: int = 0):
    global spreadsheet, _default_sheetnum, _header_cache
    spreadsheet = _retry("client.open_by_key()", lambda: client.open_by_key(spreadsheet_key))
    _default_sheetnum = default_sheetnum
    _header_cache = {}
    _refresh_worksheets_cache()   # ★追加（WSメタデータを1回で取る）



def _ws(sheetnum=None):
    """内部：対象worksheetを返す（指定がなければ default_sheetnum）"""
    if sheetnum is None:
        sheetnum = _default_sheetnum
    return spreadsheet.get_worksheet(sheetnum)


def _norm_header(s: str) -> str:
    """
    ヘッダー比較用の正規化：
    - NFKC（全角/半角ゆれ吸収）
    - 前後空白除去
    """
    s = unicodedata.normalize("NFKC", (s or ""))
    return s.strip()


def invalidate_header_cache(sheetnum=None):
    """★追加：ヘッダー行を編集した後などに呼ぶと安全"""
    global _header_cache
    if sheetnum is None:
        _header_cache = {}
    else:
        _header_cache.pop(sheetnum, None)


def get_header_map(sheetnum=None, header_row: int = 1, force: bool = False) -> dict:
    """
    ★追加：指定シートのヘッダー(1行目)から {ヘッダー名: 列番号(1-based)} を作る
    """
    if sheetnum is None:
        sheetnum = _default_sheetnum

    if (not force) and sheetnum in _header_cache:
        return _header_cache[sheetnum]

    ws = _ws(sheetnum)
    headers = ws.row_values(header_row)  # 1行目の値リスト（左から）
    m = {}
    for i, h in enumerate(headers, start=1):
        hh = _norm_header(h)
        if not hh:
            continue
        # 同名ヘッダーが複数ある場合は最初を採用（必要なら仕様変更可）
        if hh not in m:
            m[hh] = i

    _header_cache[sheetnum] = m
    return m


def col_letter(n: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA ..."""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def cell_by_header(header_name: str, rownum: int, sheetnum=None, header_row: int = 1) -> str:
    """
    ★追加：ヘッダー名と行番号からセル(A1表記)を作る
    """
    hm = get_header_map(sheetnum=sheetnum, header_row=header_row)
    key = _norm_header(header_name)
    if key not in hm:
        raise KeyError(f"Header not found: '{header_name}' (sheetnum={sheetnum})")
    col_idx = hm[key]  # 1-based
    return f"{col_letter(col_idx)}{rownum}"


# -----------------------------
# 追加：新規シート（タブ）作成
# -----------------------------
def create_new_worksheet(title=None, rows=5000, cols=200):
    from datetime import datetime
    if title is None:
        title = f"export_{datetime.now():%Y%m%d_%H%M%S}"

    ws = _retry("add_worksheet()", lambda: spreadsheet.add_worksheet(title=title, rows=rows, cols=cols))

    # ★ここが重要：追加したら一覧キャッシュ更新
    _refresh_worksheets_cache()
    invalidate_header_cache()  # ヘッダキャッシュも安全のため破棄

    # sheetnumを探す
    for i, w in enumerate(_WS_LIST_CACHE):
        if w.id == ws.id:
            return i

    raise RuntimeError(f"Created worksheet '{title}' but failed to resolve sheet index.")



# スピプレッドシートから読み込み
def read_spreadsheet(cell, sheetnum=None):
    ws = _ws(sheetnum)
    return _retry(f"acell({cell})", lambda: ws.acell(cell).value)


# ★追加：ヘッダー名で読み込み
def read_by_header(header_name: str, rownum: int, sheetnum=None, header_row: int = 1):
    cell = cell_by_header(header_name, rownum, sheetnum=sheetnum, header_row=header_row)
    return read_spreadsheet(cell, sheetnum=sheetnum)


# スピプレッドシートから全読み込み
def read_all_spreadsheet(sheetnum=0):
    ws = _ws(sheetnum)
    return _retry("get_values()", lambda: ws.get_values())


# スピプレッドシートから範囲書き込み
def write_multi_spreadsheet(cell, value, sheetnum=0):
    ws = _ws(sheetnum)
    return _retry(f"update({cell})", lambda: ws.update(cell, value))


# スプレッドシートへ書き込み（A1形式指定）
def write_spreadsheet(cell, value, note=None, sheetnum=0):
    ws = _ws(sheetnum)
    _retry(f"update_acell({cell})", lambda: ws.update_acell(cell, value))

    if note:
        # note付与はAppsScriptなので Sheets quota とは別。ここはそのままでOK
        url = "https://script.google.com/macros/s/AKfycbwV4jBgoDlyphdRxbkGRTNT3DnJ0FWS6Iwxe66aGO0czUb2N3_aMn5zGJfmWU1glN1gbA/exec"
        payload = {"cell": cell, "note": note, "sheetnum": sheetnum}
        try:
            response = requests.post(url, json=payload, timeout=15)
            print(response.text)
        except Exception as e:
            print(f"⚠️ note post failed: {e}")


# ★追加：ヘッダー名で書き込み（ヘッダー順が変わっても壊れない）
def write_by_header(header_name: str, rownum: int, value, note=None, sheetnum=0, header_row: int = 1):
    cell = cell_by_header(header_name, rownum, sheetnum=sheetnum, header_row=header_row)
    write_spreadsheet(cell, value, note=note, sheetnum=sheetnum)


# Excelのカラム計算関数（互換のため残す）
def excel_column(index):
    column = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        column = chr(65 + remainder) + column
    return column


# -----------------------------------------
# ★修正：PlaceAPI書き込みを「ヘッダー名」基準に
# -----------------------------------------
def write_spreadsheet_placeapi(rownum, placeApiInfo, sheetnum=0):
    """
    ヘッダー順が変わっても壊れない版。
    必要なヘッダー名（例）:
      open_day0 / close_day0 ... open_day6 / close_day6
      緯度 / 経度 / 住所 / URL
    """
    # 念のため：ヘッダーが新しくなってる可能性があるなら force=True にしてもOK
    # get_header_map(sheetnum=sheetnum, force=True)

    for day in range(7):
        write_by_header(f"open_day{day}", rownum, placeApiInfo.get(f"opentime_day_{day}", ""), sheetnum=sheetnum)
        write_by_header(f"close_day{day}", rownum, placeApiInfo.get(f"closetime_day_{day}", ""), sheetnum=sheetnum)

    write_by_header("緯度", rownum, placeApiInfo.get("lat", ""), sheetnum=sheetnum)
    write_by_header("経度", rownum, placeApiInfo.get("lng", ""), sheetnum=sheetnum)
    write_by_header("住所", rownum, placeApiInfo.get("address", ""), sheetnum=sheetnum)
    write_by_header("URL", rownum, placeApiInfo.get("url", ""), sheetnum=sheetnum)


def write_spreadsheet_placeapi_rfd(rownum, placeApiInfo, sheetnum=0):
    """
    こちらもヘッダー順に依存しない版（セルごとに書く）
    """
    for day in range(7):
        write_by_header(f"open_day{day}", rownum, placeApiInfo.get(f"opentime_day_{day}", ""), sheetnum=sheetnum)
        write_by_header(f"close_day{day}", rownum, placeApiInfo.get(f"closetime_day_{day}", ""), sheetnum=sheetnum)

    write_by_header("緯度", rownum, placeApiInfo.get("lat", ""), sheetnum=sheetnum)
    write_by_header("経度", rownum, placeApiInfo.get("lng", ""), sheetnum=sheetnum)
    write_by_header("住所", rownum, placeApiInfo.get("address", ""), sheetnum=sheetnum)
    write_by_header("URL", rownum, placeApiInfo.get("url", ""), sheetnum=sheetnum)



_HEADER_COL_CACHE = {}  # key: (spreadsheet_key, sheetnum) -> {header: "A" ...}

def _normalize_header(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    return s.strip()

def _col_letter(n: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA ..."""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

def get_header_col_map(sheetnum=0, refresh=False):
    """
    1行目のヘッダーから {header: colLetter} を作る
    """
    ws = _ws(sheetnum)
    cache_key = (spreadsheet.id, sheetnum)

    if (not refresh) and cache_key in _HEADER_COL_CACHE:
        return _HEADER_COL_CACHE[cache_key]

    headers = ws.row_values(1)  # 1行目
    m = {}
    for i, h in enumerate(headers, start=1):
        hh = _normalize_header(h)
        if hh:
            m[hh] = _col_letter(i)

    _HEADER_COL_CACHE[cache_key] = m
    return m

def get_col_by_header(header_name: str, sheetnum=0, fallback=None, refresh=False):
    """
    header_name の列文字を返す。無ければ fallback（例: "AE"）を返す。
    """
    m = get_header_col_map(sheetnum=sheetnum, refresh=refresh)
    key = _normalize_header(header_name)
    col = m.get(key)

    if col:
        return col

    if fallback:
        print(f"⚠️ header not found: '{header_name}'. fallback='{fallback}'")
        return fallback

    raise KeyError(f"Header not found: {header_name}")



if __name__ == "__main__":
    cell_to_write = 'B2'
    value_to_write = 'Hello, world!'
    comment = "コメントはこれ"
    write_spreadsheet(cell_to_write, value_to_write, comment)
