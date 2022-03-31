from agents1.ColorblindAgent import ColorblindAgent
from agents1.LiarAgent import LiarAgent
from bw4t.BW4TWorld import BW4TWorld
from bw4t.statistics import Statistics
from agents1.GenericAgent import GenericAgent

"""
This runs a single session. You have to log in on localhost:3000 and 
press the start button in god mode to start the session.
"""

if __name__ == "__main__":
    agents = [
        {'name':'agent1', 'botclass':ColorblindAgent, 'settings':{}}, # 'slowdown':10
        {'name':'liar', 'botclass':GenericAgent, 'settings':{}},
        ]

    print("Started world...")
    world=BW4TWorld(agents).run()
    print("DONE!")
    print(Statistics(world.getLogger().getFileName()))
