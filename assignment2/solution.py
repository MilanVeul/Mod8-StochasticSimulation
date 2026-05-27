from scipy import stats
import numpy as np
from waste_collection import WasteCollectionModel
from long_term_statistics import StatisticHolder, BatchMeansMethod, RegenerativeMethod, batch_number_lower_bound, batch_confidence_interval, regenerative_confidence_interval


alpha = 0.05
precision = 0.01
num_batches = 50

def print_batch_report(report):
    if not report:
        print("No data to display.")
        return

    headers = ["Index", "Avg Queue Len", "Avg Waiting Time", "Truck Utilisation", "Rerouting Rate"]
    template = "{:<5} | {:<15} | {:<15} | {:<21} | {:<15}"
    
    print("-" * 80)
    print(template.format(*headers))
    print("-" * 80)
    
    for i, row in enumerate(report):
        batch_nr = i + 1
        q_len = f"{row.get(StatisticHolder.AVG_QUEUE_LEN, 0.0):.5f}"
        w_time = f"{row.get(StatisticHolder.AVG_WAITING_TIME, 0.0):.5f}"
        r_rate = f"{row.get(StatisticHolder.REROUTING_RATE, 0.0):.8f}"
        
        utils = row.get(StatisticHolder.TRUCK_UTILISATION, [])
        utils_str = "[" + ", ".join(f"{u:.3f}" for u in utils) + "]"
        
        print(template.format(batch_nr, q_len, w_time, utils_str, r_rate))
        
    print("-" * 80)

def print_regenerative_report(report):
    if not report:
        print("No data to display.")
        return

    headers = ["Index", "Batch len", "Wait time", "Num req", "Q len"]
    template = "{:<5} | {:<8} | {:<15} | {:<12} | {:<12}"
    
    print("-" * 80)
    print(template.format(*headers))
    print("-" * 80)
    
    for i, row in enumerate(report):
        batch_nr = i + 1
        w_time = f"{row.get(StatisticHolder.TOTAL_WAITING_TIME, 0.0):.3f}"
        num_r = f"{row.get(StatisticHolder.NUM_REQUESTS, 0.0):.0f}"
        b_len = f"{row.get(StatisticHolder.BATCH_LENGTH, 0):.3f}"
        q_len = f"{row.get(StatisticHolder.TOTAL_QUEUE_LEN, 0):.3f}"
        
        print(template.format(batch_nr, b_len, w_time, num_r, q_len))
        
    print("-" * 80)

def get_stat(report, stat: str):
    data = [batch[stat] for batch in report]
    if isinstance(data[0], list):
        # Transpose so rows represent trucks, and columns represent batches
        return [list(row) for row in zip(*data)]
    return data

def run_batch_means():
    model = WasteCollectionModel(seed=70)

    # Initiate statistic method
    stat_method = BatchMeansMethod(model, 0, 50000, num_batches)
    model.set_statistics_method(stat_method)

    model.run()
    report = model.report()

    print_batch_report(report)

    # Batch number lower bound
    print("\nMinimal batch numbers:")
    print("  Waiting time  ", batch_number_lower_bound(get_stat(report, StatisticHolder.AVG_WAITING_TIME), precision=precision, alpha=alpha))
    print("  Queue len     ", batch_number_lower_bound(get_stat(report, StatisticHolder.AVG_QUEUE_LEN), precision=precision, alpha=alpha))
    print("  Truck util    ", [batch_number_lower_bound(truck, precision=precision, alpha=alpha) for truck in get_stat(report, StatisticHolder.TRUCK_UTILISATION)])
    print("  Rerouting     ", batch_number_lower_bound(get_stat(report, StatisticHolder.REROUTING_RATE), precision=precision, alpha=alpha))

    # Point estimations
    print("\nPoint estimations:")
    print("  Waiting time  ", np.mean(get_stat(report, StatisticHolder.AVG_WAITING_TIME)))
    print("  Queue len     ", np.mean(get_stat(report, StatisticHolder.AVG_QUEUE_LEN)))
    print("  Truck util    ", [np.mean(truck) for truck in get_stat(report, StatisticHolder.TRUCK_UTILISATION)])
    print("  Rerouting     ", np.mean(get_stat(report, StatisticHolder.REROUTING_RATE)))
    
    # Confidence intervals
    print("\nConfidence intervals:")
    print("  Waiting time  ", batch_confidence_interval(get_stat(report, StatisticHolder.AVG_WAITING_TIME), alpha))
    print("  Queue len     ", batch_confidence_interval(get_stat(report, StatisticHolder.AVG_QUEUE_LEN), alpha))
    print("  Truck util    ", [batch_confidence_interval(truck, alpha) for truck in get_stat(report, StatisticHolder.TRUCK_UTILISATION)])
    print("  Rerouting     ", batch_confidence_interval(get_stat(report, StatisticHolder.REROUTING_RATE), alpha))

def run_regenerative():
    model = WasteCollectionModel(seed=70)

    # Initiate statistic method
    stat_method = RegenerativeMethod(model, 100000)
    model.set_statistics_method(stat_method)

    model.run()
    report = model.report()

    # print_regenerative_report(report)

    num_requests = get_stat(report, StatisticHolder.NUM_REQUESTS)
    batch_lens = get_stat(report, StatisticHolder.BATCH_LENGTH)
    total_wait_time = get_stat(report, StatisticHolder.TOTAL_WAITING_TIME)
    total_q_len = get_stat(report, StatisticHolder.TOTAL_QUEUE_LEN)
    total_truck_utils = get_stat(report, StatisticHolder.TOTAL_TRUCK_UTILISATION)
    total_reroutes = get_stat(report, StatisticHolder.TOTAL_REROUTES)

    ci_wait_time = regenerative_confidence_interval(total_wait_time, num_requests, alpha)
    ci_q_len = regenerative_confidence_interval(total_q_len, batch_lens, alpha)
    ci_truck_util = [regenerative_confidence_interval(util, batch_lens, alpha) for util in total_truck_utils]
    ci_reroutes = regenerative_confidence_interval(total_reroutes, batch_lens, alpha)
    print(f"Wait time CI  = {ci_wait_time}")
    print(f"Queue len CI  = {ci_q_len}")
    print(f"Truck Util CI = {ci_truck_util}")
    print(f"Reroute CI    = {ci_reroutes}")

def run():
    run_batch_means()
    # run_regenerative()


if __name__ == "__main__":
    run()