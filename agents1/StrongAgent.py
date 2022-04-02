import random
from typing import Dict

import numpy as np
from matrx.actions.object_actions import GrabObject, DropObject
from matrx.agents.agent_utils.state import State

from agents1.GenericAgent import GenericAgent
from agents1.GenericAgentTesting import GenericAgentTesting
from agents1.Message import MessageType
from agents1.Phase import Phase
from agents1.util import manhattan_distance


class StrongAgent(GenericAgentTesting):

    def __init__(self, settings: Dict[str, object]):
        super().__init__(settings, None)

    def find_action(self, state: State):
        # check if the next goal_block has been located
        # next_block_id = min(int(self._searching_for[5]) + 1, 2)  # increment current block
        # searching_next = f"block{next_block_id}"
        if len(self._is_carrying) == 2 or len(self._not_found_yet) == 0:
            return Phase.PLAN_PATH_TO_DROP

        found_goal_blocks = 0
        for block in self._not_found_yet:
            if (len(self._goal_blocks[block]['location']) != 0):
                found_goal_blocks += 1

        if found_goal_blocks != 0:
            # pick it up if you're not carrying anything already
            if len(self._is_carrying) == 0:
                self.find_best_path_multiple_blocks(state)
                return Phase.PLAN_PATH_TO_BLOCK

            # if you're only carrying one other block,  find another block
            if len(self._is_carrying) == 1 and found_goal_blocks >= 1:
                self.find_best_path(state)
                return Phase.PLAN_PATH_TO_BLOCK

        # if agent is carrying other block, deliver it

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
        location = self._searching_for["location"]
        if self._fix_block_order:
            # print("hello")

            if Phase.FOLLOW_PATH_TO_BLOCK == self._phase:
                res = self.follow_path(state, Phase.GRAB_BLOCK)
            elif Phase.GRAB_BLOCK == self._phase and state[self.agent_name]['location'] != self._goal_blocks["block0"][
                "drop_off"]:

                res = self.grab_block(Phase.DROP_BLOCK, state)
            elif Phase.DROP_BLOCK == self._phase:
                res = self.drop_block(Phase.PLAN_PATH_TO_BLOCK)
            else:
                block = self._blocks_to_fix.get()
                # self._block_to_fix_id = id
                res = self.plan_path(self._goal_blocks[block]["drop_off"], Phase.FOLLOW_PATH_TO_BLOCK)
        elif Phase.PLAN_PATH_TO_BLOCK == self._phase:
            # print("location")
            # print(location)
            res = self.plan_path(location, Phase.FOLLOW_PATH_TO_BLOCK)

        elif Phase.GRAB_BLOCK == self._phase:
            res = self.grab_block(None, state)
            msg = self._mb.create_message(MessageType.PICK_UP_BLOCK,
                                          block_vis=self._searching_for['visualization'],
                                          location=self._searching_for['location'])

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
                    # if key == self._searching_for:
                    #    self._grab_block = self._searching_for

                    self._goal_blocks[key]['location'].append(location)
                    self._goal_blocks[key]['id'].append(obj_id)

                    msg = self._mb.create_message(MessageType.FOUND_GOAL_BLOCK,
                                                  block_vis=self._goal_blocks[key]["visualization"],
                                                  location=location)
                    self._sendMessage(msg)

        # def grab_block(self, obj_id, phase):
        """ Grabs block

        Args:
            obj_id: id of the object the agent has to grab
            phase: Next phase after grabbing a block

        Returns:
            GrabObject Action
        """

    #     self._phase = phase

    # blocks = [key for key, block in self._goal_blocks.items() if block['id'] == obj_id]
    #     self._is_carrying.add(self._searching_for["block"])

    #     return GrabObject.__name__, {'object_id': obj_id}
    def drop_block(self, phase, block_delivered=True):

        action = None
        if block_delivered and len(self._is_carrying) > 0:
            block, id = self._is_carrying.pop()
            self._currently_dropping = block
            # self._blocks_to_fix.put((int(block[5]), id))
            action = DropObject.__name__, {'object_id': id}
            if len(self._not_found_yet) == 0:
                self._fix_block_order = True

            # block_num = min(2, int(self._searching_for[5]) + 1)
            # self._searching_for = f"block{block_num}"
        if len(self._is_carrying) > 0:
            self.update_phase(Phase.PLAN_PATH_TO_DROP)
        else:
            self.update_phase(phase)
        return action

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

    def find_best_path_multiple_blocks(self, state):
        total_blocks_to_look_for = 0
        not_found_yet = self._not_found_yet.copy()
        for block in self._not_found_yet:
            if len(self._goal_blocks[block]["location"]) != 0:
                total_blocks_to_look_for += 1
            else:
                not_found_yet.discard(block)
        # not_found_yet.discard(to_remove)
        if total_blocks_to_look_for == 3:
            block_key_permutations = [[0, 1], [0, 2], [1, 2], [1, 0], [2, 0], [2, 1]]
        elif total_blocks_to_look_for == 2:
            block_key_permutations = [[0, 1], [1, 0]]
        else:
            return self.find_best_path(state)
        minDistance = 1000000
        agent_loc = state[self.agent_name]['location']
        not_found_yet_list = list(not_found_yet)

        for permutation in block_key_permutations:
            # print(self._goal_blocks[not_found_yet_list[permutation[0]]]["location"])
            # print(self._goal_blocks[not_found_yet_list[permutation[1]]]["location"])
            block0 = not_found_yet_list[permutation[0]]
            block1 = not_found_yet_list[permutation[1]]
            combinations_index_0 = np.arange(len(self._goal_blocks[block0]["location"]))
            combinations_index_1 = np.arange(len(self._goal_blocks[block1]["location"]))
            goal_block_combinations = np.array(np.meshgrid(combinations_index_0,
                                                           combinations_index_1)).T.reshape(-1, 2)
            # print(goal_block_combinations)
            for goal_block_combination in goal_block_combinations:
                block = not_found_yet_list[0]
                drop_loc = self._goal_blocks[block]["drop_off"]

                # print(goal_block_combination)
                # print(self._goal_blocks[block0]['location'])
                # print(self._goal_blocks[block0]['location'][goal_block_combination[0]])
                distance = manhattan_distance(agent_loc,
                                              self._goal_blocks[block0]['location'][goal_block_combination[0]]) \
                           + manhattan_distance(self._goal_blocks[block0]['location'][goal_block_combination[0]],
                                                self._goal_blocks[block1]['location'][goal_block_combination[1]]) \
                           + manhattan_distance(self._goal_blocks[block1]['location'][goal_block_combination[1]],
                                                drop_loc)
                if distance < minDistance:
                    minDistance = distance

                    self._searching_for["block"] = block0
                    self._searching_for["location"] = self._goal_blocks[block0]['location'][goal_block_combination[0]]
                    # print(self._searching_for['location'])
                    # index = np.argwhere(self._goal_blocks[block]["location"] == goal_block_combination[0])
                    # self._searching_for["id"] = self._goal_blocks[block]["id"][index]
                    self._searching_for["drop_off"] = drop_loc
