
from typing import Dict
from agents1.GenericAgent import GenericAgent
from agents1.Phase import Phase
from agents1.Message import MessageType

class ColorblindAgent(GenericAgent):

    def __init__(self, settings:Dict[str,object]):
        super().__init__(settings, Phase.PLAN_PATH_TO_CLOSED_DOOR)


    def initialize_state(self, state):
        super().initialize_state(state)

        for goal_block in self._goal_blocks.values():
            goal_block["visualization"]["colour"] = None

    def filter_observations(self, state):
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