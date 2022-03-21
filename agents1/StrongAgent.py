from typing import final, List, Dict, Final
import enum, random

from agents1.GenericAgent import GenericAgent
from agents1.Message import MessageBuilder, MessageType as mt
from bw4t.BW4TBrain import BW4TBrain
from matrx.agents.agent_utils.state import State
from matrx.agents.agent_utils.navigator import Navigator
from matrx.agents.agent_utils.state_tracker import StateTracker
from matrx.actions.door_actions import OpenDoorAction
from matrx.actions.object_actions import GrabObject, DropObject


class StrongAgent(GenericAgent):

    def __init__(self, settings:Dict[str,object]):
        super().__init__(settings, None)

    # def __init__(self, settings: Dict[str, object]):
    #     super().__init__(settings)
    #     self._picked_first = False
    #     self._door = None
    #     self.agent_name = None
    #     self._phase = None
    #     self._teamMembers = []
    #     self._goal_blocks = None
    #     self._searching_for = "block0"
    #     self._mb = None
    #     self._com_visited_rooms = set()
    #     self._visited_rooms = set()
    #     self._filter = 'agent'
    #
    # def initialize(self):
    #     super().initialize()
    #     self._mb = MessageBuilder(self.agent_name)
    #     self._state_tracker = StateTracker(agent_id=self.agent_id)
    #     self._navigator = Navigator(agent_id=self.agent_id,
    #                                 action_set=self.action_set, algorithm=Navigator.A_STAR_ALGORITHM)
    #
    # def filter_bw4t_observations(self, state):
    #     return state
    #
    # def follow_path(self, state, phase):
    #     """ Moves the agent towards the destination set in the navigator,
    #     with a 50% probability of abandoning the action.
    #
    #     Args:
    #         state: matrx state perceived by the agent
    #         phase: Phase of the agent after arriving to the desired destination
    #
    #     Returns: action towards the destination, or None if the agent has already arrived
    #     """
    #     self._state_tracker.update(state)
    #     # Follow path to door
    #     action = self._navigator.get_move_action(self._state_tracker)
    #     if action != None:
    #         return action, {}
    #
    #     self._phase = phase
    #
    #     return None, {}
    #
    # def plan_path(self, coord, phase):
    #     """ adds new waypoints to the navigator, sets the following phase
    #
    #     Args:
    #         coord: Coordinates that the agent has to visit
    #         phase: New phase of the agent
    #
    #     Returns: None, {}
    #
    #     """
    #     if not isinstance(coord, list):
    #         coord = [coord]
    #
    #     self._navigator.reset_full()
    #     # add waypoint to the block
    #     self._navigator.add_waypoints(coord)
    #
    #     # follow path to block
    #     self._phase = phase
    #
    #     return None, {}
    #
    # def plan_path_to_open_door(self, state, phase):
    #     """ Finds opened door that haven't been visited and plans a path to that door
    #
    #     Args:
    #         state: Matrx state perceived by the agent
    #
    #     Note:
    #         After successfully finding open and unvisited door this method changes the phase to FOLLOW_PATH_TO_OPEN_DOOR
    #
    #     Returns: None, {}
    #     """
    #     open_doors = self.find_doors(state, open=True, filter=self._filter)
    #
    #     if len(open_doors) == 0:
    #         return None, {}
    #
    #     # Randomly pick a open door
    #     # TODO: look for closest doors?
    #     self._door = random.choice(open_doors)
    #     doorLoc = self._door['location']
    #     # Location in front of door is south from door
    #     doorLoc = doorLoc[0], doorLoc[1] + 1
    #
    #     return self.plan_path(doorLoc, phase)
    #
    # def plan_room_search(self, state, phase):
    #     """ Adds waypoints to the navigator to search the whole room.
    #
    #     Args:
    #         state:matrx state perceived by the agent.
    #
    #     Note:
    #         Coordinates of the tiles the agent must visit are designed for 4x2 rooms.
    #         Assumes that agent is standing bellow the door.
    #
    #     Returns: None, {}
    #     """
    #     # get agent location
    #     agent_x, agent_y = state[self.agent_name]['location']
    #
    #     # create coordinates that we have to visit to search the room
    #     above_doors = agent_x, agent_y - 2
    #     right = agent_x + 1, agent_y - 2
    #     left = agent_x - 1, agent_y - 2
    #     left_left = agent_x - 2, agent_y - 2
    #
    #     return self.plan_path([above_doors, right, left, left_left], phase)
    #
    # def search_room(self, state, phase):
    #     """ Looks for any blocks in radius of the agent, if blocks match any goal block, records it's location and id.
    #         After each search agent moves to the waypoint given by @plan_room_search.
    #
    #     Args:
    #         state: matrx state perceived by the agent.
    #
    #     Note:
    #         Once the agent searches the entire room, if it has found a block it is looking for, it will set the phase
    #         to PLAN_PATH_TO_BLOCK, otherwise the agent looks for other rooms with phase PLAN_PATH_TO_OPEN_DOOR.
    #
    #     Returns: Movement action .
    #
    #     """
    #     self._state_tracker.update(state)
    #
    #     action = self._navigator.get_move_action(self._state_tracker)
    #
    #     if action is not None:
    #         return action, {}
    #
    #     # if we found a goal block we are searching for, go there
    #     # print(self._goal_blocks[self._searching_for])
    #     if self._goal_blocks[self._searching_for]['location'] is not None:
    #         self._phase = phase
    #     else:
    #         self._phase = None
    #
    #     return None, {}
    #
    # def grab_block(self, obj_id, phase):
    #     """ Grabs block
    #
    #     Args:
    #         obj_id: id of the object the agent has to grab
    #
    #     Returns:
    #         GrabObject Action
    #     """
    #     self._phase = phase
    #     return 'GrabObject', {'object_id': obj_id}
    #
    # def drop_block(self):
    #     """ Drops the block under the agent.
    #
    #     Note:
    #         updates the searching_for variable which indicates which goal block the agent is looking for
    #
    #     Returns:
    #         Drop Action
    #     """
    #     action = 'DropObject', {'object_id': self._goal_blocks[self._searching_for]['id']}
    #
    #     block_id = min(int(self._searching_for[5]) + 1, 2)
    #     self._searching_for = f"block{block_id}"
    #
    #     self._phase = None
    #     return action
    #
    # def initialize_state(self, state):
    #     for member in state['World']['team_members']:
    #         if member != self.agent_name and member not in self._teamMembers:
    #             self._teamMembers.append(member)
    #
    #     self._goal_blocks = {
    #         # visualization, location of the block, id, drop_off location
    #         "block0": {'visualization': state['Collect_Block']['visualization'],
    #                    'location': None,
    #                    'id': None,
    #                    'drop_location': state['Collect_Block']['location']},
    #         "block1": {'visualization': state['Collect_Block_1']['visualization'],
    #                    'location': None,
    #                    'id': None,
    #                    'drop_location': state['Collect_Block_1']['location']},
    #         "block2": {'visualization':state['Collect_Block_2']['visualization'],
    #                    'location': None,
    #                    'id': None,
    #                    'drop_location': state['Collect_Block_2']['location']}
    #     }
    #
    # def decide_on_bw4t_action(self, state: State):
    #     if self._goal_blocks is None:
    #         self.initialize_state(state)
    #
    #     self.check_surroundings_for_box(state)
    #
    #     # Process messages from team members
    #     receivedMessages = self._processMessages(self._teamMembers)
    #     # Update trust beliefs for team members
    #     self._trustBlief(self._teamMembers, receivedMessages)
    #
    #     # if action has not been selected already, select a task to work on
    #     # TODO: select action based on messages from other agents, and on weight
    #     if self._phase is None:
    #         self._phase = self.find_action(state)
    #
    #     if Phase.PLAN_PATH_TO_CLOSED_DOOR == self._phase:
    #         self.plan_path_to_closed_door(state, Phase.FOLLOW_PATH_TO_CLOSED_DOOR)
    #         # Send message of current action
    #         msg = self._mb.create_message(mt.MOVE_TO_ROOM,
    #                                       room_name=self._door['room_name'])
    #         self._sendMessage(msg)
    #
    #         return None, {}
    #
    #     if Phase.FOLLOW_PATH_TO_CLOSED_DOOR == self._phase:
    #         return self.follow_path(state, Phase.OPEN_DOOR)
    #
    #     if Phase.OPEN_DOOR == self._phase:
    #         msg = self._mb.create_message(mt.OPEN_DOOR, room_name=self._door['room_name'])
    #         self._sendMessage(msg)
    #
    #         return self.open_door(Phase.PLAN_ROOM_SEARCH)
    #
    #     if Phase.PLAN_PATH_TO_OPEN_DOOR == self._phase:
    #         msg = self._mb.create_message(mt.MOVE_TO_ROOM, room_name=self._door['room_name'])
    #         self._sendMessage(msg)
    #
    #         return self.plan_path_to_open_door(state, Phase.FOLLOW_PATH_TO_OPEN_DOOR)
    #
    #     if Phase.FOLLOW_PATH_TO_OPEN_DOOR == self._phase:
    #         return self.follow_path(state, Phase.PLAN_ROOM_SEARCH)
    #
    #     if Phase.PLAN_ROOM_SEARCH == self._phase:
    #         msg = self._mb.create_message(mt.SEARCHING_ROOM, room_name=self._door['room_name'])
    #         self._sendMessage(msg)
    #
    #         return self.plan_room_search(state, Phase.SEARCH_ROOM)
    #
    #     if Phase.SEARCH_ROOM == self._phase:
    #         return self.search_room(state, Phase.PLAN_PATH_TO_BLOCK)
    #
    #     if Phase.PLAN_PATH_TO_BLOCK == self._phase:
    #         msg = self._mb.create_message(mt.PICK_UP_BLOCK,
    #                                       block_vis=MessageBuilder.block_vis_str(
    #                                           self._goal_blocks[self._searching_for]['visualization']),
    #                                       location=MessageBuilder.location_str(
    #                                           self._goal_blocks[self._searching_for]['location']))
    #         self.send_message(msg)
    #
    #         return self.plan_path(self._goal_blocks[self._searching_for]['location'], Phase.FOLLOW_PATH_TO_BLOCK)
    #
    #     if Phase.FOLLOW_PATH_TO_BLOCK == self._phase:
    #         return self.follow_path(state, Phase.GRAB_BLOCK)
    #
    #     if Phase.GRAB_BLOCK == self._phase:
    #         # print(self._goal_blocks[self._searching_for][2])
    #         return self.grab_block(self._goal_blocks[self._searching_for]['id'], Phase.PLAN_PATH_TO_DROP)
    #
    #     if Phase.PLAN_PATH_TO_DROP == self._phase:
    #         self.plan_path(self._goal_blocks[self._searching_for]['drop_location'], Phase.RETURN_GOAL_BLOCK)
    #
    #     if Phase.RETURN_GOAL_BLOCK == self._phase:
    #         return self.follow_path(state, Phase.DROP_BLOCK)
    #
    #     if Phase.DROP_BLOCK == self._phase:
    #         msg = self._mb.create_message(mt.DROP_BLOCK,
    #                                       block_vis=MessageBuilder.block_vis_str(
    #                                           self._goal_blocks[self._searching_for]['visualization']),
    #                                       location=MessageBuilder.location_str(
    #                                           self._goal_blocks[self._searching_for]['location']))
    #         self._sendMessage(msg)
    #
    #         return self.drop_block()
    #
    # def _sendMessage(self, msg):
    #     '''
    #     Enable sending messages in one line of code
    #     '''
    #     if msg.content not in self.received_messages:
    #         self.send_message(msg)
    #
    # def _processMessages(self, teamMembers):
    #     '''
    #     Process incoming messages and create a dictionary with received messages from each team member.
    #     '''
    #     receivedMessages = {}
    #     for member in teamMembers:
    #         receivedMessages[member] = []
    #     while len(self.received_messages) != 0:
    #         mssg = self.received_messages.pop(0)
    #         for member in teamMembers:
    #             if mssg.from_id == member:
    #                 receivedMessages[member].append(mssg.content)
    #         msg = MessageBuilder.process_message(mssg)
    #         if self.trust_message(msg):
    #             # process messages:
    #             # TODO: implement another ds holding picked up blocks and dropped blocks
    #             # if other agent dropped up the goal block, update state
    #             if msg['type'] is mt.DROP_BLOCK:
    #                 self.drop_block()
    #                 self._phase = None
    #
    #             # update locations of goal blocks
    #             if msg['type'] is mt.FOUND_GOAL_BLOCK:
    #                 for key, block in self._goal_blocks.items():
    #                     if block['visualization']['colour'] == msg['visualization']['colour'] \
    #                             and block['visualization']['shape'] == msg['visualization']['shape'] \
    #                             and block['visualization']['size'] == msg['visualization']['size']:
    #                         self._goal_blocks[key][1] = msg['location']
    #
    #             # update which rooms have been visited
    #             if msg['type'] is mt.MOVE_TO_ROOM \
    #                     or msg['type'] is mt.OPEN_DOOR \
    #                     or msg['type'] is mt.SEARCHING_ROOM:
    #                 self._com_visited_rooms.add(msg['room_name'])
    #     return receivedMessages
    #
    # def _trustBlief(self, member, received):
    #     '''
    #     Baseline implementation of a trust belief. Creates a dictionary with trust belief scores for each team member, for example based on the received messages.
    #     '''
    #     # You can change the default value to your preference
    #     default = 0.5
    #     trustBeliefs = {}
    #     for member in received.keys():
    #         trustBeliefs[member] = default
    #     for member in received.keys():
    #         for message in received[member]:
    #             if 'Found' in message and 'colour' not in message:
    #                 trustBeliefs[member] -= 0.1
    #                 break
    #     return trustBeliefs
    #
    # def plan_path_to_closed_door(self, state, phase):
    #     """ Finds closed doors and plans a path to that door
    #
    #             Args:
    #                 state: Matrx state perceived by the agent
    #
    #             Returns: None, {}
    #             """
    #     closed_doors = self.find_doors(state, open=False, filter=self._filter)
    #
    #     if len(closed_doors) == 0:
    #         return None, {}
    #
    #     # Randomly pick a closed door
    #     # TODO: look for closest doors?
    #     self._door = random.choice(closed_doors)
    #     doorLoc = self._door['location']
    #     # Location in front of door is south from door
    #     doorLoc = doorLoc[0], doorLoc[1] + 1
    #
    #     return self.plan_path(doorLoc, phase)
    #
    # def open_door(self, phase):
    #     self._phase = phase
    #
    #     # open door
    #     return OpenDoorAction.__name__, {'object_id': self._door['obj_id']}
    #
    # def find_action(self, state):
    #     # returns an action based on the following ranking:
    #     #   1. if goal block has been located, start going in its direction
    #     #   2. if there are any closed doors, open them and search the rooms
    #     #   3. start searching through open rooms
    #
    #     # check if a goal block has been located
    #     if self._goal_blocks[self._searching_for]['location'] is not None \
    #             and self._picked_first is False:
    #         return Phase.PLAN_PATH_TO_BLOCK
    #
    #     # find closed door that none of the agents searched
    #     if len(self.find_doors(state, open=False, filter='everyone')) != 0:
    #         self._filter = 'everyone'
    #         return Phase.PLAN_PATH_TO_CLOSED_DOOR
    #
    #     # find closed doors that the agent has not searched
    #     if len(self.find_doors(state, open=False, filter='agent')) != 0:
    #         self._filter = 'agent'
    #         return Phase.PLAN_PATH_TO_CLOSED_DOOR
    #
    #     # find open door that the agent has not searched
    #     if len(self.find_doors(state, open=True, filter='agent')) != 0:
    #         self._filter = 'agent'
    #         return Phase.PLAN_PATH_TO_OPEN_DOOR
    #
    #     # find random open door
    #     # TODO: could replace with an 'explore' action
    #     if len(self.find_doors(state, open=True, filter='none')) != 0:
    #         self._filter = 'none'
    #         return Phase.PLAN_PATH_TO_OPEN_DOOR
    #
    # def find_doors(self, state, open=True, filter='none'):
    #     """
    #     @param filter: filter for the rooms. Values: 'none', 'agent', 'everyone'.
    #             * 'none': no filter
    #             * 'agent': only rooms that the agent has not visited
    #             * 'everyone': only rooms that no one has visited
    #     """
    #     all_doors = [door for door in state.values()
    #                  if 'class_inheritance' in door and 'Door' in door['class_inheritance']]
    #
    #     doors = None
    #     if filter == 'none':
    #         doors = all_doors
    #     if filter == 'agent':
    #         doors = [door for door in all_doors if door['room_name'] not in self._visited_rooms]
    #     if filter == 'everyone':
    #         doors = [door for door in all_doors
    #                  if door['room_name'] not in self._visited_rooms
    #                  and door['room_name'] not in self._com_visited_rooms]
    #     if open:
    #         return [door for door in doors
    #                 if door['is_open']]
    #     else:
    #         return [door for door in doors
    #                 if not door['is_open']]
    #
    # def check_surroundings_for_box(self, state):
    #     blocks = [(block['visualization'], block['location'], block['obj_id']) for block in state.values() if
    #               'class_inheritance' in block and 'CollectableBlock' in block['class_inheritance']]
    #
    #     # check if any of the found blocks are our goal block
    #     for block, location, obj_id in blocks:
    #         for key, goal_block in self._goal_blocks.items():
    #
    #             if block['colour'] == goal_block['visualization']['colour'] \
    #                     and block['shape'] == goal_block['visualization']['shape'] \
    #                     and block['size'] == goal_block['visualization']['size']:
    #                 self._goal_blocks[key]['location'] = location
    #                 self._goal_blocks[key]['id'] = obj_id
    #                 msg = self._mb.create_message(mt.FOUND_GOAL_BLOCK,
    #                                               block_vis=MessageBuilder.block_vis_str(
    #                                                   self._goal_blocks[key]['visualization']),
    #                                               location=MessageBuilder.location_str(location))
    #                 self.send_message(msg)
    #
    # def trust_message(self, mssg):
    #     return True
    #     # TODO: also check that mssg has right format
    #     pass
