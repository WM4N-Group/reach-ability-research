"""Original recorder privacy annotation bridge, NOT a sensor/tensor transform.
RegisteredObserver emits model_input=False; original v2 stream writer requires
model_input_allowed=False. The original standalone callers explicitly add this
same annotation. Preserve packet, ticks, calibration and every private value;
never weaken writer timing/shape/validity checks or pass private data as input.
"""
class PrivateCatalogBoundaryWriter:
    def __init__(self,writer):self.writer=writer;self.annotated_frames=0
    def append_visual(self,packet,*,control_tick,private_catalog):
        if type(private_catalog)is not dict or private_catalog.get('schema')!='ainav-private-registered-object-catalog-v1' or private_catalog.get('control_tick')!=control_tick or private_catalog.get('model_input')is not False:raise ValueError('Exact original RegisteredObserver private boundary only')
        if 'model_input_allowed'in private_catalog and private_catalog['model_input_allowed']is not False:raise ValueError('Conflicting original private permission must never be relaxed')
        annotated=dict(private_catalog,model_input_allowed=False)
        result=self.writer.append_visual(packet,control_tick=control_tick,private_catalog=annotated)
        self.annotated_frames+=1
        return result
    def __getattr__(self,name):return getattr(self.writer,name)
