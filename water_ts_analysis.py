#!/usr/bin/python3

import numpy as n
import pandas as p
import sys as s
import hasib as h

from matplotlib import pyplot as t


class WaterLevelAnalyser:
    def __init__(self, csv_name='Site A - Tue Feb 15 2022 to Thu Jun 30 2022.csv',
                 flood_threshold=400, water_level_increase_threshold=4,
                 event_window=300, frame_interval=5):
        # Constants
        self.unix1s = 1000000000
        self.level_water_level_increase_threshold = water_level_increase_threshold
        self.event_time_gap = n.timedelta64(event_window, 'm')
        self.frame_rate = n.timedelta64(frame_interval, 'm')
        self.flood_threshold_mm = flood_threshold

        # Read data, get useful quantities
        self._data = p.read_csv(csv_name, parse_dates=['Timestamp'])

        self.compute_stats()

    def compute_stats(self):
        self.water_level_mm = (self._data[[' Water Level [m]']]*1000)\
            .to_numpy(n.int64).flatten()
        self.ts_times = self._data[['Timestamp']]
        self.times_as_np = self.ts_times.to_numpy(n.datetime64).flatten()

        # Diffs - changes per 5 min intervals
        self.water_level_changes = n.diff(self.water_level_mm)
        self.time_intervals = n.diff(self.times_as_np)
        
        # Hasib's stats
        self.moving_std=h.moving_std(self._data,6)
        max_std=n.max(self.moving_std)
        self.std_start_threshold=max_std*(3/100)
        self.std_end_threshold=max_std*(8/100)
        self.moving_max=h.moving_max(self._data,6)

    def find_best_forcing(self,k_vals=n.linspace(-10,10,num=1000)):
        '''
        Can we figure out some reasonable underlying rainfall that might be
        driving the levels?
        '''
        self.forcing=n.ndarray((len(k_vals),len(self.water_level_mm)))
        cost_k=n.ndarray((len(k_vals),))
        height_diff=n.diff(self.water_level_mm,prepend=self.water_level_mm[:1])
        for i,k in enumerate(k_vals):
            self.forcing[i,:]=self.water_level_mm+k*height_diff
            cost_k[i]=n.abs(self.forcing[i,:]).mean()

        self.best_k_index=n.argmin(cost_k)
        self.best_forcing_guess=k_vals[self.best_k_index]

    def correct_tz(self):
        '''
        Correct the timezone.
        I'm confused by tz right now, but can assume everything is a 5 min interval
        '''
        self.time_intervals = n.array([self.frame_rate for i in self.time_intervals],
                                      dtype=n.int64)

    def plot_timeseries(self, overlay_event_starts=True, overlay_event_ends=True,
                        overlay_peaks=True, overlay_flood_ends=True, plot_event=-1,
                        overlay_forcing=False):
        '''
        Plot the timeseries being considered.
        '''

        t.plot(self.times_as_np, self.water_level_mm)
        evnts = zip(self.event_start_times, self.event_end_times, self.event_peaks_mm,
                  self.flood_end_times) if plot_event == -1 else\
                [(self.event_start_times[plot_event], self.event_end_times[plot_event],
                  self.event_peaks_mm[plot_event], self.flood_end_times[plot_event])]

        for i, j, peak, end in evnts:

            if overlay_event_starts:
                t.axvline(x=i, alpha=.5, color='red')

            if overlay_event_ends:
                t.axvline(x=j, alpha=.5, color='green')

            if overlay_peaks:
                t.plot([i, j], [peak, peak], color='purple')

            if overlay_flood_ends and peak > self.flood_threshold_mm:
                t.axvline(x=end, alpha=.2, color='blue')
        if overlay_forcing==True:
            t.plot(self.times_as_np,self.forcing[self.best_k_index,:])
            t.title('k='+str(self.best_forcing_guess))

        t.show()

    def find_event_start_end_times(self,method='G'):
        '''
        Detect rainfall events.
        Here uses a simple threshold.  Further upticks within 6 hours
        are considered part of the main event.
        '''

        if method=='G':
            # Find all times when there was an level change above the threshold
            self._increase_mask= self.water_level_changes >\
                                 self.level_water_level_increase_threshold
            self._events_mask= self._increase_mask.copy()
            time_since_last_inc= n.timedelta64(99999999, 'm')
            event_end_times= []

            # Find event end times - defined as 6 hours after last rise in the event
            for i in range(len(self._events_mask)):
                if self._events_mask[i]:
                    if time_since_last_inc < self.event_time_gap:
                        self._events_mask[i]= False
                        event_end_times[-1]= self.times_as_np[i] + self.event_time_gap
                    else:
                        event_end_times.append(
                            self.times_as_np[i]+self.event_time_gap)
                    time_since_last_inc= n.timedelta64()
                time_since_last_inc += self.frame_rate

            self.event_end_times= n.array(event_end_times)
            self.event_start_times= self.times_as_np[1:][self._events_mask]
        elif method=='H':
            self.event_start_i,self.event_end_i=h.find_peaks(self.water_level_mm,
                                                             self.moving_std,
                                                             self.moving_max)
            self.event_start_times=self.times_as_np[self.event_start_i]
            self.event_end_times=self.times_as_np[self.event_end_i]

    def find_peak_levels(self):
        peaks= []
        peak_times= []
        flood_end_times= []
        for start, end in zip(self.event_start_times, self.event_end_times):
            event_start_index= n.where(self.times_as_np == start)[0][0]
            event_end_index= n.where(self.times_as_np == end)[0][0]
            peak_i= self.water_level_mm[event_start_index:event_end_index].argmax()
            peak_times.append(self.times_as_np[event_start_index+peak_i])
            peaks.append(self.water_level_mm[event_start_index:event_end_index]
                                             [peak_i])
            flood_end_times.append(self.times_as_np[event_start_index+peak_i+n.where(
                                   self.water_level_mm[event_start_index+peak_i:] <
                                   self.flood_threshold_mm)[0][0]])

        self.event_peaks_mm= n.array(peaks)
        self.event_peak_times= n.array(peak_times)
        self.flood_end_times= n.array(flood_end_times)
        self.drawdown_rates= n.timedelta64(1, 'm') *\
        (self.event_peaks_mm-self.flood_threshold_mm) /\
            (self.flood_end_times-self.event_peak_times)


