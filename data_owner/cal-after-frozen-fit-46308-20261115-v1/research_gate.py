"""Read-only actual frozen TRAIN gate binding; no learner/model/physics imports."""
from pathlib import Path
import json,hashlib
FIT_ROOT=Path('/mnt/yuanyue/reach-runs/G3-TRAIN-only-20261115-v1')
RELEASE_SHA='670d4eb5062f903ecdadb200acbd2744647388888f8070e1066a527a2813bdd3'
PINS={'DERIVED_TRAINING_PROTOCOL.json':'d626da89847c5fe08562b152c40c9c8ee624c58b75f937b36a47390a96f8696d','CLOSED_TRAIN_ONLY_DATASET.json':'cb2cae6949032eadd91a58588be316f4c62a9c79e5547fa8e7cd8dd44c860c72','TRAIN_SOURCE_FEATURE_LABEL_GATE.json':'189cad1f79ef5b62251b080315a1b8a7bfd629eab3792955808129f4ab2f3a1c','TRAIN_FROZEN_FIT.json':'3371ac20bba8649eff3904c24b480146c5f0eac4467eb24b3fb2c015e72307c3'}
PROTOCOL='2f82530d1f880892c631c7b62cc79bfbd72d57e1b369faf99f542d02d4a53eda'
MODEL='a8b1f165d33719fcb8fc1b95c6a1a31d0861bacda2f4fcf1c06ebf30387d7766'
ROWS='882ca00beafec900597e5485beaf7fb3414676f7c8e705a4c16716405f006af6'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify():
 p=FIT_ROOT/'TRAIN_GATE_AND_FIT_RELEASE.json';assert sha(p)==RELEASE_SHA;release=json.loads(p.read_bytes());assert release['collection_protocol_file_sha256']==PROTOCOL and release['files']==PINS
 for name,pin in PINS.items():assert not(FIT_ROOT/name).is_symlink()and sha(FIT_ROOT/name)==pin
 gate=json.loads((FIT_ROOT/'TRAIN_SOURCE_FEATURE_LABEL_GATE.json').read_bytes());fit=json.loads((FIT_ROOT/'TRAIN_FROZEN_FIT.json').read_bytes())
 assert gate['status']=='CLOSED_TRAIN_SOURCE_FEATURE_LABEL_GATE_PASS_NOT_FIT_OR_DISPATCH'and gate['collection_protocol_file_sha256']==PROTOCOL and gate['closed_attempts']==gate['new_purpose_rows']==6 and gate['success_rows']==4 and gate['native_failure_rows']==2 and gate['condition_groups']==gate['distinct_public_proprio_states']==2 and not gate['old_DEV_fit']
 for path,pin in gate['source_pins'].items():assert sha(Path(path))==pin
 assert fit['status']=='TRAIN_ONLY_FIT_FROZEN_HELDOUT_NOT_COLLECTED'and fit['training_entry_executed']and fit['training_rows']==fit['closed_TRAIN_attempts']==6 and fit['model_sha256']==MODEL and fit['training_rows_sha256']==ROWS and not fit['heldout_used_for_fit']and not fit['execution_authorized']and fit['source_dataset_sha256']==PINS['CLOSED_TRAIN_ONLY_DATASET.json']
 assert release['frozen_model_content_sha256']==MODEL and not release['heldout_metrics_available']and not release['model_deployment_qualified']and release['VALIDATION10_12_not_released_by_this_file']
 return dict(release_path=str(p),release_sha256=RELEASE_SHA,gate_sha256=PINS['TRAIN_SOURCE_FEATURE_LABEL_GATE.json'],fit_file_sha256=PINS['TRAIN_FROZEN_FIT.json'],derived_manifest_sha256=PINS['DERIVED_TRAINING_PROTOCOL.json'],frozen_model_content_sha256=MODEL,training_rows_sha256=ROWS,collection_protocol_sha256=PROTOCOL,fit_once_already_completed=True,fit_or_refit_by_Data_allowed=False,CAL7_9_only=True,VAL10_12_released=False,online_or_T_complex_critic_deployment_allowed=False,weights_and_rows_exported=False)
