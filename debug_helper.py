# debug_helper.py
"""
Debug helper to track where locations are being filtered out.
Add this to your project to identify the exact cause of location losses.
"""

def track_location_changes(stage_name, original_data, current_data, location_key='original_name'):
    """
    Track and report changes in location counts between processing stages.
    
    Args:
        stage_name: Name of the processing stage
        original_data: Original list/structure containing locations
        current_data: Current list/structure containing locations
        location_key: Key to identify location names
    """
    
    def extract_locations_from_data(data):
        """Extract location names from various data structures."""
        locations = set()
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    if location_key in item:
                        locations.add(item[location_key])
                    elif 'path' in item:  # Route format
                        for place in item['path']:
                            locations.add(place[location_key])
                elif isinstance(item, list):  # Cluster format
                    for place in item:
                        if isinstance(place, dict) and location_key in place:
                            locations.add(place[location_key])
        
        return locations
    
    original_locations = extract_locations_from_data(original_data)
    current_locations = extract_locations_from_data(current_data)
    
    lost_locations = original_locations - current_locations
    added_locations = current_locations - original_locations
    
    print(f"\n=== LOCATION TRACKING: {stage_name} ===")
    print(f"Original count: {len(original_locations)}")
    print(f"Current count: {len(current_locations)}")
    
    if lost_locations:
        print(f"❌ LOST {len(lost_locations)} locations:")
        for loc in sorted(lost_locations):
            print(f"   - {loc}")
    
    if added_locations:
        print(f"➕ ADDED {len(added_locations)} locations:")
        for loc in sorted(added_locations):
            print(f"   + {loc}")
    
    if not lost_locations and not added_locations:
        print("✅ No locations lost or gained")
    
    print("=" * 50)
    
    return len(lost_locations) == 0


def debug_google_places_api(api_service, input_locations):
    """
    Debug Google Places API calls to see which locations are not found.
    """
    print("\n=== DEBUGGING GOOGLE PLACES API ===")
    
    found_places = []
    not_found = []
    
    for name in input_locations:
        try:
            find_place_result = api_service.gmaps.find_place(
                input=name, 
                input_type='textquery', 
                fields=['place_id', 'name']
            )
            
            if find_place_result['status'] == 'OK' and find_place_result['candidates']:
                place_id = find_place_result['candidates'][0]['place_id']
                found_name = find_place_result['candidates'][0].get('name', name)
                found_places.append({'input': name, 'found': found_name, 'place_id': place_id})
                print(f"✅ Found: '{name}' → '{found_name}'")
            else:
                not_found.append(name)
                print(f"❌ Not found: '{name}'")
                
        except Exception as e:
            not_found.append(name)
            print(f"❌ Error with '{name}': {e}")
    
    print(f"\nSummary: {len(found_places)}/{len(input_locations)} locations found")
    
    if not_found:
        print(f"\n❌ Locations not found by Google Places API:")
        for loc in not_found:
            print(f"   - {loc}")
        print("\nSuggestions for not found locations:")
        print("1. Try more specific names (e.g., add 'Vienna' or 'Wien')")
        print("2. Use official names in German")
        print("3. Include address information")
    
    return found_places, not_found


def debug_cluster_refinement(clusters_before, clusters_after):
    """
    Debug cluster refinement to see which places are filtered out.
    """
    print("\n=== DEBUGGING CLUSTER REFINEMENT ===")
    
    places_before = []
    places_after = []
    
    # Extract places from clusters before refinement
    for i, cluster in enumerate(clusters_before):
        for place in cluster:
            places_before.append({'cluster': i, 'place': place['original_name'], 'data': place})
    
    # Extract places from clusters after refinement  
    for i, cluster in enumerate(clusters_after):
        for place in cluster:
            places_after.append({'cluster': i, 'place': place['original_name'], 'data': place})
    
    places_before_names = {p['place'] for p in places_before}
    places_after_names = {p['place'] for p in places_after}
    
    filtered_out = places_before_names - places_after_names
    
    print(f"Before refinement: {len(places_before_names)} places in {len(clusters_before)} clusters")
    print(f"After refinement: {len(places_after_names)} places in {len(clusters_after)} clusters")
    
    if filtered_out:
        print(f"\n❌ Places filtered out during refinement:")
        for place_name in sorted(filtered_out):
            # Find which cluster it was in
            for p in places_before:
                if p['place'] == place_name:
                    print(f"   - {place_name} (was in cluster {p['cluster']})")
                    break
    else:
        print("✅ No places filtered out during refinement")
    
    return len(filtered_out) == 0