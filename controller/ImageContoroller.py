import time, pprint, json, sys
sys.path.append('../')
from components.ImageAnalysis import run_checkobject
from components.RetrieveImage import search_photos
from components.SpreadSheet import write_spreadsheet

def ServeImage(rownum, query, website_url):
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






