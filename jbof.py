# JBOF - A Dataset from Just a Bunch of Files
# Copyright (C) 2018 Bastian Bechtold

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import numpy
import uuid
import json
from pathlib import Path
import soundfile
import scipy.io

class DataSet:
    """A structured collection of items that contain data."""

    @staticmethod
    def create_dataset(directory, metadata=None, itemformat=None):
        """Create a new dataset.

        `metadata` must be JSON-serializable
        `itemformat` is a `str.format` string, to be called with an
            item's metadata to create the item's directory name.
            This is useful for creating human-readable directories.

        """
        directory = Path(directory)
        directory.mkdir()
        with (directory / '_metadata.json').open('wt') as f:
            json.dump(dict(metadata, _itemformat=itemformat), f, indent=2)
        with (directory / '__init__.py').open('wt') as f:
            f.write('import jbof\n')
            f.write('dataset = jbof.DataSet(jbof.Path(__file__).parent)\n')
        return DataSet(directory)

    def __init__(self, directory):
        directory = Path(directory)
        if not directory.exists():
            raise TypeError('DataSet directory {str(directory)} does not exist')
        self._directory = directory

    @property
    def itemformat(self):
        return self.metadata['_itemformat']

    @property
    def metadata(self):
        with (self._directory / '_metadata.json').open() as f:
            return json.load(f)

    def __getitem__(self, key):
        return self.metadata[key]

    def _itemname(self, metadata):
        itemformat = self.itemformat
        if isinstance(itemformat, str) and '{' in itemformat:
            return itemformat.format(**metadata)
        elif itemformat is None:
            return str(uuid.uuid1())
        else:
            return TypeError(f'itemname must be None, or format string, not {itemformat}')

    def all_items(self):
        """A generator that returns all items."""
        for dir in self._directory.glob('*'):
            if not dir.is_dir() or dir.stem == '__pycache__':
                continue
            yield Item(dir)

    def create_item(self, metadata):
        """Create a new, empty item with metadata."""
        dirname = self._itemname(metadata)
        (self._directory / dirname).mkdir()
        with (self._directory / dirname / '_metadata.json').open('wt') as f:
            json.dump(metadata, f)
        return Item(self._directory / dirname)


class Item:
    def __init__(self, directory):
        self._directory = directory

    @property
    def metadata(self):
        with (self._directory / '_metadata.json').open() as f:
            return json.load(f)

    def __getitem__(self, key):
        return self.metadata[key]

    def __getattr__(self, name):
        return Array(self._directory / (name + '.json'))

    def create_array(self, name, data, metadata, fileformat='npy', samplerate=None):
        """Create a new array.

        `name` is the name of the array.
        `data` must be numpy-serializable.
        `metadata` must be JSON-serializable.
        `fileformat` must be one of ['npy', 'msgpack', 'csv', 'wav', 'flac', 'ogg', 'mat']
            if fileformat is 'wav', 'flac', or 'ogg', `samplerate` must be given.

        Currently, only `fileformat`= ['msgpack', 'csv'] are not implemented.
        """
        arrayfilename = self._directory / (name + '.' + fileformat)
        if fileformat == 'npy':
            numpy.save(arrayfilename, data)
        elif fileformat in ['wav', 'flac', 'ogg']:
            if samplerate:
                soundfile.write(str(arrayfilename), data, int(samplerate))
                metadata['samplerate'] = int(samplerate)
            else:
                raise TypeError(f'Samplerate must be given for fileformat {fileformat}.')
        elif fileformat == 'mat':
            scipy.io.savemat(str(arrayfilename), dict([(name, data)]))
        else:
            raise NotImplementedError(f'Fileformat {fileformat} not supported.')

        with (self._directory / (name + '.json')).open('wt') as f:
            json.dump(dict(metadata, _filename=str(arrayfilename)), f, indent=2)

    def all_arrays(self):
        """A generator that returns all arrays as name-value pairs."""
        for meta in self._directory.glob('*.json'):
            if meta.stem == '_metadata':
                continue
            yield meta.stem, Array(meta)


class Array(numpy.ndarray):
    def __new__(cls, metafile):
        with metafile.open() as f:
            metadata = json.load(f)
        extension = Path(metadata['_filename']).suffix
        if extension == '.npy':
            data = numpy.load(metadata['_filename'])
        elif extension in ['.wav', '.flac', '.ogg']:
            data, _ = soundfile.read(metadata['_filename'])
        elif extension == '.mat':
            name = Path(metadata['_filename']).stem
            data = scipy.io.loadmat(metadata['_filename'])
            data = data[name]
        obj = numpy.asarray(data).view(cls)
        obj.metadata = metadata
        return obj

    def __array_finalize__(self, obj):
        if obj is None: return
        self.metadata = getattr(obj, 'metadata', None)
