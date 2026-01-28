from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, sys, re, json
from datetime import datetime
import traceback
import os, platform, subprocess, signal, tempfile, shutil


from components.ConnectGemini import requestGemini

sys.path.append('../')

from components.SpreadSheet import (
    configure_spreadsheet,
    read_spreadsheet,
    write_spreadsheet,
    write_spreadsheet_placeapi,
    write_multi_spreadsheet,     # ★追加
    read_all_spreadsheet,        # ★追加（任意：ヘッダーコピー用）
    create_new_worksheet,        # ★追加
)

from components.RetrieveKutikomi import open_kutikomi, search_kutikomi
from components.RequestPlacesAPI import *
from controller.CostContoroller import ServeCost
from controller.NearStController import *
from controller.ImageContoroller import *

import firebase_admin
from firebase_admin import credentials, firestore
import unicodedata
import difflib



# ==========================================================
# ★★★ 実行者が変更するのはここだけ ★★★
# ==========================================================

# --- (A) 一覧ページ → A列に施設名を投入する機能 ---
ENABLE_IMPORT_FROM_URL = True

# ★追加：このエリアだけ抽出したい（Noneなら全エリア）
AREA_FILTER_TEXT = "城東エリア"   # 例: "城東エリア" / "城南エリア" / None

# GoogleMapの口コミ検索クエリに地名を付与する
ENABLE_LOCATION_IN_KUTIKOMI_QUERY = True
KUTIKOMI_FALLBACK_PREF = "東京都"   # 他県で回すならここを変える

# 一覧ページURL（実行者が指定）
SOURCE_LIST_URL = "https://www.supersento.com/kanto/tokyo.html"   # ★ここを差し替え 

# 新規シートに「テンプレの1行目（B1〜L1等）」をコピーするか（推奨）
COPY_TEMPLATE_HEADER = True
TEMPLATE_SHEETNUM = 0
TEMPLATE_HEADER_RANGE = "A1:L1"  # scraiping_main が B1〜L1 を参照するので最低ここは欲しい

# --- (B) 出力先スプレッドシート ---
TARGET_SPREADSHEET_KEY = "1xnWPdkeu-ouaSYuDSKDK_MFMpxyEeH_hKjkFFTFI1kM"
TARGET_SHEETNUM = 0  # ENABLE_IMPORT_FROM_URL=True の場合、ここはテンプレのあるシート番号

# --- (C) Firebase 既存チェック ---
SERVICE_ACCOUNT_JSON = "onsenmatching-firebase-adminsdk-qd1mg-ccda745b2d.json"
COLLECTIONS_TO_CHECK = ["onsen_data_v2"]
FIREBASE_EXISTS_COL = "AS"
SKIP_IF_EXISTS = False

# --- (D) 施設調査を回す行範囲（A列が埋まった後に回す） ---
RUN_FULL_SCRAPING = True
TEST_ROW_FROM = 7
TEST_ROW_TO = 50   # rangeの終点は含まれないので注意


# --- (E) URL取り込み時のFirebase重複除外（NEW） ---
ENABLE_FIREBASE_DEDUP_ON_IMPORT = True

# 名前類似度しきい値
DEDUP_NAME_STRONG = 0.92   # これ以上なら住所なしでも重複扱い
DEDUP_NAME_WEAK   = 0.86   # これ以上なら住所もチェックして重複判定

# 住所類似度しきい値（住所が取れる場合のみ）
DEDUP_ADDR_MATCH  = 0.70

# 重複/類似のログを出す
LOG_DUPLICATES = True





# ==========================================================


