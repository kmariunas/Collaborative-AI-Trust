import random
from typing import Dict

from matrx.actions.object_actions import GrabObject
from matrx.agents.agent_utils.state import State

from agents1.GenericAgent import GenericAgent
from agents1.Message import MessageType
from agents1.Phase import Phase
from agents1.util import manhattan_dist


class StrongAgent(GenericAgent):

    def __init__(self, settings: Dict[str, object]):
        super().__init__(settings, None)
        self._grab_block = None
        self._is_carrying = set()

    def find_action(self, state: State):
        # check if the next goal_block has been located
        next_block_id = min(int(self._searching_for[5]) + 1, 2)  # increment current block
        searching_next = f"block{next_block_id}"
        if searching_next is not self._searching_for \
                and self._goal_blocks[searching_next]['location'] is not None \
                and searching_next not in self._is_carrying:
            # pick it up if you're not carrying anything already
            if len(self._is_carrying) == 0:
                self._grab_block = searching_next
                return Phase.PLAN_PATH_TO_BLOCK

            # if you're only carrying one other block, aka you're delivering it already
            if len(self._is_carrying) == 1:
                # pick this block up only if it is closer than the goal location
                agent_loc = state[self.agent_name]['location']
                if manhattan_dist(agent_loc, self._goal_blocks[searching_next]['location']) \
                        <= manhattan_dist(agent_loc, self._goal_blocks[self._searching_for]['drop_off']):
                    self._grab_block = searching_next
                    return Phase.PLAN_PATH_TO_BLOCK

        # if agent is carrying other block, deliver it
        if self._searching_for in self._is_carrying:
            return Phase.PLAN_PATH_TO_DROP

        # check if a goal block has been located
        if self._goal_blocks[self._searching_for]['location'] is not None \
                and self._searching_for not in self._is_carrying:
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

    def phase_action(self, state):
        res, msg = None, None
        if Phase.PLAN_PATH_TO_BLOCK == self._phase:
            res = self.plan_path(self._goal_blocks[self._grab_block]["location"], Phase.FOLLOW_PATH_TO_BLOCK)

        elif Phase.GRAB_BLOCK == self._phase:
            res = self.grab_block(self._goal_blocks[self._grab_block]["id"], None)
            msg = self._mb.create_message(MessageType.PICK_UP_BLOCK,
                                          block_vis=self._goal_blocks[self._grab_block]['visualization'],
                                          location=self._goal_blocks[self._grab_block]['location'])

        if res is None:
            res, msg = super().phase_action(state)

        return res, msg

    def check_surroundings_for_box(self, state):
        blocks = [(block['visualization'], block['location'], block['obj_id']) for block in state.values() if
                  'class_inheritance' in block and 'CollectableBlock' in block['class_inheritance']]

        # check if any of the found blocks are our goal block
        for block, location, obj_id in blocks:
            for key, goal_block in self._goal_blocks.items():

                if block['colour'] == goal_block['visualization']['colour'] \
                        and block['shape'] == goal_block['visualization']['shape'] \
                        and block['size'] == goal_block['visualization']['size']:

                    if key == self._searching_for:
                        self._grab_block = self._searching_for

                    self._goal_blocks[key]['location'] = location
                    self._goal_blocks[key]['id'] = obj_id

                    msg = self._mb.create_message(MessageType.FOUND_GOAL_BLOCK,
                                                  block_vis=self._goal_blocks[key]["visualization"],
                                                  location=location)
                    self._sendMessage(msg)

    def grab_block(self, obj_id, phase):
        """ Grabs block

        Args:
            obj_id: id of the object the agent has to grab
            phase: Next phase after grabbing a block

        Returns:
            GrabObject Action
        """
        self._phase = phase

        blocks = [key for key, block in self._goal_blocks.items() if block['id'] == obj_id]
        self._is_carrying.add(blocks[0])

        return GrabObject.__name__, {'object_id': obj_id}

    def plan_path_to_closed_door(self, state, phase):
        """ Finds doors that are still closed and plans a path to them
        Note: returns a random door
                Args:
                    state: perceived state by the agent
                    phase: Next phase after successfuly finding closed door
                Returns:
                    None, {}
                """
        closed_doors = self.find_doors(state, open=False, filter=self._filter)

        if len(closed_doors) == 0:
            self._phase = None
            return None, {}

        self._door = random.choice(closed_doors)
        doorLoc = self._door['location']
        # Location in front of door is south from door
        doorLoc = doorLoc[0], doorLoc[1] + 1
        # Send message of current action

        return self.plan_path(doorLoc, phase)
