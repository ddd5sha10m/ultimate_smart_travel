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