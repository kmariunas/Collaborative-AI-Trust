import json
import math
import os
from json import JSONEncoder
from typing import List

from agents1.Message import MessageType, MessageBuilder
from agents1.util import rooms_match, visualizations_match, locations_match


class TrustSystemEncoder(JSONEncoder):
    def default(self, o):
        return o._dict_


def _update_score(own_score, com_score):
    acc_own, tot_own = own_score  # accurate and total experiences
    acc_com, tot_com = com_score

    # the communicated score has more uncertainty than our score
    if tot_com < 0.8 * acc_own:
        return own_score  # so dont update our score

    if tot_own <= tot_com:
        common_denominator = tot_com
        keep = acc_com

        old_denominator = tot_own
        scale = acc_own
    else:
        common_denominator = tot_own
        keep = acc_own

        old_denominator = tot_com
        scale = acc_com

    # formula for update:
    # new score = [avg(common_den * scale / old_den, keep),
    #              common_den]
    avg = math.floor(
        ((common_denominator * scale / old_denominator) + keep)
        / 2)  # take floor of average

    return (avg, common_denominator)


class TrustSystem:

    def __init__(self, agent_name: str, team_members: List[str], goal_blocks, drop_off_locations):
        self._agent_name = agent_name
        self._team_members_names = team_members
        self._goal_blocks = goal_blocks
        self._drop_off_locations = drop_off_locations
        self._messages = self._init_messages()  # dict with agent names as keys, and list of (msg, tick) as value
        self._team_members = self.read_memory_file()

        self.reliability_threshold = 0.6
        self.competence_threshold = 0.6

    def read_memory_file(self):
        file_path = self._agent_name + ".json"
        if os.path.isfile(file_path):
            with open(file_path, "r") as file:
                return self.parse_file(file)
        else:
            return self.init_trust()

    def init_trust(self):
        agents_trust = dict()
        for team_member in self._team_members_names:
            agents_trust[team_member] = {
                "competence": (0, 1),
                "reliability": (0, 1)
            }
        self.write_file(agents_trust)
        return agents_trust

    def trust_message(self, msg):
        team_member = msg['from_id']
        if msg['type'] == MessageType.GOAL_BLOCKS and self._is_reliable(team_member):
            return True
        elif msg['type'] == MessageType.MOVE_TO_ROOM and self._is_reliable(team_member) \
                and self._is_competent(team_member):
            return True
        elif msg['type'] == MessageType.OPEN_DOOR and self._is_reliable(team_member):
            return True
        elif msg['type'] == MessageType.SEARCHING_ROOM and self._is_reliable(team_member) \
                and self._is_competent(team_member):
            return True
        elif msg['type'] == MessageType.FOUND_GOAL_BLOCK and self._is_reliable(team_member):
            return True
        elif msg['type'] == MessageType.FOUND_BLOCK and self._is_reliable(team_member):
            return True
        elif msg['type'] == MessageType.PICK_UP_BLOCK and self._is_reliable(team_member) \
                and self._is_competent(team_member):
            return True
        elif msg['type'] == MessageType.DROP_BLOCK and self._is_reliable(team_member):
            return True

        return False

    def update(self, received_messages, tick):
        # update trust points
        for team_member, messages in received_messages.items():
            for msg in messages:
                if msg['type'] == MessageType.REPUTATION and self._is_reliable(msg['from_id']):
                    self._update_reputation(msg['scores'])

                # update reliability and competence of team member
                elif msg['type'] == MessageType.GOAL_BLOCKS:
                    self._increase_reliability(team_member)

                elif msg['type'] == MessageType.MOVE_TO_ROOM:
                    if self._mtr_contradiction(msg, tick):
                        self._decrease_competence(team_member)

                elif msg['type'] == MessageType.OPEN_DOOR:
                    contradiction = self._od_contradiction(msg, tick)
                    if contradiction == 1:
                        self._decrease_reliability(team_member)
                    if contradiction == 2:
                        self._decrease_competence(team_member)

                elif msg['type'] == MessageType.FOUND_BLOCK:
                    self._increase_reliability(team_member)

                # elif msg['type'] == MessageType.FOUND_GOAL_BLOCK:
                #     if self._fgb_contradiction(msg):
                #         self._decrease_reliability(team_member)
                #     else:
                #         self._increase_reliability(team_member)

                elif msg['type'] == MessageType.SEARCHING_ROOM:
                    if self._sr_contradiction(msg):
                        self._decrease_reliability(team_member)
                        self._decrease_competence(team_member)
                    else:
                        self._increase_reliability(team_member)
                        self._increase_competence(team_member)

                elif msg['type'] == MessageType.PICK_UP_BLOCK:
                    if self._pb_contradiction(msg):
                        self._decrease_reliability(team_member)
                    else:
                        self._increase_reliability(team_member)

                elif msg['type'] == MessageType.DROP_BLOCK:
                    contradiction = self._db_contradiction(msg)
                    if contradiction == 0:
                        self._increase_competence(team_member)
                        self._increase_reliability(team_member)
                    elif contradiction == 1:
                        self._decrease_competence(team_member)
                    elif contradiction == 2:
                        self._decrease_reliability(team_member)

                # add new messages to private dict
                self._messages[team_member].append((msg, tick))  # also store the time stamp of the message
        self.write_file()

    def parse_file(self, file):
        res = json.loads(file.read())

        for team_member in self._team_members_names:
            if team_member not in res:
                res[team_member] = {
                    "competence": (0, 1),
                    "reliability": (0, 1)
                }
        return res

    def write_file(self, agent_trust=None):
        file_path = self._agent_name + ".json"
        with open(file_path, "w") as file:
            if agent_trust:
                file.write(json.dumps(agent_trust, cls=TrustSystemEncoder, indent=2))
            else:
                file.write(json.dumps(self._team_members, cls=TrustSystemEncoder, indent=2))

    def _init_messages(self):
        messages = dict()
        for team_member in self._team_members_names:
            messages[team_member] = list()
        return messages

    def _is_reliable(self, team_member):
        accurate, total = self._team_members[team_member]['reliability']
        return accurate / total >= self.reliability_threshold

    def _is_competent(self, team_member):
        accurate, total = self._team_members[team_member]['competence']
        return accurate / total >= self.reliability_threshold

    def _increase_reliability(self, team_member):
        accurate, total = self._team_members[team_member]['reliability']
        self._team_members[team_member]['reliability'] = (accurate + 1, total + 1)

    def _decrease_reliability(self, team_member):
        accurate, total = self._team_members[team_member]['reliability']
        self._team_members[team_member]['reliability'] = (accurate, total + 1)

    def _increase_competence(self, team_member):
        accurate, total = self._team_members[team_member]['competence']
        self._team_members[team_member]['competence'] = (accurate + 1, total + 1)

    def _decrease_competence(self, team_member):
        accurate, total = self._team_members[team_member]['competence']
        self._team_members[team_member]['competence'] = (accurate, total + 1)

    def _mtr_contradiction(self, msg, current_tick):
        """
        Method returns True if there is a contradiction
        """
        # TODO: improve ie:
        team_member = msg['from_id']
        if len(self._messages[team_member]) == 0:
            return False

        # check in previous messages if agent changed their mind
        last_message, tick = self._messages[team_member][-1]
        if last_message['type'] == MessageType.MOVE_TO_ROOM:
            return True
        # did the agent really search the room, or they only said they would
        # it takes 5 ticks to search a room
        if last_message['type'] == MessageType.SEARCHING_ROOM and current_tick - tick < 5:
            return True

        return False

    def _od_contradiction(self, msg, current_tick):
        """
        Checks if there is a contradiction with the last message when an agent says it is opening some room door
        """
        team_member = msg['from_id']
        last_message, tick = self._messages[team_member][-1]

        if last_message['type'] == MessageType.MOVE_TO_ROOM:
            if not rooms_match(last_message, msg):
                return 1
        # check if agent said they would search a room but did not
        # note: searching a room takes 5-6 seconds
        if last_message['type'] == MessageType.SEARCHING_ROOM and current_tick - tick < 5:
            return 2

        return 0

    def _fgb_contradiction(self, msg):
        """
        Method returns True if there is a contradiction
        """
        # check that the found goal block exists
        block = msg['visualization']
        matched_one = False
        for goal_block in self._goal_blocks:
            if visualizations_match(block, goal_block['visualization']):
                matched_one = True

        if not matched_one:
            return True

        # TODO: do other smarter check
        return False

    def _sr_contradiction(self, msg):  # SEARCH_ROOM
        """ Checks if there is a contradiction with the last message when an agent says it is searching a room

        @param msg: received message
        @return: True if room id does not match with the last message or if the last message is unrelated, otherwise False
        """
        team_member = msg['from_id']
        last_message, _ = self._messages[team_member][-1]

        # check if the agent moved to that room before
        if last_message['type'] == MessageType.MOVE_TO_ROOM or last_message['type'] == MessageType.OPEN_DOOR:
            return not rooms_match(last_message=last_message, msg=msg)

        return False

    def _pb_contradiction(self, msg):
        """
        Method returns True if there is a contradiction
        """
        # check that the block is exists
        block = msg['visualization']
        matched_one = False
        for goal_block in self._goal_blocks:
            # check that colour is not None (ie: colorblind did not pick up this block
            if visualizations_match(block, goal_block['visualization']):
                matched_one = True

        if not matched_one:
            return True

        # check if any agent found the same goal block at the same location
        latest_tick = -1
        last_message = None
        for team_member, messages in self._messages.items():
            for message, tick in messages:
                if message['type'] == MessageType.FOUND_GOAL_BLOCK:
                    # check that the block visualizations and
                    if visualizations_match(block, message['visualization']):
                        if tick > latest_tick:
                            latest_tick = tick
                            last_message = message

        # if the locations match, then increase the agent's reliability
        if last_message is not None and locations_match(msg['location'], last_message['location']):
            self._increase_reliability(last_message['from_id'])
            return False

        return True

    def _db_contradiction(self, msg):
        # TODO: change doc
        """ Checks if the agent has ever picked up the block it is dropping and if the agent did not drop it afterwards

        @param msg: received message
        @return: 0 if there is no contradiction
                 1 if there is a contradiction indicating that the agent is not competent
                 2 if there is a contradiction indicating that the agent is not reliable
        """
        team_member = msg['from_id']
        last_message, _ = self._messages[team_member][-1]
        goal_block_match = False

        # check if the block the agent dropped matches any of the goal blocks
        for goal_block in self._goal_blocks:
            if visualizations_match(goal_block['visualization'], msg['visualization']):
                goal_block_match = True

        if goal_block_match is False:
            return 2

        # check if the block has been dropped at the drop-off location
        location_match = False
        for drop_off in self._drop_off_locations:
            if locations_match(msg['location'], drop_off):
                location_match = True

        if not location_match:
            return 1

        # check if the agent has ever picked up the block he is dropping
        for message, _ in reversed(self._messages[team_member]):
            # if message['type'] == MessageType.DROP_BLOCK:
            #     if visualizations_match(msg['visualization'], message['visualization']):
            #         # the last thing (that is relevant) that the agent did was drop the same block it is dropping right
            #         # now, therefore contradiction
            #         return 2

            if message['type'] == MessageType.PICK_UP_BLOCK:
                if visualizations_match(msg['visualization'], message['visualization']):
                    return 0

        return 2

    def reputation_message(self, msg_builder: MessageBuilder):
        team_members_scores = dict()

        for team_member in self._team_members_names:
            team_members_scores[team_member] = {
                "reliability": self._team_members[team_member]["reliability"],
                "competence": self._team_members[team_member]["competence"]
            }
        msg = msg_builder.create_message(MessageType.REPUTATION, scores=team_members_scores)
        return msg

    def _update_reputation(self, scores):
        for agent, score in scores.items():
            if agent in self._team_members_names:
                # update reliability
                updated = _update_score(self._team_members[agent]['reliability'], score['reliability'])
                self._team_members[agent]['reliability'] = updated

                # update competence
                updated = _update_score(self._team_members[agent]['competence'], score['competence'])
                self._team_members[agent]['competence'] = updated
        self.write_file()

# TODO: check locations (ie: goal block is not a wall or goal block is inside the room the agent said they will search)