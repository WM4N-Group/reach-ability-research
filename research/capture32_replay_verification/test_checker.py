#!/usr/bin/env python3
"""Checker qualification only. Artificial two-candidate arrays, NOT a replay report."""
import sys
import copy
sys.dont_write_bytecode=True
from pathlib import Path
import unittest
import tempfile
import replay_checker as c

class Checks(unittest.TestCase):
    def test_synthetic_empty_scalar_and_chunk_roundtrip(self):
        for bits,shape in [([], [2,0,3]), ([True], []), ([False]*64, [1,64]), ([True]*26, [1,26])]:
            self.assertEqual(c.decode_mask(c.bool_payload(bits,shape)),bytes(bits))
    def test_same_count_wrong_bits_rejected(self):
        a=c.bool_payload([True,False,True,False],[1,4])
        b=c.bool_payload([False,True,False,True],[1,4])
        self.assertEqual(a['valid'],b['valid'])
        with self.assertRaises(ValueError):c.decode_mask(b,a)
    def test_same_bytes_wrong_shape_rejected(self):
        a=c.bool_payload([True,False,False,True],[1,4]);b=c.bool_payload([True,False,False,True],[2,2])
        with self.assertRaises(ValueError):c.decode_mask(b,a)
    def test_packed_corruption_rejected(self):
        p=c.bool_payload([True,False],[1,2]);p['packed_mask_base64']='AA=='
        with self.assertRaises(ValueError):c.decode_mask(p)
    def test_missing_payload_not_count_only(self):
        p=c.bool_payload([True,False],[1,2]);p.pop('packed_mask_base64')
        with self.assertRaises(KeyError):c.decode_mask(p)
    def test_dtype_and_scalar_types_not_silent_cast(self):
        t=c.typed([[1.,2.]],'float32');other=c.typed([[1.,2.]],'float64')
        with self.assertRaises(ValueError):c.tensor_check(other,t)
        with self.assertRaises(ValueError):c.typed([1,0],'bool')
        with self.assertRaises(ValueError):c.tensor_check(c.typed([.03],'float32'))
        c.tensor_check(c.typed([c.f32(.03)],'float32'))
    def chunk(self):
        # Artificial values at original boundaries; one metric rejects every synthetic candidate.
        size=2;metrics={};masks={};slacks={}
        for gate in c.GATES:
            threshold=c.f32(gate['threshold'])
            value=threshold if gate['op']=='>=' else c.f32(threshold/2)
            if gate['id']=='swing_primitive_gap':value=c.f32(threshold-.001)
            metrics[gate['metric']]=c.typed([[value]*size],'float32')
            passed=value>=threshold if gate['op']=='>=' else value<threshold
            masks[gate['id']]=c.bool_payload([passed]*size,[1,size])
            slack=c.f32(value-threshold) if gate['op']=='>=' else c.f32(threshold-value)
            slacks[gate['id']]=c.typed([[slack]*size],'float32')
        chunk=dict(ordinal=1,row=0,original_candidate_indices=[9,31],ready=c.bool_payload([False]*size,[1,size]),
                   metrics=metrics,gate_masks=masks,signed_slacks=slacks)
        original=dict(row=0,indices=[9,31],payload=copy.deepcopy(chunk['ready']))
        return chunk,original
    def test_metric_mask_and_recombination(self):
        chunk,original=self.chunk();m=c.check_chunk(chunk,original)
        self.assertEqual(list(m['swing_primitive_gap']),[0,0])
        self.assertEqual(list(m['body_path_gap']),[1,1])
    def test_swapped_candidate_order_rejected(self):
        chunk,original=self.chunk();chunk['original_candidate_indices'].reverse()
        with self.assertRaises(ValueError):c.check_chunk(chunk,original)
    def test_boolean_subgate_cannot_lie(self):
        chunk,original=self.chunk();chunk['gate_masks']['swing_primitive_gap']=c.bool_payload([True,True],[1,2])
        with self.assertRaises(ValueError):c.check_chunk(chunk,original)
    def test_margin_units_or_sign_cannot_change(self):
        chunk,original=self.chunk();chunk['signed_slacks']['swing_primitive_gap']=c.typed([[1.,1.]],'float32')
        with self.assertRaises(ValueError):c.check_chunk(chunk,original)
    def test_strict_boundary_equality_is_failure(self):
        chunk,original=self.chunk();g=next(g for g in c.GATES if g['id']=='support_ik_error')
        chunk['metrics'][g['metric']]=c.typed([[c.f32(g['threshold'])]*2],'float32')
        chunk['gate_masks'][g['id']]=c.bool_payload([False,False],[1,2])
        chunk['signed_slacks'][g['id']]=c.typed([[0.,0.]],'float32')
        self.assertEqual(list(c.check_chunk(chunk,original)[g['id']]),[0,0])
    def test_joint_cannot_be_replaced_with_any_gate(self):
        chunk,original=self.chunk();chunk['ready']=c.bool_payload([True,True],[1,2])
        with self.assertRaises(ValueError):c.check_chunk(chunk,original)
    def test_independent_exclusive_first_order_are_distinct(self):
        masks={g['id']:[1,1] for g in c.GATES}
        masks[c.GATES[0]['id']]=[0,1];masks[c.GATES[1]['id']]=[0,0]
        stats=c.statistic(masks);a,b=stats['rows'][:2]
        self.assertEqual((a['independent_rejected'],a['exclusive_rejected'],a['first_excluded_in_declared_order']),(1,0,1))
        self.assertEqual((b['independent_rejected'],b['exclusive_rejected'],b['first_excluded_in_declared_order']),(2,1,1))
    def test_original_return_type_and_value_check(self):
        original=c.typed([False],'bool');v=c.typed([True],'bool')
        with self.assertRaises(ValueError):c.tensor_check(v,original)
    def test_json_duplicate_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'duplicate.json'
            p.write_text('{"x": 1, "x": 2}\n')
            with self.assertRaises(ValueError):c.load_json(p)

if __name__=='__main__':unittest.main(verbosity=2)
