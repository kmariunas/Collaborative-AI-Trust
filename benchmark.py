import random
from copy import copy
import numpy as np
import json
from bw4t.BW4TWorld import BW4TWorld
from bw4t.statistics import Statistics
from agents1.BW4TBaselineAgent import BaseLineAgent
from agents1.BW4THuman import Human
from agents1.LiarAgent import LiarAgent
from typing import Final, List
from matrx.actions.move_actions import MoveEast, MoveSouth, MoveWest
from matrx.actions import MoveNorth, OpenDoorAction, CloseDoorAction
from matrx.grid_world import GridWorld, DropObject, GrabObject, AgentBody
from matrx import WorldBuilder
from matrx.world_builder import RandomProperty
from matrx.agents import SenseCapability
from matrx.utils import get_room_locations
from bw4t.BW4TBlocks import CollectableBlock, GhostBlock
from agents1.BW4THuman import Human
from bw4t.CollectionGoal import CollectionGoal
from bw4t.BW4TLogger import BW4TLogger
from bw4t.BW4THumanBrain import HumanBrain

BENCHMARK_WORLDSETTINGS: dict = {
    'deadline': 3000,  # Ticks after which world terminates anyway
    'tick_duration': 0.1,  # Set to 0 for fastest possible runs.
    'random_seed': 1,
    'verbose': False,
    'matrx_paused': False,
    'run_matrx_api': False,  # If you want to allow web connection
    'run_matrx_visualizer': False,  # if you want to allow web visualizer

    'key_action_map': {  # For the human agents
        'w': MoveNorth.__name__,
        'd': MoveEast.__name__,
        's': MoveSouth.__name__,
        'a': MoveWest.__name__,
        'q': GrabObject.__name__,
        'e': DropObject.__name__,
        'r': OpenDoorAction.__name__,
        'f': CloseDoorAction.__name__,
    },
    'room_size': (6, 4),  # width, height
    'nr_rooms': 9,  # total number of rooms.
    'rooms_per_row': 3,  # number of rooms per row.
    'average_blocks_per_room': 2,
    'block_shapes': [0, 1, 2],  # possible shapes of the blocks
    'block_colors': ['#0008ff', '#ff1500', '#0dff00'],  # possible colors of blocks
    'room_colors': ['#0008ff', '#ff1500', '#0dff00'],
    'wall_color': "#8a8a8a",
    'drop_off_color': "#878787",
    'block_size': 0.5,
    'nr_drop_zones': 1,  # All code assumes this is 1, don't change this.
    'nr_blocks_needed': 3,  # nr of drop tiles/target blocks
    'hallway_space': 2,  # width, height of corridors

    'agent_sense_range': 2,  # the range with which agents detect other agents
    'block_sense_range': 1,  # the range with which agents detect blocks
    'other_sense_range': np.inf,  # the range with which agents detect other objects (walls, doors, etc.)
    'agent_memory_decay': 5,  # we want to memorize states for seconds / tick_duration ticks
    'fov_occlusion': True  # true if walls block vision. Not sure if this works at all.

}

def make_agent_combinations(agent_pool, agent_number, number_of_combinations):
    print("Creating groups...")
    agent_combinations = []
    setup = []

    for i in range(0, number_of_combinations):
        agent_combinations.append([])

        while len(agent_combinations[i]) != agent_number:
            for agent in agent_pool.values():
                if len(agent_combinations[i]) == agent_number:
                    break

                if agent["max"] != agent["added"]:
                    if random.uniform(0, 1) <= agent["join_prob"]:
                        agent_copy = copy(agent["agent"])
                        agent_copy["name"] += str(agent["added"])
                        agent_combinations[i].append(agent_copy)
                        agent["added"] += 1

        setup.append({"agents": copy(agent_pool)})

        for agent in agent_pool.values():
            agent["added"] = 0

    return agent_combinations, setup

if __name__ == "__main__":
    #amount of agents in one run
    agent_number = 5
    number_of_combinations = 2 #number of random agent combinations
    number_of_runs = 3 # runs for each combination
    filename = 'data.json' # result file

    agent_pool = {
        "liar": {
            "agent": {'name':'liar', 'botclass':LiarAgent, 'settings':{}},
            "join_prob": 0.5, # probability that this agent ends up in the lineup
            "max": 10, #max number of this agent type
            "added": 0 # Do not change this one
        },
        "baseline": {
            "agent": {'name':'agent', 'botclass':BaseLineAgent, 'settings':{}},
            "join_prob": 0.7,
            "max": 10,
            "added": 0
        },
    }

    agent_combinations, setup = make_agent_combinations(agent_pool, agent_number, number_of_combinations)

    games = {}

    print("Started benchmark...")
    for idx, agent_combination in enumerate(agent_combinations):
        success_rate = 0
        total_agent_messages = None
        total_agent_drops = None
        total_agent_moves = None
        total_ticks = 0

        for i in range(0, number_of_runs):
            print(f"COMBINATION: {idx} RUN: {i}", flush=True)
            world=BW4TWorld(agent_combination,worldsettings=BENCHMARK_WORLDSETTINGS).run()
            results = Statistics(world.getLogger().getFileName())
            print(results)

            total_ticks += int(results.getLastTick())

            if results.isSucces():
                success_rate += 1

            if total_agent_messages is None:
                total_agent_drops = results._drops
                total_agent_messages = {key : int(results._messages[key]) for key in results._messages}
                total_agent_moves = results._moves
            else:
                for (messages_key, messages_value), (drops_key, drops_value), (moves_key, moves_value)\
                        in zip(results._messages.items(), results._drops.items(), results._moves.items()):
                    total_agent_messages[messages_key] += int(messages_value)
                    total_agent_drops[drops_key] += drops_value
                    total_agent_moves[moves_key] += moves_value

        games[f"game_{idx}"] = {
            "setup": results.getAgents(),
            "success_rate": success_rate / number_of_runs,
            "avg_moves": sum(total_agent_moves.values()) / number_of_runs,
            "avg_ticks": total_ticks / number_of_runs,
            "avg_agent_messages": {key : total_agent_messages[key] / number_of_runs for key in total_agent_messages},
            "avg_agent_drops": {key : total_agent_drops[key] / number_of_runs for key in total_agent_drops},
            "avg_agent_moves": {key : total_agent_moves[key] / number_of_runs for key in total_agent_moves},
        }

    with open(filename, 'w') as fp:
        json.dump(games, fp, indent=2)
