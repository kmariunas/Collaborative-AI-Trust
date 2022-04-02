import random
from typing import Dict

from matrx.agents.agent_utils.state import State

from agents1.GenericAgent import GenericAgent
from agents1.GenericAgentTesting import GenericAgentTesting
from agents1.Message import MessageBuilder
from agents1.Phase import Phase

class LiarAgent(GenericAgentTesting):

    def __init__(self, settings:Dict[str,object]):
        super().__init__(settings, Phase.PLAN_PATH_TO_CLOSED_DOOR)
        self._lying_prob = 0.80

    def initialize_state(self, state):
        """ Initialize team members and read goal blocks

        Args:
            state: state perceived by the agent
        """
        for member in state['World']['team_members']:
            if member != self.agent_name and member not in self._teamMembers:
                self._teamMembers.append(member)

        self._goal_blocks = {}

        block_name = "Collect_Block"

        for i in range(0, 3):
            self._goal_blocks[f"block{i}"] = {
                "visualization": state[block_name]['visualization'],
                "location": [],
                "id": [],
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

        self._grid_shape = state['World']['grid_shape']

    def lie_message(self, message):
        """
            generates a random lie based on the message received

        Args:
            message: str that MessageBuilder can process

        Note:
            This method can only change:
            - room name
            - block shape
            - block colour
            - location

        Returns:
            Message
        """

        content = MessageBuilder.process_message(message)
        keys = list(content.keys())

        if 'room_name' in keys:
            content['room_name'] = f'room_{(int(content["room_name"][-1]) + random.randint(1, 9)) % 9}'  # increment the room

        if 'visualization' in keys:
            # change colour to some other colour that could be found in goal blocks
            goal_block_shapes = list(map(lambda block: block['visualization']['shape'], self._goal_blocks.values()))
            goal_block_shapes.remove(content['visualization']['shape'])

            if goal_block_shapes is not None:
                content['visualization']['shape'] = random.choice(goal_block_shapes)

            # change shape to some other shape in the goal blocks
            goal_block_colours = list(map(lambda block: block['visualization']['colour'], self._goal_blocks.values()))
            goal_block_colours.remove(content['visualization']['colour'])

            if goal_block_colours is not None:
                content['visualization']['colour'] = random.choice(goal_block_colours)

        if 'location' in keys:
            content['location'] = [random.randint(0, self._grid_shape[0]), random.randint(0, self._grid_shape[1])]

        return self._mb.create_message(mt=content['type'],
                                      room_name=content.get('room_name'),
                                      block_vis=content.get('visualization'),
                                      location=content.get('location'))

    def _sendMessage(self, msg):
        '''
        Enable sending messages in one line of code
        '''
        if msg is None:
            return

        # if msg.content not in self.received_messages:
        if random.uniform(0, 1) < self._lying_prob:
            print("lied")
            msg = self.lie_message(msg)

        print("Liar:", msg.content)

        return self.send_message(msg)

    def find_action(self, state: State):
        # check if the next goal_block has been located
        #next_block_id = min(int(self._searching_for[5]) + 1, 2)  # increment current block
        #searching_next = f"block{next_block_id}"
        if len(self._is_carrying)==1:
            return Phase.PLAN_PATH_TO_DROP

        found_goal_blocks = 0
        for block in self._not_found_yet:
            if(len(self._goal_blocks[block]['location'])!=0):
                found_goal_blocks +=1

        if found_goal_blocks != 0 and len(self._is_carrying) == 0:
            # pick it up if you're not carrying anything already
            self.find_best_path(state)
            return Phase.PLAN_PATH_TO_BLOCK

        # find closed door that none of the agents searched
        if len(self.find_doors(state, open=False, filter='everyone')) != 0:
            self._filter = 'everyone'
            return Phase.PLAN_PATH_TO_CLOSED_DOOR

        # find closed doors that the agent has not searched
        if len(self.find_doors(state, open=False, filter='agent')) != 0:
            self._filter = 'agent'
            return Phase.PLAN_PATH_TO_CLOSED_DOOR

        # find open door that the agent has not searched
        if len(self.find_doors(state, open=True, filter='agent')) != 0:
            self._filter = 'agent'
            return Phase.PLAN_PATH_TO_OPEN_DOOR

        # find random open door
        # TODO: could replace with an 'explore' action
        if len(self.find_doors(state, open=True, filter='none')) != 0:
            self._filter = 'none'
            return Phase.PLAN_PATH_TO_OPEN_DOOR



