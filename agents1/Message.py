import enum
import json
import re

from matrx.messages.message import Message


class MessageType(enum.Enum):
    MOVE_TO_ROOM = 0,
    OPEN_DOOR = 1,
    SEARCHING_ROOM = 2,
    FOUND_BLOCK = 3,
    PICK_UP_BLOCK = 5,
    FOUND_GOAL_BLOCK = 4,
    DROP_BLOCK = 6


def extract_block_vis(content):
    vis = re.findall("{.*}", content)
    # vis = vis[0].replace('.', ',')

    vis = json.loads(vis[0])
    return vis


def extract_location(content):
    loc = re.findall("\(.*\)", content)
    loc = loc[0]
    location = [int(loc[1: loc.find(',')]),
                int(loc[loc.find(',') + 2: loc.find(')')])]
    return location


def extract_room(content):
    room_name = re.findall("(room_\d)", content)
    return room_name[0]


class MessageBuilder:

    def __init__(self, agent_name):
        self.agent_name = agent_name

    def create_message(self, mt, room_name=None, block_vis=None, location=None):
        # STANDARD MESSAGES
        if mt is MessageType.OPEN_DOOR:
            msg = "Opening door of " + room_name
        elif mt is MessageType.DROP_BLOCK:
            msg = "Dropped goal block " + block_vis + " at drop location " + location
        elif mt is MessageType.PICK_UP_BLOCK:
            msg = "Picking up goal block " + block_vis + " at location " + location
        elif mt is MessageType.MOVE_TO_ROOM:
            msg = "Moving to " + room_name
        elif mt is MessageType.SEARCHING_ROOM:
            msg = "Searching through " + room_name
        elif mt is MessageType.FOUND_GOAL_BLOCK:
            msg = "Found goal block " + block_vis + " at location " + location

        # NOT STANDARD MESSAGES
        elif mt is MessageType.FOUND_BLOCK:
            msg = "Found block " + block_vis + " at location " + location

        else:
            raise ValueError("not implemented")

        return Message(content=msg, from_id=self.agent_name)

    @staticmethod
    def room_name_str(room_name):
        pass

    @staticmethod
    def block_vis_str(block_vis):
        res = '{' \
              + '"size": ' + str(block_vis['size']) + ", " \
              + '"shape": ' + str(block_vis['shape']) + ", "\
              + '"colour": "' + block_vis['colour'] + "\"" \
              + '}'
        return res

    @staticmethod
    def location_str(location):
        res = '(' + f'{location[0]}, {location[1]})'
        return res

    @staticmethod
    def process_message(msg):
        res = {'from_id': msg.from_id}

        content: str = msg.content

        if content.startswith("Opening door of "):
            res['type'] = MessageType.OPEN_DOOR
            res['room_name'] = extract_room(content)
        if content.startswith("Dropped goal block "):
            res['type'] = MessageType.DROP_BLOCK
            # extract block vis
            res['visualization'] = extract_block_vis(content)
            # extract location
            res['location'] = extract_location(content)
        if content.startswith("Picking up goal block "):
            res['type'] = MessageType.PICK_UP_BLOCK
            res['visualization'] = extract_block_vis(content)
            res['location'] = extract_location(content)
        if content.startswith("Moving to "):
            res['type'] = MessageType.MOVE_TO_ROOM
            res['room_name'] = extract_room(content)
        if content.startswith("Searching through "):
            res['type'] = MessageType.SEARCHING_ROOM
            res['room_name'] = extract_room(content)
        if content.startswith("Found goal block "):
            res['type'] = MessageType.FOUND_GOAL_BLOCK
            res['visualization'] = extract_block_vis(content)
            res['location'] = extract_location(content)
        if content.startswith("Found block "):
            res['type'] = MessageType.FOUND_BLOCK
            res['visualization'] = extract_block_vis(content)
            res['location'] = extract_location(content)

        return res
