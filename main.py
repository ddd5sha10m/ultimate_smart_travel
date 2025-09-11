'''
# main.py (v2 - 修正版)
"""
程式主入口。
負責載入設定、協調各模組完成行程規劃與視覺化。
"""
import time
import config
from google_api_service import GoogleApiService
from planner import cluster_places_by_distance, refine_cluster_by_walking, plan_optimal_itinerary
from visualizer import create_itinerary_map

def main():
    start_time = time.time()
    
    # 1. 初始化 (api_service 物件只在這裡建立一次)
    api_service = GoogleApiService(config.API_KEY)

    # 2. 獲取並解析地點資料
    all_places = api_service.get_places_details(config.INPUT_LOCATIONS)
    start_coords = api_service.get_geocode(config.ITINERARY_START_LOCATION)
    end_coords = api_service.get_geocode(config.ITINERARY_END_LOCATION)

    if not all_places or not start_coords or not end_coords:
        print("無法獲取所有必要的地點資訊，程式終止。")
        return

    # 3. 執行行程規劃
    initial_clusters = cluster_places_by_distance(all_places, config.DISTANCE_THRESHOLD_KM)
    
    # [--- 修改點 ---]: 建立一個迴圈來處理 refine_clusters
    final_clusters = []
    print("\n--- 步驟 3: 進行第二階段路徑精煉 ---")
    for i, cluster in enumerate(initial_clusters):
        print(f"  處理群組 {i} ({len(cluster)} 個地點)...")
        # 將 api_service 和設定檔中的秒數傳入
        refined_cluster = refine_cluster_by_walking(cluster, api_service, config.WALKING_TIME_LIMIT_SECONDS)
        if refined_cluster:
            final_clusters.append(refined_cluster)

    # [--- 修改點 ---]: 將 api_service 和其他設定傳入
    optimal_itinerary = plan_optimal_itinerary(
        final_clusters, 
        start_coords, 
        end_coords, 
        api_service, # <--- 傳入 api_service
        config.INTER_CLUSTER_TRAVEL_MODE, 
        config.BRUTE_FORCE_LIMIT
    )

    # 4. 視覺化結果
    start_info = {'name': config.ITINERARY_START_LOCATION, 'coords': start_coords}
    end_info = {'name': config.ITINERARY_END_LOCATION, 'coords': end_coords}
    create_itinerary_map(optimal_itinerary, start_info, end_info, api_service, config.INTER_CLUSTER_TRAVEL_MODE)

    # 5. 輸出總結
    print("\n==========================")
    print("   行程規劃完成！")
    print("==========================")
    
    end_time = time.time()
    print(f"\n總執行時間: {end_time - start_time:.2f} 秒")


if __name__ == '__main__':
    main()
'''
# main.py (v6 - Corrected)
"""
Main entry point for the application.
Validates config settings and coordinates modules to complete the itinerary planning and visualization.
"""
import time
import config
from google_api_service import GoogleApiService
from planner import cluster_places_by_distance, refine_cluster_by_walking, plan_multi_day_itinerary
from visualizer import create_multi_day_map

def main():
    """Main function to run the trip planner."""
    # --- Configuration Validation ---
    print("--- Validating settings from config.py ---")
    valid_modes = ["driving", "walking", "bicycling", "transit"]
    
    try:
        inter_mode = config.INTER_CLUSTER_TRAVEL_MODE.strip().lower()
        if inter_mode not in valid_modes:
            raise ValueError(f"Invalid setting! INTER_CLUSTER_TRAVEL_MODE value '{config.INTER_CLUSTER_TRAVEL_MODE}' is not a valid option.")
        config.INTER_CLUSTER_TRAVEL_MODE = inter_mode
        print(f"  [OK] Inter-cluster travel mode: {inter_mode}")

        intra_mode = config.INTRA_CLUSTER_TRAVEL_MODE.strip().lower()
        if intra_mode not in valid_modes:
            raise ValueError(f"Invalid setting! INTRA_CLUSTER_TRAVEL_MODE value '{config.INTRA_CLUSTER_TRAVEL_MODE}' is not a valid option.")
        config.INTRA_CLUSTER_TRAVEL_MODE = intra_mode
        print(f"  [OK] Intra-cluster travel mode: {intra_mode}")
    except AttributeError as e:
        raise AttributeError(f"Configuration Error! Please ensure the variable exists in config.py. Details: {e}")

    # --- Main Process ---
    start_time = time.time()
    api_service = GoogleApiService(config.API_KEY)

    all_places = api_service.get_places_details(config.INPUT_LOCATIONS)
    start_coords = api_service.get_geocode(config.ITINERARY_START_LOCATION)
    end_coords = api_service.get_geocode(config.ITINERARY_END_LOCATION)

    if not all_places or not start_coords or not end_coords:
        print("Could not retrieve all necessary location information. Exiting program.")
        return

    initial_clusters = cluster_places_by_distance(all_places, config.DISTANCE_THRESHOLD_KM)
    
    final_clusters = []
    print("\n--- Step 3: Refining clusters ---")
    for i, cluster in enumerate(initial_clusters):
        print(f"  Processing cluster {i} with {len(cluster)} locations...")
        refined_cluster = refine_cluster_by_walking(cluster, api_service, config.WALKING_TIME_LIMIT_SECONDS)
        if refined_cluster:
            final_clusters.append(refined_cluster)

    itinerary_by_day, unvisited = plan_multi_day_itinerary(final_clusters, config, api_service)

    start_info = {'name': config.ITINERARY_START_LOCATION, 'coords': start_coords}
    end_info = {'name': config.ITINERARY_END_LOCATION, 'coords': end_coords}
    create_multi_day_map(itinerary_by_day, start_info, end_info, config, api_service)

    # --- Summary Output ---
    print("\n==========================")
    print("   Multi-Day Itinerary Plan Complete!")
    print("==========================")
    for i, day_plan in enumerate(itinerary_by_day):
        print(f"\n--- Day {i+1} ({day_plan[0]['path'][0]['arrival'].strftime('%Y-%m-%d')}) ---")
        for cluster_item in day_plan:
            print(f"  [Cluster {cluster_item['cluster_id']}]")
            for place_info in cluster_item['path']:
                print(f"    - {place_info['arrival'].strftime('%H:%M')} - {place_info['departure'].strftime('%H:%M')}: {place_info['place']['original_name']}")
    
    if unvisited:
        print("\n[Warning] The following locations could not be scheduled due to time or opening hour constraints:")
        for cluster in unvisited:
            for place in cluster:
                print(f"  - {place['original_name']}")
    
    end_time = time.time()
    print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")


if __name__ == '__main__':
    main()