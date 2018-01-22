import jbof
import shutil
import numpy

shutil.rmtree('tmp')

d = jbof.DataSet('tmp', {'foo': 'bar'})
e = d.create_entry({'foo': 'baz1'})
e.create_data('test1', numpy.random.randn(10), {'foo': 'foo1'})
e.create_data('test2', numpy.random.randn(10), {'foo': 'foo2'})
e = d.create_entry({'foo': 'baz2'})
e.create_data('test', numpy.random.randn(10), {'foo': 'foo'})

for entry in d.entries():
    print(entry.metadata)
    for name, data in entry.all_data().items():
        print(name, data.metadata, data)

from tmp import dataset
for entry in dataset.entries():
    print(entry.metadata)
    for name, data in entry.all_data().items():
        print(name, data.metadata, data)
