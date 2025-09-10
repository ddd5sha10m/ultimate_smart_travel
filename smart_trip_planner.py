import googlemaps
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from haversine import haversine, Unit
import os
import polyline
from dotenv import load_dotenv
from itertools import permutations # 用於暴力窮舉
import time # 用於計時

load_dotenv()

# --- 參數設定 ---
DISTANCE_THRESHOLD_KM = 0.8 
WALKING_TIME_LIMIT_SECONDS = 10 * 60
# [--- 新增參數 ---]
# 暴力窮舉法的上限，避免因地點過多導致計算時間過長
BRUTE_FORCE_LIMIT = 9 
#[--- 全新修改部分 ---]
# 設定群組間的交通方式
# 可用選項: "driving" (開車), "transit" (大眾運輸), "bicycling" (騎腳踏車), "walking" (走路)
INTER_CLUSTER_TRAVEL_MODE = "driving" # <--- 你可以在這裡切換！
ITINERARY_START_LOCATION = "smartments Wien Hauptbahnhof" # <--- 在這裡輸入你的起點
ITINERARY_END_LOCATION = "smartments Wien Hauptbahnhof"   # <--- 在這裡輸入你的終點
# --- 初始化 Google Maps Client ---
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    raise ValueError("請設定 GOOGLE_MAPS_API_KEY 環境變數")
gmaps = googlemaps.Client(key=API_KEY)


# (步驟 1 & 2 的函式 get_places_details 和 cluster_places_by_distance 維持不變)
# (此處為求簡潔省略，請使用前次版本中的程式碼)
### 步驟 1: 獲取地點的詳細資料 ###
def get_places_details(place_names):
    # ... (與前次版本相同)
    places_data = []
    print("--- 步驟 1: 開始獲取地點資料 ---")
    for name in place_names:
        try:
            find_place_result = gmaps.find_place(
                input=name,
                input_type='textquery',
                fields=['place_id']
            )
            if find_place_result['status'] == 'OK' and find_place_result['candidates']:
                place_id = find_place_result['candidates'][0]['place_id']
                place_details = gmaps.place(place_id=place_id, fields=[
                    'name', 'formatted_address', 'geometry', 'rating', 'place_id'
                ])['result']
                
                location = place_details['geometry']['location']
                data = {
                    'name': place_details.get('name', 'N/A'),
                    'address': place_details.get('formatted_address', 'N/A'),
                    'lat': location['lat'],
                    'lng': location['lng'],
                    'rating': place_details.get('rating', 'N/A'),
                    'place_id': place_details.get('place_id'),
                    'coords': (location['lat'], location['lng']) # 新增座標元組方便使用
                }
                places_data.append(data)
                print(f"  [成功] 獲取 '{name}'")
            else:
                print(f"  [警告] 找不到地點 '{name}'")
        except Exception as e:
            print(f"  [錯誤] 獲取 '{name}' 時發生錯誤: {e}")
    return places_data


### 步驟 2: 凝聚式層次分群 ###
def cluster_places_by_distance(places):
    # ... (與前次版本相同)
    print("\n--- 步驟 2: 進行第一階段空間分群 ---")
    if len(places) < 2:
        print("  地點數量不足，無法分群。")
        return {0: places} if places else {}

    coords = np.array([p['coords'] for p in places])
    n_points = len(places)
    distance_matrix = np.zeros((n_points, n_points))
    for i in range(n_points):
        for j in range(i, n_points):
            dist = haversine(coords[i], coords[j], unit=Unit.KILOMETERS)
            distance_matrix[i, j] = distance_matrix[j, i] = dist

    clustering = AgglomerativeClustering( 
        n_clusters=None,
        metric='precomputed', # 使用預先計算的距離矩陣
        linkage='average',
        distance_threshold=DISTANCE_THRESHOLD_KM
    )
    labels = clustering.fit_predict(distance_matrix)
    
    grouped_places = {}
    for i, place in enumerate(places):
        label = labels[i]
        if label not in grouped_places:
            grouped_places[label] = []
        grouped_places[label].append(place)
    
    print(f"  分群完成，共形成 {len(grouped_places)} 個群組。")
    # 將字典轉換為列表，方便後續排序
    return list(grouped_places.values())


