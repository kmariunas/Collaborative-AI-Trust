import random
from typing import Dict

from agents1.GenericAgent import GenericAgent
from agents1.Phase import Phase


class LazyAgent(GenericAgent):

    def __init__(self, settings: Dict[str, object]):
        super().__init__(settings, Phase.PLAN_PATH_TO_CLOSED_DOOR)
        self._finish_action = None

    def search_room(self, state):
        """ After each search agent moves to the waypoint given by @plan_room_search.

        Args:
            state: matrx state perceived by the agent.

        Note:
            Once the agent searches the entire room, if it has found a block it is looking for, it will set the phase
            to phase, otherwise the agent sets it to planb_phase

        Returns: Movement action .

        """
        if self.abandon_action(abandon_this_step_prob=0.7):
            # print('--- abandon ---')
            self.update_phase(None)
            return None, {}

        action, _ = super().search_room(state)

        if action is None:
            self._finish_action = None

        return action, _

    def follow_path(self, state, phase):
        """ Moves the agent towards the destination set in the navigator,
        with a 50% probability of abandoning the action.

        Args:
            state: matrx state perceived by the agent
            phase: Phase of the agent after arriving to the desired destination

        Returns: action towards the destination, or None if the agent has already arrived
        """
        if self.abandon_action(abandon_this_step_prob=0.3):
            # print('--- abandon ---')
            # drop block if agent is carrying one
            if self._phase is Phase.RETURN_GOAL_BLOCK:
                return self.drop_block(None, state, block_delivered=False)
            self.update_phase(None)
            return None, {}

        action, _ = super().follow_path(state, phase)

        return action, _

    def find_action(self, state):
        # TODO: update this stuff
        """
        Method returns an action, different from the previous one, based on the following ranking:
            1. if agent is carrying goal block, deliver it
            1. if goal block has been located, start going in its direction
            2. if there are any closed doors that no one has explored, explore them
            3. if there are any closed doors that the agent has not explored, explore them
            4. if there are any rooms that the agent has not explored, explore them
            5. explore random room
        """
        # if agent is carrying a block, deliver it
        if len(self._is_carrying) == 1:
            return Phase.PLAN_PATH_TO_DROP

        # if all the blocks have been delivered, rearrange them
        if len(self._searching_for) == 0:
            self._fix_block_order = True
            return Phase.PLAN_PATH_TO_DROP

        # if the next block has been located, start going in its direction
        # if the previous action was not delivering the goal block to its location
        if self._goal_blocks[self._searching_for[0]]['location'] \
                and self._previous_phase is not Phase.RETURN_GOAL_BLOCK:
            return Phase.PLAN_PATH_TO_BLOCK

        if len(self.find_doors(state, open=False, filter='everyone')) != 0:
            self._filter = 'everyone'
            return Phase.PLAN_PATH_TO_CLOSED_DOOR

        if len(self.find_doors(state, open=False, filter='agent')) != 0:
            self._filter = 'agent'
            return Phase.PLAN_PATH_TO_CLOSED_DOOR

        if len(self.find_doors(state, open=True, filter='agent')) != 0:
            self._filter = 'agent'

        else:
            self._filter = 'none'
        return Phase.PLAN_PATH_TO_OPEN_DOOR

    def plan_path_to_closed_door(self, state, phase):
        """ Finds doors that are still closed and plans a path to them
        Note: returns a random door

                Args:
                    state: perceived state by the agent
                    phase: Next phase after successfully finding closed door

                Returns:
                    None, {}
                """
        closed_doors = self.find_doors(state, open=False, filter=self._filter)

        self._door = random.choice(closed_doors)
        doorLoc = self._door['location']
        # Location in front of door is south from door
        doorLoc = doorLoc[0], doorLoc[1] + 1
        # Send message of current action

        return self.plan_path(doorLoc, phase)

    def plan_path_to_open_door(self, state, phase):
        """ Finds opened door that haven't been visited and plans a path to that door
        Note: returns a random door

        Args:
            state: Matrx state perceived by the agent
            phase: Next phase after successful plan

        Note:
            After successfully finding open and unvisited door this method changes the phase to phase

        Returns: None, {}
        """
        open_doors = self.find_doors(state, open=True, filter=self._filter)

        # look for random door
        self._door = random.choice(open_doors)
        doorLoc = self._door['location']
        # Location in front of door is south from door
        doorLoc = doorLoc[0], doorLoc[1] + 1

        return self.plan_path(doorLoc, phase)

    def abandon_action(self, abandon_this_step_prob=0.3):
        """
        Method returns true if agent abandons this action.
        Note: method updates and `finish_action` to None if the agent should abandon action.

        @param abandon_this_step_prob: probability to abandon current action at this time stamp.
        @return bool: True if agent should abandon action, False otherwise
        """
        if self._finish_action is None:
            if random.uniform(0, 1) < 0.5:
                print('-- finish action --')
                self._finish_action = True
            else:
                print('-- will not finish action --')
                self._finish_action = False

        if self._finish_action is False:
            if random.uniform(0, 1) < abandon_this_step_prob:
                print('--- abandon now --')
                # stop following path
                self._finish_action = None
                return True
        return False

    def update_phase(self, phase):
        self._finish_action = None
        self._previous_phase = self._phase
        self._phase = phase
