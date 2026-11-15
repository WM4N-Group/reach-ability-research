"""CPU-only 4x1 and individual evidence encoding of CLOSED live raw archives.
No native/Actor/Renderer/WM/API calls; NEVER qualifies methods or task success.
Input clocks, missing views and physical outcomes are not repaired or relabelled.
"""
from pathlib import Path
import argparse, datetime, hashlib, itertools, json, math, os, subprocess, time
from fractions import Fraction
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ARMS = ('A', 'B', 'C', 'D')
LABELS = dict(A='VLM + WM', B='VLM + WM + shared optimizer',
              C='AINav (native baseline)', D='AINav + shared optimizer')
FIXTURE = 'SOFTWARE_FIXTURE_NO_PHYSICS'

def require(ok, message):
    if not ok:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_bytes())

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()

class Original:
    """Only original closed main/result/accounting and direct raw metadata."""
    def __init__(self, arm, root, *, fixture=False, physics_step_s=.005):
        self.arm, self.root = arm, Path(root).resolve(strict=True)
        self.fixture = fixture
        self.main = self.root/'main'; self.raw = self.main/'raw-third-view'
        self.result = read(self.main/'result.json')
        self.ledger = read(self.root/'accounting/ledger.json')
        require(self.ledger['provenance'] == (FIXTURE if fixture else 'ACTUAL'), 'Original/fixture ledger provenance separated')
        self.meta = read(self.raw/'metadata.json'); self.close = read(self.raw/'closure.json')
        require(self.result['phase'] == 'main', 'Only terminal main, not own-zero')
        require(self.result.get('provenance') == FIXTURE if fixture else self.result.get('provenance') != FIXTURE,
                'Software fixtures must remain explicitly isolated from actual evidence')
        if not fixture:
            require(not Path('/proc/'+str(self.result['PID'])).exists(), 'Source main still has a live PID')
        rows = self.ledger['rows']; require(rows and all(r['closed'] for r in rows), 'Original ledger not closed')
        require(rows[-1]['phase'] == 'main' and rows[-1]['report_sha256'] == sha(self.main/'result.json'), 'Original terminal report binding')
        self.scope = self.result['scope_id']; self.program = self.result['program_sha256']
        require(self.scope == self.ledger['scope_id'] == self.meta['scope_id'] == self.close['scope_id'], 'Original scope binding')
        require(self.program == self.ledger['program_sha256'] == self.meta['program_sha256'] == self.close['program_sha256'], 'Original program binding')
        require(self.meta['origin'] == self.close['origin'] == 'DIRECT_CURRENT_LIVE_MUJOCO_RGB', 'Not direct live raw')
        require(self.close['metadata_sha256'] == sha(self.raw/'metadata.json'), 'Original metadata pin')
        self.camera = self.meta['camera_spec']
        require(hashlib.sha256(canonical(self.camera)).hexdigest() == self.meta['camera_spec_sha256'] == self.close['camera_spec_sha256'], 'Camera pin')
        self.width, self.height = self.camera['width'], self.camera['height']
        require(self.width >= 960 and self.height >= 540 and self.width % 2 == self.height % 2 == 0, 'Real HD required; never upscale/crop')
        stride = self.camera['stride_physics_ticks']; require(type(stride) is int and stride > 0, 'Original capture stride')
        require(math.isfinite(physics_step_s) and physics_step_s > 0, 'Finite original clock')
        self.step = physics_step_s; self.stride = stride
        self.fps = Fraction(1, 1)/(Fraction(str(physics_step_s))*stride)
        self.end_s = self.result['actual_main_world_sim_s']; self.tick = self.close['final_physics_tick']
        require(type(self.tick) is int and self.tick >= 0 and math.isfinite(self.end_s), 'Known terminal clock required')
        require(abs(self.end_s-self.tick*physics_step_s) < 1e-7 and abs(self.end_s-self.close['actual_run_end_time_s']) < 1e-7, 'Native terminal clock, not container duration')
        self.count = self.tick//stride+1
        require(self.close['complete_for_capture_grid'] and self.close['archived_frames'] == self.close['captured_frames'] == self.count,
                'Incomplete raw delivery; never rerun physical arm to fill video')
        require(not self.close['state_replay_or_rerender_used'] and not self.close['sampling_or_interpolation_of_missing_frames'], 'No derived world frames')
        self.pins = {str(p): sha(p) for p in [self.main/'result.json', self.root/'accounting/ledger.json', self.raw/'metadata.json', self.raw/'closure.json']}
        for row in self.close['chunks']:
            p = self.raw/row['path']
            require(not p.is_symlink() and p.resolve().is_relative_to(self.raw.resolve()), 'Raw chunk escapes original archive')
            require(sha(p) == row['sha256'], 'Raw chunk SHA mismatch'); self.pins[str(p)] = row['sha256']

    def frames(self):
        count = 0
        for row in self.close['chunks']:
            path = self.raw/row['path']; require(sha(path) == row['sha256'], 'Raw chunk drift')
            with np.load(path, allow_pickle=False) as data:
                rgb, ticks, times = data['rgb'], data['physics_tick'], data['actual_sim_time_s']
                require(rgb.dtype == np.uint8 and rgb.shape[1:] == (self.height, self.width, 3), 'Original unscaled RGB shape/dtype')
                require(len(rgb) == row['frames'] and 0 < len(rgb) <= self.camera['chunk_frames'], 'Chunk frame denominator')
                require(ticks.ndim == times.ndim == 1 and len(times) == len(rgb) and np.issubdtype(ticks.dtype, np.integer) and np.isfinite(times).all(), 'Original finite integer tick/time vectors')
                require(np.array_equal(ticks, np.arange(count, count+len(rgb))*self.stride), 'Missing/duplicate/off-grid raw frame')
                require(np.allclose(times, ticks*self.step, atol=1e-7, rtol=0), 'Original acquisition clock mismatch')
                require(hashlib.sha256(rgb.tobytes()).hexdigest() == row['raw_RGB_bytes_sha256'], 'Original RGB byte pin')
                require(row['first_physics_tick'] == int(ticks[0]) and row['last_physics_tick'] == int(ticks[-1]), 'Chunk endpoint clocks')
                for frame in rgb:
                    count += 1; yield frame
        require(count == self.count, 'Incomplete original iterator')

    def unchanged(self):
        return all(sha(p) == digest for p, digest in self.pins.items())

    def evidence(self):
        task = self.result.get('task_success', self.result.get('whole_task_success_claimed'))
        require(task is None or type(task) is bool, 'Do not coerce unknown task outcome')
        return dict(scope_id=self.scope, program_sha256=self.program, root=str(self.root), original_phase_passed=self.result['passed'],
                    original_task_success=task, actual_end_time_s=self.end_s, original_raw_frames=self.count,
                    source_pins=self.pins, original_error_not_copied_to_caption_or_logs=True)

