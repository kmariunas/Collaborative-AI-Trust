
from typing import Dict
from agents1.GenericAgent import GenericAgent
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
