from typing import final, List, Dict, Final
import enum, random
from bw4t.BW4TBrain import BW4TBrain
from matrx.agents.agent_utils.state import State
from matrx.agents.agent_utils.navigator import Navigator
from matrx.agents.agent_utils.state_tracker import StateTracker
from matrx.actions.door_actions import OpenDoorAction
from matrx.actions.object_actions import GrabObject, DropObject
from matrx.messages.message import Message


class Phase(enum.Enum):
    # TODO: change weights
    PLAN_PATH_TO_CLOSED_DOOR = 1,
    FOLLOW_PATH_TO_CLOSED_DOOR = 2,
    OPEN_DOOR = 3
    PLAN_PATH_TO_OPEN_DOOR = 1,
    FOLLOW_PATH_TO_OPEN_DOOR = 2,
    PLAN_ROOM_SEARCH = 3,
    SEARCH_ROOM = 4,
    PLAN_PATH_TO_BLOCK = 5
    FOLLOW_PATH_TO_BLOCK = 6,
    GRAB_BLOCK = 7,
    PLAN_PATH_TO_DROP = 8,
    RETURN_GOAL_BLOCK = 9,
    DROP_BLOCK = 10


class LazyAgent(BW4TBrain):
    # TODO: do agents share all of the observations, or can we choose what to share? | technically yes, but then colorblind anmd liar could not solve the problem
    # TODO: Are room sizes fixed? | layout the same, (map size, room size)
    # TODO: do we have to implement the filter_bw4t_observations? No, just set the attribute to None
    # TODO: where should we get the goal blocks, can I get them from state or do I have to go down and observe them ? We can observe them in the state

    # TODO: Do we want our liar to communicate or not?

    def __init__(self, settings: Dict[str, object]):
        super().__init__(settings)
        self.agent_name = None
        self._previous_phase = None
        self._phase = None
        self._teamMembers = []
        self._goal_blocks = None
        self._searching_for = "block0"
        self._finish_action = None

    def initialize(self):
        super().initialize()
        self._state_tracker = StateTracker(agent_id=self.agent_id)
        self._navigator = Navigator(agent_id=self.agent_id,
                                    action_set=self.action_set, algorithm=Navigator.A_STAR_ALGORITHM)

    def filter_bw4t_observations(self, state):
        return state

    def follow_path(self, state, phase):
        """ Moves the agent towards the destination set in the navigator,
        with a 50% probability of abandoning the action.

        Args:
            state: matrx state perceived by the agent
            phase: Phase of the agent after arriving to the desired destination

        Returns: action towards the destination, or None if the agent has already arrived
        """
        if self._finish_action is None:
            if random.uniform(0, 1) < 0.5:
                print("finish action")
                self._finish_action = True
            else:
                print("dont finish action")
                self._finish_action = False

        if self._finish_action is False:
            if random.uniform(0, 1) < 0.3:
                print("--- ABORTED ACTION ---")

                # stop following path
                self._finish_action = None

                # drop block if agent is carrying one
                if self._phase is Phase.RETURN_GOAL_BLOCK:
                    return self.drop_block(block_delivered=0)

                return None, {}

        self._state_tracker.update(state)
        # Follow path to door
        action = self._navigator.get_move_action(self._state_tracker)
        if action != None:
            return action, {}

        self.update_phase(phase)

        self._finish_action = None
        return None, {}

    def plan_path(self, coord, phase):
        """ adds new waypoints to the navigator, sets the following phase

        Args:
            coord: Coordinates that the agent has to visit
            phase: New phase of the agent

        Returns: None, {}

        """
        if not isinstance(coord, list):
            coord = [coord]

        self._navigator.reset_full()
        # add waypoint to the block
        self._navigator.add_waypoints(coord)

        # follow path to block
        self.update_phase(phase)

        return None, {}

    def plan_path_to_open_door(self, state, phase):
        """ Finds opened door that haven't been visited and plans a path to that door

        Args:
            state: Matrx state perceived by the agent

        Note:
            After successfully finding open and unvisited door this method changes the phase to FOLLOW_PATH_TO_OPEN_DOOR

        Returns: None, {}
        """
        open_doors = self.find_doors(state, open=True)

        if len(open_doors) == 0:
            return None, {}

        # Randomly pick a open door
        # TODO: look for closest doors?
        self._door = random.choice(open_doors)
        doorLoc = self._door['location']
        # Location in front of door is south from door
        doorLoc = doorLoc[0], doorLoc[1] + 1

        # Send message of current action
        self._sendMessage('Moving to ' + self._door['room_name'], self.agent_name)

        return self.plan_path(doorLoc, phase)

    def plan_room_search(self, state, phase):
        """ Adds waypoints to the navigator to search the whole room.

        Args:
            state:matrx state perceived by the agent.

        Note:
            Coordinates of the tiles the agent must visit are designed for 4x2 rooms.
            Assumes that agent is standing bellow the door.

        Returns: None, {}
        """
        # get agent location
        agent_x, agent_y = state[self.agent_name]['location']

        # create coordinates that we have to visit to search the room
        above_doors = agent_x, agent_y - 2
        right = agent_x + 1, agent_y - 2
        left = agent_x - 1, agent_y - 2
        left_left = agent_x - 2, agent_y - 2

        return self.plan_path([above_doors, right, left, left_left], phase)

    def search_room(self, state, phase):
        """ Looks for any blocks in radius of the agent, if blocks match any goal block, records it's location and id.
            After each search agent moves to the waypoint given by @plan_room_search.

        Args:
            state: matrx state perceived by the agent.

        Note:
            Once the agent searches the entire room, if it has found a block it is looking for, it will set the phase
            to PLAN_PATH_TO_BLOCK, otherwise the agent looks for other rooms with phase PLAN_PATH_TO_OPEN_DOOR.

        Returns: Movement action .

        """

        # TODO: documentation
        if self._finish_action is None:
            if random.uniform(0, 1) < 0.5:
                print("finish action")
                self._finish_action = True
            else:
                print("dont finish action")
                self._finish_action = False

        if self._finish_action is False:
            if random.uniform(0, 1) < 0.6:
                # abandon action
                self._finish_action = None
                return None, {}

        self._state_tracker.update(state)

        action = self._navigator.get_move_action(self._state_tracker)
        blocks = [(block['visualization'], block['location'], block['obj_id']) for block in state.values() if
                  'class_inheritance' in block and 'CollectableBlock' in block['class_inheritance']]

        # check if any of the found blocks are our goal block
        for block, location, obj_id in blocks:
            for key, goal_block in self._goal_blocks.items():
                # # print(block)
                # # print(goal_block[0], goal_block[1])

                if block['colour'] == goal_block[1] and block['shape'] == goal_block[0]:
                    # # print("Found goal block")

                    self._goal_blocks[key][2] = location
                    self._goal_blocks[key][3] = obj_id

        if action != None:
            return action, {}

        # if we found a goal block we are searching for, go there
        if self._goal_blocks[self._searching_for][2] is not None:
            self.update_phase(phase)
        else:
            self.update_phase(None)

        return None, {}

    def grab_block(self, obj_id, phase):
        """ Grabs block

        Args:
            obj_id: id of the object the agent has to grab

        Returns:
            GrabObject Action
        """
        self.update_phase(phase)

        return 'GrabObject', {'object_id': obj_id}

    def drop_block(self, block_delivered=0):
        """ Drops the block under the agent.

        Note:
            updates the searching_for variable which indicates which goal block the agent is looking for

        Returns:
            Drop Action
        """
        action = 'DropObject', {'object_id': self._goal_blocks[self._searching_for][3]}

        self._searching_for = f"block{int(self._searching_for[5]) + block_delivered}"

        self.update_phase(None)
        return action

    def initialize_state(self, state):
        for member in state['World']['team_members']:
            if member != self.agent_name and member not in self._teamMembers:
                self._teamMembers.append(member)

        self._goal_blocks = {
            "block0": [state['Collect_Block']['visualization']['shape'],
                       state['Collect_Block']['visualization']['colour'], None, None,
                       state['Collect_Block']['location']],
            # shape, colour, location of the block, id, drop_off location
            "block1": [state['Collect_Block_1']['visualization']['shape'],
                       state['Collect_Block_1']['visualization']['colour'], None, None,
                       state['Collect_Block_1']['location']],
            "block2": [state['Collect_Block_2']['visualization']['shape'],
                       state['Collect_Block_2']['visualization']['colour'], None, None,
                       state['Collect_Block_2']['location']]
        }

    def decide_on_bw4t_action(self, state: State):
        if self._goal_blocks is None:
            self.initialize_state(state)

        # Process messages from team members
        receivedMessages = self._processMessages(self._teamMembers)
        # Update trust beliefs for team members
        self._trustBlief(self._teamMembers, receivedMessages)

        # if action has not been selected already, select a task to work on
        # TODO: select action based on messages from other agents, and on weight
        if self._phase is None:
            self.update_phase(self.find_action(state))

        if Phase.PLAN_PATH_TO_CLOSED_DOOR == self._phase:
            # print("Phase: PLAN_PATH_TO_CLOSED_DOOR")
            return self.plan_path_to_closed_door(state, Phase.FOLLOW_PATH_TO_CLOSED_DOOR)

        if Phase.FOLLOW_PATH_TO_CLOSED_DOOR == self._phase:
            # print("Phase: FOLLOW_PATH_TO_CLOSED_DOOR")
            return self.follow_path(state, Phase.OPEN_DOOR)

        if Phase.OPEN_DOOR == self._phase:
            # print("Phase: OPEN_DOOR")
            return self.open_door()

        if Phase.PLAN_PATH_TO_OPEN_DOOR == self._phase:
            # print("Phase: PLAN_PATH_TO_OPEN_DOOR")
            return self.plan_path_to_open_door(state, Phase.FOLLOW_PATH_TO_OPEN_DOOR)

        if Phase.FOLLOW_PATH_TO_OPEN_DOOR == self._phase:
            # print("Phase: FOLLOW_PATH_TO_OPEN_DOOR")
            return self.follow_path(state, Phase.PLAN_ROOM_SEARCH)

        if Phase.PLAN_ROOM_SEARCH == self._phase:
            # print("Phase: PLAN_ROOM_SEARCH")
            return self.plan_room_search(state, Phase.SEARCH_ROOM)

        if Phase.SEARCH_ROOM == self._phase:
            # print("Phase: SEARCH_ROOM")
            return self.search_room(state, Phase.PLAN_PATH_TO_BLOCK)

        if Phase.PLAN_PATH_TO_BLOCK == self._phase:
            # print("Phase: PLAN_PATH_TO_BLOCK")
            return self.plan_path(self._goal_blocks[self._searching_for][2], Phase.FOLLOW_PATH_TO_BLOCK)

        if Phase.FOLLOW_PATH_TO_BLOCK == self._phase:
            # print("Phase: FOLLOW_PATH_TO_BLOCK")
            return self.follow_path(state, Phase.GRAB_BLOCK)

        if Phase.GRAB_BLOCK == self._phase:
            # print("Phase: GRAB_BLOCK")
            return self.grab_block(self._goal_blocks[self._searching_for][3], Phase.PLAN_PATH_TO_DROP)

        if Phase.PLAN_PATH_TO_DROP == self._phase:
            # print("Phase: PLAN_PATH_TO_DROP")
            self.plan_path(self._goal_blocks[self._searching_for][4], Phase.RETURN_GOAL_BLOCK)

        if Phase.RETURN_GOAL_BLOCK == self._phase:
            # print("Phase: RETURN_GOAL_BLOCK")
            return self.follow_path(state, Phase.DROP_BLOCK)

        if Phase.DROP_BLOCK == self._phase:
            # print("Phase: DROP_BLOCK")
            return self.drop_block(block_delivered=1)

    def _sendMessage(self, mssg, sender):
        '''
        Enable sending messages in one line of code
        '''
        msg = Message(content=mssg, from_id=sender)
        if msg.content not in self.received_messages:
            self.send_message(msg)

    def _processMessages(self, teamMembers):
        '''
        Process incoming messages and create a dictionary with received messages from each team member.
        '''
        receivedMessages = {}
        for member in teamMembers:
            receivedMessages[member] = []
        for mssg in self.received_messages:
            for member in teamMembers:
                if mssg.from_id == member:
                    receivedMessages[member].append(mssg.content)
        return receivedMessages

    def _trustBlief(self, member, received):
        '''
        Baseline implementation of a trust belief. Creates a dictionary with trust belief scores for each team member, for example based on the received messages.
        '''
        # You can change the default value to your preference
        default = 0.5
        trustBeliefs = {}
        for member in received.keys():
            trustBeliefs[member] = default
        for member in received.keys():
            for message in received[member]:
                if 'Found' in message and 'colour' not in message:
                    trustBeliefs[member] -= 0.1
                    break
        return trustBeliefs

    def plan_path_to_closed_door(self, state, phase):
        """ Finds closed doors and plans a path to that door

                Args:
                    state: Matrx state perceived by the agent

                Returns: None, {}
                """
        closed_doors = self.find_doors(state, open=False)

        if len(closed_doors) == 0:
            return None, {}

        # Randomly pick a closed door
        # TODO: look for closest doors?
        self._door = random.choice(closed_doors)
        doorLoc = self._door['location']
        # Location in front of door is south from door
        doorLoc = doorLoc[0], doorLoc[1] + 1

        # Send message of current action
        self._sendMessage('Moving to door of ' + self._door['room_name'], self.agent_name)

        return self.plan_path(doorLoc, phase)

    def open_door(self):
        self.update_phase(Phase.PLAN_ROOM_SEARCH)
        # open door
        return OpenDoorAction.__name__, {'object_id': self._door['obj_id']}

    def find_action(self, state):
        # returns an action based on the following ranking:
        #   1. if goal block has been located, start going in its direction
        #   2. if there are any closed doors, open them and search the rooms
        #   3. start searching through open rooms

        # check if a goal block has been located
        # TODO: also check messages
        if self._goal_blocks[self._searching_for][2] is not None \
                and self._previous_phase is not Phase.RETURN_GOAL_BLOCK:
            return Phase.PLAN_PATH_TO_BLOCK

        # find closed door
        if len(self.find_doors(state, open=False)) != 0:
            return Phase.PLAN_PATH_TO_CLOSED_DOOR

        # find open door
        if len(self.find_doors(state, open=True)) != 0:
            return Phase.PLAN_PATH_TO_OPEN_DOOR

    def find_doors(self, state, open=True):
        all_doors = [door for door in state.values()
                     if 'class_inheritance' in door and 'Door' in door['class_inheritance']]

        if open:
            return [door for door in all_doors
                    if door['is_open']]
        else:
            return [door for door in all_doors
                    if not door['is_open']]

    def update_phase(self, phase):
        self._previous_phase = self._phase
        self._phase = phase
