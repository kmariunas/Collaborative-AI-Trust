from agents1.ColorblindAgent import ColorblindAgent
from agents1.LazyAgent import LazyAgent
from agents1.LiarAgent import LiarAgent
from agents1.StrongAgent import StrongAgent
from bw4t.BW4TWorld import BW4TWorld
from bw4t.statistics import Statistics

"""
This runs a single session. You have to log in on localhost:3000 and 
press the start button in god mode to start the session.
"""

if __name__ == "__main__":
    agents = [
        # {'name':'lazy', 'botclass':LazyAgent, 'settings':{}}, # 'slowdown':10
        # {'name':'liar2', 'botclass':LiarAgent, 'settings':{}},
        {'name': 'liar', 'botclass': LiarAgent, 'settings': {}},
        # {'name': 'colorblind', 'botclass': ColorblindAgent, 'settings': {}},
        # {'name': 'strong', 'botclass': StrongAgent, 'settings': {}}
        ]

    print("Started world...")
    world=BW4TWorld(agents).run()
    print("DONE!")
    print(Statistics(world.getLogger().getFileName()))
