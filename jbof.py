import numpy
import uuid
import json
from pathlib import Path

class DataSet:
    def __init__(self, directory, metadata=None, entryformat=None):
        self.directory = Path(directory)

        if not (self.directory / '_metadata.json').exists():
            if not self.directory.exists():
                self.directory.mkdir()
            with open(self.directory / '_metadata.json', 'wt') as f:
                json.dump(dict(metadata, _entryformat=entryformat), f, indent=2)

    @property
    def metadata(self):
        with open(self.directory / '_metadata.json') as f:
            return json.load(f)

    @property
    def _entryformat(self):
        return self.metadata['_entryformat']

    def __getitem__(self, key):
        return self.metadata[key]

    def entryname(self, metadata):
        if isinstance(self._entryformat, str) and '{' in self._entryformat:
            return self._entryformat.format(metadata)
        elif self._entryformat is None:
            return str(uuid.uuid1())
        else:
            return TypeError(f'entryname must be None, or format string, not {self._entryformat}')

    def entries(self):
        for dir in (d for d in self.directory.glob('*') if d.is_dir()):
            yield Entry(dir)

    def create_entry(self, metadata):
        dirname = self.entryname(metadata)
        (self.directory / dirname).mkdir()
        with open(self.directory / dirname / '_metadata.json', 'w') as f:
            json.dump(metadata, f)
        return Entry(self.directory / dirname)


class Entry:
    def __init__(self, directory):
        self.directory = directory

    @property
    def metadata(self):
        with open(self.directory / '_metadata.json') as f:
            return json.load(f)

    def __getitem__(self, key):
        return self.metadata[key]

    def __getattr__(self, name):
        return Data(self.directory / name + '.json')

    def create_data(self, name, data, metadata, fileformat='npy'):
        if not fileformat == 'npy':
            raise NotImplementedError('Only npy is supported')

        datafilename = self.directory / (name + '.npy')
        with open(self.directory / (name + '.json'), 'w') as f:
            json.dump(dict(metadata, _filename=str(datafilename)), f, indent=2)
        numpy.save(datafilename, data)

    def all_data(self):
        out = {}
        for meta in self.directory.glob('*.json'):
            if meta.stem == '_metadata':
                continue
            out[meta.stem] = Data(meta)
        return out


class Data(numpy.ndarray):
    def __new__(cls, metafile):
        with metafile.open() as f:
            metadata = json.load(f)
        data = numpy.load(metadata['_filename'])
        obj = numpy.asarray(data).view(cls)
        obj.metadata = metadata
        return obj

    def __array_finalize__(self, obj):
        if obj is None: return
        self.metadata = getattr(obj, 'metadata', None)
