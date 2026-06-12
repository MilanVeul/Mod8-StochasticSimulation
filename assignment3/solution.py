from ct_simulation import CTScannerModel
from long_term_statistics import BatchMeansMethod, StatisticHolder as SH

def print_batch_report(report):
    if not report:
        print("No data to display.")
        return

    headers = ["Index", SH.TOTAL_PATIENTS, SH.SCANNER_UTIL_OFFICE, SH.SCANNER_UTIL_OUTSIDE, SH.WAIT_TIME_OUT, SH.WAIT_TIME_EMERGENCY, SH.AVG_ACCESS_TIME]
    template = "{:<5} | {:<10} | {:<15} | {:<15} | {:<15} | {:<15} | {:<15}"
    
    print("-" * 110)
    print(template.format(*headers))
    print("-" * 110)
    
    for i, row in enumerate(report):
        batch_nr = i + 1
        total = f"{row.get(SH.TOTAL_PATIENTS)}"
        s_util_office = f"{row.get(SH.SCANNER_UTIL_OFFICE, -1):.5f}"
        s_util_outside = f"{row.get(SH.SCANNER_UTIL_OUTSIDE, -1):.5f}"
        wt_out = f"{row.get(SH.WAIT_TIME_OUT, -1):.4f}"
        wt_emergency = f"{row.get(SH.WAIT_TIME_EMERGENCY, -1):.4f}"
        access_time = f"{row.get(SH.AVG_ACCESS_TIME, -1):.2f}"
        
        print(template.format(batch_nr, total, s_util_office, s_util_outside, wt_out, wt_emergency, access_time))
    print("-" * 110)

def run():
    model = CTScannerModel(70)
    batch_means = BatchMeansMethod(model, 0, 14*24*60*60, 1)
    model.set_statistics_method(batch_means)
    model.run()
    report = model.report()
    print_batch_report(report)

if __name__ == "__main__":
    run()