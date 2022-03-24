from typing import Dict
from agents1.GenericAgent import GenericAgent
from agents1.Phase import Phase
from agents1.Message import MessageType, MessageBuilder

class ColorblindAgent(GenericAgent):

    def __init__(self, settings:Dict[str,object]):
        super().__init__(settings, Phase.PLAN_PATH_TO_CLOSED_DOOR)


    def initialize_state(self, state):
        super().initialize_state(state)

        for goal_block in self._goal_blocks.values():
            goal_block["visualization"]["colour"] = None

    def filter_observations(self, state):
        """ Sets the colors of the goal blocks to None

        Args:
            state: global state

        Returns:
            filtered state
        """
        for block in state.values():
            if 'class_inheritance' in block and 'CollectableBlock' in block['class_inheritance']:
                block['visualization']['colour'] = None

        return state

    def check_surroundings_for_box(self, state):
        blocks = [(block['visualization'], block['location'], block['obj_id']) for block in state.values() if
                  'class_inheritance' in block and 'CollectableBlock' in block['class_inheritance']]

        # check if any of the found blocks are our goal block
        for block, location, obj_id in blocks:
            for key, goal_block in self._goal_blocks.items():

                if block['shape'] == goal_block['visualization']['shape'] \
                        and block['size'] == goal_block['visualization']['size']:

                    msg = self._mb.create_message(MessageType.FOUND_BLOCK,
                                                  block_vis=block,
                                                  location=location)
                    self._sendMessage(msg)

    def _processMessages(self, teamMembers):
        """
        Process incoming messages and create a dictionary with received messages from each team member.
        If a message with a goal block visualization is received, update the colour of the goal blocks that this agent
        stores.
        """
        receivedMessages = {}
        for member in teamMembers:
            receivedMessages[member] = []

        while len(self.received_messages) != 0:
            msg = self.received_messages.pop(0)
            msg = MessageBuilder.process_message(msg)

            for member in teamMembers:
                if msg['from_id'] == member:
                    # TODO: now, the agent assumes all messages can be trusted
                    # todo: update only if you trust the agent
                    # update goal block location
                    if msg['type'] is MessageType.FOUND_GOAL_BLOCK:
                        # find the goal block
                        for key, goal_block in self._goal_blocks.items():
                            if goal_block["visualization"]["shape"] == msg['visualization']["shape"]\
                                    and goal_block["visualization"]["size"] == msg['visualization']["size"]:
                                self.update_goal_block(key, msg['location'], None)

                                if self._goal_blocks[key]["visualization"]["colour"] is None:
                                    self._goal_blocks[key]["visualization"]["colour"] = msg["visualization"]["colour"]

                    elif msg['type'] is MessageType.MOVE_TO_ROOM \
                            or msg['type'] is MessageType.SEARCHING_ROOM \
                            or msg['type'] is MessageType.OPEN_DOOR:
                        self._com_visited_rooms.add(msg['room_name'])

                    elif msg['type'] is MessageType.DROP_BLOCK:
                        self.drop_block(None)

                    receivedMessages[member].append(msg)

        return receivedMessages