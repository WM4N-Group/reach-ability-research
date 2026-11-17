"""Owner D3 target-view sink/phase connection. Never polls native predicates.

The frozen context source invokes this at its fresh selected-view RETURN boundary;
only original make_target_context owns the actual view/controller construction.
"""
import hashlib
import os


class TargetSinkOwner:
    def __init__(self, *, runtime, driver_reader, budget, output_path, bind_sink, scope_id):
        if not callable(driver_reader)or not callable(bind_sink):raise ValueError('Actual owner bindings')
        self.runtime,self.driver_reader,self.budget=runtime,driver_reader,budget
        self.output_path,self.bind_sink,self.scope_id=output_path,bind_sink,scope_id
        self.stream=None;self.sinks=[];self.closed=False

    def phase(self):
        driver=self.driver_reader()
        executor=None if driver is None else driver.executor
        session=None if executor is None else executor.session
        machine=None if session is None else session.machine
        if machine is None:return 'UNKNOWN:original_machine_not_constructed'
        root=getattr(machine,'phase',None)
        finish=getattr(machine,'finish',None)
        tail=None if finish is None else getattr(finish,'phase',None)
        root=root if type(root)is str and 0<len(root)<=32 else 'UNKNOWN'
        tail=tail if type(tail)is str and 0<len(tail)<=32 else 'NONE_OR_UNKNOWN'
        return 'machine:'+root+'|finish:'+tail

    def bind(self, view):
        if self.closed or self.sinks:raise RuntimeError('Only one original first-PUSH target view, no retries')
        if self.stream is None:self.stream=self.budget.open(self.output_path,'xb')
        def write(payload):
            self.stream.write(payload);self.stream.flush();os.fsync(self.stream.fileno())
            return str(self.output_path)+'#sha256='+hashlib.sha256(payload).hexdigest()
        sink=self.bind_sink(enabled=True,env=view,runtime=self.runtime,write_record=write,
            phase_reader=self.phase,phase_source_ref='original SDK switch/machine.py:machine.phase + push/finish.py:finish.phase; frozen file SHA in D3 program',
            scope_id=self.scope_id,world_role='task',max_records=4096,max_payload_bytes=8<<20)
        self.sinks.append(sink)
        return sink

    def report(self):
        return dict(task_views=len(self.sinks),sinks=[s.report()for s in self.sinks],
                    predicates_or_clock_polled_by_report=False,aux_not_task_evidence=True)

    def close(self):
        if self.stream is not None and not self.stream.closed:self.stream.close()
        self.closed=True
