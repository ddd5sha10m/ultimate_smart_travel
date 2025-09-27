# app.py (v2 - 完整流程版)
from flask import Flask, render_template, request
from datetime import datetime
import config
from google_api_service import GoogleApiService
from planner import cluster_places_by_distance, refine_cluster_by_walking, plan_optimized_route, plan_multi_day_schedule
from visualizer import create_route_map, create_multi_day_map
from datetime import datetime, time, timedelta

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    # --- DEFINE DEFAULTS FIRST ---
    # This code now runs for BOTH GET and POST requests, so the variables always exist.
    today = datetime.now().date()
    default_start_dt = datetime.combine(today, time(9, 0))
    default_end_dt = datetime.combine(today, time(22, 0))
    # 【修改】將 strftime 的格式改成與 Flatpickr 的 dateFormat 一致
    start_time_value = default_start_dt.strftime("%Y-%m-%d %H:%M")
    end_time_value = default_end_dt.strftime("%Y-%m-%d %H:%M")

    # --- HANDLE FORM SUBMISSION ---
    if request.method == 'POST':
        # This block now only contains logic specific to POST.
        form_data = request.form
        
        # 動態更新 config 物件
        config.INPUT_LOCATIONS = [loc.strip() for loc in form_data.get('locations').splitlines() if loc.strip()]
        config.ITINERARY_START_LOCATION = form_data.get('start_location')
        config.ITINERARY_END_LOCATION = form_data.get('end_location')
        config.PLANNING_MODE = form_data.get('planning_mode')
        config.INTER_CLUSTER_TRAVEL_MODE = form_data.get('inter_mode')
        config.INTRA_CLUSTER_TRAVEL_MODE = form_data.get('intra_mode')
        
        if config.PLANNING_MODE == 'time_aware':
            config.TRIP_START_TIME = datetime.fromisoformat(form_data.get('start_time'))
            config.TRIP_END_TIME = datetime.fromisoformat(form_data.get('end_time'))
            config.DEFAULT_STAY_DURATION_MINS = int(form_data.get('stay_duration'))

        # --- 執行完整的後端規劃流程 ---
        api_service = GoogleApiService(config.API_KEY)
        
        all_places = api_service.get_places_details(config.INPUT_LOCATIONS)
        if not all_places:
            return "錯誤：無法獲取任何地點資訊，請返回上一頁檢查輸入。"

        initial_clusters = cluster_places_by_distance(all_places, config.DISTANCE_THRESHOLD_KM)
        print("\n--- 偵錯：初始分群結果 ---")
        for i, cluster in enumerate(initial_clusters):
            print(f"初始群組 {i}: {[p['name'] for p in cluster]}")
        print("--------------------------\n")


        final_clusters = []
        print("\n--- 步驟 3: 進行第二階段路徑精煉 ---")
        for i, cluster in enumerate(initial_clusters):
            print(f"  處理群組 {i} ({len(cluster)} 個地點)...")
        # MODIFIED: Always keep the cluster, just log warnings
            if len(cluster) > 0:
                final_clusters.append(cluster)
                print(f"    ✓ 保留群組 {i} 的所有 {len(cluster)} 個地點")

        # --- 根據模式，執行不同規劃並產生結果 ---
        start_info = {'name': config.ITINERARY_START_LOCATION, 'coords': api_service.get_geocode(config.ITINERARY_START_LOCATION)}
        end_info = {'name': config.ITINERARY_END_LOCATION, 'coords': api_service.get_geocode(config.ITINERARY_END_LOCATION)}
        itinerary_data, unvisited_locations = plan_multi_day_schedule(final_clusters, config, api_service)
        if unvisited_locations:
            print("\n--- 偵錯：最終被規劃演算法捨棄的地點 ---")
            print([place['name'] for cluster in unvisited_locations for place in cluster])
        print("--------------------------------------\n")
        map_html = ""

        if config.PLANNING_MODE == 'time_aware':
            start_time_str = form_data.get('start_time')
            end_time_str = form_data.get('end_time')
            config.TRIP_START_TIME = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
            config.TRIP_END_TIME = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M')
            config.DEFAULT_STAY_DURATION_MINS = int(form_data.get('stay_duration'))
            itinerary_data, unvisited_locations = plan_multi_day_schedule(final_clusters, config, api_service)
            map_html = create_multi_day_map(itinerary_data, start_info, end_info, config, api_service)
        
        elif config.PLANNING_MODE == 'location_only':
            itinerary_data, unvisited_locations = plan_optimized_route(final_clusters, config, api_service)
            map_html = create_route_map(itinerary_data, start_info, end_info, config, api_service)

        # --- 將所有結果渲染到 results.html ---
        return render_template(
            'results.html',
            itinerary_data=itinerary_data,
            unvisited=unvisited_locations,
            map_html=map_html,
            planning_mode=config.PLANNING_MODE
        )

    # --- RENDER THE HOMEPAGE FOR A GET REQUEST ---
    # This code now correctly has access to the variables defined at the top.
    return render_template(
        'index.html',
        default_start_time=start_time_value, 
        default_end_time=end_time_value
    )

if __name__ == '__main__':
    app.run(debug=True,port=5001)