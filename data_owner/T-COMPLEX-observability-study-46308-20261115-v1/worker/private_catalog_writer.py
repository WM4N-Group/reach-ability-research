"""Lossless PRIVATE metadata alias at the old recorder boundary, not INPUT8 edit.
RegisteredObserver supplies model_input=False/time_s; original mixed-rate writer
requires model_input_allowed=False. Preserve literal original catalog in sidecar,
add explicit aliases on a copy, then invoke the UNCHANGED original writer.
Both arms use identical adapter; no values/masks/observations/native state edited.
"""
import json,hashlib
class PrivateCatalogWriter:
 def __init__(self,writer,original_catalog_path):
  self.writer=writer;self.original_catalog=original_catalog_path.open('x');self.rows=0
 def __getattr__(self,name):return getattr(self.writer,name)
 def append_visual(self,packet,*,control_tick,private_catalog):
  if private_catalog.get('schema')!='ainav-private-registered-object-catalog-v1'or private_catalog.get('model_input')is not False or private_catalog.get('control_tick')!=control_tick:raise ValueError('Exact original RegisteredObserver PRIVATE catalog required')
  if 'model_input_allowed'in private_catalog or 'actual_sim_time_s'in private_catalog:raise ValueError('No overwrite/ambiguous alias')
  original=json.dumps(private_catalog,sort_keys=True,separators=(',',':'),allow_nan=False);adapted=dict(private_catalog,model_input_allowed=False,actual_sim_time_s=private_catalog['time_s'])
  self.original_catalog.write(json.dumps(dict(original_catalog=private_catalog,original_canonical_sha256=hashlib.sha256(original.encode()).hexdigest(),alias_only_added_fields=['model_input_allowed','actual_sim_time_s'],planner_or_fit_input=False),allow_nan=False)+'\n');self.original_catalog.flush()
  self.writer.append_visual(packet,control_tick=control_tick,private_catalog=adapted);self.rows+=1
 def close(self,**kwargs):
  try:return self.writer.close(**kwargs)
  finally:self.original_catalog.close()
