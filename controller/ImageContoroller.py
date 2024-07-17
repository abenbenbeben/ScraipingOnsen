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
        if img.startswith(website_url):
            OutPutImageLists.append(img)
        else:
            if not run_checkobject(img):
                OutPutImageLists.append(img)

    write_spreadsheet(f"AK{rownum}",OutPutImageLists[0])
    write_spreadsheet(f"AL{rownum}",OutPutImageLists[1])
    write_spreadsheet(f"AM{rownum}",OutPutImageLists[2])
    write_spreadsheet(f"AN{rownum}",OutPutImageLists[3])
    write_spreadsheet(f"AO{rownum}",OutPutImageLists[4])
    write_spreadsheet(f"AP{rownum}",OutPutImageLists[5])
    write_spreadsheet(f"AQ{rownum}",OutPutImageLists[6])



if __name__ == "__main__":
    
    website_url = 'https://saunarium-lava.com/'  # スーパー銭湯のURLを指定
    # photos = get_photos_from_website(website_url)
    query = 'サウナリウム高円寺'
    ServeImage(2, query, website_url)



