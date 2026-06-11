from ct_simulation import CTScannerModel
from long_term_statistics import BatchMeansMethod, StatisticHolder

def print_batch_report(report):
    if not report:
        print("No data to display.")
        return

    headers = ["Index", "S. Util Office", "S. Util Outside", "WT outp", "WT emep"]
    template = "{:<5} | {:<15} | {:<15} | {:<15} | {:<15}"
    
    print("-" * 80)
    print(template.format(*headers))
    print("-" * 80)
    
    for i, row in enumerate(report):
        batch_nr = i + 1
        s_util_office = f"{row.get(StatisticHolder.SCANNER_UTIL_OFFICE, 0.0):.5f}"
        s_util_outside = f"{row.get(StatisticHolder.SCANNER_UTIL_OUTSIDE, 0.0):.5f}"
        wt_out = f"{row.get(StatisticHolder.WAIT_TIME_OUT, 0.0):.8f}"
        wt_emergency = f"{row.get(StatisticHolder.WAIT_TIME_EMERGENCY, 0.0):.8f}"
        
        
        print(template.format(batch_nr, s_util_office, s_util_outside, wt_out, wt_emergency))
        
    print("-" * 80)

def run():
    model = CTScannerModel(70)
    batch_means = BatchMeansMethod(model, 0, 14*24*60*60, 1)
    model.set_statistics_method(batch_means)
    model.run()
    report = model.report()
    print_batch_report(report)

if __name__ == "__main__":
    run()