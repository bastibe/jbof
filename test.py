import jbof
import shutil
import numpy

shutil.rmtree('tmp', ignore_errors=True)

d = jbof.DataSet.create_dataset('tmp', {'foo': 'bar'})
e = d.create_entry({'foo': 'baz1'})
e.create_datum('test1', numpy.random.randn(10), {'foo': 'foo1'})
e.create_datum('test2', numpy.random.randn(10), {'foo': 'foo1'}, fileformat='mat')
e = d.create_entry({'foo': 'baz2'})
e.create_datum('test1', numpy.random.randn(10), {'foo': 'foo'}, fileformat='wav', samplerate=16000)
e.create_datum('test2', numpy.random.randn(10), {'foo': 'foo'}, fileformat='ogg', samplerate=16000)
e.create_datum('test3', numpy.random.randn(10), {'foo': 'foo2'}, fileformat='flac', samplerate=16000)

for entry in d.all_entries():
    print(entry.metadata)
    for name, data in entry.all_data():
        print(name, data.metadata, data)

from tmp import dataset
for entry in dataset.all_entries():
    print(entry.metadata)
    for name, data in entry.all_data():
        print(name, data.metadata, data)
