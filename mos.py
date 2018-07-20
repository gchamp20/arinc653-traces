import pos
import time
import threading

class MOS:
    def __init__(self, nbPartition, timeslices):
        self.timeslices = timeslices
        self.partitions = [pos.POS(x) for x in range(nbPartition)]
        self.events = [threading.Event() for x in range(nbPartition)]
        self.doneEvent = threading.Event()
        self.nb_runs = 3
        self.threads = [
                threading.Thread(name=str(x),
                                target=self.partitions[x].run,
                                args=(self.events[x], self.doneEvent, self.timeslices[x],
                                    self.nb_runs))
                    for x in range(nbPartition)
                ]

    def run(self, runtime):
        for x in range(len(self.partitions)):
            self.threads[x].start()

        cur = 0
        nb_iter = 0
        while nb_iter < (len(self.partitions) * self.nb_runs):
        #while True:
            self.doneEvent.clear()
            self.events[cur].set()
            self.doneEvent.wait()
            cur = (cur + 1) % len(self.partitions)
            nb_iter += 1
        print("done")
