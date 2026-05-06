from __future__ import annotations
import os, sys, random, math
from enum import Enum
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from des_library import Simulation, Event, Erlang, Exponential

# Number of vehicles
N = num_trucks= 3
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

class WasteType(Enum):
    ORGANIC = 1
    RECYCLABLE = 2
    GENERAL = 3

class TruckStatus(Enum):
    IDLE = 0
    BUSY = 1

class Request:
    def __init__(self, type: WasteType, arrival_time, service_time, end_event = None):
        self.type = type
        self.arrival_time = arrival_time
        self.service_time = service_time
        self.end_service_event = end_event

class Truck:
    def __init__(self, home_district):
        self.home_district = home_district
        self.current_district = home_district
        self.status: TruckStatus = TruckStatus.IDLE
        self.current_request = None

    def service(self, request, district):
        self.status = TruckStatus.BUSY
        self.current_request = request
        self.current_district = district

    @property
    def is_home(self) -> bool:
        return self.home_district == self.current_district


class WasteCollectionModel:
    def __init__(self, end_time, seed = 70):
        random.seed(seed)

        self.sim = Simulation()
        self.end_time = end_time

        self.district_queues: List[List[Request]] = [[] for i in range(num_districts)]
        self.trucks = []
        for i in range(num_trucks):
            self.trucks.append(Truck(home_district=i))

    
    def queue_len(self, district) -> int:
        return len(self.district_queues[district])
    
    def get_truck(self, district) -> Truck:
        for truck in self.trucks:
            if truck.home_district == district:
                return truck
            
    def pop(self, district) -> Request:
        return self.district_queues[district].pop(0)

    def run(self) -> None:
        # Schedule initial Arrival events
        for i in range(num_districts):
            self.sim.schedule(Arrival(0.0, self, i))
        
        # Run Simulation
        self.sim.run(stop_condition=lambda sim: sim.current_time > self.end_time)
        


class Arrival(Event):
    def __init__(self, time, model: WasteCollectionModel, district):
        super().__init__(time)
        self.district = district
        self.model = model

    def execute(self, sim: Simulation) -> None:
        if self.cancelled: return

        # Determine waste type and service time
        x = random.random()
        if x < p_organic_waste:
            waste = WasteType.ORGANIC
            service_time = type_1_distr.sample()
        if x < p_organic_waste + p_recyclable_waste:
            waste = WasteType.RECYCLABLE
            service_time = type_2_distr.sample()
        else:
            waste = WasteType.GENERAL
            service_time = type_3_distr.sample()

        # Queue request
        request = Request(waste, self.time, service_time)
        model.district_queues[self.district].append(request)

        # Check rerouting
        self.check_rerouting(sim)

        # Schedule new event
        inter_arrival_time = random.expovariate(request_arrival_rates[self.district])
        new_arrival = Arrival(self.time + inter_arrival_time, self.model, self.district)
        sim.schedule(new_arrival)

        # Check if the home truck is available
        home_truck: Truck = model.trucks[self.district]
        if home_truck.status == TruckStatus.IDLE:
            request = self.model.pop(self.district)
            home_truck.service(request, self.district)
            completion_time = self.time + request.service_time
            sim.schedule(EndService(self.model, completion_time, home_truck, self.district))


    def check_rerouting(self, sim: Simulation):
        home_truck = self.model.trucks[self.district]
        if self.model.queue_len(self.district) <= rerouting_thres:
            return
        if home_truck.status != TruckStatus.BUSY or home_truck.current_location != self.district:
            return
        sim.schedule(ReroutingEvent(self.time, model, home_truck))
        

class EndService(Event):
    def __init__(self, time, model: WasteCollectionModel, truck: Truck, district: int):
        super().__init__(time)
        self.model = model
        self.truck = truck
        self.district = district

    def execute(self, sim: Simulation) -> None:
        if self.cancelled: return

        # Choose next district to serve, starting from home district
        for i in range(num_districts):
            district = (self.truck.home_district + i) % num_districts
            request = self.model.pop(district)
            if not request: continue # Empty queue in this district

            if i > 0: # Not in home district, do Bernoulli trial
                x = random.random()
                if x >= friendliness: continue

            self.truck.service(request, district)
            completion_time = self.time + request.service_time
            sim.schedule(EndService(self.model, completion_time, self.truck, district))
            return

        # If no requests, go idle at home
        self.truck.status = TruckStatus.IDLE
        self.truck.current_district = self.truck.home_district
        self.truck.current_request = None


class ReroutingEvent(Event):
    def __init__(self, time, model: WasteCollectionModel, truck: Truck):
        super().__init__(time)
        self.model = model
        self.truck: Truck = truck

    def execute(self, sim: Simulation) -> None:
        if self.cancelled: return

        # Determine new service time of the request
        x = random.random()
        if x < p_organic_waste:
            service_time = type_1_distr.sample()
        if x < p_organic_waste + p_recyclable_waste:
            service_time = type_2_distr.sample()
        else:
            service_time = type_3_distr.sample()

        # Place request back in queue (head position) 
        interrupted_request = self.truck.current_request
        new_request = Request(self.truck.current_request.type, interrupted_request, service_time)
        self.model.district_queues[self.truck.current_district].insert(0, new_request)

        # Service head request in home district queue
        home_request = self.model.pop(self.truck.home_district)
        assert home_request
        self.truck.service(home_request)

        # Cancel original EndService event
        interrupted_request.end_service_event.cancel()

        # Schedule EndService for home request
        completion_time = self.time + home_request.service_time
        end_service = EndService(self.model, completion_time, self.truck, self.truck.home_district)
        home_request.end_service_event = end_service
        sim.schedule(end_service)
        

if __name__ == "__main__":
    model = WasteCollectionModel(seed=70)
    model.run()
    # model.report()