import time, pprint, json, sys
sys.path.append('../')
from components.RequestPlacesAPI import *
from components.SpreadSheet import *

def SearchNearStatiion(lat,long,rownum):
    result = get_nearby_placeapi(lat,long)
    data_row = [result["distance_text"],result["duration_text"],result["station_name"]]
    data = [data_row]
    write_multi_spreadsheet(f"AH{rownum}:AJ{rownum}",data)