# ==========================================================
# ★固定ヘッダー（この順で出力）
# ==========================================================
OUTPUT_HEADER_TEXT = """
温泉名	サウナ	ロウリュウ,ロウリュ	塩サウナ	泥	水風呂	天然	炭酸風呂,炭酸泉	漫画	Wi-fi,wifi	岩盤浴	洗顔	宿泊	open_day0	close_day0	open_day1	close_day1	open_day2	close_day2	open_day3	close_day3	open_day4	close_day4	open_day5	close_day5	open_day6	close_day6	緯度	経度	住所	URL	平日値段	休日値段	値段ソース(空)	駅距離	駅時間	最寄駅	image1	image2	image3	image4	image5	image6	image7	特徴	docId	onsenId	サウナ_口コミ1	サウナ_口コミ2	サウナ_口コミ3	サウナ_口コミ4	サウナ_口コミ5	サウナ_口コミ6	サウナ_口コミ7	サウナ_口コミ8	サウナ_口コミ9	サウナ_口コミ10	ロウリュウ,ロウリュ_口コミ1	ロウリュウ,ロウリュ_口コミ2	ロウリュウ,ロウリュ_口コミ3	ロウリュウ,ロウリュ_口コミ4	ロウリュウ,ロウリュ_口コミ5	ロウリュウ,ロウリュ_口コミ6	ロウリュウ,ロウリュ_口コミ7	ロウリュウ,ロウリュ_口コミ8	ロウリュウ,ロウリュ_口コミ9	ロウリュウ,ロウリュ_口コミ10	塩サウナ_口コミ1	塩サウナ_口コミ2	塩サウナ_口コミ3	塩サウナ_口コミ4	塩サウナ_口コミ5	塩サウナ_口コミ6	塩サウナ_口コミ7	塩サウナ_口コミ8	塩サウナ_口コミ9	塩サウナ_口コミ10	泥_口コミ1	泥_口コミ2	泥_口コミ3	泥_口コミ4	泥_口コミ5	泥_口コミ6	泥_口コミ7	泥_口コミ8	泥_口コミ9	泥_口コミ10	水風呂_口コミ1	水風呂_口コミ2	水風呂_口コミ3	水風呂_口コミ4	水風呂_口コミ5	水風呂_口コミ6	水風呂_口コミ7	水風呂_口コミ8	水風呂_口コミ9	水風呂_口コミ10	天然_口コミ1	天然_口コミ2	天然_口コミ3	天然_口コミ4	天然_口コミ5	天然_口コミ6	天然_口コミ7	天然_口コミ8	天然_口コミ9	天然_口コミ10	炭酸風呂,炭酸泉_口コミ1	炭酸風呂,炭酸泉_口コミ2	炭酸風呂,炭酸泉_口コミ3	炭酸風呂,炭酸泉_口コミ4	炭酸風呂,炭酸泉_口コミ5	炭酸風呂,炭酸泉_口コミ6	炭酸風呂,炭酸泉_口コミ7	炭酸風呂,炭酸泉_口コミ8	炭酸風呂,炭酸泉_口コミ9	炭酸風呂,炭酸泉_口コミ10	漫画_口コミ1	漫画_口コミ2	漫画_口コミ3	漫画_口コミ4	漫画_口コミ5	漫画_口コミ6	漫画_口コミ7	漫画_口コミ8	漫画_口コミ9	漫画_口コミ10	Wi-fi,wifi_口コミ1	Wi-fi,wifi_口コミ2	Wi-fi,wifi_口コミ3	Wi-fi,wifi_口コミ4	Wi-fi,wifi_口コミ5	Wi-fi,wifi_口コミ6	Wi-fi,wifi_口コミ7	Wi-fi,wifi_口コミ8	Wi-fi,wifi_口コミ9	Wi-fi,wifi_口コミ10	岩盤浴_口コミ1	岩盤浴_口コミ2	岩盤浴_口コミ3	岩盤浴_口コミ4	岩盤浴_口コミ5	岩盤浴_口コミ6	岩盤浴_口コミ7	岩盤浴_口コミ8	岩盤浴_口コミ9	岩盤浴_口コミ10	洗顔_口コミ1	洗顔_口コミ2	洗顔_口コミ3	洗顔_口コミ4	洗顔_口コミ5	洗顔_口コミ6	洗顔_口コミ7	洗顔_口コミ8	洗顔_口コミ9	洗顔_口コミ10	宿泊_口コミ1	宿泊_口コミ2	宿泊_口コミ3	宿泊_口コミ4	宿泊_口コミ5	宿泊_口コミ6	宿泊_口コミ7	宿泊_口コミ8	宿泊_口コミ9	宿泊_口コミ10
""".strip()

OUTPUT_HEADERS = [h for h in re.split(r"[\t\n]+", OUTPUT_HEADER_TEXT) if h]

