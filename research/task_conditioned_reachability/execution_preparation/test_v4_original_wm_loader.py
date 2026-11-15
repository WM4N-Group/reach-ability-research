"""Read-only inference-source/loader rejection tests; no Torch, weights or model."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from .v4_original_wm_loader import validate_inference_closure,restore_original_cpu
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'inference_source/original_behavior7a6'

class OriginalWMLoaderTests(unittest.TestCase):
    def test_exact_five_file_original_closure(self):
        path,manifest=validate_inference_closure(SOURCE)
        self.assertEqual(path,SOURCE);self.assertEqual(len(manifest['files']),5)
    def test_original_source_bytes_not_algorithm_reimplementation(self):
        _,manifest=validate_inference_closure(SOURCE)
        for name,row in manifest['files'].items():
            self.assertEqual(hashlib.sha256((SOURCE/name).read_bytes()).hexdigest(),row['sha256'])
            self.assertEqual((SOURCE/name).stat().st_size,row['bytes'])
    def test_changed_code_rejected_before_scientific_imports(self):
        with tempfile.TemporaryDirectory()as d:
            dest=Path(d)/'source';shutil.copytree(SOURCE,dest)
            with(dest/'visual_latent_behavior.py').open('ab')as f:f.write(b'\n# CHANGED SOFTWARE FIXTURE\n')
            with self.assertRaises(ValueError):validate_inference_closure(dest)
    def test_cached_other_model_namespace_rejected(self):
        with patch.dict(sys.modules,{'visual_latent_behavior':SimpleNamespace(__file__='/EXPLICIT_WRONG_NAMESPACE.py')}):
            with self.assertRaises(ValueError):validate_inference_closure(SOURCE)
    def test_wrong_checkpoint_stops_before_Torch_or_training(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'fixture.pt';p.write_bytes(b'NOT_REAL_WEIGHTS')
            before='visual_latent_behavior'in sys.modules
            with self.assertRaises(ValueError):restore_original_cpu(p,source_root=SOURCE)
            self.assertEqual('visual_latent_behavior'in sys.modules,before)
    def test_closure_has_no_native_runtime_or_Actor_import(self):
        forbidden={'mujoco','onnxruntime','gym','isaaclab'}
        for p in SOURCE.glob('*.py'):
            tree=ast.parse(p.read_bytes())
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.extend(n.name.split('.')[0]for n in node.names)
                elif isinstance(node,ast.ImportFrom)and node.module:imports.append(node.module.split('.')[0])
            self.assertFalse(forbidden.intersection(imports))

if __name__=='__main__':unittest.main()
