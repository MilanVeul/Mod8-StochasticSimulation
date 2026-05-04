from __future__ import annotations
import os, sys, random, math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from des_library import Simulation, Event, Erlang, Exponential

# Number of vehicles
N = num_vehicles = 3
# Numer of districts
M = num_districts = 3

# Arrival process

request_arrival_rates = [0.4] * num_districts
q_1 = p_organic_waste = 1/3
q_2 = p_recyclable_waste = 1/3
q_3 = p_general = 1 - q_1 - q_2

# Service time distributions
type_1_distr = Erlang(k=2, mean=1)
type_2_distr = Erlang(k=3, mean=1.5)
type_3_distr = Exponential(mean=1.0)

# Serve probability (friendliness)
p = friendliness = 0.5
# Rerouting threshold
K = rerouting_thres = 5


class WasteCollectionModel:
    def __init__(seed = 70):
        random.seed(seed)

class Arrival(Event):
    def __init__():
        pass

class ReroutingEvent(Event):
    def __init__():
        pass