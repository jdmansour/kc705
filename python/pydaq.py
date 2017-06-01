"""
This is a prototype of the actual data taking module, which
will be written in C++.  This module generates fake data,
but ideally should behave just like the future real module.

The main class that needs to be implemented is DataTaker.
"""

import threading
from collections import deque
from queue import Queue

import numpy as np

STATE_STOPPED = 'STATE_STOPPED'
STATE_RUNNING = 'STATE_RUNNING'
CMD_END_RUN = 99


def fake_data():
    x, y = np.rint(np.random.multivariate_normal([20, 5], [[4, 0], [0, 4]], 1))[0].astype(int)
    # ret = np.zeros(shape=(48, 16))
    ret = np.where(np.random.rand(48, 16)<0.001, 1, 0)
    ret[x, y] = 1
    return ret


class DataTakingThread(threading.Thread):
    """ Internal class, this is the thread that generates fake data. """
    def __init__(self):
        super().__init__()
        self.run_number = 100
        self.data_lock = threading.Lock()
        self.queue = Queue()
        self._start_next_run()

    def _start_next_run(self):
        """ Starts a new run.  Should be called within the lock. """
        self.nevents = 0
        self.accumulated_events = np.zeros(shape=(48, 16))
        self.last_events = deque(maxlen=100)
        self.run_number += 1

    def run(self):
        while True:
            if not self.queue.empty():
                cmd = self.queue.get()
                if cmd == CMD_END_RUN:
                    break

            hits = fake_data()

            with self.data_lock:
                self.nevents += 1
                self.accumulated_events += hits
                self.last_events.append(hits)

                if self.nevents > 50000:
                    # start next run
                    self._start_next_run()


class DataTaker:
    """ Mockup of the class that handles the data taking.
        This is going to be written in C++.
        
        There is no configuration yet.  One idea that I have is that we have a
        vector of "RunConfiguration" objects.  Each object has runNumber, maximum
        number of events, and all the configurations we want to make (e.g. thresholds?).
        The DataTaker would then run each RunConfiguration, take enough events, and
        automatically go to the next.  A RunConfiguration could also take infinite
        events (until manually stopped).

        What is also missing is a callback, so that this class can notify the GUI that
        something happened (a run ended, or a error occurred).
        """

    def __init__(self):
        self.state = STATE_STOPPED
        self.thread = None

    def start_run(self):
        """ Starts a new run. """
        assert self.state == STATE_STOPPED
        self.thread = DataTakingThread()
        self.thread.start()
        self.state = STATE_RUNNING

    def stop_run(self):
        """ Stops the current run. """
        assert self.state == STATE_RUNNING
        self.thread.queue.put(CMD_END_RUN)

        # Instead of joining the thread, we could wait for a
        # threading.Condition here and keep the thread active.
        self.thread.join()
        self.state = STATE_STOPPED

    def get_state(self):
        """ Returns the current state. """
        return self.state

    def get_accumulated_events(self):
        """ Returns a bunch of recent events (e.g. the last 100). """
        if not self.thread:
            return []
        with self.thread.data_lock:
            return list(self.thread.last_events)

    def get_event_number(self):
        """ Gets the current event number. """
        if not self.thread:
            return 0
        with self.thread.data_lock:
            return self.thread.nevents

    def get_run_number(self):
        """ Gets the current run number. """
        if not self.thread:
            return 0
        with self.thread.data_lock:
            return self.thread.run_number

