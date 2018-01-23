import pytest

import jbof
import shutil
import numpy
from pathlib import Path

@pytest.fixture
def example_data():
    d = jbof.DataSet.create_dataset('tmp', {'kind': 'dataset'})
    e = d.add_item({'kind': 'item'})
    e.add_array('ones', numpy.ones(10), {'kind': 'ones'}, fileformat='wav', samplerate=8000)
    e.add_array('zeros', numpy.zeros(10), {'kind': 'zeros'}, fileformat='flac', samplerate=16000)
    e.add_array('ones', numpy.ones(10), {'kind': 'ones'}, fileformat='ogg', samplerate=44100)
    e.add_array('ones', numpy.ones(10), {'kind': 'ones'}, fileformat='mat')
    e = d.add_item({'kind': 'item'})
    e.add_array('twos', numpy.ones(10)*2, {'kind': 'twos'})
    yield d
    shutil.rmtree('tmp')

def test_dataset(example_data):
    with pytest.raises(TypeError):
        d = jbof.DataSet('doesnotexist')
    d = jbof.DataSet('tmp')
    assert d.metadata == {'kind': 'dataset', '_itemformat': None}

def test_import_dataset(example_data):
    from tmp import dataset as data
    assert data._directory.absolute() == example_data._directory.absolute()

def test_items(example_data):
    items = list(example_data.all_items())
    assert len(items) == 2
    for item in items:
        assert item.metadata == {'kind': 'item'}

def test_arrays(example_data):
    visited_arrays = []
    for item in example_data.all_items():
        for name, array in item.all_arrays():
            assert numpy.all(array == {'zeros': 0, 'ones': 1, 'twos': 2}[name])
            if Path(array.metadata['_filename']).suffix in ['.wav', '.flac', '.ogg']:
                assert(array.metadata['samplerate'])
            else:
                assert len(array.metadata) == 2
            assert array.metadata['kind'] == name
            assert '_filename' in array.metadata
            visited_arrays.append(name)
    assert sorted(visited_arrays) == ['ones', 'twos', 'zeros']

def test_create_existing_dataset_raises_error():
    d = jbof.DataSet.create_dataset('tmp2', {})
    with pytest.raises(TypeError):
        jbof.DataSet.create_dataset('tmp2', {})
    shutil.rmtree('tmp2')

def test_add_existing_item_raises_error():
    d = jbof.DataSet.create_dataset('tmp2', {}, itemformat='{kind}')
    e = d.add_item({'kind': 'item1'})
    with pytest.raises(TypeError):
        d.add_item({'kind': 'item1'})
    shutil.rmtree('tmp2')

def test_add_existing_array_raises_error():
    d = jbof.DataSet.create_dataset('tmp2', {})
    e = d.add_item({})
    e.add_array('tmp', [], {})
    with pytest.raises(TypeError):
        e.add_array('tmp', [], {})
    shutil.rmtree('tmp2')

def test_add_array_from_file():
    d = jbof.DataSet.create_dataset('tmp2', {})
    e = d.add_item({})
    numpy.save('tmp.npy', numpy.ones(5))
    e.add_array_from_file('array', 'tmp.npy', {})
    assert numpy.all(e.array == 1)
    assert len(e.array) == 5
    shutil.rmtree('tmp2')
    Path('tmp.npy').unlink()
