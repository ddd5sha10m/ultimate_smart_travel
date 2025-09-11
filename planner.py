'''
# planner.py (v3 - 修正版)
"""
包含所有行程規劃、分群、排序的核心演算法。
所有需要 API 的函式都接收 api_service 物件。
"""
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from haversine import haversine, Unit
from itertools import permutations
import polyline

# 這個函式不需要 API，所以不用改
def cluster_places_by_distance(places, threshold_km):
    print("\n--- 步驟 2: 進行第一階段空間分群 ---")
    if len(places) < 2:
        return []
    coords = np.array([p['coords'] for p in places])
    n_points = len(places)
    distance_matrix = np.zeros((n_points, n_points))
    for i in range(n_points):
        for j in range(i, n_points):
            dist = haversine(coords[i], coords[j], unit=Unit.KILOMETERS)
            distance_matrix[i, j] = distance_matrix[j, i] = dist
    clustering = AgglomerativeClustering(
        n_clusters=None, metric='precomputed', linkage='average', distance_threshold=threshold_km
    )
    labels = clustering.fit_predict(distance_matrix)
    grouped_places = {}
    for i, place in enumerate(places):
        label = labels[i]
        if label not in grouped_places: grouped_places[label] = []
        grouped_places[label].append(place)
    print(f"  分群完成，共形成 {len(grouped_places)} 個群組。")
    return list(grouped_places.values())

# [--- 修改點 ---]: 函式定義新增 api_service 參數
def refine_cluster_by_walking(cluster_places, api_service, time_limit_seconds):
    num_places = len(cluster_places)
    if num_places <= 2:
        return cluster_places
    try:
        origin = f"place_id:{cluster_places[0]['place_id']}"
        destination = f"place_id:{cluster_places[-1]['place_id']}"
        waypoints = [f"place_id:{p['place_id']}" for p in cluster_places[1:-1]]
        
        # [--- 修改點 ---]: 透過 api_service 呼叫 directions API
        directions_result = api_service.gmaps.directions(
            origin=origin, destination=destination, waypoints=waypoints,
            mode="walking", optimize_waypoints=True
        )
        if not directions_result:
            return cluster_places

        path_coords = polyline.decode(directions_result[0]['overview_polyline']['points'])
        if not path_coords:
            return cluster_places

        anchor_point = np.mean(path_coords, axis=0)
        anchor_lat, anchor_lng = anchor_point[0], anchor_point[1]
        
        destination_place_ids = [f"place_id:{p['place_id']}" for p in cluster_places]
        
        # [--- 修改點 ---]: 透過 api_service 呼叫 distance_matrix API
        matrix_result = api_service.gmaps.distance_matrix(
            origins=[(anchor_lat, anchor_lng)],
            destinations=destination_place_ids,
            mode="walking"
        )
        
        refined_places = []
        if matrix_result['status'] == 'OK' and matrix_result['rows'][0]['elements']:
            elements = matrix_result['rows'][0]['elements']
            for i, place in enumerate(cluster_places):
                if elements[i]['status'] == 'OK':
                    duration_seconds = elements[i]['duration']['value']
                    if duration_seconds <= time_limit_seconds:
                        refined_places.append(place)
        return refined_places
    except Exception as e:
        print(f"    [錯誤] 在精煉群組時發生錯誤: {e}")
        return cluster_places

# [--- 修改點 ---]: 函式定義新增 api_service 參數
def plan_optimal_itinerary(clusters, start_coords, end_coords, api_service, travel_mode, limit):
    print("\n--- 步驟 4: 開始規劃最佳行程路徑 ---")
    if not clusters: return []
    
    print(f"  將使用 '{travel_mode}' 模式規劃群組間交通。")
    
    cluster_reps = {
        i: {"name": f"群組 {i}", "coords": np.mean([p['coords'] for p in cluster], axis=0)}
        for i, cluster in enumerate(clusters)
    }

    all_points_for_inter_tsp = {
        "start": {"coords": start_coords}, "end": {"coords": end_coords}
    }
    for i, rep in cluster_reps.items(): all_points_for_inter_tsp[i] = rep

    point_keys = list(all_points_for_inter_tsp.keys())
    point_coords = [all_points_for_inter_tsp[key]['coords'] for key in point_keys]

    # [--- 修改點 ---]: 透過 api_service 呼叫 distance_matrix
    matrix_result = api_service.get_distance_matrix(point_coords, travel_mode)
    
    travel_times = {}
    for i, row in enumerate(matrix_result['rows']):
        for j, element in enumerate(row['elements']):
            from_key, to_key = point_keys[i], point_keys[j]
            travel_times[(from_key, to_key)] = element['duration']['value'] if element['status'] == 'OK' else float('inf')
    
    cluster_indices = list(cluster_reps.keys())
    if len(cluster_indices) > limit:
        ordered_cluster_indices = cluster_indices
    else:
        best_order, min_duration = None, float('inf')
        for p in permutations(cluster_indices):
            current_duration = travel_times[('start', p[0])]
            for i in range(len(p) - 1): current_duration += travel_times[(p[i], p[i+1])]
            current_duration += travel_times[(p[-1], 'end')]
            if current_duration < min_duration:
                min_duration, best_order = current_duration, p
        ordered_cluster_indices = list(best_order) if best_order else cluster_indices
    
    print(f"  最佳群組拜訪順序: {['群組 ' + str(i) for i in ordered_cluster_indices]}")

    print("\n  4.2 正在計算各群組內部的最佳路徑...")
    final_itinerary, last_location_coords = [], start_coords
    path_for_intra_tsp = [None] + ordered_cluster_indices + [None] 

    for i in range(1, len(path_for_intra_tsp) - 1):
        current_cluster_idx, next_cluster_idx = path_for_intra_tsp[i], path_for_intra_tsp[i+1]
        current_cluster = clusters[current_cluster_idx]
        
        entry_point = min(current_cluster, key=lambda p: haversine(last_location_coords, p['coords']))
        
        if next_cluster_idx is not None:
            next_cluster_center = cluster_reps[next_cluster_idx]['coords']
            exit_point = min(current_cluster, key=lambda p: haversine(p['coords'], next_cluster_center))
        else:
            exit_point = min(current_cluster, key=lambda p: haversine(p['coords'], end_coords))

        waypoints = [p for p in current_cluster if p != entry_point and p != exit_point]
        if len(current_cluster) > limit:
            directions = api_service.get_directions(
                entry_point['coords'], exit_point['coords'], 
                [wp['coords'] for wp in waypoints], "walking"
            )
            waypoint_order = directions[0]['waypoint_order']
            optimized_waypoints = [waypoints[i] for i in waypoint_order]
        else:
            best_waypoint_order, min_path_dist = [], float('inf')
            if not waypoints:
                best_waypoint_order = []
            else:
                 for p in permutations(waypoints):
                    current_dist = haversine(entry_point['coords'], p[0]['coords'])
                    for j in range(len(p) - 1): current_dist += haversine(p[j]['coords'], p[j+1]['coords'])
                    current_dist += haversine(p[-1]['coords'], exit_point['coords'])
                    if current_dist < min_path_dist:
                        min_path_dist, best_waypoint_order = current_dist, p
            optimized_waypoints = list(best_waypoint_order)
        
        cluster_path = [entry_point] + optimized_waypoints
        if entry_point != exit_point: cluster_path.append(exit_point)
            
        final_itinerary.append({ "cluster_id": current_cluster_idx, "path": cluster_path })
        last_location_coords = cluster_path[-1]['coords']
        print(f"  完成群組 {current_cluster_idx} 的內部路徑規劃。")

    return final_itinerary
'''
# planner.py (v5 - Corrected)
"""
Contains all core algorithms for itinerary planning, clustering, and sorting.
All functions requiring API access now receive the api_service object.
Restored the refine_cluster_by_walking function.
"""
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from haversine import haversine, Unit
from itertools import permutations
import polyline
from datetime import timedelta

