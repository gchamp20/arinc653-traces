import pos
import time
import threading

class MOS:
    def __init__(self, nbPartition, timeslices):
        self.timeslices = timeslices
        self.partitions = [pos.POS(x) for x in range(nbPartition)]
        self.events = [threading.Event() for x in range(nbPartition)]
        self.doneEvent = threading.Event()
        self.threads = [
                threading.Thread(name=str(x),
                                target=self.partitions[x].run,
                                args=(self.events[x], self.doneEvent, self.timeslices[x])) 
                    for x in range(nbPartition)
                ]

    def run(self, runtime):
        cur = 0
        for x in range(len(self.partitions)):
            self.threads[x].start()
        for cur in range(len(self.partitions)):
        #while True:
            self.doneEvent.clear()
            self.events[cur].set()
            self.doneEvent.wait()
            cur = (cur + 1) % len(self.partitions)
