import numpy as np
from waste_collection import WasteCollectionModel
from long_term_statistics import StatisticHolder, BatchMeansMethod, RegenerativeMethod, print_report, batch_number_lower_bound, confidence_interval


alpha = 0.05
precision = 0.01
num_batches = 50

def get_stat(report, stat: str):
    data = [batch[stat] for batch in report]
    if isinstance(data[0], list):
        # Transpose so rows represent trucks, and columns represent batches
        return [list(row) for row in zip(*data)]
    return data

def run():
    model = WasteCollectionModel(seed=70)

    # Initiate statistic method
    stat_method = BatchMeansMethod(model, 0, 50000, num_batches)
    # stat_method = RegenerativeMethod(model, 1000)
    model.set_statistics_method(stat_method)

    model.run()
    report = model.report()

    print_report(report)

    # Batch number lower bound
    print("\nMinimal batch numbers:")
    print("  Waiting time  ", batch_number_lower_bound(get_stat(report, StatisticHolder.AVG_WAITING_TIME), precision=precision, alpha=alpha))
    print("  Queue len     ", batch_number_lower_bound(get_stat(report, StatisticHolder.AVG_QUEUE_LEN), precision=precision, alpha=alpha))
    print("  Truck util    ", [batch_number_lower_bound(truck, precision=precision, alpha=alpha) for truck in get_stat(report, StatisticHolder.TRUCK_UTILISATION)])

    # Point estimations
    print("\nPoint estimations:")
    print("  Waiting time  ", np.mean(get_stat(report, StatisticHolder.AVG_WAITING_TIME)))
    print("  Queue len     ", np.mean(get_stat(report, StatisticHolder.AVG_QUEUE_LEN)))
    print("  Truck util    ", [np.mean(truck) for truck in get_stat(report, StatisticHolder.TRUCK_UTILISATION)])
    print("  Rerouting     ", np.mean(get_stat(report, StatisticHolder.REROUTING_RATE)))
    
    # Confidence intervals
    print("\nConfidence intervals:")
    print("  Waiting time  ", confidence_interval(get_stat(report, StatisticHolder.AVG_WAITING_TIME), alpha))
    print("  Queue len     ", confidence_interval(get_stat(report, StatisticHolder.AVG_QUEUE_LEN), alpha))
    print("  Truck util    ", [confidence_interval(truck, alpha) for truck in get_stat(report, StatisticHolder.TRUCK_UTILISATION)])
    print("  Rerouting     ", confidence_interval(get_stat(report, StatisticHolder.REROUTING_RATE), alpha))


if __name__ == "__main__":
    run()