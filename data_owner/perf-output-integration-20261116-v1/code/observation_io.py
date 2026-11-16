"""Two explicit private IO-only edits to original AcquisitionPublisher.

No original files/modules/PIL/numpy globals are modified. This is NOT identical
bytecode: PNG/NPY go to controlled file objects; original public validation,
Observation.create and serialization stay original. Install BEFORE identity seal.
"""
import hashlib
import sys
import types
from pathlib import Path
from scoped_io import scoped_path_class

PNG_SITE = '        Image.fromarray(rgb[0, 0]).save(image)'
NPY_SITE = "        np.save(frame_dir/'depth_m.npy', depth[0, 0], allow_pickle=False)"


def load_controlled_publisher(source_path, expected_sha256, budget, *, name,
                              package='ainav.native', enabled=False):
    if type(enabled) is not bool:
        raise ValueError('Explicit opt-in')
    if not enabled:
        return None
    path = Path(source_path)
    raw = path.read_bytes()
    if path.is_symlink() or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Pinned original publisher required')
    text = raw.decode('utf-8')
    if text.count(PNG_SITE) != 1 or text.count(NPY_SITE) != 1 or name in sys.modules:
        raise ValueError('Exact two reviewed IO sites; no reload')
    text = text.replace(PNG_SITE, '        _data_png(Image.fromarray(rgb[0, 0]), image)')
    text = text.replace(NPY_SITE, "        _data_npy(np, frame_dir/'depth_m.npy', depth[0, 0])")
    def png(image, destination):
        with budget.open(destination, 'xb') as stream:
            image.save(stream, format='PNG')
    def npy(np, destination, array):
        with budget.open(destination, 'xb') as stream:
            np.save(stream, array, allow_pickle=False)
    module = types.ModuleType(name)
    module.__file__, module.__package__ = str(path), package
    sys.modules[name] = module
    try:
        exec(compile(text, str(path), 'exec'), module.__dict__)
        module.Path = scoped_path_class(budget)
        module._data_png, module._data_npy = png, npy
        module.DATA_IO_ONLY_REWRITES = ('PNG explicit file object', 'NPY explicit file object')
        return module
    except BaseException:
        del sys.modules[name]
        raise


def bind_fresh_observation_outputs(driver, module, budget, *, enabled=False):
    """New task0 driver only. Qualify with fresh adapter BEFORE native use.

    Binding is not native signoff, nor evidence of a live camera acquisition.
    """
    if enabled is not True:
        return None
    publisher = driver.publisher
    if (driver.r.step_count != 0 or driver.r.sim.queue or driver.sequence != 0
            or publisher.count != 0 or driver.executor is not None):
        raise ValueError('Only unstarted fresh driver before identity seal')
    root = budget._path(driver.root)
    pubroot = budget._path(publisher.root)
    if pubroot != root / 'query-observations':
        raise ValueError('Exact same scope/root required')
    driver.root = scoped_path_class(budget)(root)
    publisher.root = scoped_path_class(budget)(pubroot)
    publisher.publish = types.MethodType(module.AcquisitionPublisher.publish, publisher)
    return dict(IO_only_rewrites=list(module.DATA_IO_ONLY_REWRITES),
                native_qualified=False, original_modules_unchanged=True)
