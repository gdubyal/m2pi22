#!/usr/bin/python3

import numpy as n
import pandas as p
import sys as s

from matplotlib import pyplot as t


class WaterLevelAnalyser:
    def __init__(self, csv_name='Site A - Tue Feb 15 2022 to Thu Jun 30 2022.csv'):
        #Constants
        self.level_increase_threshold = 10  # 10mm
        self.unix1s = 1000000000
        self.rain_event_min_gap = self.unix1s*60*60*6  # 6 hours
        self.event_min_time_gap = 300

        #Read data,get useful quantities
        self._data = p.read_csv(csv_name, parse_dates=['Timestamp'])
            
        self.compute_stats()

    def compute_stats(self):
        self.water_levels_mm = (self._data[[' Water Level [m]']]*1000)\
            .to_numpy(n.int64)\
            .flatten()
        self.ts_times = self._data[['Timestamp']]
        self.times_as_int = self.ts_times.to_numpy(n.int64).flatten()

        #Diffs - changes per 5 min intervals
        self.water_level_changes = n.diff(self.water_levels_mm)
        self.time_intervals = n.diff(self.times_as_int)

    def correct_tz(self):
        '''
        Correct the timezone.
        I'm confused by tz right now, but can assume everything is a 5 min interval
        '''
        self.time_intervals = n.array([300*self.unix1s for i in self.time_intervals],
                                      dtype=n.int64)

    def plot_timeseries(self, overlay_increases=False):
        '''
        Plot the timeseries being considered.
        '''

        t.plot(self.times_as_int, self.water_levels_mm)
        if overlay_increases:
            for i in self.event_start_times:
                t.axvline(x=i, alpha=.5, color='red')
        t.show()

    def find_event_start_times(self):
        '''
        Detect rainfall events.
        Here uses a simple threshold.  Further upticks within 6 hours
        are considered part of the main event.
        '''
        self._increase_mask = self.water_level_changes > self.level_increase_threshold
        self.events_mask = self._increase_mask.copy()
        time_since_last_inc = n.inf
        for i in range(len(self.events_mask)):
            if self.events_mask[i]:
                if time_since_last_inc < self.event_min_time_gap:
                    self.events_mask[i] = False
                time_since_last_inc = 0
            time_since_last_inc += 5
        self.event_start_times = self.times_as_int[1:][self.events_mask]


if __name__ == '__main__':
    # By default read site A
    s.argv.append('dat/Site A - Tue Feb 15 2022 to Thu Jun 30 2022.csv')
    analyser = WaterLevelAnalyser(s.argv[1])

    analyser.find_event_start_times()
    analyser.plot_timeseries(overlay_increases=True)
