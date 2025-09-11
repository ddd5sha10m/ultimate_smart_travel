'''
# visualizer.py (v2 - 修正版)
"""
使用 Folium 建立互動式地圖來視覺化行程。
"""
import folium
from folium.plugins import BeautifyIcon
import numpy as np
import polyline

def create_itinerary_map(itinerary, start_info, end_info, api_service, travel_mode):
    if not itinerary:
        print("沒有行程可供視覺化。")
        return

    all_coords = [start_info['coords']] + [end_info['coords']]
    for item in itinerary:
        for place in item['path']:
            all_coords.append(place['coords'])
    map_center = np.mean(all_coords, axis=0)
    
    m = folium.Map(location=map_center, zoom_start=14, tiles="cartodbpositron") # 稍微放大一點

    colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A1', '#A133FF', '#33FFA1', '#FFBD33']
    
    sidebar_html = """
    <div style="position: fixed; 
               top: 10px; right: 10px; width: 280px; height: 90%; 
               background-color: white; border:2px solid grey; z-index:9999; 
               font-family: sans-serif; font-size: 14px; overflow-y: auto; padding: 10px;">
    <b>行程總覽</b><br>
    """

    folium.Marker(
        location=start_info['coords'],
        tooltip=f"起點: {start_info['name']}",
        icon=folium.Icon(color='green', icon='play', prefix='fa')
    ).add_to(m)
    folium.Marker(
        location=end_info['coords'],
        tooltip=f"終點: {end_info['name']}",
        icon=folium.Icon(color='red', icon='stop', prefix='fa')
    ).add_to(m)

    last_location_coords = start_info['coords']
    
    for i, item in enumerate(itinerary):
        color = colors[i % len(colors)]
        cluster_id = item['cluster_id']
        path = item['path']
        
        sidebar_html += f"<h4 style='color:{color};'>群組 {cluster_id + 1}</h4><ul>"
        
        for j, place in enumerate(path):
            # 使用 API 回傳的官方名稱作為 popup 標題，因為通常更完整
            popup_title = place['name']
            # 使用使用者輸入的原始名稱作為 tooltip 和側邊欄文字
            display_name = place['original_name']
            
            hours_str = "<br>".join(place.get('opening_hours', ['N/A']))
            popup_html = f"""
            <b>{popup_title}</b><br>
            地址: {place['address']}<br>
            評分: {place['rating']}<br>
            營業時間:<br>{hours_str}
            """
            
            # [--- 核心修改 1 ---]
            # 新增 tooltip，滑鼠移到標記上時會顯示地點名稱
            folium.Marker(
                location=place['coords'],
                tooltip=display_name, # <-- 顯示原始名稱
                popup=folium.Popup(popup_html, max_width=300),
                icon=BeautifyIcon(
                    icon='map-marker',
                    border_color=color,
                    text_color=color,
                    number=j + 1,
                    icon_shape='marker'
                )
            ).add_to(m)
            
            # [--- 核心修改 2 ---]
            # 側邊欄使用原始名稱
            sidebar_html += f"<li><b>{j+1}. {display_name}</b></li>" # <-- 顯示原始名稱

            if j > 0:
                # ... (路徑繪製邏輯不變)
                directions = api_service.get_directions(path[j-1]['coords'], place['coords'], mode="walking")
                if directions:
                    route_polyline = polyline.decode(directions[0]['overview_polyline']['points'])
                    folium.PolyLine(route_polyline, color=color, weight=4, opacity=0.8).add_to(m)

        sidebar_html += "</ul>"
        
        entry_point_coords = path[0]['coords']
        exit_point_coords = path[-1]['coords']
        
        directions = api_service.get_directions(last_location_coords, entry_point_coords, mode=travel_mode)
        if directions:
            route_polyline = polyline.decode(directions[0]['overview_polyline']['points'])
            folium.PolyLine(route_polyline, color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)
        
        last_location_coords = exit_point_coords

    directions = api_service.get_directions(last_location_coords, end_info['coords'], mode=travel_mode)
    if directions:
        route_polyline = polyline.decode(directions[0]['overview_polyline']['points'])
        folium.PolyLine(route_polyline, color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)
    
    sidebar_html += "</div>"
    m.get_root().html.add_child(folium.Element(sidebar_html))

    map_filename = "itinerary_map.html"
    m.save(map_filename)
    print(f"\n地圖已成功儲存至: {map_filename}")
'''

'''
# visualizer.py (v6 - 完整版)
"""
包含兩種地圖產生器：
1. create_route_map: 呈現純路徑排序。
2. create_multi_day_map: 呈現詳細的多日時間表。
"""
import folium
from folium.plugins import BeautifyIcon
import numpy as np
import polyline
from datetime import datetime, timedelta

# --- [地圖一] 純路徑地圖 (Location-Only) ---
def create_route_map(optimized_route, start_info, end_info, config, api_service):
    print("--- 步驟 5: 正在生成純路徑地圖 ---")
    if not optimized_route: return

    all_coords = [start_info['coords'], end_info['coords']]
    for item in optimized_route:
        for place in item['path']: all_coords.append(place['coords'])
    map_center = np.mean(all_coords, axis=0)
    
    m = folium.Map(location=map_center, zoom_start=13, tiles="cartodbpositron")
    colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A1', '#A133FF', '#33FFA1', '#FFBD33']
    sidebar_html = """
    <div style="position: fixed; top: 10px; right: 10px; width: 280px; height: 90%; 
               background-color: white; border:2px solid grey; z-index:9999; 
               font-family: sans-serif; font-size: 14px; overflow-y: auto; padding: 10px;">
    <b>行程順序總覽</b><br>
    """

    folium.Marker(location=start_info['coords'], tooltip=f"起點: {start_info['name']}", icon=folium.Icon(color='green', icon='play', prefix='fa')).add_to(m)
    folium.Marker(location=end_info['coords'], tooltip=f"終點: {end_info['name']}", icon=folium.Icon(color='red', icon='stop', prefix='fa')).add_to(m)

    last_coords, total_place_counter = start_info['coords'], 0
    for item in optimized_route:
        color, cluster_id, path = colors[item['cluster_id'] % len(colors)], item['cluster_id'], item['path']
        sidebar_html += f"<h4 style='color:{color};'>群組 {cluster_id}</h4><ul>"
        
        for place in path:
            total_place_counter += 1
            popup_html = f"<b>{place['name']}</b><br>地址: {place['address']}<br>評分: {place['rating']}"
            folium.Marker(
                location=place['coords'], tooltip=place['original_name'], popup=folium.Popup(popup_html, max_width=300),
                icon=BeautifyIcon(icon='map-marker', border_color=color, text_color=color, number=total_place_counter, icon_shape='marker')
            ).add_to(m)
            sidebar_html += f"<li><b>{total_place_counter}. {place['original_name']}</b></li>"

        sidebar_html += "</ul>"
        
        # 繪製路徑
        entry_coords = path[0]['coords']
        dirs = api_service.get_directions(last_coords, entry_coords, mode=config.INTER_CLUSTER_TRAVEL_MODE)
        if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)
        
        if len(path) > 1:
            points_for_line = [p['coords'] for p in path]
            dirs = api_service.get_directions(points_for_line[0], points_for_line[-1], points_for_line[1:-1], config.INTRA_CLUSTER_TRAVEL_MODE)
            if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color=color, weight=4, opacity=0.8).add_to(m)
        
        last_coords = path[-1]['coords']

    dirs = api_service.get_directions(last_coords, end_info['coords'], mode=config.INTER_CLUSTER_TRAVEL_MODE)
    if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)

    sidebar_html += "</div>"
    m.get_root().html.add_child(folium.Element(sidebar_html))
    map_filename = "itinerary_route_map.html"
    m.save(map_filename)
    print(f"\n純路徑地圖已成功儲存至: {map_filename}")

# --- [地圖二] 多日時間表地圖 (Time-Aware) ---
def create_multi_day_map(itinerary_by_day, start_info, end_info, config, api_service):
    print("--- 步驟 5: 正在生成多日行程地圖 ---")
    if not itinerary_by_day: return
    
    all_coords = [start_info['coords'], end_info['coords']]
    for day in itinerary_by_day:
        for cluster in day:
            for item in cluster['path']: all_coords.append(item['place']['coords'])
    map_center = np.mean(all_coords, axis=0)
    
    m = folium.Map(location=map_center, zoom_start=13, tiles="cartodbpositron")
    colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A1', '#A133FF', '#33FFA1', '#FFBD33']
    sidebar_html = """
    <div style="position: fixed; top: 10px; right: 10px; width: 300px; height: 90%; 
               background-color: white; border:2px solid grey; z-index:9999; 
               font-family: sans-serif; font-size: 13px; overflow-y: auto; padding: 10px;">
    <b>行程總覽</b><br>
    """
    
    folium.Marker(location=start_info['coords'], tooltip=f"起點: {start_info['name']}", icon=folium.Icon(color='green', icon='play', prefix='fa')).add_to(m)
    folium.Marker(location=end_info['coords'], tooltip=f"終點: {end_info['name']}", icon=folium.Icon(color='red', icon='stop', prefix='fa')).add_to(m)

    for day_index, day_plan in enumerate(itinerary_by_day):
        day_str = day_plan[0]['path'][0]['arrival'].strftime('%Y-%m-%d')
        sidebar_html += f"<h3 style='margin-top:15px; margin-bottom:5px;'>Day {day_index + 1} ({day_str})</h3>"
        
        last_coords = start_info['coords'] if day_index == 0 else itinerary_by_day[day_index-1][-1]['path'][-1]['place']['coords']
        daily_place_counter = 0

        for cluster_item in day_plan:
            color = colors[cluster_item['cluster_id'] % len(colors)]
            sidebar_html += f"<h4 style='color:{color};'>群組 {cluster_item['cluster_id']}</h4><ul>"
            
            path_with_time = cluster_item['path']
            for item in path_with_time:
                daily_place_counter += 1
                place, arrival, departure = item['place'], item['arrival'], item['departure']
                popup_html = f"<b>{place['name']}</b><br>預計抵達: {arrival.strftime('%H:%M')}<br>預計離開: {departure.strftime('%H:%M')}<br>地址: {place['address']}"
                
                folium.Marker(
                    location=place['coords'], tooltip=f"{arrival.strftime('%H:%M')} - {place['original_name']}", popup=folium.Popup(popup_html, max_width=300),
                    icon=BeautifyIcon(icon='map-marker', border_color=color, text_color=color, number=daily_place_counter, icon_shape='marker')
                ).add_to(m)
                sidebar_html += f"<li><b>{arrival.strftime('%H:%M')}</b>: {place['original_name']}</li>"
            
            # 繪製路徑
            entry_coords = path_with_time[0]['place']['coords']
            dirs = api_service.get_directions(last_coords, entry_coords, mode=config.INTER_CLUSTER_TRAVEL_MODE, departure_time=path_with_time[0]['arrival'] - timedelta(minutes=30))
            if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)
            
            if len(path_with_time) > 1:
                points_for_line = [p['place']['coords'] for p in path_with_time]
                dirs = api_service.get_directions(points_for_line[0], points_for_line[-1], points_for_line[1:-1], config.INTRA_CLUSTER_TRAVEL_MODE, departure_time=path_with_time[0]['departure'])
                if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color=color, weight=4, opacity=0.8).add_to(m)

            last_coords = path_with_time[-1]['place']['coords']

    dirs = api_service.get_directions(last_coords, end_info['coords'], mode=config.INTER_CLUSTER_TRAVEL_MODE)
    if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)
    
    sidebar_html += "</div>"
    m.get_root().html.add_child(folium.Element(sidebar_html))
    map_filename = "itinerary_schedule_map.html"
    m.save(map_filename)
    print(f"\n多日行程地圖已成功儲存至: {map_filename}")
    '''
import folium
from folium.plugins import BeautifyIcon
import numpy as np
import polyline
from datetime import datetime, timedelta

# --- [地圖一] 純路徑地圖 (Location-Only) ---
def create_route_map(optimized_route, start_info, end_info, config, api_service):
    print("--- 步驟 5: 正在生成純路徑地圖 ---")
    if not optimized_route: return

    all_coords = [start_info['coords'], end_info['coords']]
    for item in optimized_route:
        for place in item['path']: all_coords.append(place['coords'])
    map_center = np.mean(all_coords, axis=0)
    
    m = folium.Map(location=map_center, zoom_start=13, tiles="cartodbpositron")
    colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A1', '#A133FF', '#33FFA1', '#FFBD33']
    sidebar_html = """
    <div style="position: fixed; top: 10px; right: 10px; width: 280px; height: 90%; 
               background-color: white; border:2px solid grey; z-index:9999; 
               font-family: sans-serif; font-size: 14px; overflow-y: auto; padding: 10px;">
    <b>行程順序總覽</b><br>
    """

    folium.Marker(location=start_info['coords'], tooltip=f"起點: {start_info['name']}", icon=folium.Icon(color='green', icon='play', prefix='fa')).add_to(m)
    folium.Marker(location=end_info['coords'], tooltip=f"終點: {end_info['name']}", icon=folium.Icon(color='red', icon='stop', prefix='fa')).add_to(m)

    last_coords, total_place_counter = start_info['coords'], 0
    for item in optimized_route:
        color, cluster_id, path = colors[item['cluster_id'] % len(colors)], item['cluster_id'], item['path']
        sidebar_html += f"<h4 style='color:{color};'>群組 {cluster_id}</h4><ul>"
        
        for place in path:
            total_place_counter += 1
            popup_html = f"<b>{place['name']}</b><br>地址: {place['address']}<br>評分: {place['rating']}"
            folium.Marker(
                location=place['coords'], tooltip=place['original_name'], popup=folium.Popup(popup_html, max_width=300),
                icon=BeautifyIcon(icon='map-marker', border_color=color, text_color=color, number=total_place_counter, icon_shape='marker')
            ).add_to(m)
            sidebar_html += f"<li><b>{total_place_counter}. {place['original_name']}</b></li>"

        sidebar_html += "</ul>"
        
        # 繪製路徑
        entry_coords = path[0]['coords']
        # [--- 確認修正 ---] 確保使用群組間的交通模式
        dirs = api_service.get_directions(last_coords, entry_coords, mode=config.INTER_CLUSTER_TRAVEL_MODE)
        if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)
        
        if len(path) > 1:
            points_for_line = [p['coords'] for p in path]
            # [--- 確認修正 ---] 確保使用群組內的交通模式
            dirs = api_service.get_directions(points_for_line[0], points_for_line[-1], points_for_line[1:-1], mode=config.INTRA_CLUSTER_TRAVEL_MODE)
            if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color=color, weight=4, opacity=0.8).add_to(m)
        
        last_coords = path[-1]['coords']

    # [--- 確認修正 ---] 確保使用群組間的交通模式
    dirs = api_service.get_directions(last_coords, end_info['coords'], mode=config.INTER_CLUSTER_TRAVEL_MODE)
    if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)

    sidebar_html += "</div>"
    print("  純路徑地圖 HTML 已產生。")
    return m._repr_html_()

# --- [地圖二] 多日時間表地圖 (Time-Aware) ---
def create_multi_day_map(itinerary_by_day, start_info, end_info, config, api_service):
    print("--- 步驟 5: 正在生成多日行程地圖 ---")
    if not itinerary_by_day: return
    
    all_coords = [start_info['coords'], end_info['coords']]
    for day in itinerary_by_day:
        for cluster in day:
            for item in cluster['path']: all_coords.append(item['place']['coords'])
    map_center = np.mean(all_coords, axis=0)
    
    m = folium.Map(location=map_center, zoom_start=13, tiles="cartodbpositron")
    colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A1', '#A133FF', '#33FFA1', '#FFBD33']
    sidebar_html = """
    <div style="position: fixed; top: 10px; right: 10px; width: 300px; height: 90%; 
               background-color: white; border:2px solid grey; z-index:9999; 
               font-family: sans-serif; font-size: 13px; overflow-y: auto; padding: 10px;">
    <b>行程總覽</b><br>
    """
    
    folium.Marker(location=start_info['coords'], tooltip=f"起點: {start_info['name']}", icon=folium.Icon(color='green', icon='play', prefix='fa')).add_to(m)
    folium.Marker(location=end_info['coords'], tooltip=f"終點: {end_info['name']}", icon=folium.Icon(color='red', icon='stop', prefix='fa')).add_to(m)

    for day_index, day_plan in enumerate(itinerary_by_day):
        day_str = day_plan[0]['path'][0]['arrival'].strftime('%Y-%m-%d')
        sidebar_html += f"<h3 style='margin-top:15px; margin-bottom:5px;'>Day {day_index + 1} ({day_str})</h3>"
        
        last_coords = start_info['coords'] if day_index == 0 else itinerary_by_day[day_index-1][-1]['path'][-1]['place']['coords']
        daily_place_counter = 0

        for cluster_item in day_plan:
            color = colors[cluster_item['cluster_id'] % len(colors)]
            sidebar_html += f"<h4 style='color:{color};'>群組 {cluster_item['cluster_id']}</h4><ul>"
            
            path_with_time = cluster_item['path']
            for item in path_with_time:
                daily_place_counter += 1
                place, arrival, departure = item['place'], item['arrival'], item['departure']
                popup_html = f"<b>{place['name']}</b><br>預計抵達: {arrival.strftime('%H:%M')}<br>預計離開: {departure.strftime('%H:%M')}<br>地址: {place['address']}"
                
                folium.Marker(
                    location=place['coords'], tooltip=f"{arrival.strftime('%H:%M')} - {place['original_name']}", popup=folium.Popup(popup_html, max_width=300),
                    icon=BeautifyIcon(icon='map-marker', border_color=color, text_color=color, number=daily_place_counter, icon_shape='marker')
                ).add_to(m)
                sidebar_html += f"<li><b>{arrival.strftime('%H:%M')}</b>: {place['original_name']}</li>"
            
            # 繪製路徑
            entry_coords = path_with_time[0]['place']['coords']
            dirs = api_service.get_directions(last_coords, entry_coords, mode=config.INTER_CLUSTER_TRAVEL_MODE, departure_time=path_with_time[0]['arrival'] - timedelta(minutes=30))
            if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)
            
            if len(path_with_time) > 1:
                points_for_line = [p['place']['coords'] for p in path_with_time]
                # [--- 確認修正 ---] 確保使用群組內的交通模式
                dirs = api_service.get_directions(points_for_line[0], points_for_line[-1], points_for_line[1:-1], mode=config.INTRA_CLUSTER_TRAVEL_MODE, departure_time=path_with_time[0]['departure'])
                if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color=color, weight=4, opacity=0.8).add_to(m)

            last_coords = path_with_time[-1]['place']['coords']

    # [--- 確認修正 ---] 確保使用群組間的交通模式
    dirs = api_service.get_directions(last_coords, end_info['coords'], mode=config.INTER_CLUSTER_TRAVEL_MODE)
    if dirs: folium.PolyLine(polyline.decode(dirs[0]['overview_polyline']['points']), color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)
    
    sidebar_html += "</div>"
    print("  多日行程地圖 HTML 已產生。")
    return m._repr_html_()