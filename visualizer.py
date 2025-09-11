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
# visualizer.py (v4 - Corrected)
"""
Uses Folium to create an interactive map to visualize the multi-day itinerary.
This version fixes the BeautifyIcon rendering error.
"""
import folium
from folium.plugins import BeautifyIcon
import numpy as np
import polyline

def create_multi_day_map(itinerary_by_day, start_info, end_info, config, api_service):
    """Creates and saves a multi-day itinerary map."""
    print("--- Step 5: Generating the multi-day itinerary map ---")
    if not itinerary_by_day:
        print("  No itinerary to visualize.")
        return

    all_coords = [start_info['coords']] + [end_info['coords']]
    for day_plan in itinerary_by_day:
        for cluster_item in day_plan:
            for place_info in cluster_item['path']:
                all_coords.append(place_info['place']['coords'])
    
    if not all_coords:
        map_center = [25.03, 121.56] # Default to Taipei
    else:
        map_center = np.mean(all_coords, axis=0)
    
    m = folium.Map(location=map_center, zoom_start=13, tiles="cartodbpositron")

    colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A1', '#A133FF', '#33FFA1', '#FFBD33']
    
    sidebar_html = """
    <div style="position: fixed; top: 10px; right: 10px; width: 300px; height: 90%; 
               background-color: white; border:2px solid grey; z-index:9999; 
               font-family: sans-serif; font-size: 13px; overflow-y: auto; padding: 10px;">
    <b>Itinerary Overview</b><br>
    """

    folium.Marker(
        location=start_info['coords'],
        tooltip=f"Start: {start_info['name']}",
        icon=folium.Icon(color='green', icon='play', prefix='fa')
    ).add_to(m)
    folium.Marker(
        location=end_info['coords'],
        tooltip=f"End: {end_info['name']}",
        icon=folium.Icon(color='red', icon='stop', prefix='fa')
    ).add_to(m)

    for day_index, day_plan in enumerate(itinerary_by_day):
        day_start_date = day_plan[0]['path'][0]['arrival'].strftime('%Y-%m-%d')
        sidebar_html += f"<h3 style='margin-top:15px; margin-bottom:5px;'>Day {day_index + 1} ({day_start_date})</h3>"
        
        last_location_coords = start_info['coords'] if day_index == 0 else itinerary_by_day[day_index-1][-1]['path'][-1]['place']['coords']
        daily_place_counter = 0

        for cluster_item in day_plan:
            color = colors[cluster_item['cluster_id'] % len(colors)]
            sidebar_html += f"<h4 style='color:{color};'>Cluster {cluster_item['cluster_id']}</h4><ul>"
            
            path_with_time = cluster_item['path']
            for place_info in path_with_time:
                daily_place_counter += 1
                place = place_info['place']
                arrival_time = place_info['arrival']
                departure_time = place_info['departure']
                
                popup_title = place['name']
                display_name = place['original_name']
                
                popup_html = f"""
                <b>{popup_title}</b><br>
                <b>Arrival:</b> {arrival_time.strftime('%H:%M')}<br>
                <b>Departure:</b> {departure_time.strftime('%H:%M')}<br>
                <b>Address:</b> {place['address']}<br>
                <b>Rating:</b> {place['rating']}
                """
                
                # --- This is the corrected section ---
                folium.Marker(
                    location=place['coords'],
                    tooltip=f"{arrival_time.strftime('%H:%M')} - {display_name}",
                    popup=folium.Popup(popup_html, max_width=300),
                    icon=BeautifyIcon(
                        icon='map-marker',
                        border_color=color,
                        text_color=color,
                        number=daily_place_counter, # Use a running daily counter
                        icon_shape='marker'
                    )
                ).add_to(m)
                # --- End of corrected section ---

                sidebar_html += f"<li><b>{arrival_time.strftime('%H:%M')}</b>: {display_name}</li>"

                # Drawing paths logic remains the same...
                if daily_place_counter > 1:
                    # Get coordinates of the previous point for path drawing
                    prev_place_info = day_plan[0]['path'][daily_place_counter - 2] if len(day_plan[0]['path']) >= daily_place_counter else None
                    if prev_place_info:
                        prev_coords = prev_place_info['place']['coords']
                        directions = api_service.get_directions(prev_coords, place['coords'], mode=config.INTRA_CLUSTER_TRAVEL_MODE)
                        if directions:
                            route_polyline = polyline.decode(directions[0]['overview_polyline']['points'])
                            folium.PolyLine(route_polyline, color=color, weight=4, opacity=0.8).add_to(m)

            sidebar_html += "</ul>"
            
            # Draw path from last location to this cluster's entry point
            entry_point_coords = path_with_time[0]['place']['coords']
            directions = api_service.get_directions(last_location_coords, entry_point_coords, mode=config.INTER_CLUSTER_TRAVEL_MODE)
            if directions:
                route_polyline = polyline.decode(directions[0]['overview_polyline']['points'])
                folium.PolyLine(route_polyline, color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)

            last_location_coords = path_with_time[-1]['place']['coords']

    # Draw path from the last location of the trip to the final end point
    directions = api_service.get_directions(last_location_coords, end_info['coords'], mode=config.INTER_CLUSTER_TRAVEL_MODE)
    if directions:
        route_polyline = polyline.decode(directions[0]['overview_polyline']['points'])
        folium.PolyLine(route_polyline, color='black', weight=3, opacity=0.7, dash_array='5, 5').add_to(m)
    
    sidebar_html += "</div>"
    m.get_root().html.add_child(folium.Element(sidebar_html))

    map_filename = "itinerary_map.html"
    m.save(map_filename)
    print(f"\nMap has been successfully saved to: {map_filename}")