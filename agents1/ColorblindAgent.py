
from typing import Dict
from agents1.GenericAgent import GenericAgent
from agents1.Phase import Phase

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