def col_letter(n: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA ..."""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

HEADER_COL = {name: col_letter(i + 1) for i, name in enumerate(OUTPUT_HEADERS)}


# Selenium用の専用プロファイル（ここがコツ：これを使うChromeだけを狙い撃ちでkillできる）
SELENIUM_PROFILE_DIR = os.path.join(tempfile.gettempdir(), "onsen_matching_selenium_profile")

def _ps_list_posix():
    # mac/linux: pid と cmdline を全部取る
    out = subprocess.check_output(["ps", "-axo", "pid=,command="], text=True)
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        pid_str, cmd = line.split(None, 1)
        yield int(pid_str), cmd

def _kill_pid_posix(pid: int):
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        pass

def cleanup_orphaned_selenium():
    """
    1) 前回残った Chrome(このプロファイル利用中) を kill
    2) chromedriver を kill（他のseleniumも一緒に消える可能性あり）
    3) プロファイルディレクトリを削除（ロック回避）
    """
    system = platform.system()

    if system in ("Darwin", "Linux"):
        # (A) このスクリプトのプロファイルを使ってる Chrome を狙い撃ちで kill
        for pid, cmd in _ps_list_posix():
            if pid == os.getpid():
                continue
            if SELENIUM_PROFILE_DIR in cmd:
                _kill_pid_posix(pid)

        # (B) chromedriver が残ってるなら kill（雑に全部落ちる点は注意）
        # 安全にしたいならこの行はコメントアウトしてもOK
        subprocess.run(["pkill", "-x", "chromedriver"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # (C) プロファイル削除（「user data dir is already in use」対策）
        shutil.rmtree(SELENIUM_PROFILE_DIR, ignore_errors=True)

    elif system == "Windows":
        # chromedriver を終了
        subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # プロファイル削除
        shutil.rmtree(SELENIUM_PROFILE_DIR, ignore_errors=True)

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={SELENIUM_PROFILE_DIR}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    # options.add_argument("--headless=new")  # 画面不要ならON
    return webdriver.Chrome(options=options)




# driver = webdriver.Chrome()  ← これを消す
driver = None


# ---------------------------
# Firestore
# ---------------------------
def get_firestore_client():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_JSON)
        firebase_admin.initialize_app(cred)
    return firestore.client()

DB = get_firestore_client()


def query_same_name_docs(collection_name: str, onsen_name: str):
    col = DB.collection(collection_name)
    try:
        q = col.where("onsen_name", "==", onsen_name)
    except TypeError:
        from google.cloud.firestore_v1 import FieldFilter
        q = col.where(filter=FieldFilter("onsen_name", "==", onsen_name))
    return list(q.stream())


def check_exists_in_firebase(onsen_name: str):
    hits = []
    for c in COLLECTIONS_TO_CHECK:
        docs = query_same_name_docs(c, onsen_name)
        for d in docs:
            hits.append((c, d))
    return hits

def _nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")

def normalize_name(name: str) -> str:
    s = _nfkc(name).lower()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[‐-–—−ー]", "-", s)  # ハイフン類
    s = re.sub(r"[()（）\[\]【】『』「」]", "", s)
    return s.strip()

def normalize_addr(addr: str) -> str:
    s = _nfkc(addr).lower()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[‐-–—−ー]", "-", s)
    s = re.sub(r"[()（）\[\]【】『』「」]", "", s)
    return s.strip()

def sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()

def extract_city_ward(addr: str) -> str:
    """
    ざっくり市区町村を抜く（例: 台東区 / 墨田区 / 横浜市 など）
    """
    a = _nfkc(addr)
    m = re.search(r"(.{1,10}?(?:市|区|町|村))", a)
    return m.group(1) if m else ""

def build_firestore_index():
    """
    COLLECTIONS_TO_CHECK を全部 stream して、(名前, 住所) の検索用インデックスを作る。
    返り値: prefix_index, all_docs
    """
    all_docs = []
    prefix_index = {}  # 先頭2文字 -> list[doc]

    for c in COLLECTIONS_TO_CHECK:
        for d in DB.collection(c).stream():
            data = d.to_dict() or {}
            name = data.get("onsen_name", "") or ""
            addr = data.get("place", "") or data.get("address", "") or ""

            nname = normalize_name(name)
            naddr = normalize_addr(addr)

            docinfo = {
                "collection": c,
                "docid": d.id,
                "name": name,
                "addr": addr,
                "nname": nname,
                "naddr": naddr,
                "cityward": extract_city_ward(addr),
            }
            all_docs.append(docinfo)

            p = nname[:2] if len(nname) >= 2 else nname
            prefix_index.setdefault(p, []).append(docinfo)

    return prefix_index, all_docs


def find_duplicate_in_firestore(candidate_name: str, candidate_addr: str, prefix_index):
    """
    (候補名, 候補住所) が Firestore に重複として存在するか判定する。
    戻り値:
      - duplicate=True: (True, best_match, reason, scores)
      - duplicate=False: (False, best_match_or_None, reason, scores)
    """
    cn = normalize_name(candidate_name)
    ca = normalize_addr(candidate_addr)
    c_city = extract_city_ward(candidate_addr)

    # ざっくり候補集合（先頭2文字）
    p = cn[:2] if len(cn) >= 2 else cn
    candidates = prefix_index.get(p, [])

    # 先頭2文字が弱いケース向けに、末尾2文字も追加（保険）
    if len(cn) >= 2:
        p2 = cn[-2:]
        candidates = candidates + prefix_index.get(p2, [])

    # 重複候補が少なすぎる/ゼロの時は諦め（誤検出を避ける）
    if not candidates:
        return False, None, "no_candidates", {}

    best = None
    best_name_score = 0.0
    best_addr_score = 0.0

    for doc in candidates:
        # 完全一致
        if cn and cn == doc["nname"]:
            return True, doc, "exact_name", {"name": 1.0, "addr": 0.0}

        name_score = sim(cn, doc["nname"])
        if name_score > best_name_score:
            best_name_score = name_score
            # 住所スコア（両方ある時のみ）
            addr_score = sim(ca, doc["naddr"]) if (ca and doc["naddr"]) else 0.0
            best_addr_score = addr_score
            best = doc

    # 強一致：住所なくても重複扱い
    if best and best_name_score >= DEDUP_NAME_STRONG:
        return True, best, "strong_name", {"name": best_name_score, "addr": best_addr_score}

    # 弱一致：住所も見て判断
    if best and best_name_score >= DEDUP_NAME_WEAK:
        # 住所が両方あれば類似度で判定
        if ca and best["naddr"]:
            if best_addr_score >= DEDUP_ADDR_MATCH:
                return True, best, "name+addr_match", {"name": best_name_score, "addr": best_addr_score}
            else:
                return False, best, "name_similar_but_addr_diff", {"name": best_name_score, "addr": best_addr_score}

        # 住所が片方欠ける場合：市区町村だけでも一致するなら重複寄り
        if c_city and best["cityward"] and c_city == best["cityward"]:
            return True, best, "name+cityward_match", {"name": best_name_score, "addr": best_addr_score}

        return False, best, "name_similar_but_no_addr", {"name": best_name_score, "addr": best_addr_score}

    return False, best, "not_similar", {"name": best_name_score, "addr": best_addr_score}


def _short_err(e: Exception, max_chars: int = 900) -> str:
    et = type(e).__name__
    msg = str(e)
    tb = traceback.format_exc()
    s = f"{et}: {msg}\n\n{tb}"
    return s[:max_chars]

def safe_run(step_name: str, fn, *, sheetnum=None, error_cell=None, on_error_value="ERR"):
    """
    fn() を実行し、例外が起きても止めずに None を返す。
    error_cell が指定されていれば、そのセルに on_error_value と note(エラー)を書き込む。
    """
    try:
        return fn()
    except Exception as e:
        print(f"❌ {step_name} failed: {e}")
        traceback.print_exc()

        if sheetnum is not None and error_cell:
            try:
                write_spreadsheet(
                    error_cell,
                    on_error_value,
                    note=f"[{step_name}]\n{_short_err(e)}",
                    sheetnum=sheetnum
                )
            except Exception as e2:
                print(f"⚠️ failed to write error note ({step_name}): {e2}")

        return None


# ==========================================================
# ★追加：URLの一覧ページから「県」「エリア」「施設名一覧」を抽出
# ==========================================================
PREF_RE = re.compile(
    r"(北海道|東京都|神奈川県|埼玉県|千葉県|茨城県|栃木県|群馬県|"
    r"青森県|岩手県|宮城県|秋田県|山形県|福島県|"
    r"新潟県|富山県|石川県|福井県|山梨県|長野県|"
    r"岐阜県|静岡県|愛知県|三重県|"
    r"滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|"
    r"鳥取県|島根県|岡山県|広島県|山口県|"
    r"徳島県|香川県|愛媛県|高知県|"
    r"福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)"
)

def sanitize_sheet_title(s: str) -> str:
    # Google Sheetsで禁止されがちな文字を置換
    s = re.sub(r"[\[\]\*\/\\\?\:]", "_", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:90]  # タイムスタンプ分を考慮して余裕を持たせる


def extract_prefecture_from_page(driver) -> str:
    """
    県名はサイトによって表示場所が違うので、
    title / h1 / breadcrumb など複数から探す
    """
    candidates = []

    try:
        candidates.append(driver.title or "")
    except:
        pass

    # よくある：h1/h2
    for xp in ["//h1", "//h2", "//h3", "//*[@class[contains(.,'breadcrumb')]]"]:
        try:
            els = driver.find_elements(By.XPATH, xp)
            for e in els:
                t = (e.text or "").strip()
                if t:
                    candidates.append(t)
        except:
            pass

    for t in candidates:
        m = PREF_RE.search(t)
        if m:
            return m.group(1)

    # 見つからない場合は空で返す（呼び出し側でフォールバック）
    return ""


def extract_area_from_page(driver) -> str:
    """
    スクショのように「○○エリア」が上に出ている想定。
    """
    els = driver.find_elements(By.XPATH, "//*[contains(normalize-space(.),'エリア')]")
    texts = []
    for e in els:
        t = (e.text or "").strip()
        if t and len(t) <= 30:
            texts.append(t)

    # 最も短くてそれっぽいものを採用（例: 城東エリア）
    if texts:
        texts.sort(key=len)
        return texts[0]

    return ""


def find_area_container(driver, area_text: str):
    """
    ページ内で area_text（例: '城南エリア'）が書かれている要素を探し、
    その近くに「名称」列を含む table を持つ最寄りの親コンテナを返す。
    """
    # まずは完全一致 → ダメなら部分一致
    xpaths = [
        f"//*[normalize-space()='{area_text}']",
        f"//*[contains(normalize-space(), '{area_text}')]",
    ]

    for xp in xpaths:
        for el in driver.find_elements(By.XPATH, xp):
            try:
                # 「名称」ヘッダーを含むtableを内包する最寄りの祖先を探す
                container = el.find_element(
                    By.XPATH,
                    "./ancestor::*[.//table[.//th[contains(normalize-space(.),'名称')]]][1]"
                )
                return container
            except Exception:
                continue

    return None


def extract_facilities_from_table(table_el):
    """
    指定された table から、(住所, 施設名) を抽出する。
    スクショ想定: 1列目=住所, 2列目=名称
    """
    items = []
    rows = table_el.find_elements(By.XPATH, ".//tr[td]")
    for r in rows:
        tds = r.find_elements(By.CSS_SELECTOR, "td")
        if len(tds) < 2:
            continue

        address = (tds[0].text or "").strip()

        name = (tds[1].text or "").strip()
        if not name:
            try:
                name = tds[1].find_element(By.TAG_NAME, "a").text.strip()
            except Exception:
                pass

        if name:
            items.append({"name": name, "address": address})

    # 重複除去（nameベースで順序維持）
    seen = set()
    uniq = []
    for it in items:
        key = it["name"]
        if key not in seen:
            seen.add(key)
            uniq.append(it)
    return uniq


def extract_facilities_from_page(driver, area_filter_text: str = None):
    """
    area_filter_text が指定されていれば、そのエリア見出しの表だけ抽出。
    None ならページ内の最初の「名称」テーブルから抽出。
    """
    if area_filter_text:
        container = find_area_container(driver, area_filter_text)
        if not container:
            raise RuntimeError(f"指定エリアが見つかりません: {area_filter_text}")

        tables = container.find_elements(By.XPATH, ".//table[.//th[contains(normalize-space(.),'名称')]]")
        if not tables:
            raise RuntimeError(f"指定エリア内に対象テーブルが見つかりません: {area_filter_text}")

        items = []
        for t in tables:
            items.extend(extract_facilities_from_table(t))

        # nameで重複除去（順序維持）
        seen = set()
        uniq = []
        for it in items:
            if it["name"] not in seen:
                seen.add(it["name"])
                uniq.append(it)
        return uniq

    table = driver.find_element(By.XPATH, "//table[.//th[contains(normalize-space(.),'名称')]]")
    return extract_facilities_from_table(table)




def import_facilities_to_new_sheet(list_url: str, area_filter_text: str = None) -> int:
    driver.get(list_url)

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//table[.//th[contains(normalize-space(.),'名称')]]"))
    )

    pref = extract_prefecture_from_page(driver) or "不明県"
    area = area_filter_text or (extract_area_from_page(driver) or "不明エリア")

    # ★施設(住所+名称)を取得
    facilities = extract_facilities_from_page(driver, area_filter_text=area_filter_text)

    # ★Firebaseインデックス作成（1回だけ）
    prefix_index = None
    if ENABLE_FIREBASE_DEDUP_ON_IMPORT:
        print("🔎 Firestore index building...")
        prefix_index, _ = build_firestore_index()
        print("✅ Firestore index ready")

    # ★重複除外
    filtered = []
    skipped = []

    for it in facilities:
        name = it["name"]
        addr = it.get("address", "")

        if ENABLE_FIREBASE_DEDUP_ON_IMPORT and prefix_index:
            is_dup, best, reason, scores = find_duplicate_in_firestore(name, addr, prefix_index)
            if is_dup:
                skipped.append((it, best, reason, scores))
                if LOG_DUPLICATES:
                    print("🛑 DUPLICATE-SKIP")
                    print(f"  new : {name} / {addr}")
                    if best:
                        print(f"  hit : [{best['collection']}] {best['name']} / {best['addr']} (docId={best['docid']})")
                    print(f"  why : {reason}  score(name={scores.get('name',0):.3f}, addr={scores.get('addr',0):.3f})")
                continue
            else:
                # 似てるが住所違い等で「追加」するケースもログ
                if LOG_DUPLICATES and best and reason.startswith("name_similar"):
                    print("🟡 SIMILAR-BUT-KEEP")
                    print(f"  new : {name} / {addr}")
                    print(f"  hit : [{best['collection']}] {best['name']} / {best['addr']} (docId={best['docid']})")
                    print(f"  why : {reason}  score(name={scores.get('name',0):.3f}, addr={scores.get('addr',0):.3f})")

        filtered.append(it)

    # ---- シート作成 ----
    title_base = sanitize_sheet_title(f"{pref}_{area}")
    new_title = f"{title_base}_{datetime.now():%Y%m%d_%H%M%S}"

    # ★列数はヘッダー数に合わせて十分確保（CZ等が出ても耐える）
    cols_needed = max(500, len(OUTPUT_HEADERS) + 10)
    new_sheetnum = create_new_worksheet(
        title=new_title,
        rows=max(2000, len(filtered) + 50),
        cols=cols_needed
    )

    last_col = col_letter(len(OUTPUT_HEADERS))
    write_multi_spreadsheet(f"A1:{last_col}1", [OUTPUT_HEADERS], sheetnum=new_sheetnum)

    # 参考：抽出元URLは「A1のメモ」に入れておく（セル値は変えない）
    write_spreadsheet(f"{HEADER_COL['温泉名']}1", "温泉名", note=f"抽出元URL: {list_url}", sheetnum=new_sheetnum)

    # 温泉名（A列固定想定だが、念のためヘッダー名から列を取る）
    name_col = HEADER_COL["温泉名"]
    name_values = [[it["name"]] for it in filtered]
    if name_values:
        start = 2
        end = start + len(name_values) - 1
        write_multi_spreadsheet(f"{name_col}{start}:{name_col}{end}", name_values, sheetnum=new_sheetnum)

    # 住所（ヘッダーの「住所」列へ入れる：B列ではない点が重要）
    addr_col = HEADER_COL["住所"]
    addr_values = [[it.get("address", "")] for it in filtered]
    if addr_values:
        start = 2
        end = start + len(addr_values) - 1
        write_multi_spreadsheet(f"{addr_col}{start}:{addr_col}{end}", addr_values, sheetnum=new_sheetnum)
    # ★ここまで★

    print(f"✅ 取得: {len(facilities)}件 / 追加: {len(filtered)}件 / 重複除外: {len(skipped)}件")
    print(f"✅ 新規シート: {new_title} (sheetnum={new_sheetnum})")
    return new_sheetnum

# 口コミ書き込みユーティリティ
def _uniq_keep_order(items):
    seen = set()
    out = []
    for x in items:
        t = (x or "").strip()
        if not t:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out

def write_reviews_to_cols(sheetnum, rownum, prefix, reviews, max_n=10):
    reviews = _uniq_keep_order(reviews)[:max_n]

    # 1行ぶんの横並び配列（足りない分は空）
    row_values = [(reviews[i] if i < len(reviews) else "") for i in range(max_n)]

    # 口コミ1〜口コミN は同一行で横に連続している前提（OUTPUT_HEADER_TEXT順）
    start_col = HEADER_COL.get(f"{prefix}_口コミ1")
    end_col   = HEADER_COL.get(f"{prefix}_口コミ{max_n}")

    # 連続していない/見つからない場合は従来通りにフォールバック
    if not start_col or not end_col:
        for i in range(1, max_n + 1):
            h = f"{prefix}_口コミ{i}"
            col = HEADER_COL.get(h)
            if not col:
                continue
            cell = f"{col}{rownum}"
            value = row_values[i-1]
            write_spreadsheet(cell, value, sheetnum=sheetnum)
        return reviews

    # ★ここが本命：10セルを1回で更新
    write_multi_spreadsheet(
        f"{start_col}{rownum}:{end_col}{rownum}",
        [row_values],
        sheetnum=sheetnum
    )
    return reviews


def write_placeapi_bulk(rownum, placeApiInfo, sheetnum=0):
    # ★open_day0 〜 URL までが OUTPUT_HEADER_TEXT 順で連続している前提
    headers = []
    values = []

    for day in range(7):
        headers.append(f"open_day{day}")
        values.append(placeApiInfo.get(f"opentime_day_{day}", ""))

        headers.append(f"close_day{day}")
        values.append(placeApiInfo.get(f"closetime_day_{day}", ""))

    headers += ["緯度", "経度", "住所", "URL"]
    values  += [
        placeApiInfo.get("lat", ""),
        placeApiInfo.get("lng", ""),
        placeApiInfo.get("address", ""),
        placeApiInfo.get("url", ""),
    ]

    start_col = HEADER_COL[headers[0]]
    end_col   = HEADER_COL[headers[-1]]

    write_multi_spreadsheet(
        f"{start_col}{rownum}:{end_col}{rownum}",
        [values],
        sheetnum=sheetnum
    )



def _clean_json_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()

def generate_feature_text(placeName: str, cat_summary: dict) -> tuple[str, str|None]:
    """
    cat_summary 例:
    {
      "サウナ": {"count": 1, "reviews": ["...","..."]},
      ...
    }
    戻り値: (feature_text, note_evidence)
    """
    # “根拠”としてGeminiに渡す素材を作る（短く）
    lines = [f"施設名: {placeName}"]
    for cat, v in cat_summary.items():
        c = v.get("count", 0)
        lines.append(f"- {cat}: {c}")
        for r in (v.get("reviews") or [])[:2]:  # 各カテゴリ最大2件だけ
            lines.append(f"  口コミ: {r}")

    facts = "\n".join(lines)

    system = (
        "あなたは温浴施設の紹介文作成者です。"
        "与えられた情報（件数・口コミ）だけを根拠に、施設の特徴を作ってください。"
        "推測・一般論・外部知識は禁止。根拠が無い内容は絶対に書かない。"
    )
    user = (
        "次の情報だけを使って、特徴を3行で作成してください。\n"
        "・各行は最大45文字程度\n"
        "・箇条書き（'・'）で3行\n"
        "・出力は必ずJSONのみ\n\n"
        "出力形式:\n"
        "{\"feature\":\"・...\\n・...\\n・...\",\"evidence\":\"...\"}\n\n"
        "入力:\n" + facts
    )

    raw = requestGemini(system, user)
    raw = _clean_json_text(raw)

    try:
        obj = json.loads(raw)
        feature = (obj.get("feature") or "").strip()
        evidence = (obj.get("evidence") or "").strip() or None
        return feature, evidence
    except Exception:
        # JSONで返らない時はフォールバック（最低限）
        fallback = "・口コミ情報不足\n・設備情報不足\n・要手動確認"
        return fallback, f"Gemini raw:\n{raw}"


def build_kutikomi_query(place_name: str, address: str | None, fallback_pref: str = "東京都") -> str:
    """
    GoogleMap検索で同名誤ヒットを避けるためのクエリを作る
    優先: 施設名 + 市区町村（住所から抽出）
    フォールバック: 施設名 + 東京都（など）
    """
    place_name = (place_name or "").strip()
    address = (address or "").strip()

    cityward = extract_city_ward(address) if address else ""
    if cityward:
        return f"{place_name} {cityward}".strip()

    # 住所が無い / 市区町村が取れない場合
    return f"{place_name} {fallback_pref}".strip()


# ==========================================================
# 既存の scraiping_main（★必ず sheetnum を受け取り、全 read/write に渡す）
# ==========================================================
def scraiping_main(rownum, sheetnum=None):
    if sheetnum is None:
        raise ValueError("scraiping_main: sheetnum is required")

    # 施設名取得
    name_col = HEADER_COL.get("温泉名")
    if not name_col:
        print("⚠️ ヘッダー『温泉名』が見つからないためスキップ")
        return

    placeName = safe_run(
        "read placeName",
        lambda: read_spreadsheet(f"{name_col}{rownum}", sheetnum=sheetnum),
        sheetnum=sheetnum,
        error_cell=f"{name_col}{rownum}"
    )

    if not placeName or not str(placeName).strip():
        print(f"⚠️ row {rownum}: 施設名が空なのでスキップ")
        return

    # Firebase既存チェック（ここで落ちても止めない）
    def _firebase_check():
        hits = check_exists_in_firebase(placeName)
        if hits:
            msg = f"Firebase既存あり({len(hits)}件)"
            lines = []
            for c, d in hits:
                data = d.to_dict() or {}
                lines.append(f"- [{c}] docId={d.id} / place={data.get('place','')} / url={data.get('url','')}")
            note = "\n".join(lines)
            write_spreadsheet(f"{FIREBASE_EXISTS_COL}{rownum}", msg, note, sheetnum=sheetnum)
            if SKIP_IF_EXISTS:
                return "SKIP"
        else:
            write_spreadsheet(f"{FIREBASE_EXISTS_COL}{rownum}", "Firebase既存なし", sheetnum=sheetnum)
        return "OK"

    fb_status = safe_run(
        "firebase check",
        _firebase_check,
        sheetnum=sheetnum,
        error_cell=f"{FIREBASE_EXISTS_COL}{rownum}"
    )
    if fb_status == "SKIP":
        return

    # 住所を取得（無ければ空）
    addr_col = HEADER_COL.get("住所")
    address = ""
    if addr_col:
        address = safe_run(
            "read address",
            lambda: read_spreadsheet(f"{addr_col}{rownum}", sheetnum=sheetnum),
            sheetnum=sheetnum,
            error_cell=f"{addr_col}{rownum}"
        ) or ""

    # GoogleMap検索クエリ（施設名 + 区市 を優先）
    query1 = placeName
    query2 = None
    if ENABLE_LOCATION_IN_KUTIKOMI_QUERY:
        query1 = build_kutikomi_query(placeName, address, fallback_pref=KUTIKOMI_FALLBACK_PREF)
        # フォールバック（区市が取れた場合でも、念のため都道府県版を用意）
        query2 = f"{placeName} {KUTIKOMI_FALLBACK_PREF}".strip()

    print(f"🔎 kutikomi query: {query1}")

    opened = safe_run(
        "open_kutikomi(query1)",
        lambda: open_kutikomi(driver, query1),
        sheetnum=sheetnum,
        error_cell=f"{name_col}{rownum}"
    )


    # 1回目が失敗したら、都道府県フォールバックでもう一回だけ試す
    if not opened and ENABLE_LOCATION_IN_KUTIKOMI_QUERY and query2 and query2 != query1:
        print(f"🔁 retry kutikomi query: {query2}")
        opened = safe_run(
            "open_kutikomi(query2)",
            lambda: open_kutikomi(driver, query2),
            sheetnum=sheetnum,
            error_cell=f"{name_col}{rownum}"
        )

    if not opened:
        safe_run(
            "mark same-name",
            lambda: write_spreadsheet(f"B{rownum}", "同一名称あり/検索失敗", sheetnum=sheetnum),
            sheetnum=sheetnum,
            error_cell=f"B{rownum}"
        )
        return


    KUTIKOMI_CATEGORIES = [
        ("サウナ", "サウナ"),
        ("ロウリュウ,ロウリュ", "ロウリュウ,ロウリュ"),
        ("塩サウナ", "塩サウナ"),
        ("泥", "泥"),
        ("水風呂", "水風呂"),
        ("天然", "天然"),
        ("炭酸風呂,炭酸泉", "炭酸風呂,炭酸泉"),
        ("漫画", "漫画"),
        ("Wi-fi,wifi", "Wi-fi,wifi"),
        ("岩盤浴", "岩盤浴"),
        ("洗顔", "洗顔"),
        ("宿泊", "宿泊"),
    ]

    forcount = 0
    cat_summary = {}

    for cat_header, review_prefix in KUTIKOMI_CATEGORIES:
        cat_col = HEADER_COL.get(cat_header)
        if not cat_col:
            continue

        # キーワードの読み込みが失敗しても空扱いで続行
        header_keywords = cat_header
        search_keywords = header_keywords.split(",")

        max_count = 0
        all_reviews = []
        notes = []

        for keyword in search_keywords:
            keyword = keyword.strip()
            if not keyword:
                continue

            r = safe_run(
                f"search_kutikomi {cat_header}:{keyword}",
                lambda: search_kutikomi(driver, keyword, forcount),
                sheetnum=sheetnum,
                error_cell=f"{cat_col}{rownum}"
            )
            forcount += 1

            if not r:
                continue

            max_count = max(max_count, r.get("count", 0))
            all_reviews.extend(r.get("reviews") or [])
            if r.get("note"):
                notes.append(f"[{keyword}] {r['note']}")

        picked = safe_run(
            f"write reviews {cat_header}",
            lambda: write_reviews_to_cols(sheetnum, rownum, review_prefix, all_reviews, max_n=10),
            sheetnum=sheetnum,
            error_cell=f"{cat_col}{rownum}"
        ) or []

        note_text = "\n\n".join(notes) if notes else None
        safe_run(
            f"write count {cat_header}",
            lambda: write_spreadsheet(f"{cat_col}{rownum}", max_count, note_text, sheetnum=sheetnum),
            sheetnum=sheetnum,
            error_cell=f"{cat_col}{rownum}"
        )

        cat_summary[cat_header] = {"count": max_count, "reviews": picked}

    # PlaceAPI（失敗しても後続をスキップしつつ進む）
    placeApiInfo = safe_run(
        "get_placeapi_data",
        lambda: get_placeapi_data(placeName),
        sheetnum=sheetnum,
        error_cell=f"{HEADER_COL.get('URL','A')}{rownum}"  # URL列が無ければA
    )

    if placeApiInfo:
        safe_run(
            "write_placeapi_bulk",
            lambda: write_placeapi_bulk(rownum, placeApiInfo, sheetnum=sheetnum),
            sheetnum=sheetnum,
            error_cell=f"{HEADER_COL.get('URL','A')}{rownum}"
        )

    # 料金（失敗しても次へ）
    heijitu_col = HEADER_COL.get("平日値段")
    safe_run(
        "ServeCost",
        lambda: ServeCost(driver, "東京都", placeName, rownum, sheetnum=sheetnum),
        sheetnum=sheetnum,
        error_cell=f"{heijitu_col}{rownum}" if heijitu_col else None
    )

    # 最寄駅（lat/lngが無ければスキップ）
    if placeApiInfo and placeApiInfo.get("lat") and placeApiInfo.get("lng"):
        ekikyori_col = HEADER_COL.get("駅距離")
        safe_run(
            "SearchNearStatiion",
            lambda: SearchNearStatiion(placeApiInfo["lat"], placeApiInfo["lng"], rownum, sheetnum=sheetnum),
            sheetnum=sheetnum,
            error_cell=f"{ekikyori_col}{rownum}" if ekikyori_col else None
        )
    else:
        print(f"⚠️ row {rownum}: lat/lng無しのため最寄駅検索スキップ")

    # 画像（失敗しても次へ）
    img1_col = HEADER_COL.get("image1")
    safe_run(
        "ServeImage",
        lambda: ServeImage(rownum, (placeApiInfo or {}).get("name", placeName), (placeApiInfo or {}).get("url"), sheetnum=sheetnum),
        sheetnum=sheetnum,
        error_cell=f"{img1_col}{rownum}" if img1_col else None
    )

    # 特徴（失敗しても次へ）
    feat_col = HEADER_COL.get("特徴")
    if feat_col:
        res = safe_run(
            "generate_feature_text",
            lambda: generate_feature_text(placeName, cat_summary),
            sheetnum=sheetnum,
            error_cell=f"{feat_col}{rownum}"
        )
        if res:
            feature_text, evidence = res
            safe_run(
                "write feature",
                lambda: write_spreadsheet(f"{feat_col}{rownum}", feature_text, note=evidence, sheetnum=sheetnum),
                sheetnum=sheetnum,
                error_cell=f"{feat_col}{rownum}"
            )



# ==========================================================
# main（★Phase2は必ず sheetnum を決めて渡す）
# ==========================================================
if __name__ == "__main__":
    try:
        cleanup_orphaned_selenium()   # ★起動前に残骸掃除

        driver = create_driver()      # ★tryの中で生成（finallyで確実に閉じられる）

        configure_spreadsheet(TARGET_SPREADSHEET_KEY, default_sheetnum=TARGET_SHEETNUM)
        safe_run("check_firewall", lambda: check_firewall())

        sheetnum_to_use = TARGET_SHEETNUM

        if ENABLE_IMPORT_FROM_URL:
            new_sheetnum = safe_run(
                "import_facilities_to_new_sheet",
                lambda: import_facilities_to_new_sheet(SOURCE_LIST_URL, area_filter_text=AREA_FILTER_TEXT)
            )
            if new_sheetnum is not None:
                sheetnum_to_use = new_sheetnum

        if RUN_FULL_SCRAPING:
            for value in range(TEST_ROW_FROM, TEST_ROW_TO):
                safe_run(
                    f"scraiping_main row={value}",
                    lambda v=value: scraiping_main(v, sheetnum=sheetnum_to_use),
                    sheetnum=sheetnum_to_use,
                    error_cell=f"{HEADER_COL.get('温泉名','A')}{value}"
                )
                print("休憩中")
                time.sleep(30)

    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass



