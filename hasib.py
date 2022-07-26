
import numpy as np

# Calculate moving STD of last *few hours
def moving_std(df,period_in_hour):
    wl_mm=df[" Water Level [m]"].to_numpy()*1000  # water level in mm
    mov_std=[0]
    mean_mov=[wl_mm[0]]
    for i in range(np.size(wl_mm)):
        periods=int(period_in_hour*(60/5))
        if i<periods:
            mov_std.append(np.std(wl_mm[:i+1]))
            mean_mov.append(np.mean(wl_mm[:i+1]))
        else:
            mov_std.append(np.std(wl_mm[i-periods:i+1]))
            mean_mov.append(np.mean(wl_mm[i-periods:i+1]))
    return mov_std
#Calculate moving MEAN of last *few hours
def moving_mean(df,period_in_hour):
    wl_mm=df[" Water Level [m]"].to_numpy()*1000  # water level in mm
    mean_mov=[wl_mm[0]]
    for i in range(np.size(wl_mm)):
        periods=int(period_in_hour*(60/5))
        if i<periods:
            mean_mov.append(np.mean(wl_mm[:i+1]))
        else:
            mean_mov.append(np.mean(wl_mm[i-periods:i+1]))
    return mean_mov

# Calculate moving MAX of last *few hours
def moving_max(df,period_in_hour):
    wl_mm=df[" Water Level [m]"].to_numpy()*1000  # water level in mm
    mov_max=[wl_mm[0]]
    for i in range(np.size(wl_mm)):
        periods=int(period_in_hour*(60/5))
        if i<periods:
            mov_max.append(np.max(wl_mm[:i+1]))
        else:
            mov_max.append(np.max(wl_mm[i-periods:i+1]))
    return mov_max


def IdentifyEvents_3(df,dry_hours_skip,moving_hours,rng8p,rng3p,std_mov):
    #  This method use moving STD (std_mov) (last (moving_hours) hours) for start and end of an event
    # For the start of an event use: std_mov > *8 percent of range of std_mov
    # To detect the end of an event use: std_mov < 3 percentage of range of std_mov
    skip=int(dry_hours_skip*(60/5))    # (dry_hours_skip) hours of no significant change in water level means start of another event
    #wlc_mm=np.diff(df[" Water Level [m]"])*1000 # water level change measured in mm
    wl_mm=df[" Water Level [m]"].to_numpy()*1000  # water level in mm

    nre=True     #indicator if the current time falls under "No Rain Event" or not
    start_time=[]
    end_time=[]
    start_index=[]
    end_index=[]
    i=1
    while i<df.shape[0]-1:
        if std_mov[i]>=rng8p:
            if nre==True:
                # This is a new rainfall event
                start_time.append(df["Timestamp"][df.index.to_list()[0]+i])
                start_index.append(df.index.to_list()[0]+i)
                nre=False
                i+=1
            while std_mov[i]>rng3p:
                i+=1
            if np.max(std_mov[i+1:i+skip+1])<rng8p:
                # dry period starts from index i+1
                end_time.append(df["Timestamp"][df.index.to_list()[0]+i])
                end_index.append(df.index.to_list()[0]+i)
                nre=True
                i=i+skip
        i+=1

    return start_time,end_time,start_index,end_index,np.subtract(end_index,start_index),wl_mm

def find_peaks(wl,std_mov,max_mov):
    '''
    Find and filter peaks for event starts and ends
    '''
    # finding peak and bottom (wellflood duration)
    np.size(wl)
    np.size(std_mov)
    start=[]
    end=[]
    i=1
    while i <np.size(wl)-1:
        if max_mov[i]-wl[i]>2:
            start.append(i-1)
            while max_mov[i]-wl[i]>0:
                i+=1
                if i>=np.size(wl):
                    break
            end.append(i-1)
        i+=1
    np.size(start)
    # Discards peaks that's have very small amount of drawdown
    i=0
    while i<np.size(start)-1:
        if abs(wl[start[i]]-wl[end[i]])<150:
            if wl[start[i]]<wl[start[i+1]]:
                start.pop(i)
                end.pop(i)
            else:
                start.pop(i+1)
                end.pop(i)
            continue
        else:
            i+=1
    print(start)
    i=0
    while i<np.size(start)-1:
        if abs(wl[end[i]]-wl[start[i+1]])<150:
            end.pop(i)
            start.pop(i+1)
            continue
        else:
            i+=1
    print(start)
    # Discard peaks which are very close to each other
    i=0
    while i<np.size(start)-1:
        if (start[i+1]-start[i])<25:
            if wl[start[i+1]]>wl[start[i]]:
                start.pop(i)
                end.pop(i)
            else:
                start.pop(i+1)
                end.pop(i)
            continue
        else:
            i+=1
    print(start)
    return start,end