def cluster_places_by_distance(places, threshold_km):
    """Clusters places based on geographical distance."""
    print("\n--- Step 2: Performing initial spatial clustering ---")
    if len(places) < 2:
        return []

    coords = np.array([p['coords'] for p in places])
    n_points = len(places)
    distance_matrix = np.zeros((n_points, n_points))
    for i in range(n_points):
        for j in range(i, n_points):
            dist = haversine(coords[i], coords[j], unit=Unit.KILOMETERS)
            distance_matrix[i, j] = distance_matrix[j, i] = dist

    clustering = AgglomerativeClustering(
        n_clusters=None, metric='precomputed', linkage='average', distance_threshold=threshold_km
    )
    labels = clustering.fit_predict(distance_matrix)
    
    grouped_places = {}
    for i, place in enumerate(places):
        label = labels[i]
        if label not in grouped_places:
            grouped_places[label] = []
        grouped_places[label].append(place)
    
    print(f"  Clustering complete, formed {len(grouped_places)} groups.")
    return list(grouped_places.values())

def refine_cluster_by_walking(cluster_places, api_service, time_limit_seconds):
    """Refines a single cluster based on a 15-minute walking radius from its path's anchor point."""
    num_places = len(cluster_places)
    if num_places <= 2:
        return cluster_places
    try:
        origin = f"place_id:{cluster_places[0]['place_id']}"
        destination = f"place_id:{cluster_places[-1]['place_id']}"
        waypoints = [f"place_id:{p['place_id']}" for p in cluster_places[1:-1]]
        
        directions_result = api_service.gmaps.directions(
            origin=origin, destination=destination, waypoints=waypoints,
            mode="walking", optimize_waypoints=True
        )
        if not directions_result:
            return cluster_places

        path_coords = polyline.decode(directions_result[0]['overview_polyline']['points'])
        if not path_coords:
            return cluster_places

        anchor_point = np.mean(path_coords, axis=0)
        
        destination_place_ids = [f"place_id:{p['place_id']}" for p in cluster_places]
        
        matrix_result = api_service.gmaps.distance_matrix(
            origins=[(anchor_point[0], anchor_point[1])],
            destinations=destination_place_ids,
            mode="walking"
        )
        
        refined_places = []
        if matrix_result['status'] == 'OK' and matrix_result['rows'][0]['elements']:
            elements = matrix_result['rows'][0]['elements']
            for i, place in enumerate(cluster_places):
                if elements[i]['status'] == 'OK':
                    duration_seconds = elements[i]['duration']['value']
                    if duration_seconds <= time_limit_seconds:
                        refined_places.append(place)
        return refined_places
    except Exception as e:
        print(f"    [Error] An error occurred while refining the cluster: {e}")
        return cluster_places

