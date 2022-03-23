import random
from typing import Dict
from agents1.GenericAgent import GenericAgent
from agents1.Message import MessageBuilder
from agents1.Phase import Phase

class LiarAgent(GenericAgent):
    # TODO: do agents share all of the observations, or can we choose what to share? | technically yes, but then colorblind anmd liar could not solve the problem
    # TODO: Are room sizes fixed? | layout the same, (map size, room size)
    # TODO: do we have to implement the filter_bw4t_observations? No, just set the attribute to None
    # TODO: where should we get the goal blocks, can I get them from state or do I have to go down and observe them ? We can observe them in the state

    # TODO: Do we want our liar to communicate or not?

    def __init__(self, settings:Dict[str,object]):
        super().__init__(settings, Phase.PLAN_PATH_TO_CLOSED_DOOR)
        self._lying_prob = 0.80

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
            content['room_name'] = f'room_{(int(content["room_name"][-1]) + 1) % 9}'  # increment the room

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
            return self.send_message(self.lie_message(msg))

        return self.send_message(msg)



