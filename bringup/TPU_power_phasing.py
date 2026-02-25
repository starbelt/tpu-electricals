import pandas as pd

def verify_power_sequence(csv_filepath):
    # load saleae export
    df = pd.read_csv(csv_filepath)
    
    # define voltage thresholds for "stable" or "on"
    th_3v3 = 3.0
    th_1v8 = 1.6
    th_pswitch = 1.5
    
    # helper to find the first time a signal crosses a threshold
    def get_cross_time(column_name, threshold):
        if column_name not in df.columns:
            return None
        # boolean mask to find where voltage exceeds threshold
        crossed = df[column_name] >= threshold
        if not crossed.any():
            return None
        # get index of first occurrence and return the time
        idx = crossed.idxmax()
        return df['Time [s]'].iloc[idx]

    # get timestamps for critical sequence events
    t_snvs = get_cross_time('VDD_SNVS_IN', th_3v3)
    t_dcdc_in = get_cross_time('DCDC_IN', th_3v3)
    t_pswitch = get_cross_time('DCDC_PSWITCH', th_pswitch)
    t_1v8 = get_cross_time('VDD_1V8', th_1v8)
    
    print("power sequence verification:")
    
    # 1. check snvs comes first
    if t_snvs is not None and t_dcdc_in is not None:
        if t_snvs <= t_dcdc_in:
            print(f"pass: vdd_snvs_in is on before dcdc_in")
        else:
            print(f"fail: vdd_snvs_in came on after dcdc_in")
    else:
        print("warn: could not find snvs or dcdc_in crossing")

    # 2. check pswitch 1ms delay requirement
    if t_dcdc_in is not None and t_pswitch is not None:
        delay_ms = (t_pswitch - t_dcdc_in) * 1000
        if delay_ms >= 1.0:
            print(f"pass: dcdc_pswitch delay is {delay_ms:.2f} ms")
        else:
            print(f"fail: dcdc_pswitch delay is {delay_ms:.2f} ms (needs >= 1ms)")
    else:
        print("warn: dcdc_pswitch never reached threshold in this capture")
        
    # 3. check 1.8v comes after pswitch (as per fig 4)
    if t_pswitch is not None and t_1v8 is not None:
        if t_1v8 > t_pswitch:
            print("pass: 1v8 rail comes after dcdc_pswitch")
        else:
            print("fail: 1v8 rail comes before dcdc_pswitch is ready")
    elif t_1v8 is not None and t_dcdc_in is not None:
        # fallback check if pswitch is flat but we want to know if 1v8 raced 3v3
        if t_1v8 <= t_dcdc_in:
            print("fail: 1v8 rail is coming up at the same time as dcdc_in")

import pandas as pd

def check_dcdc_ramp(csv_filepath):
    df = pd.read_csv(csv_filepath)
    
    # grab the first timestamp where thresholds are crossed
    # using 0.1v as the start of the dcdc_in ramp
    t_dcdc_start = df.loc[df['DCDC_IN'] >= 0.1, 'Time [s]'].iloc[0]
    t_dcdc_3v = df.loc[df['DCDC_IN'] >= 3.0, 'Time [s]'].iloc[0]
    t_pswitch_1v5 = df.loc[df['DCDC_PSWITCH'] >= 1.5, 'Time [s]'].iloc[0]
    
    # figure out how long the ramp took and the delay
    dcdc_ramp_time = t_dcdc_3v - t_dcdc_start
    pswitch_delay = t_pswitch_1v5 - t_dcdc_3v
    
    # find the actual rc time constant
    # charging to 50% takes 0.693 * rc
    real_rc = pswitch_delay / 0.693
    
    # nxp rule: dcdc_in must hit 3.0v within 0.3 * rc
    max_allowed_ramp = 0.3 * real_rc
    
    print(f"dcdc_in ramp time: {dcdc_ramp_time * 1000:.2f} ms")
    print(f"pswitch delay: {pswitch_delay * 1000:.2f} ms")
    print(f"calculated rc: {real_rc * 1000:.2f} ms")
    print(f"max allowed ramp: {max_allowed_ramp * 1000:.2f} ms")
    
    if dcdc_ramp_time <= max_allowed_ramp:
        print("pass: dcdc_in ramps fast enough")
    else:
        print("fail: dcdc_in ramps too slow for this rc value")

# run the check
verify_power_sequence("bringup/dcdc_pswitch_1v8.csv")
check_dcdc_ramp("bringup/dcdc_pswitch_1v8.csv")