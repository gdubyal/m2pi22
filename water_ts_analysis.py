#!/usr/bin/python3

import numpy as n
import pandas as p
import sys as s

from matplotlib import pyplot as t


class WaterLevelAnalyser:
    def __init__(self, csv_name='Site A - Tue Feb 15 2022 to Thu Jun 30 2022.csv'):
        # Constantsjkkjj
        self.level_increase_threshold = 4  # 10mm
        self.unix1s = 1000000000
        self.rain_event_min_gap = self.unix1s*60*60*6  # 6 hours
        self.event_min_time_gap = 300
        self.data_rate = 300*self.unix1s

        # Read data,get useful quantities
        self._data = p.read_csv(csv_name, parse_dates=['Timestamp'])

        self.compute_stats()

    def compute_stats(self):
        self.water_levels_mm = (self._data[[' Water Level [m]']]*1000)\
            .to_numpy(n.int64)\
            .flatten()
        self.ts_times = self._data[['Timestamp']]
        self.times_as_int = self.ts_times.to_numpy(n.int64).flatten()

        # Diffs - changes per 5 min intervals
        self.water_level_changes = n.diff(self.water_levels_mm)
        self.time_intervals = n.diff(self.times_as_int)

    def correct_tz(self):
        '''
        Correct the timezone.
        I'm confused by tz right now, but can assume everything is a 5 min interval
        '''
        self.time_intervals = n.array([self.data_rate for i in self.time_intervals],
                                      dtype=n.int64)

    def plot_timeseries(self, overlay_event_starts=True,
                        overlay_event_ends=True, overlay_peaks=True):
        '''
        Plot the timeseries being considered.
        '''

        t.plot(self.times_as_int, self.water_levels_mm)

        for i, j, peak in zip(self.event_start_times, self.event_end_times, self.event_peaks):

            if overlay_event_starts:
                t.axvline(x=i, alpha=.5, color='red')

            if overlay_event_ends:
                t.axvline(x=j, alpha=.5, color='green')

            if overlay_peaks:
                print(peak)
                t.plot([i,j],[peak,peak],color='purple')
                #t.axhline(y=peak,xmin=i,xmax=j,color='purple')

        t.show()

    def find_event_start_end_times(self):
        '''
        Detect rainfall events.
        Here uses a simple threshold.  Further upticks within 6 hours
        are considered part of the main event.
        '''

        # Find all times when there was an level change above the threshold
        self._increase_mask = self.water_level_changes > self.level_increase_threshold
        self.events_mask = self._increase_mask.copy()
        time_since_last_inc = n.inf
        _event_end_times = []

        # Find event end times - defined as 6 hours after last rise in the event
        for i in range(len(self.events_mask)):
            if self.events_mask[i]:
                if time_since_last_inc < self.event_min_time_gap:
                    self.events_mask[i] = False
                else:
                    _event_end_times.append(0)
                _event_end_times[-1] = self.times_as_int[i]+300*60*self.unix1s
                time_since_last_inc = 0
            time_since_last_inc += 5

        self.event_end_times = n.array(_event_end_times)
        self.event_start_times = self.times_as_int[1:][self.events_mask]

    def find_peak_levels(self):
        _peaks = []
        for start, end in zip(self.event_start_times, self.event_end_times):
            event_start_index = n.where(self.times_as_int==start)[0][0]
            event_end_index = n.where(self.times_as_int==end)[0][0]
            _peaks.append(self.water_levels_mm[event_start_index:event_end_index].max())

        self.event_peaks = n.array(_peaks)

    def detect_implied_rainfall(self):
        '''
        Find event end times, when the grogram figures water levels are down again.
        '''


if __name__ == '__main__':
    # By default read site A
    s.argv.append('dat/Site A - Tue Feb 15 2022 to Thu Jun 30 2022.csv')
    analyser = WaterLevelAnalyser(s.argv[1])

    analyser.find_event_start_end_times()
    analyser.find_peak_levels()
    analyser.plot_timeseries(overlay_event_starts=True,
                             overlay_event_ends=True,
                             overlay_peaks=True)