def plan_multi_day_itinerary(clusters, config, api_service):
    """Re-architected planner that simulates the trip chronologically to create a multi-day schedule."""
    print("\n--- Step 4: Planning the multi-day itinerary schedule ---")
    if not clusters:
        return [], []
    
    # This section for pre-calculating the optimal cluster order can be added back later for further optimization.
    # For now, we process clusters in the order they are given to focus on time-based scheduling.
    ordered_cluster_indices = list(range(len(clusters)))
    
    itinerary_by_day = []
    unvisited_clusters = ordered_cluster_indices[:]
    current_time = config.TRIP_START_TIME
    
    # Use the start location as the very first "last location"
    last_location_coords = api_service.get_geocode(config.ITINERARY_START_LOCATION)

    while current_time < config.TRIP_END_TIME and unvisited_clusters:
        day_plan = []
        day_start_time = current_time.replace(hour=config.DAY_START_HOUR, minute=0, second=0)
        day_end_time = current_time.replace(hour=config.DAY_END_HOUR, minute=0, second=0)
        current_time = max(current_time, day_start_time)

        clusters_to_try_today = unvisited_clusters[:]
        for cluster_idx in clusters_to_try_today:
            cluster = clusters[cluster_idx]
            
            entry_point = min(cluster, key=lambda p: haversine(last_location_coords, p['coords']))
            travel_matrix = api_service.get_distance_matrix(
                [last_location_coords], [entry_point['coords']], config.INTER_CLUSTER_TRAVEL_MODE, current_time
            )
            
            travel_duration_secs = travel_matrix['rows'][0]['elements'][0].get('duration', {}).get('value', 0)
            arrival_time = current_time + timedelta(seconds=travel_duration_secs)

            # This section for pre-calculating the internal path can be added back for further optimization
            internal_path = cluster

            temp_time = arrival_time
            cluster_is_visitable = True
            projected_path_with_time = []
            
            for i, place in enumerate(internal_path):
                if i > 0:
                    internal_travel_matrix = api_service.get_distance_matrix(
                        [internal_path[i-1]['coords']], [place['coords']], config.INTRA_CLUSTER_TRAVEL_MODE, temp_time
                    )
                    internal_travel_secs = internal_travel_matrix['rows'][0]['elements'][0].get('duration', {}).get('value', 0)
                    temp_time += timedelta(seconds=internal_travel_secs)
                
                if temp_time >= day_end_time or not api_service.is_open_at(place, temp_time):
                    cluster_is_visitable = False
                    break
                
                departure_time = temp_time + timedelta(minutes=config.DEFAULT_STAY_DURATION_MINS)
                projected_path_with_time.append({"place": place, "arrival": temp_time, "departure": departure_time})
                temp_time = departure_time
            
            if cluster_is_visitable and temp_time < day_end_time:
                day_plan.append({
                    "cluster_id": cluster_idx,
                    "path": projected_path_with_time
                })
                current_time = temp_time
                last_location_coords = projected_path_with_time[-1]['place']['coords']
                unvisited_clusters.remove(cluster_idx)
        
        if day_plan:
            itinerary_by_day.append(day_plan)
        
        current_time = (current_time + timedelta(days=1)).replace(hour=0, minute=0, second=0)

    return itinerary_by_day, [clusters[i] for i in unvisited_clusters]