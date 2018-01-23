import pytest

import jbof
import shutil
import numpy

@pytest.fixture
def example_data():
    d = jbof.DataSet.create_dataset('tmp', {'kind': 'dataset'})
    e = d.create_entry({'kind': 'entry'})
    e.create_datum('ones', numpy.ones(10), {'kind': 'ones'})
    e.create_datum('zeros', numpy.zeros(10), {'kind': 'zeros'})
    e = d.create_entry({'kind': 'entry'})
    e.create_datum('twos', numpy.ones(10)*2, {'kind': 'twos'})
    yield d
    shutil.rmtree('tmp')

def test_dataset(example_data):
    with pytest.raises(TypeError):
        d = jbof.DataSet('doesnotexist')
    d = jbof.DataSet('tmp')
    assert d.metadata == {'kind': 'dataset', '_entryformat': None}


def test_import_dataset(example_data):
    from tmp import dataset as data
    assert data.directory.absolute() == example_data.directory.absolute()

def test_entries(example_data):
    entries = list(example_data.all_entries())
    assert len(entries) == 2
    for entry in entries:
        assert entry.metadata == {'kind': 'entry'}

def test_data(example_data):
    visited_data = []
    for entry in example_data.all_entries():
        for name, data in entry.all_data():
            assert numpy.all(data == {'zeros': 0, 'ones': 1, 'twos': 2}[name])
            assert len(data.metadata) == 2
            assert data.metadata['kind'] == name
            assert '_filename' in data.metadata
            visited_data.append(name)
    assert sorted(visited_data) == ['ones', 'twos', 'zeros']
