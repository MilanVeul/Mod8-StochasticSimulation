from __future__ import annotations
import sys, os, random, math
from enum import Enum
from typing import List, Optional
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from des_library import Simulation, Event, Uniform, Exponential

import simtime
from simtime import DayPart
from long_term_statistics import LongTermStatistic

SHOWUP_PROBABILITY = 0.84

NUM_CHAIRS = 3
NUM_SCANNERS_OFFICE_HOURS = 2
NUM_SCANNERS_OUTSIDE_OFFICE_HOURS = 1

SLOTS_PER_DAYPART = 16
MAX_SCHEDULED_OUTPATIENTS_MORNING = 4
MAX_SCHEDULED_OUTPATIENTS_AFTERNOON = 3

class PatientType(Enum):
    IN = 1
    OUT = 2
    EMERGENCY = 3

class Patient:
    def __init__(self, patient_type: PatientType, request_time: float):
        self.type: PatientType = patient_type
        self.request_time: int = request_time 
        self.arrival_time: int = -1

class CTScannerModel:
    def __init__(self, seed: int):
        self.sim: Simulation = Simulation()
        self.init_distribution(seed)

        self.emergency_queue: List = []
        self.normal_queue: List = []

        # Initialize schedule
        self.clear_schedule() 
        self.waiting_list: List = []
        
        # Simulation starts in the night
        self.active_scanners = 0

    def init_distribution(self, seed):
        random.seed(seed)
        self.distr_scan_time = Uniform(10, 19)
        self.distr_emergency_patients = Exponential(24 / 24 * 60) # 24 per 24 hours
        self.distr_out_patients = Exponential(8 / 23 * 60) # 23 for 8 office hours
        self.distr_in_patients = Exponential(24 / 153 * 60) # maximum of 153 per 24 hours
    
    def set_statistics_method(self, stat: LongTermStatistic):
        self.stat_holder = stat
        self.sim.on_before_event(stat.before_hook)
        self.sim.on_after_event(stat.after_hook)

    def run(self):
        # Schedule first events
        self.sim.schedule(RequestScanEvent(0, self, PatientType.IN))
        self.sim.schedule(RequestScanEvent(0, self, PatientType.OUT))
        self.sim.schedule(RequestScanEvent(0, self, PatientType.EMERGENCY))
        self.sim.schedule(ScheduleNextWeekEvent(self, 5*24*60 - 1)) # Scan first ScheduleNextWeekEvent on Friday 23:59

        self.sim.run()

    def report(self):
        return self.stat_holder.reports

    def clear_schedule(self):
        # Represents the number of scheduled patients per time slot
        # For each slot: [total # patients planned, # outpatients planned]
        self.schedule: List = [[[[0,0] for _ in range(SLOTS_PER_DAYPART)] 
                                for _ in range(2)] 
                               for _ in range(5)]

    def add_to_queue(self, patient: Patient):
        """Adds a patient to the correct priority queue."""
        if patient.type == PatientType.EMERGENCY:
            self.emergency_queue.append(patient)
        else:
            self.normal_queue.append(patient)
    
    def next_patient(self) -> Optional[Patient]:
        """Removes the first patient from the queue and returns it."""
        if len(self.emergency_queue) > 0:
            return self.emergency_queue.pop(0)
        if len(self.normal_queue) > 0:
            return self.normal_queue.pop(0)
        return None

    # Methods to log statistics
    def record_arrival(self, patient: Patient):
        time = self.sim.current_time
        # Record new patient
        self.stat_holder.stat_total_patients.increment()
        # Record whether they wait outside
        if self.queue_size > NUM_CHAIRS:
            self.stat_holder.stat_wait_outside.increment()
        # Record if it is an inpatient that requested during office hours, but is helped after office hours
        requested_during_office = simtime.daypart(patient.request_time) != DayPart.OUTSIDE_OFFICE_HOURS
        scheduled_after_office = simtime.daytime(time) == 16*60
        if requested_during_office and scheduled_after_office:
            self.stat_holder.stat_inp_req_office_wait.increment()
        # Record wait start
        patient.arrival_time = time

    def record_access_time(self, patient: Patient):
        if patient.type != PatientType.OUT: return
        days = simtime.day(self.sim.current_time) - simtime.day(patient.request_time)
        self.stat_holder.stat_access_time.record(days)

    def record_request(self, patient: Patient):
        # We only record inpatients during office hours
        if patient.type != PatientType.IN:
            return
        is_office_hours = simtime.daypart(self.sim.current_time) != DayPart.OUTSIDE_OFFICE_HOURS
        if not is_office_hours:
            return
        self.stat_holder.stat_inp_req_office_total.increment()

    def update_scanner_util(self):
        batch_time = self.stat_holder.batch_time()
        self.stat_holder.stat_scanner_util.update(batch_time, self.active_scanners)
    
    def record_wait_time(self, patient: Patient):
        wait_time = self.sim.current_time - patient.arrival_time
        # print(wait_time)
        if patient.type == PatientType.EMERGENCY:
            self.stat_holder.stat_wait_time_emergency.record(wait_time)
        elif patient.type == PatientType.OUT:
            self.stat_holder.stat_wait_time_out.record(wait_time)
    
    @property
    def queue_size(self) -> int:
        """Returns the total queue size."""
        return len(self.normal_queue) + len(self.emergency_queue)
    
    @property
    def in_office_hours(self) -> bool:
        time = self.sim.current_time
        weekday = simtime.day(time) <= 4
        office_hours = 8*60 <= simtime.daytime(time) <= 16*60
        if weekday and office_hours:
            return True
        return False
    
    @property
    def scanners(self) -> int:
        if self.in_office_hours:
            return NUM_SCANNERS_OFFICE_HOURS
        return NUM_SCANNERS_OUTSIDE_OFFICE_HOURS


