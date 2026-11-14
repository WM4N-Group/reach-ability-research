"""Opt-in CURRENT live-world third-view raw RGB, never state replay/rerender.
Disabled imports/constructs nothing. Ordinary video failures are optional;
mutation of live simulation by a capture callback remains fail-closed safety.
"""
from pathlib import Path
import hashlib
import importlib
import inspect
import json
import math
import os

ACTUAL = 'DIRECT_CURRENT_LIVE_MUJOCO_RGB'
SOFTWARE = 'SOFTWARE_FIXTURE_NOT_EXPERIMENT_FOOTAGE'
ROLE = 'PRIVATE_VIDEO_EVIDENCE_NOT_PLANNER_INPUT_OR_FIT'


class CaptureMutation(RuntimeError):
    pass


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def camera_spec(value):
    v = dict(value)
    need(v.get('kind') in ('fixed_free', 'named_world'), 'Explicit external camera kind')
    for k in ('width', 'height', 'stride_physics_ticks', 'chunk_frames', 'max_bytes'):
        need(type(v.get(k)) is int and v[k] > 0, 'Positive exact camera quantity: ' + k)
    need(v['width'] <= 4096 and v['height'] <= 4096 and v['chunk_frames'] <= 64,
         'Bound raw-frame buffers before allocation')
    if v['kind'] == 'fixed_free':
        need(type(v.get('lookat')) in (list, tuple) and len(v['lookat']) == 3,
             'Freeze one common lookat, never follow outcome-dependent state')
        for x in [*v['lookat'], v.get('distance'), v.get('azimuth'), v.get('elevation')]:
            need(type(x) in (int, float) and math.isfinite(x), 'Finite predeclared camera pose')
        need(v['distance'] > 0, 'Positive camera distance')
    else:
        need(type(v.get('name')) is str and bool(v['name']), 'Named world camera required')
    return v


def spec_sha(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode()).hexdigest()


class LiveMuJoCoCamera:
    """Renderer owns no world. Must be constructed only in a NEW qualified run.
    The supplied snapshot/unchanged are the ORIGINAL onboard observer's read-only
    guards. No mj_step, mj_forward, MjData, state-file load or physics setter here.
    """
    def __init__(self, runtime, spec, *, snapshot, unchanged,
                 software_fixture=False, module_loader=None):
        self.r = runtime
        self.spec = camera_spec(spec)
        self.snapshot, self.unchanged = snapshot, unchanged
        self.model, self.data = runtime.sim.model, runtime.sim.data
        need(callable(snapshot) and callable(unchanged), 'Original state-preservation callbacks')
        module = (module_loader or (lambda: importlib.import_module('mujoco')))()
        need(software_fixture or (module.__name__ == 'mujoco' and module.__version__ == '3.3.2'),
             'Current exact native module, never a replay implementation')
        self.origin = SOFTWARE if software_fixture else ACTUAL
        self.dt = float(self.model.opt.timestep)
        need(self.dt == .005, 'Original native200Hz clock')
        visual = self.model.vis.global_
        need(self.spec['width'] <= visual.offwidth and self.spec['height'] <= visual.offheight,
             'Do not mutate shared model offscreen dimensions for video')
        if self.spec['kind'] == 'named_world':
            ref = self.model.camera(self.spec['name'])
            need(int(self.model.cam_bodyid[ref.id]) == 0,
                 'Do not mislabel body-attached onboard RGB as external third view')
            self.camera = self.spec['name']
        else:
            self.camera = module.MjvCamera()
            self.camera.type = module.mjtCamera.mjCAMERA_FREE
            self.camera.lookat[:] = self.spec['lookat']
            for k in ('distance', 'azimuth', 'elevation'):
                setattr(self.camera, k, self.spec[k])
        self.renderer = module.Renderer(self.model, height=self.spec['height'], width=self.spec['width'])
        self.provenance = dict(origin=self.origin, role=ROLE,
            camera_spec=self.spec, camera_spec_sha256=spec_sha(self.spec),
            mujoco_version=getattr(module, '__version__', None),
            current_live_model_object_id=id(self.model), current_live_data_object_id=id(self.data),
            no_state_file_or_saved_review_model_input=True,
            current_capture_only_not_historical_P0_binding=True)
        try:
            source = inspect.getsourcefile(module.Renderer)
            self.provenance['current_renderer_source_sha256'] = sha(source) if source else None
        except (OSError, TypeError):
            self.provenance['current_renderer_source_sha256'] = None

    def clock(self):
        need(self.r.sim.model is self.model and self.r.sim.data is self.data,
             'Capture must remain bound to this SAME actual live world')
        tick, stamp = self.r.step_count, float(self.data.time)
        need(type(tick) is int and tick >= 0 and math.isfinite(stamp) and
             abs(stamp - tick * self.dt) < 1e-7, 'Exact current runtime tick/sim clock')
        return tick, stamp

    def frame(self):
        import numpy as np
        tick, stamp = self.clock()
        before = self.snapshot()
        try:
            self.renderer.disable_depth_rendering()
            self.renderer.update_scene(self.data, camera=self.camera)
            rgb = self.renderer.render().copy()
        finally:
            if not self.unchanged(before, self.snapshot()):
                raise CaptureMutation('Capture callback mutated live physics/state/queue; never roll it back')
            try:
                after_clock = self.clock()
            except Exception as error:
                raise CaptureMutation('Capture invalidated the live clock/binding') from error
            if after_clock != (tick, stamp):
                raise CaptureMutation('Capture advanced the live simulation clock')
        need(rgb.dtype == np.uint8 and rgb.shape == (self.spec['height'], self.spec['width'], 3),
             'Direct actual RGB uint8, no interpolation/synthetic frame')
        return tick, stamp, rgb

    def close(self):
        self.renderer.close()


