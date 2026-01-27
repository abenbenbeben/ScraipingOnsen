import time, pprint, json, sys, os
sys.path.append('../')
from components.ImageAnalysis import run_checkobject
from components.RetrieveImage import search_photos
from components.SpreadSheet import write_multi_spreadsheet, get_col_by_header  # ★write_multi_spreadsheet を使う

def ServeImage(rownum, query, website_url, sheetnum=0):
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

    header_names = ["image1", "image2", "image3", "image4", "image5", "image6", "image7"]
    fallback_cols = ["AK", "AL", "AM", "AN", "AO", "AP", "AQ"]

    cols = [
        get_col_by_header(h, sheetnum=sheetnum, fallback=fallback_cols[i])
        for i, h in enumerate(header_names)
    ]

    # ★7セル分を1回で更新（足りない分は空）
    row_values = []
    for i in range(7):
        row_values.append(OutPutImageLists[i] if i < len(OutPutImageLists) else "")

    start_col = cols[0]
    end_col   = cols[-1]
    write_multi_spreadsheet(
        f"{start_col}{rownum}:{end_col}{rownum}",
        [row_values],
        sheetnum=sheetnum
    )



if __name__ == "__main__":
    website_url = 'https://saunarium-lava.com/'
    query = 'サウナリウム高円寺'
    ServeImage(2, query, website_url, sheetnum=0)
