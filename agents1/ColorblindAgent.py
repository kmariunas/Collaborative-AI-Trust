from asyncio import Queue
from typing import Dict

from agents1 import util
from agents1.GenericAgent import GenericAgent
from agents1.Message import MessageType
from agents1.Phase import Phase


class ColorblindAgent(GenericAgent):
    """
    TODO:
        1. Colorblind says he is a helper
        2. lazy now has a pool of agents that can help him carry the blocks
        3. Lazy delegates task to one of the agents
        4. Colorblind says that he is busy
        5. Colorblind carries the block
        6. Once done, says he is available again

    """
    def __init__(self, settings:Dict[str,object]):
        super().__init__(settings, Phase.PLAN_PATH_TO_CLOSED_DOOR)
        self.helping = None # the lazy agent we are helping
        self.delegated_tasks = Queue()
        self._searching_for = []

    def initialize_state(self, state):
        """ Initialize team members and read goal blocks

        Args:
            state: state perceived by the agent
        """
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

    def find_action(self, state):

        if not self.delegated_tasks.empty() and len(self._is_carrying) == 0: # if we have some delegated tasks (for now picking up blocks) we do that
            task = self.delegated_tasks.get_nowait()

            self._searching_for = [task["searching_for"]]
            self.plan_path(task["location"], None)

            self.delegated_tasks.task_done()

            return Phase.FOLLOW_PATH_TO_BLOCK
        else:
            return super().find_action(state)

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

    def _processMessages(self, received_messages):
        """
        Process incoming messages and create a dictionary with received messages from each team member.
        """
        for messages in received_messages.values():
            for msg in messages:
                if msg['type'] is MessageType.GOAL_BLOCKS:
                    for key, goal_block in msg["goal_blocks"].items():
                        self._goal_blocks[key]["visualization"]["colour"] = goal_block["visualization"]["colour"]

                if self.trust_system.trust_message(msg):
                    # update goal block location
                    if msg['type'] is MessageType.FOUND_GOAL_BLOCK:
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
                        if len(self._searching_for) == 0:
                            continue
                        ###
                        if msg['location'] == self._goal_blocks[self._searching_for[0]]['drop_off']:
                            self._phase = Phase.DROP_BLOCK

                            for key, goal_block in self._goal_blocks.items():
                                if goal_block['drop_off'] == msg['location'] \
                                        and goal_block in self._searching_for:
                                    # remove goal block from searching_for
                                    self._searching_for.remove(goal_block)

                    elif msg['type'] is MessageType.HELP_CARRY:
                        if self._phase != Phase.DROP_BLOCK and self._phase != Phase.GRAB_BLOCK\
                            and self._phase != Phase.PLAN_PATH_TO_BLOCK and self._phase != Phase.FOLLOW_PATH_TO_BLOCK \
                                and self._phase != Phase.PLAN_PATH_TO_DROP and self._phase != Phase.RETURN_GOAL_BLOCK:
                            self._phase = None

                        for key, block in self._goal_blocks.items():
                            if util.visualizations_match(block["visualization"], msg['block_vis']):
                                # if key is not None and key != self._searching_for[0]:
                                if self._goal_blocks[key]["id"] is None:
                                    self._goal_blocks[key]["id"] = msg["block_id"]
                                    self._goal_blocks[key]["location"] = msg["location"]

                                    task = {
                                        'location': msg['location'],
                                        'block_id': msg['block_id'],
                                        'block_vis': msg['block_vis'],
                                        "searching_for": key
                                    }
                                    self.delegated_tasks.put_nowait(task)
                                    break