class OptionalRawThirdView:
    """Lossless direct raw-frame MASTER; not a claim that a clip is encoded.
    An ordinary camera/storage/quota failure ends video only, records partial
    coverage and MUST NOT become a native-success condition or retry reason.
    """
    def __init__(self, root, *, enabled=False, source_factory=None,
                 scope_id=None, episode_id=None, program_sha256=None):
        need(type(enabled) is bool, 'Explicit opt-in')
        self.enabled, self.root = enabled, Path(root)
        self.source = None
        self.origin = None
        self.owns_root = False
        self.status = 'DISABLED'
        self.reason = None
        self.buffer, self.chunks = [], []
        self.captured = self.archived = self.bytes = 0
        self.last_tick = None
        self.closed = False
        self.binding = dict(scope_id=scope_id, episode_id=episode_id, program_sha256=program_sha256)
        if not enabled:
            return  # Do not even read runtime/factory or create output directory.
        try:
            need(all(type(x) is str and x for x in self.binding.values()), 'Explicit new scope/program identities')
            need(not self.root.exists() and not self.root.is_symlink(), 'Never overwrite/reopen an old recording root')
            need(callable(source_factory), 'Live source factory required')
            self.source = source_factory()
            need(type(self.source) is LiveMuJoCoCamera, 'Exact current-live adapter only; no replay-file/frame provider')
            need(self.source.origin in (ACTUAL, SOFTWARE), 'Known direct/explicit test provenance')
            self.origin = self.source.origin
            self.spec = camera_spec(self.source.spec)
            self.root.mkdir(parents=True, exist_ok=False)
            self.owns_root = True
            self.status = 'CAPTURING'
            self._write_new('metadata.json', dict(schema='Data-direct-third-view-raw-metadata-v1',
                **self.binding, **self.source.provenance, native_success_gate=False,
                raw_frame_master_not_state_replay=True, encoded_video_created=False))
        except CaptureMutation:
            raise
        except Exception as error:
            self._fail(error)

    def _write_new(self, name, value):
        with (self.root / name).open('x') as f:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write(chr(10));f.flush();os.fsync(f.fileno())

    def _fail(self, error):
        self.status = 'VIDEO_UNAVAILABLE_OR_INCOMPLETE'
        self.reason = type(error).__name__ + ': ' + str(error)
        self.buffer = []  # No synthesized/retimed replacement for dropped frames.
        if self.source is not None:
            try:self.source.close()
            except Exception:pass
            self.source = None

    def capture_if_due(self):
        """Call at original review hook AND tick zero, never step for a frame.
        Read runtime.step_count, not the host's possibly lagging tick counter.
        The same-tick call is idempotent; missing grid epochs remain incomplete.
        """
        if self.status != 'CAPTURING':
            return None
        try:
            tick, _ = self.source.clock()
        except CaptureMutation:
            raise
        except Exception as error:
            self._fail(error)
            return None
        if tick == self.last_tick or tick % self.spec['stride_physics_ticks']:
            return None
        return self.capture()

    def capture(self):
        if self.status != 'CAPTURING':
            return None
        try:
            tick, stamp, rgb = self.source.frame()
            stride = self.spec['stride_physics_ticks']
            expected = 0 if self.last_tick is None else self.last_tick + stride
            need(tick == expected, 'Missing/duplicate live camera epoch; do not invent or compress time')
            self.buffer.append((tick, stamp, rgb))
            self.last_tick = tick
            self.captured += 1
            if len(self.buffer) >= self.spec['chunk_frames']:
                self._flush()
            return dict(physics_tick=tick, actual_sim_time_s=stamp,
                        origin=self.source.origin if self.source else None)
        except CaptureMutation as error:
            self._fail(error)
            self.status = 'CAPTURE_STATE_MUTATION_REQUIRES_NATIVE_SAFE_STOP'
            raise  # A real state mutation is safety/truth failure, not video quality.
        except Exception as error:
            self._fail(error)
            return None

    def _flush(self):
        import numpy as np
        if not self.buffer:
            return
        ticks = np.array([r[0] for r in self.buffer], dtype=np.int64)
        stamps = np.array([r[1] for r in self.buffer], dtype=np.float64)
        images = np.stack([r[2] for r in self.buffer])
        # Conservative bound before optional video can consume the native reserve.
        bound = images.nbytes + ticks.nbytes + stamps.nbytes + 65536 + images.nbytes // 1000
        need(self.bytes + bound <= self.spec['max_bytes'], 'Stop optional video at its own frozen quota')
        rel = Path('raw-rgb') / ('%06d.npz' % len(self.chunks))
        p = self.root / rel;p.parent.mkdir(exist_ok=True)
        with p.open('xb') as f:
            np.savez_compressed(f, rgb=images, physics_tick=ticks, actual_sim_time_s=stamps)
        size = p.stat().st_size
        self.bytes += size
        self.chunks.append(dict(path=str(rel), sha256=sha(p), frames=len(ticks),
            first_physics_tick=int(ticks[0]), last_physics_tick=int(ticks[-1]),
            raw_RGB_bytes_sha256=hashlib.sha256(images.tobytes()).hexdigest()))
        self.archived += len(ticks)
        self.buffer = []

    def close(self):
        if self.closed:
            return self.closure
        final_tick = final_time = None
        if self.status == 'CAPTURING':
            try:
                final_tick, final_time = self.source.clock()
                self._flush()
            except CaptureMutation:raise
            except Exception as error:self._fail(error)
        complete = (self.status == 'CAPTURING' and self.last_tick is not None and
                    self.last_tick == final_tick // self.spec['stride_physics_ticks'] * self.spec['stride_physics_ticks'] and
                    self.captured == self.archived)
        self.closure = dict(schema='Data-direct-third-view-raw-closure-v1', **self.binding,
            origin=self.origin,
            role=ROLE, status='RAW_FRAME_MASTER_COMPLETE' if complete else self.status,
            native_success_gate=False, retry_or_resampling_granted=False,
            direct_from_current_live_runtime=complete and self.source.origin == ACTUAL,
            complete_for_capture_grid=bool(complete), captured_frames=self.captured,
            archived_frames=self.archived, bytes=self.bytes, chunks=self.chunks,
            final_physics_tick=final_tick, actual_run_end_time_s=final_time,
            last_acquired_physics_tick=self.last_tick, missing_reason=self.reason,
            camera_spec_sha256=spec_sha(self.spec) if hasattr(self, 'spec') else None,
            metadata_sha256=sha(self.root/'metadata.json') if self.owns_root and (self.root/'metadata.json').exists() else None,
            encoded_video_created=False, state_replay_or_rerender_used=False,
            sampling_or_interpolation_of_missing_frames=False)
        if self.owns_root:
            try:self._write_new('closure.json', self.closure)
            except Exception as error:
                self.closure['closure_storage_error'] = type(error).__name__ + ': ' + str(error)
                self.closure['complete_for_capture_grid'] = False
        if self.source is not None:
            try:self.source.close()
            except Exception as error:self.closure['source_close_error'] = str(error)
        self.closed = True
        return self.closure


