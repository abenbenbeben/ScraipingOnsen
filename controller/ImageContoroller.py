import time, pprint, json, sys, os
sys.path.append('../')
from components.ImageAnalysis import run_checkobject
from components.RetrieveImage import search_photos
from components.SpreadSheet import write_spreadsheet, get_col_by_header


def ServeImage(rownum, query, website_url, sheetnum=0):
    """
    sheetnum: 書き込み先シート番号（0-based）
    ヘッダー名から列を引くので、列順が変わっても壊れない
    """
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/abeyuichi/スクレイピング/onsenscraiping-010c634e8f24.json"

    if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")

    OutPutImageLists = []
    ImageLists = search_photos(query, website_url)

    for img in ImageLists:
        if len(OutPutImageLists) >= 7:
            break

        if website_url is not None and img.startswith(website_url):
            OutPutImageLists.append(img)
        else:
            if not run_checkobject(img):
                OutPutImageLists.append(img)

    # ★ヘッダー名から列取得（見つからない場合は従来列へフォールバック）
    header_names = ["image1", "image2", "image3", "image4", "image5", "image6", "image7"]
    fallback_cols = ["AK", "AL", "AM", "AN", "AO", "AP", "AQ"]

    cols = [
        get_col_by_header(h, sheetnum=sheetnum, fallback=fallback_cols[i])
        for i, h in enumerate(header_names)
    ]

    for col, image in zip(cols, OutPutImageLists):
        write_spreadsheet(f"{col}{rownum}", image, sheetnum=sheetnum)

    # 画像が7枚未満のとき、残りセルを空にしたいならここをON（任意）
    for col in cols[len(OutPutImageLists):]:
        write_spreadsheet(f"{col}{rownum}", "", sheetnum=sheetnum)


if __name__ == "__main__":
    website_url = 'https://saunarium-lava.com/'
    query = 'サウナリウム高円寺'
    ServeImage(2, query, website_url, sheetnum=0)