if __name__ == '__main__':

    import argparse

    prs= argparse.ArgumentParser(
        description='Water level timeseries analyser')

    # By default read site A
    prs.add_argument('--csv', '-c',
                     default='dat/Site A - Tue Feb 15 2022 to Thu Jun 30 2022.csv',
                     help='The csv file containing water level history')
    prs.add_argument('--flood_threshold', '-f', default=400, type=int,
                     help='Flood level threshold (mm)')
    prs.add_argument('--water_level_increase_threshold', '-i', default=4, type=int,
                     help='Water level increase threshold (mm/time step)')
    prs.add_argument('--find_best_forcing','-b',action='store_true',
                     help='Find possible underlying forcing')
    prs.add_argument('--method','-m',default='H',
                     help='Method to use (H or G)')
    prs.set_defaults(find_best_forcing=False)
    args= prs.parse_args()
    analyser= WaterLevelAnalyser(args.csv, flood_threshold=args.flood_threshold,
                    water_level_increase_threshold=args.water_level_increase_threshold)

    analyser.find_event_start_end_times(method=args.method)
    analyser.find_peak_levels()
    if args.find_best_forcing:
        analyser.find_best_forcing()
    analyser.plot_timeseries(overlay_event_starts=True,overlay_event_ends=True,
                             overlay_peaks=True,overlay_flood_ends=True,
                             overlay_forcing=args.find_best_forcing)
