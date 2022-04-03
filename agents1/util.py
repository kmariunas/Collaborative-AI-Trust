# TODO: doc


def manhattan_distance(point, location):
    return abs(point[0] - location[0]) + abs(point[1] - location[1])


def locations_match(loc1, loc2):
    x1, y1 = loc1
    x2, y2 = loc2
    return x1 == x2 and y1 == y2


def visualizations_match(block1, block2):
    if block1['colour'] is not None and block2['colour'] is not None:
        return block1['colour'] == block2['colour'] \
               and block1['shape'] == block2['shape'] \
               and block1['size'] == block2['size']
    else:
        return block1['shape'] == block2['shape'] \
               and block1['size'] == block2['size']


def rooms_match(last_message, msg):
    if last_message['room_name'] != msg['room_name']:
        return False
    return True
