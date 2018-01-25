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
import shutil
import hashlib
import soundfile
import scipy.io

def delete_dataset(dataset):
    """Deletes the whole dataset permanently from the hard drive."""
    if dataset._readonly:
        raise RuntimeError('DataSet is read-only')
    if not isinstance(dataset, DataSet):
        raise TypeError('dataset must be of type DataSet')
    shutil.rmtree(dataset._directory)
    dataset._directory = None

def create_dataset(directory, metadata=None, itemformat=None):
    """Create a new dataset.

    `metadata` must be JSON-serializable
    `itemformat` is a `str.format` string, to be called with an
        item's metadata to create the item's directory name.
        This is useful for creating human-readable directories.

    """
    if metadata is None:
        metadata = {}
    directory = Path(directory)
    if directory.exists():
        raise TypeError('A directory with name {str(directory)} already exists')
    directory.mkdir()
    with (directory / '_metadata.json').open('wt') as f:
        json.dump(dict(metadata, _itemformat=itemformat), f, indent=2)
    with (directory / '__init__.py').open('wt') as f:
        f.write('import jbof\n')
        f.write('dataset = jbof.DataSet(jbof.Path(__file__).parent)\n')
    return DataSet(directory, readonly=False)


class DataSet:
    """A structured collection of items that contain data."""

    def __init__(self, directory, readonly=True):
        directory = Path(directory)
        if not directory.exists():
            raise TypeError('DataSet directory {str(directory)} does not exist')
        self._directory = directory
        self._readonly = readonly

    @property
    def itemformat(self):
        with (self._directory / '_metadata.json').open() as f:
            return json.load(f)['_itemformat']

    @property
    def metadata(self):
        with (self._directory / '_metadata.json').open() as f:
            metadata = json.load(f)
            del metadata['_itemformat']
            return metadata

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
        for dir in self._directory.iterdir():
            if not dir.is_dir() or dir.stem == '__pycache__':
                continue
            yield Item(dir, self._readonly)

    def find_items(self, **query):
        """Search for items that match `query`.

        Query can be arbitrary keyword arguments that are matched in
        the metadata.
        - if the query is a string, e.g. `foo='bar'`, the metadata
          must contain `foo='bar'`.
        - if the query is a list of strings, e.g. `foo=['bar', 'baz']`,
          the metadata must contain either `foo='bar'` or `foo='baz'`.

        """
        for item in self.all_items():
            for key, value in query.items():
                if isinstance(value, str):
                    value = [value]
                if key not in item.metadata or item.metadata[key] not in value:
                    break
            else:
                yield item

    def find_one_item(self, **query):
        """Search for items that match `query`.

        See `find_items` for details.
        """
        for item in self.find_items(**query):
            return item

    def add_item(self, name=None, metadata=None):
        """Add a new, empty item."""
        if self._readonly:
            raise RuntimeError('DataSet is read-only')
        if name is None:
            dirname = self._itemname(metadata)
        else:
            dirname = str(name)

        if metadata is None:
            metadata = {}

        if self.has_item(dirname):
            raise TypeError(f'Item with name {str(dirname)} already exists')

        (self._directory / dirname).mkdir()
        with (self._directory / dirname / '_metadata.json').open('wt') as f:
            json.dump(metadata, f)
        return Item(self._directory / dirname, self._readonly)

    def has_item(self, name):
        """Check if item of name exists."""
        return (self._directory / name).exists()

    def __contains__(self, name):
        return self.has_item(name)

    def get_item(self, name):
        """Get an item by name."""
        if not self.has_item(name):
            raise TypeError('no item {name}')
        return Item(self._directory / name, self._readonly)

    def delete_item(self, item):
        """Deletes item permanently from the hard drive."""
        if self._readonly:
            raise RuntimeError('DataSet is read-only')
        if isinstance(item, str):
            item = self.get_item(item)
        if not isinstance(item, Item):
            raise TypeError('item must be of type Item or str')
        shutil.rmtree(item._directory)
        item._directory = None

    def calculate_hash(self):
        """Calculates an md5 hash of all data."""
        itemhashes = []
        for item in self.all_items():
            filehashes = []
            for file in item._directory.iterdir():
                with file.open('br') as f:
                    filehashes.append(hashlib.md5(f.read()).digest())
            filehashes = sorted(filehashes)
            itemhashes.append(hashlib.md5(b''.join(filehashes)).digest())
        itemhashes = sorted(itemhashes)
        return hashlib.md5(b''.join(itemhashes)).hexdigest()


