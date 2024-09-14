import requests, json, pprint
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

# 環境変数をロードする
load_dotenv()

def check_firewall():
    api_key = os.getenv("PLACES_API_KEY")
    params = {
        "query": "沼部公園",
        "key":api_key,
        "region" : "jp",
        "language" : "ja",
    }
    url_overview = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    res_overview = requests.get(url_overview, params= params)
    if 'error_message' in res_overview.text:
        print(res_overview.text)
        raise Exception("IPアドレスエラー")



def get_placeapi_data(place_name):
    api_key = os.getenv("PLACES_API_KEY")
    opentime_day_0 = opentime_day_1 = opentime_day_2 = opentime_day_3 = opentime_day_4 = opentime_day_5 = opentime_day_6 = None
    closetime_day_0 = closetime_day_1 = closetime_day_2 = closetime_day_3 = closetime_day_4 = closetime_day_5 = closetime_day_6 = None

    params = {
        "query": place_name,
        "key":api_key,
        "region" : "jp",
        "language" : "ja",
    }
    url_overview = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    res_overview = requests.get(url_overview, params= params)
    if 'error_message' in res_overview.text:
        print(res_overview.text)
        raise Exception("IPアドレスエラー")
    place = json.loads(res_overview.text)

    # 緯度経度を抽出
    lat = place['results'][0]['geometry']['location']['lat']
    lng = place['results'][0]['geometry']['location']['lng']
    place_id = place['results'][0]['place_id']

    url_detail = "https://maps.googleapis.com/maps/api/place/details/json"
    params_detail = {
        "place_id": place_id,
        "key":api_key,
        "region" : "jp",
        "language" : "ja",
    }
    res_detail = requests.get(url_detail, params= params_detail)
    place_detail = json.loads(res_detail.text)

    # 初期値をNoneに設定
    opentime_day_0 = opentime_day_1 = opentime_day_2 = opentime_day_3 = opentime_day_4 = opentime_day_5 = opentime_day_6 = None
    closetime_day_0 = closetime_day_1 = closetime_day_2 = closetime_day_3 = closetime_day_4 = closetime_day_5 = closetime_day_6 = None

    
    if 'result' not in place_detail:
        pprint.pprint(place_detail)
        raise KeyError("place_detail に 'result' キーが見つかりません。")
    # periodsが存在するか確認し、存在する場合は処理を行う
    periods = place_detail['result'].get("opening_hours", {}).get("periods", [])

    for period in periods:
        if 'open' in period:
            if period['open']['day'] == 0:
                opentime_day_0 = period['open']['time']
            elif period['open']['day'] == 1:
                opentime_day_1 = period['open']['time']
            elif period['open']['day'] == 2:
                opentime_day_2 = period['open']['time']
            elif period['open']['day'] == 3:
                opentime_day_3 = period['open']['time']
            elif period['open']['day'] == 4:
                opentime_day_4 = period['open']['time']
            elif period['open']['day'] == 5:
                opentime_day_5 = period['open']['time']
            elif period['open']['day'] == 6:
                opentime_day_6 = period['open']['time']

        if 'close' in period:
            if period['close']['day'] == 0:
                closetime_day_0 = period['close']['time']
            elif period['close']['day'] == 1:
                closetime_day_1 = period['close']['time']
            elif period['close']['day'] == 2:
                closetime_day_2 = period['close']['time']
            elif period['close']['day'] == 3:
                closetime_day_3 = period['close']['time']
            elif period['close']['day'] == 4:
                closetime_day_4 = period['close']['time']
            elif period['close']['day'] == 5:
                closetime_day_5 = period['close']['time']
            elif period['close']['day'] == 6:
                closetime_day_6 = period['close']['time']
    
    # 住所の抽出
    formatted_address = place_detail['result']['formatted_address']
    address_parts = formatted_address.split(' ', 1)  # 最初のスペースで分割
    address = address_parts[1] if len(address_parts) > 1 else formatted_address

    # webサイトURLを取得
    url = place_detail.get('result', {}).get('website')

    #　正式名称
    name = place_detail['result']['name']

    # 県名
    html_code = place_detail['result']['adr_address']
    soup = BeautifulSoup(html_code, 'html.parser')
    prefecture_name = soup.find('span', class_='region').text



    result = {
        "opentime_day_0": opentime_day_0,
        "opentime_day_1": opentime_day_1,
        "opentime_day_2": opentime_day_2,
        "opentime_day_3": opentime_day_3,
        "opentime_day_4": opentime_day_4,
        "opentime_day_5": opentime_day_5,
        "opentime_day_6": opentime_day_6,
        "closetime_day_0": closetime_day_0,
        "closetime_day_1": closetime_day_1,
        "closetime_day_2": closetime_day_2,
        "closetime_day_3": closetime_day_3,
        "closetime_day_4": closetime_day_4,
        "closetime_day_5": closetime_day_5,
        "closetime_day_6": closetime_day_6,
        "lat": lat,
        "lng": lng,
        "address": address,
        "url": url,
        "prefecture_name": prefecture_name,
        "name": name,
    }

    return result

def get_nearby_placeapi(lat,long):
    distance_text = ""
    duration_text = ""

    url = "https://places.googleapis.com/v1/places:searchNearby"
    api_key = os.getenv("PLACES_API_KEY")
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.location"
    }

    payload = {
        "includedTypes": ["train_station"],
        "languageCode": "ja",
        "maxResultCount": 10,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": long
                },
                "radius": 1000.0
            }
        }
    }

    data = None
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if json.loads(response.text) != {}:
        data = json.loads(response.text)
        origin_latitude = data['places'][0]['location']['latitude']
        origin_longitude = data['places'][0]['location']['longitude']
        destination_latitude = lat
        destination_longitude = long

        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            'origins': f"{origin_latitude},{origin_longitude}",
            'destinations': f"{destination_latitude},{destination_longitude}",
            'mode': 'walking',
            'key': api_key
        }

        response_distancematrix = requests.get(url, params=params)
        data_distancematrix = json.loads(response_distancematrix.text)
        distance_text = data_distancematrix['rows'][0]['elements'][0]['distance']['text']
        duration_text = data_distancematrix['rows'][0]['elements'][0]['duration']['text']
        station_name = data['places'][0]['displayName']['text']
    else:
        distance_text = "nostation"
        station_name = ""
    
    
    result = {
        "distance_text": distance_text,
        "duration_text": duration_text,
        "station_name": station_name
    }

    return result



    
if __name__ == "__main__":
    print("Script execution started")
    dataresult = get_placeapi_data("千代乃湯")
    lat = dataresult["lat"]
    long = dataresult["lng"]

    print(lat)
    print(long)

    # get_nearby_placeapi(lat,long)

