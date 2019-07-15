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
import zipfile
import io


def _unwrap_numpy_types(data):
    """Helper for encoding h5py attrs to JSON (may contain numpy.int64)."""
    if issubclass(numpy.dtype(data).type, numpy.integer) and numpy.isscalar(data):
        return int(data)
    elif issubclass(numpy.dtype(data).type, numpy.floating) and numpy.isscalar(data):
        return float(data)
    else:
        raise TypeError(f"can't encode {data} ({type(data)}) as JSON")


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

    - `metadata` must be JSON-serializable
    - `itemformat` is a ``str.format`` string, to be called with an
      item's metadata to create the item's directory name.
      This is useful for creating human-readable directories.

    """
    if metadata is None:
        metadata = {}
    directory = Path(directory)
    if directory.exists():
        raise TypeError(f'A directory with name {str(directory)} already exists')
    directory.mkdir()
    with (directory / '_metadata.json').open('wt') as f:
        json.dump(dict(metadata, _itemformat=itemformat), f, indent=2, sort_keys=True, default=_unwrap_numpy_types)
    with (directory / '__init__.py').open('wt') as f:
        f.write('import jbof\n')
        f.write('dataset = jbof.DataSet(jbof.Path(__file__).parent)\n')
    return DataSet(directory, readonly=False)


class DataSet:
    """A structured collection of items that contain data."""

    def __init__(self, directory, readonly=True):
        directory = Path(directory)
        if not directory.exists():
            raise TypeError(f'DataSet directory {str(directory)} does not exist')
        if not directory.is_dir() and (directory / '_metadata.json').exists():
            raise TypeError(f'{str(directory)} does not seem to be a DataSet')
        self._directory = directory
        self._readonly = readonly
        self._cache = []

    @property
    def itemformat(self):
        """The ``str.format`` format string for generating item names from metadata."""
        with (self._directory / '_metadata.json').open() as f:
            return json.load(f)['_itemformat']

    @property
    def metadata(self):
        """The Dataset's metadata dict."""
        with (self._directory / '_metadata.json').open() as f:
            metadata = json.load(f)
            del metadata['_itemformat']
            return metadata

    @property
    def name(self):
        """The dataset's directory name."""
        return self._directory.name

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

        if self._cache:
            yield from self._cache
        else:
            cache = []
            for dir in self._directory.iterdir():
                if not dir.is_dir() or dir.stem == '__pycache__':
                    continue
                item = Item(dir, self._readonly)
                cache.append(item)
                yield item
            else: # if all items were traversed:
                self._cache = cache

    def find_items(self, **query):
        """Search for items that match `query`.

        Query can be arbitrary keyword arguments that are matched in
        the metadata.

        - if the query is a string, e.g. `foo='bar'`, the metadata
          must contain `foo='bar'`.
        - if the query is a list of strings, e.g. `foo=['bar', 'baz']`,
          the metadata must contain either `foo='bar'` or `foo='baz'`.

        Returns a generator that walks all matching items.

        If there are many items, the first run might be slow, but
        subsequent `find_items` will search through cached metadata,
        and will run faster.

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
            json.dump(metadata, f, indent=2, sort_keys=True, default=_unwrap_numpy_types)

        item = Item(self._directory / dirname, self._readonly)
        if self._cache:
            self._cache.append(item)
        return item

    def has_item(self, name):
        """Check if item of name exists.

        Or use ``name in dataset`` instead.
        """
        return (self._directory / name).exists()

    def __contains__(self, name):
        return self.has_item(name)

    def get_item(self, name):
        """Get an item by name."""
        if not self.has_item(name):
            raise TypeError(f'no item {name}')
        return Item(self._directory / name, self._readonly)

    def __getitem__(self, name):
        return self.get_item(name)

    def delete_item(self, item):
        """Deletes item permanently from the hard drive.

        This invalidates the ``find_items`` cache.
        """
        if self._readonly:
            raise RuntimeError('DataSet is read-only')
        if isinstance(item, str):
            item = self.get_item(item)
        if not isinstance(item, Item):
            raise TypeError('item must be of type Item or str')
        self._cache = [] # invalidate cache
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
    """A collection of arrays in a dataset."""

    def __init__(self, directory, readonly):
        self._directory = directory
        self._readonly = readonly
        self._metadata_cache = None
        self._array_cache = {}

    @property
    def metadata(self):
        """The item's metadata dict."""
        # use hasattr for compatibility with older, pickled Items:
        if not hasattr(self, '_metadata_cache') or not self._metadata_cache:
            with (self._directory / '_metadata.json').open() as f:
                self._metadata_cache = json.load(f)
        return self._metadata_cache

    @property
    def name(self):
        """The item's directory name."""
        return self._directory.name

    def __getattr__(self, name):
        if name in ['__getstate__', '_directory', '_readonly', '_metadata_cache', '_array_cache']:
            raise AttributeError()
        if not self.has_array(name):
            raise TypeError(f'no array {name}')
        if name not in self._array_cache:
            self._array_cache[name] = Array(self._directory / (name + '.json'))
        return self._array_cache[name]

    def __getstate__(self):
        state = self.__dict__
        state['_metadata_cache'] = None
        state['_array_cache'] = {}
        return state

    def __eq__(self, other):
        return self._directory.samefile(other._directory)

    def __hash__(self):
        return hash(self._directory / '_metadata.json')

    def all_arrays(self):
        """A generator that returns all arrays as name-value pairs."""
        for meta in self._directory.glob('*.json'):
            if meta.stem == '_metadata':
                continue
            yield meta.stem, getattribute(self, meta.stem)

    def add_array_from_file(self, name, filename, metadata=None):
        """Add a new array from an existing file.

        - `name` is the name of the array.
        - `filename` is the file to be added (must be one of ``.npy``,
          ``.wav``, ``.flac``, ``.ogg``, ``.mat``)
        - `metadata` must be JSON-serializable.

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
            json.dump(dict(metadata, _filename=arrayfilename.name), f, indent=2, sort_keys=True, default=_unwrap_numpy_types)

        return Array(metafilename)

    def add_array(self, name, data, metadata=None, fileformat='npy', samplerate=None):
        """Add a new array.

        - `name` is the name of the array.
        - `data` must be numpy-serializable.
        - `metadata` must be JSON-serializable.
        - `fileformat` must be one of [``'npy'``, ``'wav'``, ``'flac'``, ``'ogg'``, ``'mat'``]
          if fileformat is ``'wav'``, ``'flac'``, or ``'ogg'``, ``samplerate`` must be given.

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
            json.dump(dict(metadata, _filename=arrayfilename.name), f, indent=2, sort_keys=True, default=_unwrap_numpy_types)

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
        if metafilename in self._array_cache:
            del self._array_cache[arrayfilename.stem]

    def has_array(self, name):
        """Check if array of name exists.

        Or use ``name in item`` instead.
        """
        return (self._directory / (name + '.json')).is_file()

    def __contains__(self, name):
        return self.has_array(name)