class RequestScanEvent(Event):
    """Handles a request for a scan for all patient types, and schedules a new request."""
    def __init__(self, time, model, patient_type: PatientType):
        super().__init__(time)
        self.model: CTScannerModel = model
        self.patient_type = patient_type

    def get_current_inpatient_rate(self, simulation_time):
        """Returns the rate of the inpatient requests as determined in the project report."""
        daytime = simtime.daytime(simulation_time)
        if daytime < 9*60 or daytime > 15*60:
            return 9 / (24*60) 
        else:
            return (9 + 72 * (1 + math.cos(2*math.pi*daytime / 180 + math.pi))) / (24*60)
    
    def next_inpatient_request_time(self, simulation_time):
        """Returns the next inpatient request time."""
        time = simulation_time
        while True:
            time = time + self.model.distr_in_patients.sample()

            current_rate = self.get_current_inpatient_rate(time)
            lambda_zero = 1 / self.model.distr_in_patients.mean
            p = current_rate / lambda_zero

            if random.random() < p:
                return time # We accept this sample

    def next_outpatient_request_time(self, simulation_time):
        next_time = simulation_time + self.model.distr_out_patients.sample()
        if simtime.daytime(next_time) > 16*60: # Time is after office hours
            overtime = simtime.daytime(next_time) - 16*60
            day = simtime.day(simulation_time)
            next_time = day*24*60 + 8*60 + overtime
        return next_time

    def execute(self, sim: Simulation):
        patient = Patient(self.patient_type, sim.current_time)

        if patient.type == PatientType.EMERGENCY:
            self.move_to_waiting_room(sim, patient)            

        # Schedule patient
        if self.patient_type == PatientType.IN:
            if simtime.weekday(sim.current_time) >= 5: # Weekend
                self.move_to_waiting_room(sim, patient)
            else:
                schedule_inpatient(self.model, patient, sim.current_time)
        elif self.patient_type == PatientType.OUT:
            schedule_outpatients(self.model, [patient], sim.current_time)
        
        # Get time of next request
        if self.patient_type == PatientType.EMERGENCY:
            next_request_time = sim.current_time + self.model.distr_emergency_patients.sample()
        elif self.patient_type == PatientType.OUT:
            next_request_time = self.next_outpatient_request_time(sim.current_time)
        elif self.patient_type == PatientType.IN:
            next_request_time =  self.next_inpatient_request_time(sim.current_time)
        # Schedule next request
        next_request = RequestScanEvent(next_request_time, self.model, patient.type)
        sim.schedule(next_request)

        # Log request
        self.model.record_request(patient)

    def move_to_waiting_room(self, sim: Simulation, patient: Patient):
        """Schedules an arrival event for the given patient."""
        arrival_event = ArrivalEvent(sim.current_time, self.model, patient)
        sim.schedule(arrival_event)