def same_capture(sources):
    require(tuple(sources) == ARMS, 'Exactly four named arms required')
    require(len({s.root for s in sources.values()}) == len({s.scope for s in sources.values()}) == 4, 'Four distinct original roots/scopes; not relabelled duplicate')
    first = sources['A']
    require(all(s.camera == first.camera and s.fps == first.fps and s.step == first.step for s in sources.values()), 'One original camera/grid for all arms')
    return first

@lru_cache(maxsize=1)
def caption_font():
    path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    return ImageFont.truetype(str(path), 17) if path.exists() else ImageFont.load_default()

def panel(source, frame, k, *, fixture=False):
    # A header is added; acquired world pixels are never annotated, cropped or resized.
    image = Image.new('RGB', (source.width, source.height+96), 'black'); draw = ImageDraw.Draw(image)
    font = caption_font()
    draw.text((8, 4), f'{source.arm}: {LABELS[source.arm]} | original sim clock {float(Fraction(k,1)/source.fps):.3f}s', font=font, fill='white')
    label = 'SOFTWARE FIXTURE / NO SCIENTIFIC RESULT' if fixture else 'DIRECT LIVE RAW / 1x / LABELS DO NOT CERTIFY METHOD IDENTITY'
    draw.text((8, 28), label, font=font, fill=(255, 220, 80))
    task = source.evidence()['original_task_success']; task_label = 'UNKNOWN' if task is None else str(task)
    draw.text((8, 52), f'Original phase PASS={source.result["passed"]}; full task={task_label}; terminal={source.end_s:.3f}s', font=font, fill='white')
    if frame is None:
        require(k >= source.count, 'Missing acquired frame cannot become an end slate')
        draw.text((8, 76), 'ENDED / NO FURTHER OBSERVATION - original end time above', font=font, fill='white')
    else:
        require(k < source.count, 'Cannot extend world after original recording')
        image.paste(Image.fromarray(frame), (0, 96))
    return image

