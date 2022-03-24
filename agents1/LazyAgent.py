import random
from typing import Dict

from agents1.GenericAgent import GenericAgent
from agents1.Phase import Phase


class LazyAgent(GenericAgent):

    def __init__(self, settings: Dict[str, object]):
        super().__init__(settings, Phase.PLAN_PATH_TO_CLOSED_DOOR)
        self._finish_action = None

    def search_room(self, state, phase):
        """ After each search agent moves to the waypoint given by @plan_room_search.

        Args:
            state: matrx state perceived by the agent.
            phase: Next phase if the goal block is found in the room

        Note:
            Once the agent searches the entire room, if it has found a block it is looking for, it will set the phase
            to phase, otherwise the agent sets it to planb_phase

        Returns: Movement action .

        """
        if self.abandon_action(abandon_this_step_prob=0.6):
            self.update_phase(None)
            return None, {}

        action, _ = super().search_room(state, phase)

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
            # drop block if agent is carrying one
            if self._phase is Phase.RETURN_GOAL_BLOCK:
                return self.drop_block(None, block_delivered=0)
            self.update_phase(None)
            return None, {}

        action, _ = super().follow_path(state, phase)

        return action, _

    def find_action(self, state):
        """
        Method returns an action, different from the previous one, based on the following ranking:
            1. if you're carrying a goal block that has already been delivered, drop the block
            1. if goal block has been located, start going in its direction
            2. if there are any closed doors that no one has explored, explore them
            3. if there are any closed doors that the agent has not explored, explore them
            4. if there are any rooms that the agent has not explored, explore them
            5. explore random room
        """
        # if you're carrying a block that has been delivered already, drop that block
        if len(self._is_carrying) != 0 and self._searching_for not in self._is_carrying:
            return Phase.DROP_BLOCK

        # check if a goal block has been located
        # make sure that agent does not repeat the same action
        if self._goal_blocks[self._searching_for]["location"] is not None \
                and self._previous_phase is not Phase.RETURN_GOAL_BLOCK \
                and self._previous_phase is not Phase.GRAB_BLOCK:
            return Phase.PLAN_PATH_TO_BLOCK

        if len(self.find_doors(state, open=False, filter='everyone')) != 0:
            self._filter = 'everyone'
            return Phase.PLAN_PATH_TO_CLOSED_DOOR

        if len(self.find_doors(state, open=False, filter='agent')) != 0:
            self._filter = 'agent'
            return Phase.PLAN_PATH_TO_CLOSED_DOOR

        if len(self.find_doors(state, open=True, filter='agent')) != 0:
            self._filter = 'agent'

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

        # if len(closed_doors) == 0:
        #     self._phase = None
        #     return None, {}

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
                self._finish_action = True
            else:
                self._finish_action = False

        if self._finish_action is False:
            if random.uniform(0, 1) < abandon_this_step_prob:
                # stop following path
                self._finish_action = None
                print("--- abandon action ---")

                return True
        return False