class ArrivalEvent(Event):
    """Handles the arrival of a Patient in the waiting room. Places the patient in the queue."""
    def __init__(self, time, model, patient: Patient):
        super().__init__(time)
        self.model: CTScannerModel = model
        self.patient: Patient = patient

    def execute(self, sim: Simulation):
        # Log time between request and scheduling
        self.model.record_access_time(self.patient)

        if self.patient_type == PatientType.OUT and random.random() > SHOWUP_PROBABILITY:
            return # Patient does not show up

        self.patient.arrival_time = sim.current_time

        if self.model.active_scanners < self.model.scanners:
            start_event = StartScanEvent(self.model, sim.current_time, self.patient)
            sim.schedule(start_event)
            return
        # No scanners available; place in queue
        self.model.add_to_queue(self.patient)

        # Log arrival to statistics
        self.model.record_arrival(self.patient)

class StartScanEvent(Event):
    """Handles the start of a CT scan. Samples the scan time uniformly."""
    def __init__(self, model: CTScannerModel, time, patient: Patient):
        super().__init__(time)
        self.model: CTScannerModel = model
        self.patient = patient
    
    def execute(self, sim: Simulation):
        scan_time = self.model.distr_scan_time.sample()
        end_time = sim.current_time + scan_time
        end_event = EndScanEvent(self.model, end_time)
        sim.schedule(end_event)
        self.model.active_scanners += 1

        self.model.record_wait_time(self.patient)
        self.model.update_scanner_util()

class EndScanEvent(Event):
    """Handles the end of a CT scan. Starts the scan of next patient if present."""
    def __init__(self, model: CTScannerModel, time):
        super().__init__(time)
        self.model: CTScannerModel = model
    
    def execute(self, sim: Simulation):
        next_patient = self.model.next_patient()
        if next_patient is not None:
            start_event = StartScanEvent(self.model, sim.current_time, next_patient)
            sim.schedule(start_event)
        self.model.active_scanners -= 1

        self.model.update_scanner_util()
    
class ScheduleNextWeekEvent(Event):
    def __init__(self, model: CTScannerModel, time):
        super().__init__(time)
        self.model: CTScannerModel = model
    
    def execute(self, sim: Simulation):
        print(f"Planning {len(self.model.waiting_list)} outpatients for next week...")
        self.model.clear_schedule()
        
        waiting_list = self.model.waiting_list.copy()
        self.model.waiting_list.clear()
        schedule_outpatients(self.model, waiting_list, sim.current_time, next_week=True)
        
        # Schedule same event next week again
        next_time = sim.current_time + 7*24*60 # next week
        next_event = ScheduleNextWeekEvent(self.model, next_time)
        sim.schedule(next_event)


