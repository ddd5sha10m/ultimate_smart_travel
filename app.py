# app.py (v2 - 完整流程版)
from flask import Flask, render_template, request
from datetime import datetime
import config
from google_api_service import GoogleApiService
from planner import cluster_places_by_distance, refine_cluster_by_walking, plan_optimized_route, plan_multi_day_schedule
from visualizer import create_route_map, create_multi_day_map

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # --- 1. 從表單接收並清理資料 ---
        # 將網頁傳來的字串，轉換為後端需要的格式 (例如 datetime 物件)
        form_data = request.form
        
        # 動態更新 config 物件，這樣所有模組都能取用到最新的使用者設定
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

        # --- 2. 執行完整的後端規劃流程 ---
        api_service = GoogleApiService(config.API_KEY)
        
        all_places = api_service.get_places_details(config.INPUT_LOCATIONS)
        if not all_places:
            # TODO: 應回傳一個錯誤頁面
            return "錯誤：無法獲取任何地點資訊，請返回上一頁檢查輸入。"

        initial_clusters = cluster_places_by_distance(all_places, config.DISTANCE_THRESHOLD_KM)
        final_clusters = []
        for i, cluster in enumerate(initial_clusters):
            refined = refine_cluster_by_walking(cluster, api_service, config.WALKING_TIME_LIMIT_SECONDS)
            if refined:
                final_clusters.append(refined)

        # --- 3. 根據模式，執行不同規劃並產生結果 ---
        start_info = {'name': config.ITINERARY_START_LOCATION, 'coords': api_service.get_geocode(config.ITINERARY_START_LOCATION)}
        end_info = {'name': config.ITINERARY_END_LOCATION, 'coords': api_service.get_geocode(config.ITINERARY_END_LOCATION)}
        
        itinerary_data = None
        unvisited_locations = None
        map_html = ""

        if config.PLANNING_MODE == 'time_aware':
            itinerary_data, unvisited_locations = plan_multi_day_schedule(final_clusters, config, api_service)
            map_html = create_multi_day_map(itinerary_data, start_info, end_info, config, api_service)
        
        elif config.PLANNING_MODE == 'location_only':
            itinerary_data, unvisited_locations = plan_optimized_route(final_clusters, config, api_service)
            map_html = create_route_map(itinerary_data, start_info, end_info, config, api_service)

        # --- 4. 將所有結果渲染到 results.html ---
        return render_template(
            'results.html',
            itinerary_data=itinerary_data,
            unvisited=unvisited_locations,
            map_html=map_html,
            planning_mode=config.PLANNING_MODE
        )

    # 如果是 GET 請求，就顯示設定頁面
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)