class Item:
    def __init__(self, directory, readonly):
        self._directory = directory
        self._readonly = readonly

    @property
    def metadata(self):
        with (self._directory / '_metadata.json').open() as f:
            return json.load(f)

    def __getattr__(self, name):
        return Array(self._directory / (name + '.json'))

    def __eq__(self, other):
        return self._directory.samefile(other._directory)

    def __hash__(self):
        return hash(self._directory / '_metadata.json')

    def all_arrays(self):
        """A generator that returns all arrays as name-value pairs."""
        for meta in self._directory.glob('*.json'):
            if meta.stem == '_metadata':
                continue
            yield meta.stem, Array(meta)

    def add_array_from_file(self, name, filename, metadata=None):
        """Add a new array from an existing file.

        `name` is the name of the array.
        `filename` is the file to be added (must be one of `npy`,
            `msgpack`, `csv`, `wav`, `flac`, `ogg`, `mat`)
        `metadata` must be JSON-serializable.

        """
        if self._readonly:
            raise RuntimeError('DataSet is read-only')
        if metadata is None:
            metadata = {}
        filename = Path(filename)
        if not filename.exists():
            raise TypeError(f'File {filename} does not exist')
        if filename.suffix in ['.wav', '.flac', '.ogg']:
            with soundfile.SoundFile(str(filename)) as f:
                metadata = dict(metadata, samplerate=f.samplerate)

        arrayfilename = self._directory / (name + filename.suffix)
        if arrayfilename.exists():
            raise TypeError(f'Array with name {arrayfilename.name} already exists')

        shutil.copy(filename, arrayfilename)

        metafilename = self._directory / (name + '.json')
        with metafilename.open('wt') as f:
            json.dump(dict(metadata, _filename=str(arrayfilename)), f, indent=2, sort_keys=True)

        return Array(metafilename)

    def add_array(self, name, data, metadata=None, fileformat='npy', samplerate=None):
        """Add a new array.

        `name` is the name of the array.
        `data` must be numpy-serializable.
        `metadata` must be JSON-serializable.
        `fileformat` must be one of ['npy', 'msgpack', 'csv', 'wav', 'flac', 'ogg', 'mat']
            if fileformat is 'wav', 'flac', or 'ogg', `samplerate` must be given.

        Currently, only `fileformat`= ['msgpack', 'csv'] are not implemented.
        """
        if self._readonly:
            raise RuntimeError('DataSet is read-only')
        if metadata is None:
            metadata = {}
        arrayfilename = self._directory / (name + '.' + fileformat)
        if arrayfilename.exists():
            raise TypeError(f'Array with name {arrayfilename.name} already exists')
        if fileformat == 'npy':
            numpy.save(arrayfilename, data)
        elif fileformat in ['wav', 'flac', 'ogg']:
            if samplerate:
                soundfile.write(str(arrayfilename), data, int(samplerate))
                metadata = dict(metadata, samplerate=samplerate)
            else:
                raise TypeError(f'Samplerate must be given for fileformat {fileformat}.')
        elif fileformat == 'mat':
            scipy.io.savemat(str(arrayfilename), dict([(name, data)]))
        else:
            raise NotImplementedError(f'Fileformat {fileformat} not supported.')

        metafilename = (self._directory / (name + '.json'))
        with metafilename.open('wt') as f:
            json.dump(dict(metadata, _filename=str(arrayfilename)), f, indent=2, sort_keys=True)

        return Array(metafilename)

    def delete_array(self, array):
        """Deletes array permanently from the hard drive."""
        if self._readonly:
            raise RuntimeError('DataSet is read-only')
        if not isinstance(array, Array):
            raise TypeError('array must be of type Array')
        arrayfilename = Path(array._filename)
        metafilename = arrayfilename.with_suffix('.json')
        arrayfilename.unlink()
        metafilename.unlink()

    def has_array(self, name):
        return (self._directory / (name + '.json')).exists()

    def __contains__(self, name):
        return self.has_array(name)


class Array(numpy.ndarray):
    """A subclass of numpy.ndarray with a `_filename` and `metadata`."""
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
        obj._filename = metadata['_filename']
        del metadata['_filename']
        obj.metadata = metadata
        return obj

    def __array_finalize__(self, obj):
        if obj is None: return
        self.metadata = getattr(obj, 'metadata', None)
        self._filename = getattr(obj, '_filename', None)
