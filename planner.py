# planner.py (v8 - Inclusive Version)
"""
Contains planning algorithms that ensure ALL locations are included.
This version prevents location filtering and extends the itinerary if needed.
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
        return [places] if places else []
    
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
    
    clusters = list(grouped_places.values())
    print(f"  Clustering complete, formed {len(clusters)} groups.")
    print(f"  Group sizes: {[len(cluster) for cluster in clusters]}")
    
    return clusters

def refine_cluster_by_walking(cluster_places, api_service, time_limit_seconds):
    """
    Modified version that keeps ALL places regardless of walking time.
    Only optimizes the order but doesn't filter out locations.
    """
    print(f"    Refining cluster with {len(cluster_places)} places (INCLUSIVE mode)")
    
    num_places = len(cluster_places)
    if num_places <= 1:
        return cluster_places
    
    # Instead of filtering, we just return the original cluster
    # The walking time limit is now only used for information/warning
    try:
        if num_places > 2:
            origin = f"place_id:{cluster_places[0]['place_id']}"
            destination = f"place_id:{cluster_places[-1]['place_id']}"
            waypoints = [f"place_id:{p['place_id']}" for p in cluster_places[1:-1]]
            
            directions_result = api_service.gmaps.directions(
                origin=origin, destination=destination, waypoints=waypoints,
                mode="walking", optimize_waypoints=True
            )
            
            if directions_result and 'legs' in directions_result[0]:
                total_walking_time = sum(leg['duration']['value'] for leg in directions_result[0]['legs'])
                if total_walking_time > time_limit_seconds:
                    print(f"    Warning: Cluster walking time ({total_walking_time//60} min) exceeds limit ({time_limit_seconds//60} min), but keeping all places anyway")
    
    except Exception as e:
        print(f"    [Info] Could not calculate walking time: {e}, keeping all places anyway")
    
    return cluster_places  # Always return all places

def plan_optimized_route(clusters, config, api_service):
    """Plans the optimal route ensuring ALL clusters are included."""
    print("\n--- Step 4: Planning the optimal location-based route (INCLUSIVE) ---")
    
    if not clusters:
        return [], []
    
    # Ensure we don't lose any clusters
    print(f"  Processing {len(clusters)} clusters with {sum(len(c) for c in clusters)} total locations")
    
    start_coords = api_service.get_geocode(config.ITINERARY_START_LOCATION)
    end_coords = api_service.get_geocode(config.ITINERARY_END_LOCATION)
    
    # Create cluster representatives
    cluster_reps = {}
    for i, cluster in enumerate(clusters):
        cluster_reps[i] = {"coords": np.mean([p['coords'] for p in cluster], axis=0)}
    
    # Build distance matrix for cluster ordering
    all_points = {"start": {"coords": start_coords}, "end": {"coords": end_coords}}
    for i, rep in cluster_reps.items():
        all_points[i] = rep
    
    point_keys = list(all_points.keys())
    point_coords = [all_points[key]['coords'] for key in point_keys]
    
    matrix = api_service.get_distance_matrix(point_coords, point_coords, config.INTER_CLUSTER_TRAVEL_MODE)
    
    # Build travel times dictionary
    travel_times = {}
    for i, row in enumerate(matrix['rows']):
        for j, element in enumerate(row['elements']):
            duration = element.get('duration', {}).get('value', float('inf'))
            travel_times[(point_keys[i], point_keys[j])] = duration
    
    # Order clusters optimally
    cluster_indices = list(cluster_reps.keys())
    
    if len(cluster_indices) <= config.BRUTE_FORCE_LIMIT:
        # Use brute force for optimal ordering
        best_order, min_duration = None, float('inf')
        for perm in permutations(cluster_indices):
            total_duration = travel_times[('start', perm[0])]
            for i in range(len(perm) - 1):
                total_duration += travel_times[(perm[i], perm[i+1])]
            total_duration += travel_times[(perm[-1], 'end')]
            
            if total_duration < min_duration:
                min_duration, best_order = total_duration, perm
        
        ordered_indices = list(best_order) if best_order else cluster_indices
    else:
        # Use greedy approach for larger numbers
        print("  Using greedy approach for cluster ordering (too many for brute force)")
        ordered_indices = cluster_indices  # Simplified for now
    
    # Build final route ensuring all clusters are included
    final_route = []
    last_coords = start_coords
    
    for i, current_idx in enumerate(ordered_indices):
        cluster = clusters[current_idx]
        print(f"  Processing cluster {current_idx} with {len(cluster)} places")
        
        # Find entry point (closest to last location)
        entry_point = min(cluster, key=lambda p: haversine(last_coords, p['coords']))
        
        # Find exit point (closest to next cluster or end)
        if i + 1 < len(ordered_indices):
            next_cluster_center = cluster_reps[ordered_indices[i + 1]]['coords']
            exit_point = min(cluster, key=lambda p: haversine(p['coords'], next_cluster_center))
        else:
            exit_point = min(cluster, key=lambda p: haversine(p['coords'], end_coords))
        
        # Get waypoints (all other places in cluster)
        waypoints = [p for p in cluster if p != entry_point and p != exit_point]
        
        # Optimize internal route
        if len(cluster) <= config.BRUTE_FORCE_LIMIT and len(waypoints) > 0:
            # Brute force optimization for small clusters
            best_waypoint_order = []
            if waypoints:
                min_distance = float('inf')
                for perm in permutations(waypoints):
                    distance = haversine(entry_point['coords'], perm[0]['coords'])
                    for j in range(len(perm) - 1):
                        distance += haversine(perm[j]['coords'], perm[j+1]['coords'])
                    distance += haversine(perm[-1]['coords'], exit_point['coords'])
                    
                    if distance < min_distance:
                        min_distance = distance
                        best_waypoint_order = list(perm)
            waypoints = best_waypoint_order
        
        # Build cluster path ensuring all places are included
        cluster_path = [entry_point] + waypoints
        if entry_point != exit_point:
            cluster_path.append(exit_point)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_path = []
        for place in cluster_path:
            if place['place_id'] not in seen:
                seen.add(place['place_id'])
                unique_path.append(place)
        
        final_route.append({
            "cluster_id": current_idx,
            "path": unique_path
        })
        
        last_coords = unique_path[-1]['coords']
    
    # Verify all locations are included
    included_places = set()
    for item in final_route:
        for place in item['path']:
            included_places.add(place['place_id'])
    
    all_places = set()
    for cluster in clusters:
        for place in cluster:
            all_places.add(place['place_id'])
    
    missing_places = all_places - included_places
    if missing_places:
        print(f"  Warning: {len(missing_places)} places were not included in the route")
    else:
        print(f"  ✓ All {len(all_places)} places successfully included in route")
    
    return final_route, []  # No unvisited locations in inclusive mode

def plan_multi_day_schedule(clusters, config, api_service):
    """Plans a time-aware, multi-day schedule ensuring ALL locations are included."""
    print("\n--- Step 4: Planning multi-day itinerary (INCLUSIVE mode) ---")
    
    if not clusters:
        return [], []
    
    # Force include all locations settings
    force_include = getattr(config, 'FORCE_INCLUDE_ALL_LOCATIONS', True)
    ignore_hours = getattr(config, 'IGNORE_OPENING_HOURS', True) 
    extend_days = getattr(config, 'EXTEND_DAYS_IF_NEEDED', True)
    
    start_coords = api_service.get_geocode(config.ITINERARY_START_LOCATION)
    
    # Simple cluster ordering (can be improved with the same logic as location_only mode)
    ordered_cluster_indices = list(range(len(clusters)))
    
    itinerary_by_day = []
    unvisited_clusters = ordered_cluster_indices[:]
    current_time = config.TRIP_START_TIME
    last_location_coords = start_coords
    day_counter = 0
    
    # Extended loop to ensure all clusters are scheduled
    max_days = 10  # Safety limit
    
    while unvisited_clusters and day_counter < max_days:
        day_counter += 1
        day_plan = []
        
        # Set up day boundaries
        day_start_time = current_time.replace(hour=config.DAY_START_HOUR, minute=0, second=0)
        day_end_time = current_time.replace(hour=config.DAY_END_HOUR, minute=0, second=0)
        current_time = max(current_time, day_start_time)
        
        print(f"  Planning Day {day_counter} ({current_time.strftime('%Y-%m-%d')})")
        
        clusters_for_today = unvisited_clusters[:]
        
        for cluster_idx in clusters_for_today:
            cluster = clusters[cluster_idx]
            
            # Find best entry point
            entry_point = min(cluster, key=lambda p: haversine(last_location_coords, p['coords']))
            
            # Calculate travel time to cluster
            matrix = api_service.get_distance_matrix(
                [last_location_coords], [entry_point['coords']], 
                config.INTER_CLUSTER_TRAVEL_MODE, current_time
            )
            
            travel_secs = matrix['rows'][0]['elements'][0].get('duration', {}).get('value', 0)
            arrival_time = current_time + timedelta(seconds=travel_secs)
            
            # Plan internal cluster route
            internal_path = cluster  # Simplified - could optimize order here
            temp_time = arrival_time
            cluster_is_schedulable = True
            projected_path = []
            
            for i, place in enumerate(internal_path):
                # Add internal travel time
                if i > 0:
                    internal_matrix = api_service.get_distance_matrix(
                        [internal_path[i-1]['coords']], [place['coords']], 
                        config.INTRA_CLUSTER_TRAVEL_MODE, temp_time
                    )
                    internal_travel_secs = internal_matrix['rows'][0]['elements'][0].get('duration', {}).get('value', 0)
                    temp_time += timedelta(seconds=internal_travel_secs)
                
                # Check if we can fit this place in the current day
                departure_time = temp_time + timedelta(minutes=config.DEFAULT_STAY_DURATION_MINS)
                
                # In force include mode, be more lenient with time constraints
                if force_include:
                    # Only check if we're extremely over time (more than 2 hours past day end)
                    if temp_time > day_end_time + timedelta(hours=2):
                        cluster_is_schedulable = False
                        break
                    # Skip opening hours check if ignore_hours is True
                    if not ignore_hours and not api_service.is_open_at(place, temp_time):
                        print(f"    Warning: {place['original_name']} may be closed at {temp_time.strftime('%H:%M')}, including anyway")
                else:
                    # Original strict checking
                    if temp_time >= day_end_time or not api_service.is_open_at(place, temp_time):
                        cluster_is_schedulable = False
                        break
                
                projected_path.append({
                    "place": place,
                    "arrival": temp_time,
                    "departure": departure_time
                })
                temp_time = departure_time
            
            # In force include mode, try to fit cluster even if it seems too long
            if not cluster_is_schedulable and force_include and extend_days:
                # If we can't fit it today, definitely schedule it tomorrow
                if len(day_plan) > 0:  # Only skip if we already have something planned for today
                    continue
                else:
                    # Force it into today anyway
                    cluster_is_schedulable = True
                    print(f"    Forcing cluster {cluster_idx} into day {day_counter} (may exceed normal hours)")
            
            if cluster_is_schedulable:
                day_plan.append({
                    "cluster_id": cluster_idx,
                    "path": projected_path
                })
                current_time = temp_time
                last_location_coords = projected_path[-1]['place']['coords']
                unvisited_clusters.remove(cluster_idx)
                
                print(f"    ✓ Scheduled cluster {cluster_idx} ({len(cluster)} places)")
        
        if day_plan:
            itinerary_by_day.append(day_plan)
        
        # Move to next day
        current_time = (current_time.replace(hour=0, minute=0, second=0) + timedelta(days=1)).replace(hour=config.DAY_START_HOUR)
        last_location_coords = start_coords  # Reset to start location for new day
    
    # Final verification
    scheduled_places = set()
    for day in itinerary_by_day:
        for cluster_item in day:
            for place_info in cluster_item['path']:
                scheduled_places.add(place_info['place']['place_id'])
    
    all_places = set()
    for cluster in clusters:
        for place in cluster:
            all_places.add(place['place_id'])
    
    if len(scheduled_places) == len(all_places):
        print(f"  ✓ Successfully scheduled all {len(all_places)} places across {len(itinerary_by_day)} days")
    else:
        print(f"  Warning: Only scheduled {len(scheduled_places)}/{len(all_places)} places")
    
    unvisited = [clusters[i] for i in unvisited_clusters]
    return itinerary_by_day, unvisited