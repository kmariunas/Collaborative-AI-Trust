from typing import Dict
from agents1.GenericAgent import GenericAgent
from agents1.Phase import Phase
from agents1.Message import MessageType, MessageBuilder
from agents1.GenericAgentTesting import GenericAgentTesting
from agents1.TrustSystem import TrustSystem


class ColorblindAgent(GenericAgent):

    def __init__(self, settings: Dict[str, object]):
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


    def initialize_state(self, state):
        """ Initialize team members and read goal blocks
        Args:
            state: state perceived by the agent
        """
        for member in state['World']['team_members']:
            if member != self.agent_name and member not in self._teamMembers:
                self._teamMembers.append(member)

        self._sendMessage(self._mb.create_message(MessageType.CAN_HELP))

        self._goal_blocks = {}

        block_name = "Collect_Block"

        for i in range(0, 3):
            self._goal_blocks[f"block{i}"] = {
                "visualization": state[block_name]['visualization'],
                "location": None,
                "id": None,
                "drop_off": state[block_name]['location']
            }

            self._searching_for = {
                "block": None,
                "visualization": state[block_name]['visualization'],
                "location": None,
                "id": None,
                "drop_off": state[block_name]['location']
            }

            block_name = f"Collect_Block_{i + 1}"

        self.initialize_trust_system()
        self._grid_shape = state['World']['grid_shape']

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
        """
        receivedMessages = {}
        for member in teamMembers:
            receivedMessages[member] = []

        while len(self.received_messages) != 0:
            msg = self.received_messages.pop(0)
            self._messages.add(msg)
            msg = MessageBuilder.process_message(msg)

            for member in teamMembers:
                if msg['from_id'] == member:
                    # TODO: now, the agent assumes all messages can be trusted
                    # todo: update only if you trust the agent
                    if msg['type'] is MessageType.GOAL_BLOCKS:
                        self._goal_blocks = msg["goal_blocks"]
                    # update goal block location
                    elif msg['type'] is MessageType.FOUND_GOAL_BLOCK:
                        # find the goal block
                        for key, goal_block in self._goal_blocks.items():
                            if goal_block['visualization']['shape'] == msg['visualization']['shape'] \
                                    and goal_block['visualization']['size'] == msg['visualization']['size'] \
                                    and goal_block['visualization']['colour'] == msg['visualization']['colour']:
                                self.update_goal_block(key, goal_block['location'], goal_block['id'])

                    elif msg['type'] is MessageType.MOVE_TO_ROOM \
                            or msg['type'] is MessageType.SEARCHING_ROOM \
                            or msg['type'] is MessageType.OPEN_DOOR:
                        self._com_visited_rooms.add(msg['room_name'])

                    elif msg['type'] is MessageType.DROP_BLOCK \
                            and msg['location'] == self._goal_blocks[self._searching_for]['drop_off']:
                        self._phase = Phase.DROP_BLOCK

                    receivedMessages[member].append(msg)

        return receivedMessages