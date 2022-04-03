import random
from copy import copy
import numpy as np
import json

from agents1.GenericAgentTesting import GenericAgentTesting
from agents1.StrongAgent import StrongAgent
from bw4t.BW4TWorld import BW4TWorld
from bw4t.statistics import Statistics
from agents1.BW4TBaselineAgent import BaseLineAgent
from agents1.BW4THuman import Human
from agents1.LiarAgent import LiarAgent
from agents1.GenericAgent import GenericAgent
from agents1.StrongAgent import StrongAgent
from agents1.LazyAgent import LazyAgent
from agents1.ColorblindAgent import ColorblindAgent

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
import warnings

#TODO: 1. std, 2. fix success rate, 3. graphs? 4. sum all the results for individual agents as well, 5. prepare all the templates for agents
# TODO: do no return actions for thins like plan path

# amount of agents in one run
random_seed = random.randint(0, 42000)

DEBUG_MODE = False

number_of_agents = 2, 6 # from - to, the number of agents in each configuration is selkected randomly
number_of_combinations = 5  # number of random agent combinations
number_of_runs = 20  # runs for each combination
filename = 'data.json'  # result file
run_matrx_api = DEBUG_MODE
run_matrx_visualizer = DEBUG_MODE
matrx_paused = DEBUG_MODE
deadline = 1000 # max number of ticks
tick_duration = 0 # 0 = fastest

agent_pool = {
    # "baseline": {
    #     "agent": {'name': 'baseline', 'botclass': BaseLineAgent, 'settings': {}},
    #     "join_prob": 0.7,
    #     "max": 0,
    #     "added": 0
    # },
    # "generic": {  # name here has to match name in agent_pool[agent_name][agent]
    #     "agent": {'name': 'generic', 'botclass': GenericAgent, 'settings': {}},
    #     "join_prob": 0.5,  # probability that this agent ends up in the lineup
    #     "max": 0,  # max number of this agent type
    #     "added": 0  # Do not change this one
    # },
    "strong": {  # name here has to match name in agent_pool[agent_name][agent]
        "agent": {'name': 'strong', 'botclass': StrongAgent, 'settings': {}},
        "join_prob": 0.5,  # probability that this agent ends up in the lineup
        "max": 4,  # max number of this agent type
        "added": 0  # Do not change this one
    },
    "colorblind": {  # name here has to match name in agent_pool[agent_name][agent]
        "agent": {'name': 'colorblind', 'botclass': ColorblindAgent, 'settings': {}},
        "join_prob": 0.5,  # probability that this agent ends up in the lineup
        "max": 4,  # max number of this agent type
        "added": 0  # Do not change this one
    },
    "liar": {  # name here has to match name in agent_pool[agent_name][agent]
        "agent": {'name': 'liar', 'botclass': LiarAgent, 'settings': {}},
        "join_prob": 0.5,  # probability that this agent ends up in the lineup
        "max": 4,  # max number of this agent type
        "added": 0  # Do not change this one
    },
    "lazy": {  # name here has to match name in agent_pool[agent_name][agent]
        "agent": {'name': 'lazy', 'botclass': LazyAgent, 'settings': {}},
        "join_prob": 0.5,  # probability that this agent ends up in the lineup
        "max": 4,  # max number of this agent type
        "added": 0  # Do not change this one
    },
}

