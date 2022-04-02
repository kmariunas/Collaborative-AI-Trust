# TODO: doc


def manhattan_distance(point, location):
    return abs(point[0] - location[0]) + abs(point[1] - location[1])


def locations_match(loc1, loc2):
    x1, y1 = loc1
    x2, y2 = loc2
    return x1 == x2 and y1 == y2


def visualizations_match(viz1, viz2):
    return viz1['shape'] == viz2['shape'] and viz1['size'] == viz2['size'] and viz1['colour'] == viz2['colour']