class Array(numpy.ndarray):
    """A subclass of numpy.ndarray with a `_filename` and `metadata`."""
    def __new__(cls, metafile):
        with metafile.open() as f:
            metadata = json.load(f)
        extension = Path(metadata['_filename']).suffix.lower()
        # Use Path(...).name for compatibility with earlier version
        # that stored more than just the name:
        filename = metafile.parent / Path(metadata['_filename']).name
        if extension == '.npy':
            data = numpy.load(filename)
        elif extension in ['.wav', '.flac', '.ogg']:
            data, samplerate = soundfile.read(str(filename))
            metadata['samplerate'] = samplerate
        elif extension == '.mat':
            data = scipy.io.loadmat(filename)
            data = data[filename.stem]
        obj = numpy.asarray(data).view(cls)
        obj._filename = metadata['_filename']
        del metadata['_filename']
        obj.metadata = metadata
        return obj

    def __array_finalize__(self, obj):
        if obj is None: return
        self.metadata = getattr(obj, 'metadata', None)
        self._filename = getattr(obj, '_filename', None)


def dataset_to_hdf(dataset, hdffilename):
    """Convert the dataset to HDF5."""
    import h5py

    file = h5py.File(hdffilename, 'w')
    for k, v in dataset.metadata.items():
        file.attrs[k] = v
    for item in dataset.all_items():
        grp = file.create_group(item.name)
        for k, v in item.metadata.items():
            grp.attrs[k] = v
        for name, array in item.all_arrays():
            dset = grp.create_dataset(name, data=array)
            for k, v in array.metadata.items():
                dset.attrs[k] = v
            dset.attrs['_filename'] = array._filename
    file.close()


def hdf_to_dataset(hdfdataset, directory):
    """Convert a HDF5 dataset to a JBOF directory."""
    d = create_dataset(directory, hdfdataset.metadata)
    for item in hdfdataset.all_items():
        e = d.add_item(item.name, item.metadata)
        for name, array in item.all_arrays():
            format = Path(array._filename).suffix[1:]
            a = e.add_array(name, array, array.metadata, fileformat=format,
                            samplerate=array.metadata.get('samplerate', None))