def raw_frames(root, *, allow_software_fixture=False):
    """Only source RGB, no saved-state or renderer path in this decoder."""
    import numpy as np
    root = Path(root)
    closure = json.loads((root/'closure.json').read_bytes())
    need(closure['schema'] == 'Data-direct-third-view-raw-closure-v1' and
         closure['state_replay_or_rerender_used'] is False and
         (closure['origin'] == ACTUAL or (allow_software_fixture and closure['origin'] == SOFTWARE)),
         'Only directly acquired raw RGB; old state replay/onboard is not third view')
    need(sha(root/'metadata.json') == closure['metadata_sha256'], 'Camera provenance changed')
    metadata = json.loads((root/'metadata.json').read_bytes())
    spec = camera_spec(metadata['camera_spec'])
    need(metadata['origin'] == closure['origin'] and
         spec_sha(spec) == closure['camera_spec_sha256'], 'Common camera provenance')
    count = 0
    for row in closure['chunks']:
        rel = Path(row['path']);p = root/rel
        need(not rel.is_absolute() and '..' not in rel.parts and not p.is_symlink() and
             p.resolve().is_relative_to(root.resolve()) and sha(p) == row['sha256'], 'Raw chunk pin/path')
        with np.load(p, allow_pickle=False) as z:
            need(set(z.files) == {'rgb', 'physics_tick', 'actual_sim_time_s'}, 'Exact raw video ABI')
            need(z['rgb'].dtype == np.uint8 and len(z['rgb']) == row['frames'] and
                 hashlib.sha256(z['rgb'].tobytes()).hexdigest() == row['raw_RGB_bytes_sha256'],
                 'Raw RGB pixels unchanged')
            n = row['frames']
            need(type(n) is int and n > 0 and
                 z['rgb'].shape == (n, spec['height'], spec['width'], 3) and
                 z['physics_tick'].dtype == np.int64 and z['physics_tick'].shape == (n,) and
                 z['actual_sim_time_s'].dtype == np.float64 and z['actual_sim_time_s'].shape == (n,),
                 'Exact frame/clock dimensions and numeric ABI')
            need(int(z['physics_tick'][0]) == row['first_physics_tick'] and
                 int(z['physics_tick'][-1]) == row['last_physics_tick'], 'Chunk clock bounds')
            for tick, stamp, rgb in zip(z['physics_tick'], z['actual_sim_time_s'], z['rgb']):
                need(int(tick) == count * spec['stride_physics_ticks'] and
                     math.isfinite(float(stamp)) and abs(float(stamp)-int(tick)*.005) < 1e-7,
                     'Exact original sample grid; no gap filling or nonfinite clocks')
                count += 1
                yield int(tick), float(stamp), rgb.copy()
    need(count == closure['archived_frames'], 'No silent loss/addition of source frames')


