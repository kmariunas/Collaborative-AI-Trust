import sys
from queue import Queue, PriorityQueue
from typing import Dict

from matrx.actions.door_actions import OpenDoorAction
from matrx.actions.object_actions import GrabObject, DropObject
from matrx.agents.agent_utils.navigator import Navigator
from matrx.agents.agent_utils.state import State
from matrx.agents.agent_utils.state_tracker import StateTracker

from agents1.Message import MessageBuilder, MessageType
from agents1.Phase import Phase
from agents1.TrustSystem import TrustSystem
from agents1.util import locations_match, manhattan_distance, visualizations_match
from bw4t.BW4TBrain import BW4TBrain


def closest_point_idx(point, list_of_points):
    # manhattan distance
    min_distance = sys.maxsize
    closest_idx = None

    for idx, location in enumerate(list_of_points):
        distance = manhattan_distance(point, location)

        if distance < min_distance:
            min_distance = distance
            closest_idx = idx

    return closest_idx


class GenericAgentTesting(BW4TBrain):

    def __init__(self, settings: Dict[str, object], phase: Phase = None):
        super().__init__(settings)
        self.trust_system = None
        self._messages = set()
        self._door = None
        self.agent_name = None
        self._phase = phase
        self._teamMembers = []
        self._visited_rooms = set()
        self._com_visited_rooms = set()  # not updated rn
        self._goal_blocks = None
        self._filter = 'agent'
        self._currently_dropping = None

        self._searching_for = None
        self._not_found_yet = set()
        self._not_found_yet.add("block0")
        self._not_found_yet.add("block1")
        self._not_found_yet.add("block2")
        self._mb = None  # message builder
        self._previous_phase = None
        self._is_carrying = set()

        self._fix_block_order = False
        self._blocks_to_fix = Queue()
        self._blocks_to_fix.put("block1")
        self._blocks_to_fix.put("block2")

        self._grid_shape = None

        self._get_rid_of_block = set()

    def initialize(self):
        super().initialize()
        self._mb = MessageBuilder(self.agent_name)
        self._state_tracker = StateTracker(agent_id=self.agent_id)
        self._navigator = Navigator(agent_id=self.agent_id,
                                    action_set=self.action_set, algorithm=Navigator.A_STAR_ALGORITHM)

    def filter_bw4t_observations(self, state):
        return state

    def follow_path(self, state, phase):
        """ Moves the agent towards the destination set in the navigator

        Args:
            state: matrx state perceived by the agent
            phase: Phase of the agent after arriving to the desired destination

        Returns: action towards the destination, or None if the agent has already arrived
        """
        self._state_tracker.update(state)
        # Follow path to door
        action = self._navigator.get_move_action(self._state_tracker)
        if action is not None:
            return action, {}

        self.update_phase(phase)
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

    def find_action(self, state):
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

    def find_doors(self, state, open=True, filter='none'):
        """
        Method returns list of doors filtered with the passed params.

        @param state
        @param open: True to return open doors, False otherwise
        @param filter: filter for the rooms. Values: 'none', 'agent', 'everyone'.
                * 'none': no filter
                * 'agent': only rooms that the agent has not visited
                * 'everyone': only rooms that no one has visited
        """
        all_doors = [door for door in state.values()
                     if 'class_inheritance' in door and 'Door' in door['class_inheritance']]

        doors = None
        if filter == 'none':
            doors = all_doors
        if filter == 'agent':
            doors = [door for door in all_doors if door['room_name'] not in self._visited_rooms]
        if filter == 'everyone':
            doors = [door for door in all_doors
                     if door['room_name'] not in self._visited_rooms
                     and door['room_name'] not in self._com_visited_rooms]
        if open:
            return [door for door in doors
                    if door['is_open']]
        else:
            return [door for door in doors
                    if not door['is_open']]

    def plan_path_to_closed_door(self, state, phase: Phase):
        """ Finds doors that are still closed and plans a path to them

        Args:
            state: perceived state by the agent
            phase: Next phase after successfully finding closed door

        Returns:
            None, {}
        """
        closed_doors = self.find_doors(state, open=False, filter=self._filter)

        if len(closed_doors) == 0:
            self.update_phase(None)
            return None, {}

        door_idx = closest_point_idx(state[self.agent_name]['location'],
                                     list(map(lambda x: x["location"], closed_doors)))
        self._door = closed_doors[door_idx]
        doorLoc = self._door['location']
        # Location in front of door is south from door
        doorLoc = doorLoc[0], doorLoc[1] + 1
        # Send message of current action

        return self.plan_path(doorLoc, phase)

    def open_door(self, phase):
        """ opens the door

        Args:
            phase: Next phase after opening the door

        Returns:
            OpenDoorAction
        """
        self.update_phase(phase)
        # Open door
        return OpenDoorAction.__name__, {'object_id': self._door['obj_id']}

    def plan_path_to_open_door(self, state, phase):
        """ Finds opened door that haven't been visited and plans a path to that door

        Args:
            state: Matrx state perceived by the agent
            phase: Next phase after successful plan

        Note:
            After successfully finding open and unvisited door this method changes the phase to phase

        Returns: None, {}
        """
        open_doors = self.find_doors(state, open=True, filter=self._filter)

        if len(open_doors) == 0:
            self.update_phase(None)
            return None, {}

        # look for closest door
        door_idx = closest_point_idx(state[self.agent_name]['location'], list(map(lambda x: x["location"], open_doors)))

        self._door = open_doors[door_idx]
        doorLoc = self._door['location']
        # Location in front of door is south from door
        doorLoc = doorLoc[0], doorLoc[1] + 1

        return self.plan_path(doorLoc, phase)

    def plan_room_search(self, state, phase):
        """ Adds waypoints to the navigator to search the whole room.

        Args:
            state: matrx state perceived by the agent.
            phase: Next phase after planning

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
        left_left = agent_x - 2, agent_y - 2

        return self.plan_path([above_doors, right, left_left], phase)

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

        self._state_tracker.update(state)

        action = self._navigator.get_move_action(self._state_tracker)

        if action is not None:
            return action, {}
        self._visited_rooms.add(self._door['room_name'])

        # if we found a goal block we are searching for, go there
        if self._searching_for["location"] is not None:
            self.update_phase(phase)
        else:
            self.update_phase(None)

        return None, {}

    def grab_block(self, phase, state):
        """ Grabs block

        Args:
            state:
            phase: Next phase after grabbing a block

        Returns:
            GrabObject Action
        """

        self.update_phase(phase)
        blocks_id = [block['obj_id'] for block in state.values() if
                     'class_inheritance' in block and 'CollectableBlock' in block['class_inheritance']
                     and block['is_collectable'] and block['location'] == state[self.agent_name]['location']]

        if len(blocks_id) == 0:
            # remove block location
            for block in self._goal_blocks.values():
                for location in block['location']:
                    if locations_match(location, state[self.agent_name]['location']):
                        index = block['location'].index(location)
                        block['id'].pop(index)
                        block['location'].pop(index)
            self.update_phase(None)
            return None, {}

        self._is_carrying.add((self._searching_for["block"], blocks_id[0]))

        self._not_found_yet.discard(self._searching_for["block"])
        # print("after: ")
        # print(self._is_carrying)

        return GrabObject.__name__, {'object_id': blocks_id[0]}

    def drop_block(self, state, phase, block_delivered=True):
        """ Drops the block under the agent.

        Args:
            phase: Next phase after dropping the block
            block_delivered: whether the block was delivered to the drop-off location

        Note:
            updates the searching_for variable which indicates which goal block the agent is looking for

        Returns:
            Drop Action or None
        """

        # gather any possible blocks that are already found
        if len(self._get_rid_of_block) > 0:
            block, id = self._get_rid_of_block.pop()
            self._is_carrying.discard((block, id))

            action = DropObject.__name__, {'object_id': id}
            msg = self._mb.create_message(MessageType.DROP_BLOCK,
                                          block_vis=self._goal_blocks[block]['visualization'],
                                          location=state[self.agent_name]['location'])
            self._sendMessage(msg)
            if len(self._get_rid_of_block) > 0:
                self.update_phase(Phase.DROP_BLOCK)
            else:
                return action

        elif len(self._is_carrying) > 0:

            block, id = self._is_carrying.pop()
            msg = self._mb.create_message(MessageType.DROP_BLOCK,
                                          block_vis=self._goal_blocks[block]['visualization'],
                                          location=state[self.agent_name]['location'])
            self._sendMessage(msg)
            action = DropObject.__name__, {'object_id': id}
            if block_delivered:

                if len(self._not_found_yet) == 0:
                    self._fix_block_order = True
                self.update_phase(phase)
            else:
                self._blocks_to_fix = Queue()
                self._blocks_to_fix.put("block1")
                self._blocks_to_fix.put("block2")
                self.update_phase(None)
                self._not_found_yet.add(block)

            return action
        else:
            return None, {}

    def initialize_trust_system(self):
        drop_off_locations = [block['drop_off'] for block in self._goal_blocks.values()]
        self.trust_system = TrustSystem(self.agent_name, self._teamMembers, self._goal_blocks.values(),
                                        drop_off_locations)
        msg = self.trust_system.reputation_message(self._mb)
        self._sendMessage(msg)

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

        self.initialize_trust_system()

        self._sendMessage(self._mb.create_message(MessageType.GOAL_BLOCKS, goal_blocks=self._goal_blocks))
        self._grid_shape = state['World']['grid_shape']

    def phase_action(self, state):
        msg = None
        res = None, {}
        if self._fix_block_order:
            if Phase.PLAN_PATH_TO_DROP == self._phase:
                block = self._blocks_to_fix.get()
                res = self.plan_path(self._goal_blocks[block]["drop_off"], Phase.FOLLOW_PATH_TO_BLOCK)
            elif Phase.FOLLOW_PATH_TO_BLOCK == self._phase:
                self.follow_path(state, Phase.GRAB_BLOCK)
            elif Phase.GRAB_BLOCK == self._phase \
                    and state[self.agent_name]['location'] != self._goal_blocks["block0"]["drop_off"]:
                res = self.grab_block(Phase.DROP_BLOCK, state)
            elif Phase.DROP_BLOCK == self._phase:
                res = self.drop_block(state, Phase.PLAN_PATH_TO_BLOCK)
        else:
            if Phase.PLAN_PATH_TO_CLOSED_DOOR == self._phase:
                res = self.plan_path_to_closed_door(state, Phase.FOLLOW_PATH_TO_CLOSED_DOOR)
                msg = self._mb.create_message(MessageType.MOVE_TO_ROOM, room_name=self._door['room_name'])

            elif Phase.FOLLOW_PATH_TO_CLOSED_DOOR == self._phase:
                res = self.follow_path(state, Phase.OPEN_DOOR)

            elif Phase.OPEN_DOOR == self._phase:
                res = self.open_door(Phase.PLAN_ROOM_SEARCH)
                msg = self._mb.create_message(MessageType.OPEN_DOOR, room_name=self._door['room_name'])

            elif Phase.PLAN_PATH_TO_OPEN_DOOR == self._phase:
                res = self.plan_path_to_open_door(state, Phase.FOLLOW_PATH_TO_OPEN_DOOR)
                msg = self._mb.create_message(MessageType.MOVE_TO_ROOM, room_name=self._door['room_name'])

            elif Phase.FOLLOW_PATH_TO_OPEN_DOOR == self._phase:
                res = self.follow_path(state, Phase.PLAN_ROOM_SEARCH)

            elif Phase.PLAN_ROOM_SEARCH == self._phase:
                res = self.plan_room_search(state, Phase.SEARCH_ROOM)
                msg = self._mb.create_message(MessageType.SEARCHING_ROOM, room_name=self._door['room_name'])

            elif Phase.SEARCH_ROOM == self._phase:
                res = self.search_room(state, None)

            elif Phase.PLAN_PATH_TO_BLOCK == self._phase:
                self.find_best_path(state)
                res = self.plan_path(self._searching_for["location"], Phase.FOLLOW_PATH_TO_BLOCK)

            elif Phase.FOLLOW_PATH_TO_BLOCK == self._phase:
                res = self.follow_path(state, Phase.GRAB_BLOCK)

            elif Phase.GRAB_BLOCK == self._phase:
                res = self.grab_block(Phase.PLAN_PATH_TO_DROP, state)

                msg = self._mb.create_message(MessageType.PICK_UP_BLOCK,
                                              block_vis=self._searching_for['visualization'],
                                              location=self._searching_for['location'])

            elif Phase.PLAN_PATH_TO_DROP == self._phase:
                block, id = list(self._is_carrying)[0]
                res = self.plan_path(self._goal_blocks[block]["drop_off"], Phase.RETURN_GOAL_BLOCK)

            elif Phase.RETURN_GOAL_BLOCK == self._phase:
                res = self.follow_path(state, Phase.DROP_BLOCK)

            elif Phase.DROP_BLOCK == self._phase:
                res = self.drop_block(state, None)
        # else:
        #     raise Exception('phase might be None')

        return res, msg

    def check_surroundings_for_box(self, state):
        blocks = [(block['visualization'], block['location'], block['obj_id']) for block in state.values() if
                  'class_inheritance' in block and 'CollectableBlock' in block['class_inheritance'] and block[
                      'is_collectable']]

        # check if any of the found blocks are our goal block
        for block, location, obj_id in blocks:
            for key, goal_block in self._goal_blocks.items():

                if block['colour'] == goal_block['visualization']['colour'] \
                        and block['shape'] == goal_block['visualization']['shape'] \
                        and block['size'] == goal_block['visualization']['size']:
                    self.update_goal_block(key, location, obj_id)

                    msg = self._mb.create_message(MessageType.FOUND_GOAL_BLOCK,
                                                  block_vis=self._goal_blocks[key]["visualization"],
                                                  location=location)
                    self._sendMessage(msg)

    def decide_on_bw4t_action(self, state: State):
        if self._goal_blocks is None:
            self.initialize_state(state)

        self.check_surroundings_for_box(state)

        # parse messages from team members
        received_messages = self._parse_messages()
        # Update trust beliefs for team members
        self.trust_system.update(received_messages, state['World']['nr_ticks'])
        # select action based on received messages
        self._processMessages(received_messages)

        # if action has not been selected already, select a task to work on
        # TODO: select action based on messages from other agents, and on weight
        if self._phase is None:
            self.update_phase(self.find_action(state))

        res, msg = self.phase_action(state)
        if (res == None):
            self.update_phase(self.find_action(state))
            res, msg = self.phase_action(state)
        self._sendMessage(msg)

        return res

    def _sendMessage(self, msg):
        """
        Enable sending messages in one line of code
        """
        if msg is None:
            return

        pmsg = MessageBuilder.process_message(msg)

        if pmsg['type'] is not MessageType.FOUND_GOAL_BLOCK and pmsg['type'] is not MessageType.FOUND_BLOCK:
            self.send_message(msg)
            self._messages.add(msg.content)
            # print(self.agent_name, msg.content)
        elif msg.content not in self._messages:
            self.send_message(msg)
            self._messages.add(msg.content)
            # print(self.agent_name, msg.content)


    def _processMessages(self, received_messages):
        """
        Process incoming messages.
        """

        for messages in received_messages.values():
            for msg in messages:
                if self.trust_system.trust_message(msg):
                    if msg['type'] is MessageType.FOUND_GOAL_BLOCK:
                        # find the goal block
                        for key, goal_block in self._goal_blocks.items():
                            if goal_block['visualization']['shape'] == msg['visualization']['shape'] \
                                    and goal_block['visualization']['size'] == msg['visualization']['size'] \
                                    and goal_block['visualization']['colour'] == msg['visualization']['colour']:
                                self.update_goal_block(key, msg['location'], "-1")

                    elif msg['type'] is MessageType.MOVE_TO_ROOM \
                            or msg['type'] is MessageType.SEARCHING_ROOM \
                            or msg['type'] is MessageType.OPEN_DOOR:
                        self._com_visited_rooms.add(msg['room_name'])

                    elif msg['type'] is MessageType.DROP_BLOCK:
                        # if msg['location'] == self._goal_blocks[self._searching_for[0]]['drop_off']:
                        #     self._phase = Phase.DROP_BLOCK
                        # for key, goal_block in self._goal_blocks.items():
                        #     if locations_match(goal_block['drop_off'], msg['location']) \
                        #             and key in self._searching_for:
                        #         # remove goal block from searching_for
                        #         self._searching_for.remove(key)
                        drop_off_locs = [block['drop_off'] for block in self._goal_blocks.values()]
                        if msg['location'] in drop_off_locs:
                            # find block
                            for key, block in self._goal_blocks.items():
                                if visualizations_match(block['visualization'], msg['visualization']):
                                    self._not_found_yet.discard(key)

                            if len(self._is_carrying) > 0:
                                for block, id in self._is_carrying:
                                    if self._goal_blocks[block]["drop_off"] == msg['location']:
                                        self._get_rid_of_block.add((block, id))
                                        self._phase = Phase.DROP_BLOCK

    def _processMessages(self, received_messages):
        """
        Process incoming messages.
        """

        for messages in received_messages.values():
            for msg in messages:
                if self.trust_system.trust_message(msg):
                    if msg['type'] is MessageType.FOUND_GOAL_BLOCK:
                        # find the goal block
                        for key, goal_block in self._goal_blocks.items():
                            if goal_block['visualization']['shape'] == msg['visualization']['shape'] \
                                    and goal_block['visualization']['size'] == msg['visualization']['size'] \
                                    and goal_block['visualization']['colour'] == msg['visualization']['colour']:
                                self.update_goal_block(key, msg['location'], "-1")

                    elif msg['type'] is MessageType.MOVE_TO_ROOM \
                            or msg['type'] is MessageType.SEARCHING_ROOM:
                        self._com_visited_rooms.add(msg['room_name'])

                    # TODO: fix agent is still looking or blocks that have been dropped
                    elif msg['type'] is MessageType.DROP_BLOCK:
                        # print(msg)
                        # print(self.agent_name)
                        # print("carrying:")
                        # print(self._is_carrying)
                        # print("not found before:")
                        # print(self._not_found_yet)
                        # block, id = list(self._is_carrying)[0]
                        drop_off_locs = [block['drop_off'] for block in self._goal_blocks.values()]
                        # print(drop_off_locs)
                        # print(msg['location'])
                        if msg['location'] in drop_off_locs:
                            # find block
                            for key, block in self._goal_blocks.items():
                                if visualizations_match(block['visualization'], msg['visualization']):
                                    # print(key)
                                    # print(self._not_found_yet)
                                    self._not_found_yet.discard(key)
                                    # print("after:")
                                    # print(self._not_found_yet)

                            if len(self._is_carrying) > 0:
                                for block, id in self._is_carrying:
                                    if self._goal_blocks[block]["drop_off"] == msg['location']:
                                        self._get_rid_of_block.add((block, id))
                                        self._phase = Phase.DROP_BLOCK

    def update_phase(self, phase):
        self._previous_phase = self._phase
        self._phase = phase

    def update_goal_block(self, block_key, new_block_location, new_block_id):
        self._goal_blocks[block_key]["location"].append(new_block_location)
        self._goal_blocks[block_key]["id"].append(new_block_id)

    def find_best_path(self, state):
        agent_loc = state[self.agent_name]['location']
        minDistance = 1000000

        for block in self._not_found_yet:
            drop_loc = self._goal_blocks[block]["drop_off"]
            for index, location in enumerate(self._goal_blocks[block]["location"]):

                distance = manhattan_distance(agent_loc, location) + manhattan_distance(location, drop_loc)
                if distance < minDistance:
                    minDistance = distance
                    self._searching_for["block"] = block
                    self._searching_for["location"] = location
                    self._searching_for["id"] = self._goal_blocks[block]["id"][index]
                    self._searching_for["drop_off"] = drop_loc


    def _parse_messages(self):
        """
        Parses incoming messages and create a dictionary with received messages from each team member.
        """
        receivedMessages = {}
        for member in self._teamMembers:
            receivedMessages[member] = []

        while len(self.received_messages) != 0:
            msg = self.received_messages.pop(0)
            self._messages.add(msg)
            msg = MessageBuilder.process_message(msg)

            for member in self._teamMembers:
                if msg['from_id'] == member:
                    receivedMessages[member].append(msg)

        return receivedMessages