BENCHMARK_WORLDSETTINGS: dict = {
    'deadline': deadline,  # Ticks after which world terminates anyway
    'tick_duration': tick_duration,  # Set to 0 for fastest possible runs.
    'random_seed': random_seed,
    'verbose': False,
    'matrx_paused': matrx_paused,
    'run_matrx_api': run_matrx_api,  # If you want to allow web connection
    'run_matrx_visualizer': run_matrx_visualizer,  # if you want to allow web visualizer

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
        print(i)
        agent_combinations.append([])

        while len(agent_combinations[i]) != agent_number:
            for agent in agent_pool.values():
                if len(agent_combinations[i]) == agent_number:
                    break
                print(agent)
                if agent["max"] != agent["added"]:

                    if random.uniform(0, 1) <= agent["join_prob"]:
                        print(agent["agent"]["name"], flush=True)
                        agent_copy = copy(agent["agent"])
                        agent_copy["name"] += str(agent["added"])
                        agent_combinations[i].append(agent_copy)
                        agent["added"] += 1

        setup.append({"agents": copy(agent_pool)})

        for agent in agent_pool.values():
            agent["added"] = 0

    return agent_combinations, setup

if __name__ == "__main__":

    agent_combinations, setup = make_agent_combinations(agent_pool, random.randint(number_of_agents[0], number_of_agents[1]), number_of_combinations)


    games = {
        "results": None
    }

    strat_ticks = []
    strat_success_rate = 0
    strat_moves = 0
    strat_agent_messages = {
        key: 0 for key in agent_pool.keys()
    }
    strat_agent_drops = {
        key: 0 for key in agent_pool.keys() # for easier comparison metrics are dictionaries containing agents
    }
    strat_agent_moves = {
        key: 0 for key in agent_pool.keys()
    }


    print("Started benchmark...")
    for idx, agent_combination in enumerate(agent_combinations):
        success_rate = 0
        total_agent_messages = None
        total_agent_drops = None
        total_agent_moves = None
        total_ticks = []
        print(agent_combination)
        for i in range(0, number_of_runs):
            print(f"COMBINATION: {idx} RUN: {i}", flush=True)

            random_seed = random.randint(0, 42000)
            BENCHMARK_WORLDSETTINGS['random_seed'] = random_seed

            world=BW4TWorld(agent_combination,worldsettings=BENCHMARK_WORLDSETTINGS).run()
            results = Statistics(world.getLogger().getFileName())
            print(results)

            total_ticks.append(int(results.getLastTick())) # add tick to list

            if results.isSucces() == 'True':
                success_rate += 1

            print(success_rate)

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

        strat_success_rate += success_rate
        strat_moves += sum(total_agent_moves.values())
        strat_ticks += total_ticks

        for (messages_key, messages_value), (drops_key, drops_value), (moves_key, moves_value)\
                in zip(total_agent_messages.items(), total_agent_drops.items(), total_agent_moves.items()):

            strat_agent_messages[messages_key.rstrip("0123456789")] += messages_value
            strat_agent_moves[moves_key.rstrip("0123456789")]+= moves_value
            strat_agent_drops[drops_key.rstrip("0123456789")] += drops_value


        games[f"combination_{idx}"] = {
            "setup": results.getAgents(),
            "seed": random_seed,
            "success_rate": success_rate / number_of_runs,
            "avg_moves": sum(total_agent_moves.values()) / number_of_runs,
            "avg_ticks": sum(total_ticks) / number_of_runs,
            "game_ticks": total_ticks,
            "tick_std": np.std(total_ticks),
            "avg_agent_messages": {key : total_agent_messages[key] / number_of_runs for key in total_agent_messages},
            "avg_agent_drops": {key : total_agent_drops[key] / number_of_runs for key in total_agent_drops},
            "avg_agent_moves": {key : total_agent_moves[key] / number_of_runs for key in total_agent_moves},
        }

    games["results"] = {
        "agents": list(agent_pool.keys()),
        "success_rate": strat_success_rate / total_runs,
        "avg_moves": strat_moves / total_runs,
        "avg_ticks": sum(strat_ticks) / total_runs,
        "tick_std": np.std(strat_ticks),
        "avg_agent_messages": {key : strat_agent_messages[key] / total_runs for key in strat_agent_messages},
        "avg_agent_drops": {key: strat_agent_drops[key] / total_runs for key in strat_agent_drops},
        "avg_agent_moves": {key: strat_agent_moves[key] / total_runs for key in strat_agent_moves},
    }

    with open(filename, 'w') as fp:
        json.dump(games, fp, indent=4)