def comparison_presentation(left, right, *, speed=1, completion_times_s=(None, None)):
    """Presentation plan only. No interpolation/time warp/renderer/encoder."""
    need(type(speed) in (int, float) and math.isfinite(speed) and speed > 0, 'One common playback speed')
    for c in (left, right):
        need(c.get('origin') == ACTUAL and c.get('complete_for_capture_grid') is True and
             c.get('encoded_video_created') is False and c.get('state_replay_or_rerender_used') is False,
             'Both actual direct raw masters, not retrospective rendered clips')
    need(left['camera_spec_sha256'] == right['camera_spec_sha256'], 'Same frozen camera/sampling identity')
    need(len(completion_times_s) == 2 and all(t is None or
        (type(t) in (int, float) and math.isfinite(t) and t >= 0) for t in completion_times_s),
        'Original completion clocks or UNKNOWN, never derive success from movie length')
    return dict(schema='Data-raw-camera-comparison-presentation-plan-v1',
        speed_multiplier=speed, original_sim_completion_times_s=list(completion_times_s),
        same_camera_identity=True, resampling=False, interpolation=False,
        per_arm_time_warp=False, common_time_origin='actual experiment sim time',
        after_end_panel='BLACK_AND_LABELLED_END_NOT_A_NEW_EXPERIMENT_FRAME',
        source_frame_masters_required=True, new_renderer_or_physics_calls=0)
