from mos import MOS

timeslices = [10, 15, 20]
m = MOS(len(timeslices), timeslices)
m.run(1000)
