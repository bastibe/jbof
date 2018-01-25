import pytest
import numpy
from pathlib import Path
import soundfile
import jbof

@pytest.fixture
def empty_tmp_dataset(request):
    d = jbof.create_dataset('tmp', {'kind': 'dataset'})
    request.addfinalizer(lambda: jbof.delete_dataset(d))
    yield d

@pytest.fixture
def tmp_dataset(request):
    d = jbof.create_dataset('tmp', {'kind': 'dataset'})
    request.addfinalizer(lambda: jbof.delete_dataset(d))
    e = d.add_item(name='first', metadata={'kind': 'item'})
    e.add_array('ones', numpy.ones(10), {'kind': 'ones'}, fileformat='wav', samplerate=8000)
    e.add_array('zeros', numpy.zeros(10), {'kind': 'zeros'}, fileformat='flac', samplerate=16000)
    e.add_array('ones', numpy.ones(10), {'kind': 'ones'}, fileformat='ogg', samplerate=44100)
    e.add_array('ones', numpy.ones(10), {'kind': 'ones'}, fileformat='mat')
    e = d.add_item(metadata={'kind': 'item'})
    e.add_array('twos', numpy.ones(10)*2, {'kind': 'twos'})
    yield d

def test_dataset(tmp_dataset):
    with pytest.raises(TypeError):
        d = jbof.DataSet('doesnotexist')
    d = jbof.DataSet('tmp')
    assert d.metadata == {'kind': 'dataset'}

def test_import_dataset(tmp_dataset):
    from tmp import dataset as data
    assert data._directory.absolute() == tmp_dataset._directory.absolute()

def test_items(tmp_dataset):
    items = list(tmp_dataset.all_items())
    assert tmp_dataset.has_item('first')
    assert 'first' in tmp_dataset
    assert not tmp_dataset.has_item('doesnotexist')
    assert 'doesnotexist' not in tmp_dataset
    assert tmp_dataset.get_item('first') in items
    assert len(items) == 2
    for item in items:
        assert item.metadata == {'kind': 'item'}

def test_arrays(tmp_dataset):
    visited_arrays = []
    assert tmp_dataset.get_item('first').has_array('ones')
    assert 'ones' in tmp_dataset.get_item('first')
    assert not tmp_dataset.get_item('first').has_array('doesnotexist')
    assert 'doesnotexist' not in tmp_dataset.get_item('first')
    for item in tmp_dataset.all_items():
        for name, array in item.all_arrays():
            assert numpy.all(array == {'zeros': 0, 'ones': 1, 'twos': 2}[name])
            if Path(array._filename).suffix in ['.wav', '.flac', '.ogg']:
                assert(array.metadata['samplerate'])
            else:
                assert len(array.metadata) == 1
            assert array.metadata['kind'] == name
            assert hasattr(array, '_filename')
            visited_arrays.append(name)
    assert sorted(visited_arrays) == ['ones', 'twos', 'zeros']

def test_create_existing_dataset_raises_error(empty_tmp_dataset):
    with pytest.raises(TypeError):
        jbof.create_dataset('tmp')

def test_add_existing_item_raises_error(empty_tmp_dataset):
    e = empty_tmp_dataset.add_item({'kind': 'item1'})
    with pytest.raises(TypeError):
        empty_tmp_dataset.add_item({'kind': 'item1'})

def test_add_existing_array_raises_error(empty_tmp_dataset):
    e = empty_tmp_dataset.add_item()
    e.add_array('tmp', [])
    with pytest.raises(TypeError):
        e.add_array('tmp', [])

def test_add_array_from_file(empty_tmp_dataset):
    e = empty_tmp_dataset.add_item()
    numpy.save('tmp.npy', numpy.ones(5))
    e.add_array_from_file('array', 'tmp.npy')
    assert numpy.all(e.array == 1)
    assert len(e.array) == 5
    Path('tmp.npy').unlink()

def test_add_array_from_audio_file(empty_tmp_dataset):
    e = empty_tmp_dataset.add_item()
    soundfile.write('tmp.wav', numpy.zeros(44100), 44100)
    e.add_array_from_file('array', 'tmp.wav')
    assert numpy.all(e.array == 0)
    assert len(e.array) == 44100
    assert e.array.metadata['samplerate'] == 44100
    Path('tmp.wav').unlink()

def test_audio_array(empty_tmp_dataset):
    e = empty_tmp_dataset.add_item()
    e.add_array('array', numpy.zeros(44100), fileformat='wav', samplerate=44100)
    assert numpy.all(e.array == 0)
    assert len(e.array) == 44100
    assert e.array.metadata['samplerate'] == 44100

def test_delete_dataset():
    d = jbof.create_dataset('tmp3')
    jbof.delete_dataset(d)
    with pytest.raises(TypeError):
        d = jbof.DataSet('tmp3')

def test_delete_item(empty_tmp_dataset):
    e = empty_tmp_dataset.add_item()
    assert len(list(empty_tmp_dataset.all_items())) == 1
    empty_tmp_dataset.delete_item(e)
    assert len(list(empty_tmp_dataset.all_items())) == 0

def test_delete_array(empty_tmp_dataset):
    e = empty_tmp_dataset.add_item()
    a = e.add_array('tmp', [])
    assert len(list(e.all_arrays())) == 1
    e.delete_array(a)
    assert len(list(e.all_arrays())) == 0

def test_find_items(empty_tmp_dataset):
    e1 = empty_tmp_dataset.add_item(metadata={'foo': 'bar'})
    e2 = empty_tmp_dataset.add_item(metadata={'foo': 'baz', 'raz':'boo'})
    e3 = empty_tmp_dataset.add_item(metadata={'foo': 'quz'})
    assert set(empty_tmp_dataset.find_items(doesnot='exist')) == set()
    assert set(empty_tmp_dataset.find_items(foo='bar')) == {e1}
    assert set(empty_tmp_dataset.find_items(foo=['bar', 'baz'])) == {e1, e2}
    assert set(empty_tmp_dataset.find_items(foo='quz', raz='boo')) == set()