def encode(sources, output, *, fixture=False, cpus=(36,37), wall_cap_s=1800, output_cap_bytes=1024**3):
    first = same_capture(sources)
    require(all(s.fixture == fixture for s in sources.values()), 'Cannot relabel fixture or actual source mode')
    require(set(cpus).issubset(os.sched_getaffinity(0)) and len(cpus) == 2, 'Two explicitly available CPU cores')
    require(math.isfinite(wall_cap_s) and wall_cap_s > 0 and type(output_cap_bytes) is int and output_cap_bytes > 0, 'Finite postprocessing caps')
    output = Path(output).absolute()
    require(not any(output.resolve().is_relative_to(s.root) for s in sources.values()), 'Derived output must be outside immutable original roots')
    output.mkdir(); os.sched_setaffinity(0, set(cpus))
    start = time.monotonic(); artifacts = {}
    for kind in (*ARMS, 'four-panel'):
        width = first.width*(4 if kind == 'four-panel' else 1); height = first.height+96
        path = output/(kind+'-direct-original-1x.mp4')
        command = ['/usr/bin/ffmpeg','-nostdin','-hide_banner','-loglevel','error','-n','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{width}x{height}','-framerate',str(first.fps),'-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
        with (output/(kind+'-ffmpeg.stderr')).open('xb') as err:
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=err)
            try:
                frames = itertools.zip_longest(*(s.frames() for s in sources.values())) if kind == 'four-panel' else ((frame,) for frame in sources[kind].frames())
                count = 0
                for k, row in enumerate(frames):
                    require(time.monotonic()-start < wall_cap_s, 'Postprocess wall cap, not physical task failure')
                    require(sum(p.stat().st_size for p in output.glob('*.mp4')) < output_cap_bytes, 'Postprocess output cap, never resample')
                    if kind == 'four-panel':
                        image = Image.new('RGB', (width,height), 'black')
                        for j,(arm,frame) in enumerate(zip(ARMS,row)):image.paste(panel(sources[arm],frame,k,fixture=fixture),(j*first.width,0))
                    else:image = panel(sources[kind], row[0], k, fixture=fixture)
                    proc.stdin.write(image.tobytes()); count += 1
                proc.stdin.close(); require(proc.wait(timeout=120) == 0, 'ffmpeg failed; partial outputs preserved')
            finally:
                if proc.poll() is None:proc.kill(); proc.wait()
                if proc.stdin and not proc.stdin.closed:proc.stdin.close()
        expected = max(s.count for s in sources.values()) if kind == 'four-panel' else sources[kind].count
        require(count == expected, 'Output frame denominator')
        probe = json.loads(subprocess.check_output(['/usr/bin/ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_read_frames','-of','json',str(path)], text=True, timeout=60))
        stream = probe['streams'][0]
        require(int(stream['nb_read_frames']) == expected and Fraction(stream['r_frame_rate']) == first.fps and (stream['width'],stream['height']) == (width,height), 'Encoded stream clock/shape mismatch')
        artifacts[kind] = dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size, frames=count, probe=probe)
    require(sum(p.stat().st_size for p in output.glob('*.mp4')) <= output_cap_bytes, 'Final postprocess output cap')
    require(all(s.unchanged() for s in sources.values()), 'Source changed during export')
    result = dict(schema='Data-four-arm-direct-original-evidence-encoding-v1', at=datetime.datetime.now().astimezone().isoformat(),
                  role=FIXTURE if fixture else 'POSTPROCESS_ONLY_NOT_METHOD_OR_TASK_QUALIFICATION',
                  method_labels_from_comparison_definition_not_encoder_certification=True,
                  actual_methods_must_be_verified_from_original_planner_WM_API_native_records=True,
                  source={a:s.evidence() for a,s in sources.items()}, artifacts=artifacts,
                  header_added_px=96, original_world_RGB_unmodified_before_lossy_H264=True,
                  four_horizontal_columns_same_original_sim_clock=True, no_world_frame_interpolation_duplication_crop_or_resize=True,
                  post_end_black_slate_not_frozen_world=True, native_end_time_not_container_duration=True,
                  source_SHA_before_after_identical=True, no_native_Actor_Renderer_WM_API_or_physics_calls=True,
                  native_outcomes_not_rewritten=True, missing_video_never_authorizes_physical_retry=True,
                  postprocess_wall_s=time.monotonic()-start)
    with (output/'manifest.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', action='append', required=True, help='Exactly A=/absolute/closed/root ... D=...')
    parser.add_argument('--out', type=Path, required=True); parser.add_argument('--cpus', default='36,37')
    parser.add_argument('--physics-step-s', type=float, default=.005)
    parser.add_argument('--fixture-mode', action='store_true', help='Only explicitly software-labelled fixture roots')
    args = parser.parse_args(); pairs = [v.split('=',1) for v in args.arm]
    require(len(pairs) == 4 and len({a for a,p in pairs}) == 4 and {a for a,p in pairs} == set(ARMS), 'Exactly A/B/C/D')
    paths = dict(pairs); require(all(Path(p).is_absolute() for p in paths.values()), 'Absolute original roots')
    sources = {a:Original(a, paths[a], fixture=args.fixture_mode, physics_step_s=args.physics_step_s) for a in ARMS}
    result = encode(sources, args.out, fixture=args.fixture_mode, cpus=tuple(map(int,args.cpus.split(','))))
    print(json.dumps(dict(manifest_path=str(args.out/'manifest.json'),role=result['role'],artifacts=result['artifacts']),indent=2))
if __name__ == '__main__':main()
