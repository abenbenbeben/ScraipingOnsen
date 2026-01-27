import time, pprint, json, sys
sys.path.append('../')
from components.RequestPlacesAPI import *
from components.SpreadSheet import write_multi_spreadsheet


def SearchNearStatiion(lat, long, rownum, sheetnum=0):
    """
    sheetnum: 書き込み先シート番号（0-based）
    """
    result = get_nearby_placeapi(lat, long)
    data_row = [result["distance_text"], result["duration_text"], result["station_name"]]
    data = [data_row]
    write_multi_spreadsheet(f"AH{rownum}:AJ{rownum}", data, sheetnum=sheetnum)
