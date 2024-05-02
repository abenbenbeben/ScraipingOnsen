import time, pprint, json, sys
sys.path.append('../')
from components.RequestPlacesAPI import *
from components.SpreadSheet import *

def SearchNearStatiion(lat,long,rownum):
    result = get_nearby_placeapi(lat,long)
    write_spreadsheet(f"AH{rownum}",result["distance_text"])
    write_spreadsheet(f"AI{rownum}",result["duration_text"])
    write_spreadsheet(f"AJ{rownum}",result["station_name"])