# (步驟 3 refine_cluster_by_walking 維持不變)
# (此處為求簡潔省略，請使用前次版本中的程式碼)
def refine_cluster_by_walking(cluster_places):
    # ... (與前次版本相同)
    num_places = len(cluster_places)
    
    if num_places <= 2:
        return cluster_places
        
    try:
        origin = f"place_id:{cluster_places[0]['place_id']}" # 起點
        destination = f"place_id:{cluster_places[-1]['place_id']}" # 終點
        waypoints = [f"place_id:{p['place_id']}" for p in cluster_places[1:-1]] #取中繼點
        
        directions_result = gmaps.directions( # 使用 Directions API 規劃路徑
            origin=origin,
            destination=destination,
            waypoints=waypoints,
            mode="walking",
            optimize_waypoints=True
        )
        
        if not directions_result:
            print("    [警告] 無法規劃路徑，跳過此群組的精煉步驟。")
            return cluster_places

        path_polyline = directions_result[0]['overview_polyline']['points'] 
        path_coords = polyline.decode(path_polyline)
        
        if not path_coords:
            return cluster_places

        anchor_point = np.mean(path_coords, axis=0) 
        anchor_lat, anchor_lng = anchor_point[0], anchor_point[1] # 取路徑中點作為參考點
        
        destination_place_ids = [f"place_id:{p['place_id']}" for p in cluster_places]
        
        matrix_result = gmaps.distance_matrix( # 使用 Distance Matrix API 計算步行時間
            origins=[(anchor_lat, anchor_lng)],
            destinations=destination_place_ids,
            mode="walking"
        )
        
        refined_places = []
        if matrix_result['status'] == 'OK' and matrix_result['rows'][0]['elements']: 
            elements = matrix_result['rows'][0]['elements'] # 取得從參考點到各地點的距離和時間
            for i, place in enumerate(cluster_places): # 檢查每個地點的步行時間
                if elements[i]['status'] == 'OK':
                    duration_seconds = elements[i]['duration']['value'] # 取得步行時間（秒）
                    if duration_seconds <= WALKING_TIME_LIMIT_SECONDS: # 若在可接受範圍內，則保留
                        refined_places.append(place)
        
        return refined_places

    except Exception as e:
        print(f"    [錯誤] 在精煉群組時發生錯誤: {e}")
        return cluster_places


