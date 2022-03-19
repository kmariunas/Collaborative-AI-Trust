
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
    PLAN_PATH_TO_OPEN_DOOR=1,
    FOLLOW_PATH_TO_OPEN_DOOR=2,
    PLAN_ROOM_SEARCH=3,
    SEARCH_ROOM=4,
    PLAN_PATH_TO_BLOCK=5
    FOLLOW_PATH_TO_BLOCK=6,
    GRAB_BLOCK=7,
    PLAN_PATH_TO_DROP=8,
    RETURN_GOAL_BLOCK=9,
    DROP_BLOCK=10


class LiarAgent(BW4TBrain):
    # TODO: do agents share all of the observations, or can we choose what to share? | technically yes, but then colorblind anmd liar could not solve the problem
    # TODO: Are room sizes fixed? | layout the same, (map size, room size)
    # TODO: do we have to implement the filter_bw4t_observations? No, just set the attribute to None
    # TODO: where should we get the goal blocks, can I get them from state or do I have to go down and observe them ? We can observe them in the state

    # TODO: Do we want our liar to communicate or not?

    def __init__(self, settings:Dict[str,object]):
        super().__init__(settings)
        self.agent_name = None
        self._phase = Phase.PLAN_PATH_TO_OPEN_DOOR
        self._lying_prob = 0.80
        self._teamMembers = []
        self._visited_rooms = []
        self._goal_blocks = None
        self._searching_for = "block0"

    def initialize(self):
        super().initialize()
        self._state_tracker = StateTracker(agent_id=self.agent_id)
        self._navigator = Navigator(agent_id=self.agent_id, 
            action_set=self.action_set, algorithm=Navigator.A_STAR_ALGORITHM)

    def filter_bw4t_observations(self, state):
        return state

    def follow_path(self, state, phase):
        """ Moves the agent towards the a destination set in the navigator

        Args:
            state: matrx state perceived by the agent
            phase: Phase of the agent after arriving to the desired destination

        Returns: action towards the destination, or None if the agent has already arrived
        """
        self._state_tracker.update(state)
        # Follow path to door
        action = self._navigator.get_move_action(self._state_tracker)
        if action != None:
            return action, {}

        self._phase = phase
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
        self._phase = phase

        return None, {}

    def plan_path_to_open_door(self, state, phase):
        """ Finds opened door that haven't been visited and plans a path to that door

        Args:
            state: Matrx state perceived by the agent

        Note:
            After successfully finding open and unvisited door this method changes the phase to FOLLOW_PATH_TO_OPEN_DOOR

        Returns: None, {}
        """
        all_doors = [door for door in state.values()
                     if 'class_inheritance' in door and 'Door' in door['class_inheritance']]

        open_doors = [door for door in all_doors
                      if door['is_open'] and door['room_name'] not in self._visited_rooms]

        if len(open_doors) == 0:
            return None, {}

        # Randomly pick a open door
        # TODO: look for closest doors?
        self._door = random.choice(open_doors)
        doorLoc = self._door['location']
        # Location in front of door is south from door
        doorLoc = doorLoc[0], doorLoc[1] + 1

        # Send message of current action or lie
        if random.uniform(0, 1) > self._lying_prob:
            self._sendMessage('Moving to ' + self._door['room_name'], self.agent_name)
        else:
            all_doors = [door for door in all_doors
                         if door['room_name'] != self._door['room_name']]

            random_lie = random.choice(all_doors)
            self._sendMessage('Moving to ' + random_lie['room_name'], self.agent_name)

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
        agent_x, agent_y= state[self.agent_name]['location']

        # create coordinates that we have to visit to search the room
        above_doors = agent_x, agent_y - 2
        right = agent_x + 1, agent_y - 2
        left_left = agent_x - 2, agent_y - 2

        return self.plan_path([above_doors, right, left_left], phase)

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
        self._state_tracker.update(state)

        action = self._navigator.get_move_action(self._state_tracker)
        blocks = [(block['visualization'], block['location'], block['obj_id']) for block in state.values() if 'class_inheritance' in block and 'CollectableBlock' in block['class_inheritance']]

        # check if any of the found blocks are our goal block
        for block, location, obj_id in blocks:
            for key, goal_block in self._goal_blocks.items():

                if block['colour'] == goal_block[1] and block['shape'] == goal_block[0]:

                    self._goal_blocks[key][2] = location
                    self._goal_blocks[key][3] = obj_id

        if action != None:
            return action, {}

        self._visited_rooms.append(self._door['room_name'])

        # if we found a goal block we are searching for, go there
        if self._goal_blocks[self._searching_for][2] is not None:
            self._phase = phase
        else:
            self._phase = Phase.PLAN_PATH_TO_OPEN_DOOR

        return None, {}

    def grab_block(self, obj_id, phase):
        """ Grabs block

        Args:
            obj_id: id of the object the agent has to grab

        Returns:
            GrabObject Action
        """
        self._phase = phase

        return 'GrabObject', {'object_id': obj_id}

    def drop_block(self, phase):
        """ Drops the block under the agent.

        Note:
            updates the searching_for variable which indicates which goal block the agent is looking for

        Returns:
            Drop Action
        """
        self._phase = phase
        action = 'DropObject', {'object_id': self._goal_blocks[self._searching_for][3]}

        self._searching_for = f"block{int(self._searching_for[5]) + 1}"

        return action

    def initialize_state(self, state):
        for member in state['World']['team_members']:
            if member!=self.agent_name and member not in self._teamMembers:
                self._teamMembers.append(member)

        self._goal_blocks = {
            "block0": [state['Collect_Block']['visualization']['shape'], state['Collect_Block']['visualization']['colour'], None, None, state['Collect_Block']['location']], #shape, colour, location of the block, id, drop_off location
            "block1": [state['Collect_Block_1']['visualization']['shape'], state['Collect_Block_1']['visualization']['colour'], None, None, state['Collect_Block_1']['location']],
            "block2": [state['Collect_Block_2']['visualization']['shape'], state['Collect_Block_2']['visualization']['colour'], None, None, state['Collect_Block_2']['location']]
        }

    def decide_on_bw4t_action(self, state:State):
        if self._goal_blocks is None:
            self.initialize_state(state)

        # Process messages from team members
        receivedMessages = self._processMessages(self._teamMembers)
        # Update trust beliefs for team members
        self._trustBlief(self._teamMembers, receivedMessages)
        # print(f"Phase: {self._phase}")
        
        while True:
            if Phase.PLAN_PATH_TO_OPEN_DOOR==self._phase:
                # print("Phase: PLAN_PATH_TO_OPEN_DOOR")
                return self.plan_path_to_open_door(state, Phase.FOLLOW_PATH_TO_OPEN_DOOR)

            if Phase.FOLLOW_PATH_TO_OPEN_DOOR==self._phase:
                # print("Phase: FOLLOW_PATH_TO_OPEN_DOOR")
                return self.follow_path(state, Phase.PLAN_ROOM_SEARCH)

            if Phase.PLAN_ROOM_SEARCH==self._phase:
                # print("Phase: PLAN_ROOM_SEARCH")
                return self.plan_room_search(state, Phase.SEARCH_ROOM)

            if Phase.SEARCH_ROOM==self._phase:
                # print("Phase: SEARCH_ROOM")
                return self.search_room(state, Phase.PLAN_PATH_TO_BLOCK)

            if Phase.PLAN_PATH_TO_BLOCK==self._phase:
                # print("Phase: PLAN_PATH_TO_BLOCK")
                return self.plan_path(self._goal_blocks[self._searching_for][2], Phase.FOLLOW_PATH_TO_BLOCK)

            if Phase.FOLLOW_PATH_TO_BLOCK==self._phase:
                # print("Phase: FOLLOW_PATH_TO_BLOCK")
                return self.follow_path(state, Phase.GRAB_BLOCK)

            if Phase.GRAB_BLOCK==self._phase:
                # print("Phase: GRAB_BLOCK")
                return self.grab_block(self._goal_blocks[self._searching_for][3], Phase.PLAN_PATH_TO_DROP)

            if Phase.PLAN_PATH_TO_DROP==self._phase:
                # print("Phase: PLAN_PATH_TO_DROP")
                self.plan_path(self._goal_blocks[self._searching_for][4],Phase.RETURN_GOAL_BLOCK)

            if Phase.RETURN_GOAL_BLOCK==self._phase:
                # print("Phase: RETURN_GOAL_BLOCK")
                return self.follow_path(state, Phase.DROP_BLOCK)

            if Phase.DROP_BLOCK==self._phase:
                # print("Phase: DROP_BLOCK")
                return self.drop_block(Phase.SEARCH_ROOM)

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
                    trustBeliefs[member]-=0.1
                    break
        return trustBeliefs
