import math
try:
    import osmnx as ox
    import networkx as nx
    OSMNX_AVAILABLE = True
except Exception:
    OSMNX_AVAILABLE = False

def _straight_line_route(start, end, steps=20):
    """Generates a straight line route between start and end coordinates."""
    lat1, lon1 = start
    lat2, lon2 = end
    coords = []
    for i in range(steps + 1):
        t = i / steps
        coords.append((lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t))
    return coords

def _generate_alternatives(start, end):
    """Generates simple alternative straight-line routes with slight offsets."""
    base = _straight_line_route(start, end, steps=40)

    def offset_coords(coords, meters_offset):
        res = []
        for lat, lon in coords:
            lat_off = lat + (meters_offset / 111000.0)  # approx
            res.append((lat_off, lon))
        return res

    return [base, offset_coords(base, 8), offset_coords(base, -8)]

def haversine_m(a, b):
    """Calculate distance in meters between two lat/lon points."""
    lat1, lon1 = a
    lat2, lon2 = b
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    aa = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(aa))
    return 6371 * c * 1000  # meters

def compute_routes(start, end, max_routes=3):
    """
    start/end are (lat, lon)
    Returns list of routes, each route is list of (lat, lon)
    """
    if OSMNX_AVAILABLE:
        try:
            # Midpoint & distance padding
            mid = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
            base_dist = haversine_m(start, end)
            padding = max(1000, int(base_dist * 1.5))  # larger padding for alternative paths

            # Build walkable graph
            G = ox.graph_from_point(mid, dist=padding, network_type='walk', simplify=True)
            G_simple = nx.Graph(G)  # convert to simple graph

            # Nearest node functions
            try:
                nearest_nodes = ox.distance.nearest_nodes
            except Exception:
                nearest_nodes = ox.nearest_nodes

            orig_node = nearest_nodes(G_simple, start[1], start[0])
            dest_node = nearest_nodes(G_simple, end[1], end[0])

            # Try k-shortest simple paths
            paths_gen = nx.shortest_simple_paths(G_simple, orig_node, dest_node, weight='length')
            routes = []
            for path in paths_gen:
                route_nodes = [(G_simple.nodes[n]['y'], G_simple.nodes[n]['x']) for n in path]
                if route_nodes not in routes:  # avoid duplicates
                    routes.append(route_nodes)
                if len(routes) >= max_routes:
                    break

            if routes:
                return routes

        except Exception as e:
            print("OSMnx routing failed:", e)

    # Fallback: simple straight-line alternatives
    return _generate_alternatives(start, end)[:max_routes]