# [--- 全新步驟 4: 規劃最佳行程路徑 ---]
# [--- 函式已更新 ---]
def plan_optimal_itinerary(clusters, start_location, end_location, travel_mode="driving"):
    """
    規劃拜訪所有群組及群組內地點的最佳順序。
    新增 start_location 和 end_location 參數。
    """
    print("\n--- 步驟 4: 開始規劃最佳行程路徑 ---")
    
    valid_modes = ["driving", "transit", "bicycling", "walking"]
    if travel_mode not in valid_modes:
        raise ValueError(f"無效的交通方式: '{travel_mode}'。請從 {valid_modes} 選擇。")
    print(f"  將使用 '{travel_mode}' 模式規劃群組間交通。")
    print(f"  行程起點: {start_location}, 終點: {end_location}")

    if not clusters:
        print("  沒有群組可供規劃。")
        return

    # --- 4.1 優化群組間的拜訪順序 (Inter-Cluster TSP with fixed endpoints) ---
    print("  4.1 正在計算群組間的最佳拜訪順序...")
    
    cluster_reps = {
        i: {"name": f"群組 {i}", "coords": np.mean([p['coords'] for p in cluster], axis=0)}
        for i, cluster in enumerate(clusters)
    }

    # [--- 修改部分 ---]
    # 將起點、終點和所有群組中心點放在一起，一次性取得座標和計算距離
    try:
        start_coords = gmaps.geocode(start_location)[0]['geometry']['location']
        end_coords = gmaps.geocode(end_location)[0]['geometry']['location']
    except IndexError:
        raise ValueError("無法解析起點或終點的地址，請確認地址名稱是否正確。")

    all_points_for_inter_tsp = {
        "start": {"name": start_location, "coords": (start_coords['lat'], start_coords['lng'])},
        "end": {"name": end_location, "coords": (end_coords['lat'], end_coords['lng'])}
    }
    for i, rep in cluster_reps.items():
        all_points_for_inter_tsp[i] = rep

    point_keys = list(all_points_for_inter_tsp.keys())
    point_coords = [all_points_for_inter_tsp[key]['coords'] for key in point_keys]

    api_params = {'origins': point_coords, 'destinations': point_coords, 'mode': travel_mode}
    if travel_mode == 'transit':
        from datetime import datetime, timedelta
        # 根據現在時間，規劃1小時後的行程
        departure_time = datetime.now() + timedelta(hours=1)
        api_params['departure_time'] = departure_time
        print(f"  大眾運輸模式：已將出發時間設為 {departure_time.strftime('%Y-%m-%d %H:%M')} 以取得預估時間。")

    matrix_result = gmaps.distance_matrix(**api_params)
    
    travel_times = {}
    for i, row in enumerate(matrix_result['rows']):
        for j, element in enumerate(row['elements']):
            from_key = point_keys[i]
            to_key = point_keys[j]
            travel_times[(from_key, to_key)] = element['duration']['value'] if element['status'] == 'OK' else float('inf')
    
    cluster_indices = list(cluster_reps.keys())
    if len(cluster_indices) > BRUTE_FORCE_LIMIT:
        print(f"  [警告] 群組數量 ({len(cluster_indices)}) 過多，跳過群組排序以節省時間。")
        ordered_cluster_indices = cluster_indices
    else:
        best_order = None
        min_duration = float('inf')
        
        # [--- 核心邏輯修改 ---]
        # 窮舉所有群組的排列組合，找出 (起點 -> ...群組... -> 終點) 的最短路徑
        for p in permutations(cluster_indices):
            # 計算 起點 -> 第一個群組 的時間
            current_duration = travel_times[('start', p[0])]
            # 計算 群組之間 的時間
            for i in range(len(p) - 1):
                current_duration += travel_times[(p[i], p[i+1])]
            # 計算 最後一個群組 -> 終點 的時間
            current_duration += travel_times[(p[-1], 'end')]
            
            if current_duration < min_duration:
                min_duration = current_duration
                best_order = p
        ordered_cluster_indices = list(best_order) if best_order else cluster_indices
    
    print(f"  最佳群組拜訪順序: {['群組 ' + str(i) for i in ordered_cluster_indices]}")

    # --- 4.2 優化各群組內部的拜訪路徑 (Intra-Cluster TSP) ---
    print("\n  4.2 正在計算各群組內部的最佳路徑...")
    final_itinerary = []
    last_location_coords = all_points_for_inter_tsp['start']['coords']

    path_for_intra_tsp = [None] + ordered_cluster_indices + [None] 

    for i in range(1, len(path_for_intra_tsp) - 1):
        current_cluster_idx = path_for_intra_tsp[i]
        next_cluster_idx = path_for_intra_tsp[i+1]
        
        current_cluster = clusters[current_cluster_idx]
        
        entry_point = min(current_cluster, key=lambda p: haversine(last_location_coords, p['coords']))
        
        # [--- 核心邏輯修改 ---]
        # 決定離開點
        if next_cluster_idx is not None:
            # 如果後面還有群組，離開點是離下個群組中心最近的點
            next_cluster_center = cluster_reps[next_cluster_idx]['coords']
            exit_point = min(current_cluster, key=lambda p: haversine(p['coords'], next_cluster_center))
        else:
            # 如果是最後一個群組，離開點是離「行程終點」最近的點
            end_point_coords = all_points_for_inter_tsp['end']['coords']
            exit_point = min(current_cluster, key=lambda p: haversine(p['coords'], end_point_coords))

        # (此函式剩餘部分不變，此處為求簡潔省略，請沿用前一版的程式碼)
        waypoints = [p for p in current_cluster if p != entry_point and p != exit_point]
        if len(current_cluster) > BRUTE_FORCE_LIMIT:
            # ...
            directions_result = gmaps.directions(
                origin=entry_point['coords'],
                destination=exit_point['coords'],
                waypoints=[wp['coords'] for wp in waypoints],
                mode="walking",
                optimize_waypoints=True
            )
            waypoint_order = directions_result[0]['waypoint_order']
            optimized_waypoints = [waypoints[i] for i in waypoint_order]
        else:
            best_waypoint_order = []
            min_path_dist = float('inf')
            if not waypoints:
                best_waypoint_order = []
            else:
                 for p in permutations(waypoints): # 窮舉所有中繼點的排列組合
                    current_dist = haversine(entry_point['coords'], p[0]['coords'])
                    for j in range(len(p) - 1):
                        current_dist += haversine(p[j]['coords'], p[j+1]['coords'])
                    current_dist += haversine(p[-1]['coords'], exit_point['coords'])
                    if current_dist < min_path_dist:
                        min_path_dist = current_dist
                        best_waypoint_order = p
            optimized_waypoints = list(best_waypoint_order)
        cluster_path = [entry_point] + optimized_waypoints
        if entry_point != exit_point:
            cluster_path.append(exit_point)
        final_itinerary.append({ "cluster_id": current_cluster_idx, "path": cluster_path })
        last_location_coords = cluster_path[-1]['coords']
        print(f"  完成群組 {current_cluster_idx} 的內部路徑規劃。")

    return final_itinerary


