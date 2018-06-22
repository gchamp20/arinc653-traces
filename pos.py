import os
import time
import threading
import sys
from babeltrace import *

class ClockManager:
    instance = None
    def __init__(self):
        if not ClockManager.instance:
            ClockManager.instance = CTFWriter.Clock('A_clock')
            ClockManager.instance.description = "Big Clock"

    def get_clock(self):
        return ClockManager.instance

    def sample(self):
        ClockManager.instance.time = int(time.time() * 10 ** 9)


class WriterManager:
    instance = None
    def __init__(self, trace_path):
        if not WriterManager.instance:
            WriterManager.instance = CTFWriter.Writer(trace_path)
            WriterManager.instance.add_clock(ClockManager().get_clock())
            WriterManager.instance.add_environment_field("Python_version", str(sys.version_info))

    def get_writer(self):
        return WriterManager.instance

class POSTracer:
    def __init__(self, uuid, trace_path):
        self.c = ClockManager().get_clock()
        self.writer = WriterManager(trace_path).get_writer()
        self.stream_class = CTFWriter.StreamClass("p" + str(uuid))
        self.stream_class.clock = self.c
        self.id = uuid
        self.create_event_types()
        self.create_stream()

    def create_event_types(self):
        int32_field_decl = CTFWriter.IntegerFieldDeclaration(32)
        struct_field_decl = CTFWriter.StructureFieldDeclaration()
        struct_field_decl.add_field(int32_field_decl, "pid")
        self.stream_class.event_context_type = struct_field_decl

        event_class = CTFWriter.EventClass("task_create")
        int32_type = CTFWriter.IntegerFieldDeclaration(32)
        event_class.add_field(int32_type, "tid")
        self.stream_class.add_event_class(event_class)
        self.tcreateEventClass = event_class

        self.schedswitchEventClass = CTFWriter.EventClass("sched_switch_in")
        int32_type = CTFWriter.IntegerFieldDeclaration(32)
        self.schedswitchEventClass.add_field(int32_type, "tid")
        self.stream_class.add_event_class(self.schedswitchEventClass)

    def create_stream(self):
        self.stream = self.writer.create_stream(self.stream_class)

    def task_create(self, tid):
        ClockManager().sample()
        e = CTFWriter.Event(self.tcreateEventClass)
        e.payload("tid").value = tid
        print(e)
        #e.stream_context.field("pid").value = self.id
        self.stream.append_event(e)
        self.flush()

    def sched_switch(self, tid):
        ClockManager().sample()
        e = CTFWriter.Event(self.schedswitchEventClass)
        e.payload("tid").value = tid
        e.stream_event_context.field("pid").value = self.id
        self.stream.append_event(e)
        self.flush()

    def flush(self):
        self.stream.flush()

class POS:
    def __init__(self, uuid):
        self.id = uuid
        self.tracer = POSTracer(uuid, os.getcwd() + '/traces')

    def run(self, e, done, runtime):
        print(self.id, "is init")
        self.tracer.task_create(0)
        #while True:
        e.wait()
        budget = runtime
        while budget > 0:
            print(self.id, "is running")
            time.sleep(0.001)
            self.tracer.sched_switch(0)
            budget -= 1
        self.tracer.flush()
        e.clear()
        done.set()

