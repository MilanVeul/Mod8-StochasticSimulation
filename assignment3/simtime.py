from enum import Enum

class DayPart(Enum):
    OUTSIDE_OFFICE_HOURS = -1
    MORNING = 0
    AFTERNOON = 1

def week(simulation_time: float):
    return day(simulation_time) // 7

def weektime(simulation_time: float):
    return weekday(simulation_time)*24*60 + daytime(simulation_time)

def day(simulation_time: float):
    return simulation_time // (24*60)

def daytime(simulation_time: float):
    return simulation_time % (60*24)

def weekday(simulation_time: float):
    return day(simulation_time) % 7

def daypart(simulation_time: float) -> int:
    dtime = daytime(simulation_time)
    if 8*60 <= dtime < 12*60:
        return DayPart.MORNING
    if 12*60 <= dtime <= 16*60:
        return DayPart.AFTERNOON
    return DayPart.OUTSIDE_OFFICE_HOURS

def slot(simulation_time: float, slots_per_daypart: int):
    dpart = daypart(simulation_time)
    if dpart == DayPart.OUTSIDE_OFFICE_HOURS:
        return -1
    slot_time = (daytime(simulation_time) - 8*60) - dpart*4*60
    slot_length = 4*60 / slots_per_daypart
    slot = slot_time // slot_length
    return slot

def slot_start(weekday: int, daypart: int, slot: int):
    """Returns the start time of the slot IN WEEKTIME"""
    return (24*60*weekday + 8*60) + daypart*4*60 + slot*15