import os
import time
import threading
import sys
import babeltrace.writer as btw
import random

class ClockManager:
    instance = None
    def __init__(self):
        if not ClockManager.instance:
            ClockManager.instance = btw.Clock('A_clock')
            ClockManager.instance.description = "Big Clock"

    def get_clock(self):
        return ClockManager.instance

    def sample(self):
        ClockManager.instance.time = int(time.time() * 10 ** 9)


class WriterManager:
    instance = None
    def __init__(self, trace_path):
        if not WriterManager.instance:
            WriterManager.instance = btw.Writer(trace_path)
            WriterManager.instance.add_clock(ClockManager().get_clock())
            WriterManager.instance.add_environment_field("Python_version", str(sys.version_info))

    def get_writer(self):
        return WriterManager.instance

class POSTracer:
    def __init__(self, uuid, trace_path):
        self.c = ClockManager().get_clock()
        self.writer = WriterManager(trace_path).get_writer()
        self.stream_class = btw.StreamClass("p" + str(uuid))
        self.stream_class.clock = self.c
        self.id = uuid
        self.create_event_types()
        self.create_stream()

    def create_event_types(self):
        int32_field_decl = btw.IntegerFieldDeclaration(32)
        struct_field_decl = btw.StructureFieldDeclaration()
        struct_field_decl.add_field(int32_field_decl, "pid")
        struct_field_decl.add_field(int32_field_decl, "cpu_id")
        self.stream_class.packet_context_type = struct_field_decl
        self.stream_context_decl = struct_field_decl

        event_class = btw.EventClass("task_create")
        int32_type = btw.IntegerFieldDeclaration(32)
        event_class.add_field(int32_type, "tid")
        self.stream_class.add_event_class(event_class)
        self.tcreateEventClass = event_class

        self.schedswitchEventClass = btw.EventClass("task_switch")
        int32_type = btw.IntegerFieldDeclaration(32)
        self.schedswitchEventClass.add_field(int32_type, "next_tid")
        self.stream_class.add_event_class(self.schedswitchEventClass)

        self.irqEntryEventClass = btw.EventClass("irq_entry")
        int32_type = btw.IntegerFieldDeclaration(32)
        self.irqEntryEventClass.add_field(int32_type, "irq")
        self.stream_class.add_event_class(self.irqEntryEventClass)

        self.irqExitEventClass = btw.EventClass("irq_exit")
        int32_type = btw.IntegerFieldDeclaration(32)
        self.irqExitEventClass.add_field(int32_type, "irq")
        self.stream_class.add_event_class(self.irqExitEventClass)

        self.syscallEntryEventClass = btw.EventClass("sys_raw_entry")
        int32_type = btw.IntegerFieldDeclaration(32)
        self.syscallEntryEventClass.add_field(int32_type, "id")
        self.stream_class.add_event_class(self.syscallEntryEventClass)

        self.syscallExitEventClass = btw.EventClass("sys_raw_exit")
        int32_type = btw.IntegerFieldDeclaration(32)
        self.syscallExitEventClass.add_field(int32_type, "id")
        self.stream_class.add_event_class(self.syscallExitEventClass)


    def create_stream(self):
        self.stream = self.writer.create_stream(self.stream_class)
        packet_context = self.stream.packet_context
        f = packet_context.field("pid")
        f.value = self.id
        f = packet_context.field("cpu_id")
        f.value = 1

    def task_create(self, tid):
        ClockManager().sample()
        e = btw.Event(self.tcreateEventClass)
        e.payload("tid").value = tid

        #ctx = btw.StructureField(self.stream_context_decl)
        #ctx.field("pid").value = self.id
        #e.stream_context = ctx

        self.stream.append_event(e)

    def sched_switch(self, tid):
        ClockManager().sample()
        e = btw.Event(self.schedswitchEventClass)
        e.payload("next_tid").value = tid

        #ctx = btw.StructureField(self.stream_context_decl)
        #ctx.field("pid").value = self.id
        #e.stream_context = ctx

        self.stream.append_event(e)

    def irq_entry(self, irq):
        ClockManager().sample()
        e = btw.Event(self.irqEntryEventClass)
        e.payload("irq").value = irq
        self.stream.append_event(e)

    def irq_exit(self, irq):
        ClockManager().sample()
        e = btw.Event(self.irqExitEventClass)
        e.payload("irq").value = irq
        self.stream.append_event(e)

    def syscall_exit(self, irq):
        ClockManager().sample()
        e = btw.Event(self.syscallExitEventClass)
        e.payload("id").value = irq
        self.stream.append_event(e)

    def syscall_entry(self, irq):
        ClockManager().sample()
        e = btw.Event(self.syscallEntryEventClass)
        e.payload("id").value = irq
        self.stream.append_event(e)

    def flush(self):
        self.stream.flush()

class POS:
    def __init__(self, uuid):
        self.id = uuid
        self.tracer = POSTracer(uuid, os.getcwd() + '/traces')

    def run(self, e, done, runtime):
        nb_task = random.randrange(1, 10)
        print(self.id, "is init", nb_task)
        tasks = [0 for i in range(nb_task)]
        t = 0
        tasks[t] = 1

        e.wait()
        self.tracer.task_create(t)
        self.tracer.sched_switch(t)

        budget = runtime
        handling_interrupt = False
        handling_syscall = False

        int_number = -1

        int_duration = -1
        syscall_duration = -1
        while budget > 0:
            #print(self.id, "is running")
            if not handling_interrupt and not handling_syscall:
                if random.randrange(0, 100) > 80:
                    old_t = t
                    t = random.randrange(0, nb_task)
                    if t != old_t:
                        if tasks[t] == 0:
                            self.tracer.task_create(t)
                            tasks[t] = 1
                        self.tracer.sched_switch(t)
                elif random.randrange(0, 100) > 90:
                    handling_syscall = True
                    syscall_duration = random.randrange(1, 10) * 0.0005
                    self.tracer.syscall_entry(2)
                elif random.randrange(0, 100) > 97:
                    handling_interrupt = True
                    int_number = random.randrange(10, 40)
                    int_duration = random.randrange(1, 5) * 0.0005
                    self.tracer.irq_entry(int_number)
            else:
                if handling_interrupt:
                    int_duration -= 0.001
                    if int_duration <= 0:
                        self.tracer.irq_exit(int_number)
                        handling_interrupt = False
                elif handling_syscall:
                    syscall_duration -= 0.001
                    if syscall_duration <= 0:
                        self.tracer.syscall_exit(2)
                        handling_syscall = False

            time.sleep(0.001)
            #self.tracer.sched_switch(0)
            budget -= 1

        if handling_interrupt:
            time.sleep(int_duration)
            self.tracer.irq_exit(int_number)

        self.tracer.flush()
        e.clear()
        done.set()

