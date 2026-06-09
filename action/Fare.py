import csv
import json
import os
import re
import sys
import shutil



def extract_fare_attributes():
    route_groups = {}

    print(f"Extracting GTFS fare attributes...")
    raw_text = open('gtfs/fare_attributes.txt', encoding="utf8").read()
    rows = list(csv.reader(raw_text.splitlines()))
    if not rows:
        return {}, {}

    header = rows[0]
    data_rows = rows[1:] if header and header[0].strip().lower() == "fare_id" else rows


    for parts in data_rows:
        if len(parts) < 3:
            continue

        fare_id = parts[0].strip()
        if not fare_id or fare_id.strip().lower() == "fare_id":
            continue

        try:
            price = float(parts[1])
        except ValueError:
            continue

        route_id = "-".join(fare_id.split("-")[:2])
        match = re.search(r"-(\d+)-(\d+)$", fare_id)
        if not match:
            continue

        orig = int(match.group(1))
        dest = int(match.group(2))
        if orig >= dest:
            continue

        #get the agency_id from the fare_id, which is the last part after the last '-'  
        agency_id = parts[5]
        
        route_groups.setdefault(agency_id + '-' + route_id, []).append((orig, dest, price))

    return route_groups


def summarize_route_fares(pairs):
    if not pairs:
        return []

    pair_price = {(o, d): p for o, d, p in pairs}
    min_stop = min(o for o, d, _ in pairs)
    max_stop = max(d for o, d, _ in pairs)
    full_price = pair_price.get((min_stop, max_stop), max(p for _, _, p in pairs))

    full_section = {
        "range": [min_stop, max_stop],
        "price": full_price,
    }

    sections = []
    
    # Build a map of (start, price) -> [ends]
    fare_map = {}
    for (start, end), price in pair_price.items():
        key = (start, price)
        if key not in fare_map:
            fare_map[key] = []
        fare_map[key].append(end)
    
    # For each (start, price) combination, create a range [start, max_end]
    for (start, price), ends in fare_map.items():
        max_end = max(ends)
        sections.append({
            "range": [start, max_end],
            "price": price,
        })

    # Consolidate ranges with same end and price
    consolidated = {}
    for section in sections:
        end, price = section["range"][1], section["price"]
        key = (end, price)
        if key not in consolidated:
            consolidated[key] = []
        consolidated[key].append(section["range"][0])
    
    # Rebuild sections with consolidated ranges
    unique_sections = []
    for (end, price), starts in consolidated.items():
        min_start = min(starts)
        # Skip if this matches the full_section
        if min_start == full_section["range"][0] and end == full_section["range"][1] and price == full_section["price"]:
            continue
        unique_sections.append({
            "range": [min_start, end],
            "price": price,
        })

    unique_sections.sort(key=lambda x: (x["range"][0], x["range"][1]))
    return [full_section] + unique_sections


if __name__ == "__main__":
    route_groups = extract_fare_attributes()

    # Clean up fare directory before writing new files
    if os.path.exists("fare"):
        shutil.rmtree("fare")
    os.makedirs("fare", exist_ok=True)

    for route_id, pairs in route_groups.items():
        #currency = route_currencies.get(route_id, "HKD")
        summary = summarize_route_fares(pairs)
        output_path = os.path.join("fare", f"{route_id}.json")
        with open(output_path, "w", encoding="utf-8") as out_file:
            json.dump(summary, out_file, indent=2)

    print(f"Wrote {len(route_groups)} files to fare/")