class HDFDataSet(DataSet):

    def __init__(self, filename):
        import h5py
        self._file = h5py.File(filename, 'r')
        self._readonly = True

    @property
    def metadata(self):
        return dict(self._file.attrs)

    def all_items(self):
        """A generator that returns all items."""
        for grp in self._file.values():
            yield HDFItem(grp)

    def has_item(self, name):
        """Check if item of name exists."""
        return name in self._file

    def get_item(self, name):
        """Get an item by name."""
        if not self.has_item(name):
            raise TypeError(f'no item {name}')
        return HDFItem(self._file[name])

    def calculate_hash(self):
        """Calculates an md5 hash of all data."""
        raise NotImplementedError('Can not calculate hash of HDF DataSet')


class HDFItem(Item):
    def __init__(self, group):
        self._group = group
        self._readonly = True

    @property
    def metadata(self):
        return dict(self._group.attrs)

    @property
    def name(self):
        return Path(self._group.name).name

    def __getattr__(self, name):
        return HDFArray(self.group[name])

    def __eq__(self, other):
        return self._group == other._group

    def __hash__(self):
        return hash(self._group)

    def all_arrays(self):
        """A generator that returns all arrays as name-value pairs."""
        for name, value in self._group.items():
            yield name, HDFArray(value)

    def has_array(self, name):
        return name in self._group


class HDFArray(Array):
    """A subclass of numpy.ndarray with a `_filename` and `metadata`."""
    def __new__(cls, data):
        obj = numpy.asarray(data).view(cls)
        obj.metadata = dict(data.attrs)
        obj._filename = obj.metadata['_filename']
        del obj.metadata['_filename']
        return obj


class ZIPDataSet(DataSet):

    def __init__(self, filename):
        self._zipfile = zipfile.ZipFile(filename, 'r')
        self._filetree = {}
        for info in self._zipfile.infolist():
            if info.is_dir() or '__pycache__' in info.filename:
                continue
            *parts, name = info.filename.split('/')
            dir = self._filetree
            for part in parts:
                if part not in dir:
                    dir[part] = {}
                dir = dir[part]
            dir[name] = info
        while len(self._filetree) == 1:
            self._filetree = self._filetree[list(self._filetree.keys())[0]]
        self._readonly = True

    @property
    def metadata(self):
        with self._zipfile.open(self._filetree['_metadata.json'].filename) as f:
            metadata = json.load(f)
            del metadata['_itemformat']
            return metadata

    def all_items(self):
        """A generator that returns all items."""
        for name, dir in self._filetree.items():
            if not isinstance(dir, dict):
                continue
            yield ZIPItem(self._zipfile, name, dir)

    def has_item(self, name):
        """Check if item of name exists."""
        return name in self._filetree


    def get_item(self, name):
        """Get an item by name."""
        if not self.has_item(name):
            raise TypeError(f'no item {name}')
        return ZIPItem(self._zipfile, name, self._filetree[name])

    def calculate_hash(self):
        """Calculates an md5 hash of all data."""
        raise NotImplementedError('Can not calculate hash of ZIP DataSet')


class ZIPItem(Item):
    def __init__(self, zipfile, directory, filetree):
        self._zipfile = zipfile
        self._directory = directory
        self._filetree = filetree
        self._readonly = True

    @property
    def metadata(self):
        with self._zipfile.open(self._filetree['_metadata.json'].filename) as f:
            return json.load(f)

    @property
    def name(self):
        return self._directory

    def __getattr__(self, name):
        return ZIPArray(self._zipfile, self._filetree[name + '.json'])

    def __eq__(self, other):
        return self._directory == other._directory

    def __hash__(self):
        return hash(self._directory)

    def all_arrays(self):
        """A generator that returns all arrays as name-value pairs."""
        for name, info in self._filetree.items():
            if name.endswith('.json') and not name.startswith('_metadata'):
                yield name[:-5], ZIPArray(self._zipfile, info)

    def has_array(self, name):
        return name + '.json' in self._filetree


class ZIPArray(Array):
    """A subclass of numpy.ndarray with a `_filename` and `metadata`."""
    def __new__(cls, zipfile, fileinfo):
        with zipfile.open(fileinfo.filename) as f:
            metadata = json.load(f)
        extension = Path(metadata['_filename']).suffix
        with zipfile.open(metadata['_filename']) as f:
            f = io.BytesIO(f.read())
            if extension == '.npy':
                data = numpy.load(f)
            elif extension in ['.wav', '.flac', '.ogg']:
                data, _ = soundfile.read(f)
            elif extension == '.mat':
                name = Path(metadata['_filename']).stem
                data = scipy.io.loadmat(f)
                data = data[name]
        obj = numpy.asarray(data).view(cls)
        obj._filename = metadata['_filename']
        del metadata['_filename']
        obj.metadata = metadata
        return obj