# --- 主程式執行區塊 ---
if __name__ == '__main__':
    start_time = time.time()
    input_locations = [
        "安可鐘", "維也納聖彼得教堂", "德梅爾咖啡店", "聖斯德望主教座堂", "奧地利國家圖書館",
        "霍夫堡", "奧地利國會大廈", "Haus der Musik", 
        "維也納博物館", "卡爾教堂", 
        "美景宮", "Kunsthistorisches Museum Wien", "Naturhistorisches Museum Wien",
        "維也納市政廳",
        "百水公寓"
    ]
    
    all_places = get_places_details(input_locations)
    initial_clusters_list = cluster_places_by_distance(all_places)
    
    print("\n--- 步驟 3: 進行第二階段路徑精煉 ---")
    final_clusters = []
    for i, cluster in enumerate(initial_clusters_list):
        cluster_names = [p['name'] for p in cluster]
        print(f"  處理群組 {i} ({len(cluster)} 個地點): {', '.join(cluster_names)}")
        refined_cluster = refine_cluster_by_walking(cluster)
        if refined_cluster:
            final_clusters.append(refined_cluster)
            
    # [--- 修改部分 ---]
    # 將頂部設定的交通方式傳入函式
    optimal_itinerary = plan_optimal_itinerary(
        final_clusters,
        start_location=ITINERARY_START_LOCATION,
        end_location=ITINERARY_END_LOCATION,
        travel_mode=INTER_CLUSTER_TRAVEL_MODE
    )
    
    # (後續顯示結果的程式碼不變)
    print("\n==========================")
    print("   最佳化行程規劃結果")
    print("==========================")
    if not optimal_itinerary:
        print("未能產生任何行程。")
    else:
        total_places_count = 0
        print(f"行程起點: {ITINERARY_START_LOCATION}")
        for item in optimal_itinerary:
            print(f"\n--- 第 {item['cluster_id']} 號群組行程 ---")
            for place in item['path']:
                print(f"  -> {place['name']}")
                total_places_count += 1
        print(f"\n行程終點: {ITINERARY_END_LOCATION}")
        print(f"\n總計規劃了 {len(optimal_itinerary)} 個區域，{total_places_count} 個地點。")

    end_time = time.time()
    print(f"\n總執行時間: {end_time - start_time:.2f} 秒")
# (後續顯示結果的程式碼不變)