# Current policy:   If patients request before of during office hours, they are scanned within office hours. 
#                   if they request after office hours, they are immediately placed in the waiting room
#                   If they request in weekend, they are immediately placed in the waiting room
#                   If there is no room left, let them arrive in the queue at the end of the office hours
def schedule_inpatient(model: CTScannerModel, patient: Patient, current_time: float):
    current_weekday = simtime.weekday(current_time)
    if current_weekday >= 5: # Inpatients dont need to be scanned in the weekend
        model.sim.schedule(ArrivalEvent(model.sim.current_time, model, patient))
        return
    # Check if we are after office hours
    if simtime.daytime(current_time) > 16*60: # After office hours; move to waiting room
        model.sim.schedule(ArrivalEvent(model.sim.current_time, model, patient))
        return

    weektime = simtime.weektime(current_time)
    
    # Look for first available slot
    for day in range(5):
        for daypart in range(2):
            for slot in range(SLOTS_PER_DAYPART):
                if simtime.slot_start(day, daypart, slot) <= weektime:
                    continue # Slot is in the past
                if model.schedule[day][daypart][slot][0] >= NUM_SCANNERS_OFFICE_HOURS:
                    continue # Slot is full
                schedule_patient_in_slot(model, patient, day, daypart, slot)
                return
    
    # If the inpatient has not been scheduled, let them arrive at the end of the office hours
    day = simtime.day(current_time)
    arrival_time = day*24*60 + 16*60
    model.sim.schedule(ArrivalEvent(arrival_time, model, patient))

# Policy: Only schedule MAX_SCHEDULED_OUTPATIENTS_MORNING per hour in the morning
#           and MAX_SCHEDULED_OUTPATIENTS_AFTERNOON per hour in the afternoon
def schedule_outpatients(model: CTScannerModel, patients: List[Patient], current_time: float, next_week = False):
    if len(patients) == 0:
        return
    current_weekday = simtime.weekday(current_time)
    if (not next_week) and current_weekday >= 4: # Friday
        model.waiting_list.extend(patients)
        

    
    weektime = simtime.weektime(current_time)
    current_patient = 0
    hourly_outpatients = 0
    # Look for first available slot 
    for day in range(5):
        for daypart in range(2):
            max_hourly_outpatients = \
                MAX_SCHEDULED_OUTPATIENTS_MORNING if daypart == DayPart.MORNING \
                else MAX_SCHEDULED_OUTPATIENTS_AFTERNOON
            
            for slot in range(SLOTS_PER_DAYPART):
                if slot % 4 == 0: 
                    # Count the number of outpatients scheduled in this hour beforehand
                    hourly_outpatients = sum(model.schedule[day][daypart][hour_slot][1] for hour_slot in range(slot, slot+4))
                is_past = simtime.slot_start(day, daypart, slot) <= weektime
                is_today = day == current_weekday
                is_illegal_slot = (not next_week) and (is_past or is_today)
                if is_illegal_slot:
                    continue
                if hourly_outpatients >= max_hourly_outpatients:
                    continue

                remaining_spots = NUM_SCANNERS_OFFICE_HOURS - model.schedule[day][daypart][slot][0]
                allowed_allocations = min(remaining_spots, max_hourly_outpatients - hourly_outpatients)
                for _ in range(allowed_allocations):
                    schedule_patient_in_slot(model, patients[current_patient], day, daypart, slot)
                    current_patient += 1
                    hourly_outpatients += 1
                    if current_patient == len(patients):
                        return # Every outpatient has been scheduled
    
    # Place all non-scheduled patients in waiting list 
    model.waiting_list.extend(patients[current_patient:])

def schedule_patient_in_slot(model: CTScannerModel, patient: Patient, day: int, daypart: int, slot: int):
    model.schedule[day][daypart][slot][0] += 1
    if patient.type == PatientType.OUT:
        model.schedule[day][daypart][slot][1] += 1
    
    time = model.sim.current_time
    week = simtime.week(time)
    slot_start_relative = simtime.slot_start(day, daypart, slot)
    wtime = simtime.weektime(time)
    if wtime > slot_start_relative:
        week += 1 # Slot is next week
    
    slot_start = week * 7*24*60 + slot_start_relative
    model.sim.schedule(ArrivalEvent(slot_start, model, patient))

