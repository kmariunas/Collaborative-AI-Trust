import enum
import json
import re

from matrx.messages.message import Message


class MessageType(enum.Enum):
    """
    Enum for implemented message types
    """
    MOVE_TO_ROOM = 0,
    OPEN_DOOR = 1,
    SEARCHING_ROOM = 2,
    FOUND_BLOCK = 3,
    PICK_UP_BLOCK = 5,
    FOUND_GOAL_BLOCK = 4,
    DROP_BLOCK = 6


def extract_block_vis(content):
    """
    Takes in message content and returns the block visualization (if message contains it).
    """
    vis = re.findall("{.*}", content)  # find block visualization

    vis = json.loads(vis[0])  # cast string to dict
    return vis


def extract_location(content):
    """
    Takes in message content and returns the location (if message contains it).
    """
    loc = re.findall("\(.*\)", content)  # find location
    loc = loc[0]
    location = (int(loc[1: loc.find(',')]),
                int(loc[loc.find(',') + 2: loc.find(')')]))  # parse string to list
    return location


def extract_room(content):
    """
    Takes in message content and returns the room name (if message contains it).
    """
    room_name = re.findall("(room_\d)", content)
    return room_name[0]


def block_vis_str(block_vis):
    """
    Method takes in block visualization and returns the correct string representation.
    """
    if block_vis is None:
        return None
    res = '{' \
          + '"size": ' + str(block_vis["size"]) + ", " \
          + '"shape": ' + str(block_vis["shape"]) + ", " \
          + '"colour": "' + str(block_vis["colour"]) + "\"" \
          + '}'
    return res


def location_str(location):
    """
    Method takes in location and returns the correct string representation.
    """
    if location is None:
        return None

    res = '(' + f'{location[0]}, {location[1]})'
    return res


class MessageBuilder:
    """
    Class for sending and reading messages following the communication protocol mentioned in the assignment. To
    create new messages, make sure to add a new MessageType, and implement the create_message and process_message
    methods.

    Implemented custom messages:
    * FOUND_BLOCK: "Found block [block_vis] at location [location]"
    """

    def __init__(self, agent_name):
        self.agent_name = agent_name

    def create_message(self, mt, room_name=None, block_vis=None, location=None):
        """
        Method returns a matrx Message object with a string content built with the passed parameters

        @param mt: MessageType
        @param room_name: str, thr room name (ie: room_3)
        @param block_vis: a dictionary as the one used in the BW4TBaselineAgent to store the block visualization.
            Dict must contain 'size', 'colour', and 'shape' keys and values
        @param location: list with coordinates (ie: [8, 8])

        @return: matrx Message.
        """

        block_vis = block_vis_str(block_vis)
        location = location_str(location)

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
    def process_message(msg):
        """
        Method takes in matrx Message and parses the content into a dictionary
        @param msg: matrx Message
        @return dict: {
                        'from_id': id the sender agent,
                        'type': MessageType,
                        'room_name': room name mentioned in the message,
                        'visualization': block visualization dict with keys: {'size', 'shape', 'colour'},
                        'location': location (list) mentioned in the message
                    }
        """
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
