import os, time, requests
from typing import List, Optional
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from urllib.parse import urljoin

load_dotenv()

# 既存の環境変数名を流用（必要なら GOOGLE_MAPS_API_KEY 等に変更してOK）
PLACES_API_KEY = os.getenv("PLACES_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
PLACES_BASE = "https://places.googleapis.com/v1"


# ----------------------------
# fallback: 公式サイトから抽出（最終手段）
# ----------------------------
def get_photos_from_website(url: str) -> List[str]:
    """
    公式サイトからの抽出はノイズが多いので、fallback用途に限定。
    og:image / img / srcset を拾って、アイコン等をざっくり除外する。
    """
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    urls: List[str] = []

    # og:image を優先
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        urls.append(urljoin(url, og.get("content")))

    # img src / srcset
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            urls.append(urljoin(url, src))

        srcset = img.get("srcset")
        if srcset:
            # "url 1x, url 2x" 形式を雑に分解
            for part in srcset.split(","):
                u = part.strip().split(" ")[0].strip()
                if u:
                    urls.append(urljoin(url, u))

    # ざっくりノイズ除外（ロゴ/アイコン/スプライトなど）
    def _looks_noise(u: str) -> bool:
        low = u.lower()
        noise_keys = ["logo", "icon", "sprite", "favicon", "apple-touch-icon", "loading", "spinner"]
        if any(k in low for k in noise_keys):
            return True
        if low.endswith(".svg"):
            return True
        return False

    uniq = []
    seen = set()
    for u in urls:
        if not u or _looks_noise(u):
            continue
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)

    return uniq


# ----------------------------
# Places API helpers
# ----------------------------
def _headers(field_mask: Optional[str] = None) -> dict:
    h = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": PLACES_API_KEY,
    }
    if field_mask:
        h["X-Goog-FieldMask"] = field_mask
    return h


def _request_with_retry(method: str, url: str, *, headers=None, json_body=None, params=None, timeout=15, retry=3):
    last_err = None
    for i in range(retry):
        try:
            resp = requests.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
                timeout=timeout,
            )
            # 429/5xx は軽くリトライ
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (i + 1))
                continue
            return resp
        except Exception as e:
            last_err = e
            time.sleep(1.0 * (i + 1))
    raise last_err if last_err else RuntimeError("request failed")


def _search_place_id(query: str) -> Optional[str]:
    """
    places:searchText で placeId を取得
    """
    if not PLACES_API_KEY:
        raise RuntimeError("PLACES_API_KEY (or GOOGLE_MAPS_API_KEY) is not set")

    url = f"{PLACES_BASE}/places:searchText"
    body = {"textQuery": query}

    # 最低限 place.id が返ればOK
    resp = _request_with_retry(
        "POST",
        url,
        headers=_headers("places.id"),
        json_body=body,
        timeout=20,
        retry=3,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"places:searchText failed: {resp.status_code} {resp.text[:300]}")

    data = resp.json() or {}
    places = data.get("places") or []
    if not places:
        return None

    return places[0].get("id")


def _get_place_photos(place_id: str) -> List[str]:
    """
    places.get で photos[].name を取得
    """
    url = f"{PLACES_BASE}/places/{place_id}"
    resp = _request_with_retry(
        "GET",
        url,
        headers=_headers("photos"),
        timeout=20,
        retry=3,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"places.get failed: {resp.status_code} {resp.text[:300]}")

    place = resp.json() or {}
    photos = place.get("photos") or []
    # photos[i].name を返す（例: "places/XXXX/photos/YYYY"）
    return [p.get("name") for p in photos if p.get("name")]


def _get_photo_uri(photo_name: str, max_width_px: int = 1600) -> Optional[str]:
    """
    places.photos.getMedia で photoUri を取得（skipHttpRedirect=true）
    """
    url = f"{PLACES_BASE}/{photo_name}/media"
    params = {"maxWidthPx": max_width_px, "skipHttpRedirect": "true"}

    resp = _request_with_retry(
        "GET",
        url,
        headers={"X-Goog-Api-Key": PLACES_API_KEY},
        params=params,
        timeout=20,
        retry=3,
    )

    if resp.status_code != 200:
        return None

    j = resp.json() or {}
    return j.get("photoUri")


# ----------------------------
# main entry (旧 search_photos を置換)
# ----------------------------
def search_photos(query: str, website_url: Optional[str] = None, place_id: Optional[str] = None,
                 max_results: int = 20, max_width_px: int = 1600) -> List[str]:
    """
    1) Places写真（推奨） → 2) だめなら公式サイト抽出（fallback）
    """
    # まず Places 写真
    try:
        pid = place_id or _search_place_id(query)
        if pid:
            photo_names = _get_place_photos(pid)
            out: List[str] = []
            seen = set()

            for name in photo_names:
                if len(out) >= max_results:
                    break
                u = _get_photo_uri(name, max_width_px=max_width_px)
                if not u:
                    continue
                if u in seen:
                    continue
                seen.add(u)
                out.append(u)

            if out:
                return out
    except Exception as e:
        # Places取得失敗時はfallbackへ
        print(f"[warn] Places photo fetch failed: {e}")

    # fallback: 公式サイト（ノイズ多いので少量）
    if website_url:
        return get_photos_from_website(website_url)[:max_results]

    return []


if __name__ == "__main__":
    website_url = "https://saunarium-lava.com/"
    query = "サウナリウム高円寺"
    photos = search_photos(query, website_url)
    for p in photos[:10]:
        print(p)
