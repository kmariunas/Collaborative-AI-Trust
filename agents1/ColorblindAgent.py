from typing import Dict
from agents1.GenericAgent import GenericAgent
from agents1.Phase import Phase
from agents1.Message import MessageType, MessageBuilder
from agents1.GenericAgentTesting import GenericAgentTesting

class ColorblindAgent(GenericAgent):
    """
    TODO:
        1. Colrblind says he is a helper
        2. lazy now has a pool of agents that can help him carry the blocks
        3. Lazy delegates task to one of the agents
        4. Colorblind says that he is busy
        5. Colorblind carries the block
        6. Once done, says he is available again


        1. Lazy sends a message telling that he needs HELP_CARRY
        2. Colorblind reacts to message by saying I will carry your blocks with the agent name that he is helping
        3. lazy accepts
        3. Lazy understands that he does not need to carry the blocks he finds
        4. Lazy finds a block and sends message CARRY with goal block parameters
        5. Colorblind goes there and takes the block
    """
    def __init__(self, settings:Dict[str,object]):
        super().__init__(settings, Phase.PLAN_PATH_TO_CLOSED_DOOR)
        self.helping = None # the lazy agent we are helping


    def initialize_state(self, state):
        for member in state['World']['team_members']:
            if member != self.agent_name and member not in self._teamMembers:
                self._teamMembers.append(member)

        msg = self._mb.create_message(MessageType.CAN_HELP)
        self._sendMessage(msg)

        self._goal_blocks = {}

        block_name = "Collect_Block"

        for i in range(0, 3):
            self._goal_blocks[f"block{i}"] = {
                "visualization": state[block_name]['visualization'],
                "location": None,
                "id": None,
                "drop_off": state[block_name]['location']
            }

            block_name = f"Collect_Block_{i + 1}"

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
                                self.update_goal_block(key, msg['location'], goal_block['id'])

                    elif msg['type'] is MessageType.MOVE_TO_ROOM \
                            or msg['type'] is MessageType.SEARCHING_ROOM \
                            or msg['type'] is MessageType.OPEN_DOOR:
                        self._com_visited_rooms.add(msg['room_name'])


                    elif msg['type'] is MessageType.DROP_BLOCK:
                        if msg['location'] == self._goal_blocks[self._searching_for[0]]['drop_off']:
                            self._phase = Phase.DROP_BLOCK

                            for key, goal_block in self._goal_blocks.items():
                                if goal_block['drop_off'] == msg['location'] \
                                        and goal_block in self._searching_for:
                                    # remove goal block from searching_for
                                    self._searching_for.remove(goal_block)

                    # elif msg['type'] is MessageType.HELP_CARRY and self.helping is None:
                    #     self.helping = member
                    #     msg = self._mb.create_message(MessageType.HELPING, agent_name=self.helping)
                    #     self._sendMessage(msg)

                    receivedMessages[member].append(msg)

        return receivedMessages