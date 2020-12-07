import math

def calc_running_index(activity,user):
    print(activity)
    max_hr = user.max_hr
    x = activity['hr']/max_hr*1.45-0.30
    distance = float(activity['distance'])
    up = int(activity['up'])
    down = int(activity['down'])
    if down > 0:
        d = distance + 6*up - 4* down
    else:
        d = distance + 3 * up 
    RIO = (213.9/activity['duration']) * ((d/1000)**1.06) + 3.5
    runningIndex = round(RIO/x,2)
    return runningIndex

def calc_trimp_tss(activity,user):
    rest_hr = int(user.rest_hr)
    max_hr = int(user.max_hr)
    lactate_th = user.lactate_th
    hrr = (int(activity['hr']) - rest_hr)/(max_hr - rest_hr)
    trimp = 0 
    duration = round(activity['duration'])
    for i in range(0,duration):
        trimp = trimp + 1 * hrr * 0.64 * math.exp(1.92 * hrr)
    hr_lthr = (lactate_th - rest_hr)/(max_hr - rest_hr)
    hour_lthr = 60 * hr_lthr * 0.64 * math.exp(1.92 * hr_lthr)
    tss = (trimp/hour_lthr)*100

    return (round(tss,2),round(trimp,2))
       
