from mos import MOS

timeslices = [100, 150, 200]
m = MOS(len(timeslices), timeslices)
m.run(1000)
