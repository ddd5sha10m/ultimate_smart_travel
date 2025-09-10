# google_api_service.py (v2 - 修正版)
"""
封裝所有與 Google Maps API 的互動。
"""
import googlemaps
from datetime import datetime, timedelta

class GoogleApiService:
    def __init__(self, api_key):
        self.gmaps = googlemaps.Client(key=api_key)

    def get_places_details(self, place_names):
        places_data = []
        print("--- 步驟 1: 開始獲取地點資料 ---")
        for name in place_names: # 'name' 就是使用者輸入的原始名稱
            try:
                find_place_result = self.gmaps.find_place(
                    input=name,
                    input_type='textquery',
                    fields=['place_id']
                )
                if find_place_result['status'] == 'OK' and find_place_result['candidates']:
                    place_id = find_place_result['candidates'][0]['place_id']
                    place_details = self.gmaps.place(place_id=place_id, fields=[
                        'name', 'formatted_address', 'geometry', 'rating', 'place_id', 'opening_hours'
                    ])['result']
                    
                    location = place_details['geometry']['location']
                    data = {
                        # [--- 核心修改 ---]
                        'original_name': name, # 將使用者輸入的原始名稱儲存起來
                        'name': place_details.get('name', 'N/A'), # API 回傳的官方名稱
                        'address': place_details.get('formatted_address', 'N/A'),
                        'lat': location['lat'],
                        'lng': location['lng'],
                        'rating': place_details.get('rating', 'N/A'),
                        'place_id': place_details.get('place_id'),
                        'coords': (location['lat'], location['lng']),
                        'opening_hours': place_details.get('opening_hours', {}).get('weekday_text', ['N/A'])
                    }
                    places_data.append(data)
                    print(f"  [成功] 獲取 '{name}'")
                else:
                    print(f"  [警告] 找不到地點 '{name}'")
            except Exception as e:
                print(f"  [錯誤] 獲取 '{name}' 時發生錯誤: {e}")
        return places_data

    # (此檔案中其餘的函式 get_geocode, get_distance_matrix, get_directions 維持不變)
    def get_geocode(self, location_name):
        try:
            geocode_result = self.gmaps.geocode(location_name)
            if geocode_result:
                loc = geocode_result[0]['geometry']['location']
                return (loc['lat'], loc['lng'])
        except Exception as e:
            print(f"解析 '{location_name}' 座標時出錯: {e}")
            return None
        raise ValueError(f"無法解析地址: {location_name}")

    def get_distance_matrix(self, coords_list, travel_mode):
        api_params = {'origins': coords_list, 'destinations': coords_list, 'mode': travel_mode}
        if travel_mode == 'transit':
            departure_time = datetime.now() + timedelta(hours=2)
            api_params['departure_time'] = departure_time
        
        return self.gmaps.distance_matrix(**api_params)

    def get_directions(self, origin_coords, dest_coords, waypoints_coords=None, mode="driving"):
        if waypoints_coords:
            # optimize_waypoints 參數只在 waypoints 存在時才有意義
            return self.gmaps.directions(origin_coords, dest_coords, waypoints=waypoints_coords, mode=mode, optimize_waypoints=True)
        else:
            return self.gmaps.directions(origin_coords, dest_coords, mode=mode)