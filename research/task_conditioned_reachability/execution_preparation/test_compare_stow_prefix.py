"""Tiny synthetic NPZ fixtures ONLY; no original episode/physics replay."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from .compare_stow_prefix import compare_closed_prefix,sha,FIELDS


class PrefixComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.roots=[Path(self.tmp.name)/n for n in ('baseline','candidate')]

    def make(self,root,*,chunks=(3,3),change=None,capture=.01):
        episode=root/'episode';episode.mkdir(parents=True)
        arrays={k:np.zeros((6,5,18) if k in ('issued','delayed') else (6,18)) for k in FIELDS}
        if change is not None:change(arrays)
        rows=[];offset=0
        for number,n in enumerate(chunks):
            p=episode/('chunk%02d.npz'%number);ticks=np.arange(offset+1,offset+n+1)
            np.savez(p,physical_tick=ticks,time_s=ticks*.005,**{k:v[offset:offset+n] for k,v in arrays.items()})
            rows.append(dict(path=p.name,sha256=sha(p)));offset+=n
        (episode/'index.json').write_text(json.dumps(dict(commands=rows)))
        events=[] if capture is None else [dict(event='actual_unloaded_supported_retreat_and_full_path_checked',time=capture)]
        raw=dict(scope_id=root.name,selected_requests=[dict(skill='PUSH')],actual_model_numeric_sha256='a'*64,
                 episode_closure=dict(storage_complete=True,index_sha256=sha(episode/'index.json')),
                 actual_native_results=[dict(skill='push',finish=dict(protected_stow=dict(events=events)))])
        (root/'result.json').write_text(json.dumps(raw));return sha(root/'result.json')

    def compare(self,**kwargs):
        return compare_closed_prefix(*self.roots,baseline_result_sha256=self.hashes[0],candidate_result_sha256=self.hashes[1],**kwargs)

    def test_different_chunk_boundaries_and_first_difference_after_capture(self):
        a=self.make(self.roots[0]);b=self.make(self.roots[1],chunks=(2,4),change=lambda d:d['issued'].__setitem__((2,0,0),1.))
        self.hashes=[a,b];r=self.compare()
        self.assertTrue(r['prefix_match']);self.assertEqual(r['capture_boundary_physics_tick'],2)
        self.assertEqual(r['compared_common_physics_steps'],6)
        self.assertEqual(r['first_bitwise_difference_tick']['issued'],3)
        self.assertTrue(r['different_motor_commands_observed'])

    def test_difference_before_intervention_is_not_a_controlled_prefix(self):
        a=self.make(self.roots[0]);b=self.make(self.roots[1],change=lambda d:d['q_before'].__setitem__((0,0),1.))
        self.hashes=[a,b];self.assertFalse(self.compare()['prefix_match'])

    def test_missing_capture_not_implicitly_zero_or_pass(self):
        self.hashes=[self.make(self.roots[0]),self.make(self.roots[1],capture=None)]
        self.assertIsNone(self.compare()['prefix_match'])

    def test_signed_zero_is_bitwise_difference_not_allclose(self):
        self.hashes=[self.make(self.roots[0]),self.make(self.roots[1],change=lambda d:d['issued'].__setitem__((0,0,0),-0.))]
        r=self.compare();self.assertEqual(r['first_bitwise_difference_tick']['issued'],1)
        self.assertFalse(r['prefix_match'])

    def test_input_pin_and_self_comparison_refused(self):
        self.hashes=[self.make(self.roots[0]),self.make(self.roots[1])]
        with self.assertRaises(ValueError):compare_closed_prefix(*self.roots,baseline_result_sha256='0'*64,candidate_result_sha256=self.hashes[1])
        with self.assertRaises(ValueError):compare_closed_prefix(self.roots[0],self.roots[0],baseline_result_sha256=self.hashes[0],candidate_result_sha256=self.hashes[0])

    def test_npz_mutation_refused_not_silently_rehashed(self):
        self.hashes=[self.make(self.roots[0]),self.make(self.roots[1])]
        with (self.roots[1]/'episode/chunk00.npz').open('ab') as f:f.write(b'x')
        with self.assertRaisesRegex(ValueError,'chunk'):self.compare()


if __name__=='__main__':unittest.main()
