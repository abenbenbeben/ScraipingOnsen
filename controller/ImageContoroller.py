import time, pprint, json, sys, os
sys.path.append('../')
from components.ImageAnalysis import run_checkobject
from components.RetrieveImage import search_photos
from components.SpreadSheet import write_spreadsheet

def ServeImage(rownum, query, website_url):

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

    columns = ['AK', 'AL', 'AM', 'AN', 'AO', 'AP', 'AQ']
    for col, image in zip(columns, OutPutImageLists):
        write_spreadsheet(f"{col}{rownum}", image)



if __name__ == "__main__":
    
    website_url = 'https://saunarium-lava.com/'  # スーパー銭湯のURLを指定
    # photos = get_photos_from_website(website_url)
    query = 'サウナリウム高円寺'
    ServeImage(2, query, website_url)



