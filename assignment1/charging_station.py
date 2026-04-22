from __future__ import annotations
import random
import os
import sys
import math
import bisect
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from des_library import Simulation, Event, TimeWeightedStatistic, SampleStatistic, Counter


class Vehicle:
    def __init__(
            self, 
            vehicle_number: int,
            arrival_time: int, 
            battery_percentage: float
        ):
        self.number = vehicle_number
        self.arrival_time = arrival_time
        self.battery_percentage = battery_percentage
        self.depature_event: DepartureEvent = None
        self.reneging_event: RenegingEvent = None
        self.charging_start: int = -1


class ChargingStationModel:
    def __init__(self, num_stations: int = 4, termination_number: int = 800, seed: int = 70):
        random.seed(seed)

        self.termination_number = termination_number
        self.sim = Simulation()
        self.num_stations = num_stations
        self.stations: List[Vehicle] = []
        self.queue: List[Vehicle] = []

        self.completions = Counter()
        self.avg_queue_len = TimeWeightedStatistic()
        self.avg_waiting_time = SampleStatistic() 
        self.renegings = Counter() 
        self.total_queued_veh = Counter()
        self.charger_util = TimeWeightedStatistic()
        self.early_deps = Counter() 

    def run(self):
        schedule_arrival(self.sim, 0, self)
        self.sim.run()
    
    def queue_vehicle(self, vehicle):
        self.queue.append(vehicle)
        self.avg_queue_len.update(self.sim.current_time, len(self.queue))


    def leave_queue(self, vehicle: Vehicle, renege: bool = False):
        if renege:
            self.renegings.increment()
        else:
            self.avg_waiting_time.record(self.sim.current_time - vehicle.arrival_time)
        self.queue.remove(vehicle)
        self.total_queued_veh.increment()
        self.avg_queue_len.update(self.sim.current_time, len(self.queue))

    def charge_vehicle(self, vehicle):
        if len(self.stations) >= self.num_stations: 
            raise Exception("Station is full!")

        self.stations.append(vehicle)
        self.charger_util.update(self.sim.current_time, len(self.stations))
        print(f"Vehicle {vehicle.number} charges ({len(self.stations)}/{self.num_stations})")

    def leave_charging(self, leaving_vehicle: Vehicle, early_departure: bool) -> Optional[Vehicle]:
        """Removes vehicle from charging stations and removes and returns the first vehicle in queue."""
        self.stations.remove(leaving_vehicle)

        first_vehicle = None
        if len(self.queue) > 0:
            first_vehicle = self.queue[0]

        # Stats
        self.completions.increment()
        if early_departure:
            self.early_deps.increment()
        self.charger_util.update(self.sim.current_time, len(self.stations))

        if self.completions.value >= self.termination_number:
            self.terminate()
            return None
        return first_vehicle
    
    def report(self):
        now = self.sim.current_time
        print("-------- STATISTICS --------")
        print(f"Avg Queue Length     {self.avg_queue_len.mean(now):.2f}")
        print(f"Avg Waiting Time     {self.avg_waiting_time.mean():.2f}")
        print(f"Reneging Fraction    {(self.renegings.value / self.total_queued_veh.value):.2f}")
        print(f"Charger Utilisation  {self.charger_util.mean(now):.2f}")
        print(f"Early-Dep Franction  {(self.early_deps.value / self.completions.value):.2f}")
        print(self.early_deps.value )

    def terminate(self):
        self.report()
        self.sim.stop()

    @property
    def has_capacity(self) -> bool:
        return len(self.stations) < self.num_stations
    

######################################

def schedule_arrival(sim: Simulation, vehicle_number: int, model: ChargingStationModel):
    time = sim.current_time + 15 * (1 + math.sin(vehicle_number*math.pi / 12))**2 + 2
    arrival_event = ArrivalEvent(time, model, vehicle_number+1)
    sim.schedule(arrival_event)

def schedule_departure_event(sim: Simulation, vehicle: Vehicle, model: ChargingStationModel):
    vehicle.charging_start = sim.current_time
    dep_time = sim.current_time + get_charging_duration(vehicle)
    dep_event = DepartureEvent(dep_time, vehicle, model)
    vehicle.depature_event = dep_event
    sim.schedule(dep_event)


def get_charging_duration(vehicle: Vehicle):
    return 60 * (1-vehicle.battery_percentage)

def get_battery_percentage(vehicle_number):
    return 0.5 * abs(math.sin(vehicle_number * math.pi / 7) + 1)

#######################################

class ArrivalEvent(Event):
    def __init__(self, time: float, model: ChargingStationModel, vehicle_number: int):
        super().__init__(time)
        self.model = model
        self.vehicle_number = vehicle_number
    
    def execute(self, sim: Simulation):
        if self.cancelled: return
        print(f"Vehicle {self.vehicle_number} arrived.")
        battery_percentage = get_battery_percentage(self.vehicle_number)

        if len(self.model.queue) == 0 and self.model.has_capacity:
            new_vehicle = Vehicle(self.vehicle_number, sim.current_time, battery_percentage)
            self.model.charge_vehicle(new_vehicle)
            schedule_departure_event(sim, new_vehicle, self.model)
        else:
            patience = 20 * (1 + abs(math.cos(self.vehicle_number * math.e)))
            new_vehicle = Vehicle(self.vehicle_number, sim.current_time, battery_percentage)
            reneging_event = RenegingEvent(sim.current_time + patience, new_vehicle, self.model)
            new_vehicle.reneging_event = reneging_event
            self.model.queue_vehicle(new_vehicle)
            sim.schedule(reneging_event)

        # Schedule new arrival
        schedule_arrival(sim, self.vehicle_number, self.model)

class RenegingEvent(Event):
    def __init__(self, time: float, vehicle: Vehicle, model: ChargingStationModel):
        super().__init__(time)
        self.model = model
        self.vehicle = vehicle
    
    def execute(self, sim: Simulation):
        if self.cancelled: return
        print(f"Vehicle {self.vehicle.number} renegated.")
        self.model.leave_queue(self.vehicle, True)

class DepartureEvent(Event):
    def __init__(self, time: float, vehicle: Vehicle, model: ChargingStationModel, early: bool = False):
        super().__init__(time)
        self.model = model
        self.vehicle = vehicle
        self.early = early
    
    def execute(self, sim: Simulation):
        if self.cancelled: return
        print(f"Vehicle {self.vehicle.number} left.")
        # Replace vehicle in charging station
        new_vehicle = self.model.leave_charging(self.vehicle, self.early)

        if not new_vehicle: return
        new_vehicle.reneging_event.cancel()
        self.model.leave_queue(new_vehicle, False)
        self.model.charge_vehicle(new_vehicle)
        schedule_departure_event(sim, new_vehicle, self.model)

        # Handle early departure
        queue_len = len(self.model.queue)
        if queue_len > 0 and queue_len % 5 == 0:
            for veh in self.model.stations:
                departure_time = veh.charging_start + get_charging_duration(veh)
                if departure_time - sim.current_time <= 15: continue
                if random.random() > 0.2: continue
                print(f"Vehicle is departing early.")
                # Cancel original departure event
                veh.depature_event.cancel()
                # Create early departure event
                early_dep_time = sim.current_time + 2
                early_dep_event = DepartureEvent(early_dep_time, veh, self.model, True)
                veh.depature_event = early_dep_event
                sim.schedule(early_dep_event)


if __name__ == "__main__":
    model = ChargingStationModel(4, 800)
    model.run()

