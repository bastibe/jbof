# JBOF - A Dataset from Just a Bunch of Files

Many datasets consist of large collections of disjointed files, often with various levels of metadata. Managing such a dataset is finicky and error-prone. JBOF standardizes the creation and access to such a dataset.

JBOF is free software under the terms of the GPL v3 license.

## Structure

In JBOF, a dataset consists of many *entries*, each of which may contain many *data*. The dataset, each entry, and each datum can have arbitrary metadata.

On disk, a dataset in JBOF is organized as follows:
```
dataset
├── __init__.py
├── _metadata.json
├── entry1
│   ├── _metadata.json
│   ├── datum1.json
│   ├── datum1.npy
│   ├── datum2.json
│   └── datum2.npy
└── entry2
    ├── _metadata.json
    ├── datum1.json
    └── datum2.npy
```

- The *dataset* directory contains its own metadata as *_metadata.json*, and sub-directories for each *entry*.
- Each *entry* directory contains its own metadata as *_metadata.json*, and pairs of files for each *datum*.
- Each *datum* is a pair of files, one for metadata *datum.json*, and one containing the actual data *datum.npy*.

By making sure that each operation on the dataset and entries is atomic, multiple processes can read/write the dataset concurrently without fear of data corruption or race conditions.

## Reading Data

To load a dataset, you can either import it, or load it from a URI:
```python
# either:
>>> from dataset import dataset
# or
>>> import jbod
>>> dataset = jbod.DataSet('dataset')
```

Access the dataset's metadata:
```python
# get all metadata:
>>> dataset.metadata
{'example': 'arbitrary JSON data'}
# get just one key:
>>> dataset['example']
'arbitrary JSON data'
```

Access the dataset's entries:
```python
>>> for entry in dataset.all_entries():
>>>     print(entry.metadata)
{'again': 'arbitrary JSON data'}
```

Access each entry's data:
```python
# either:
>>> for name, datum in entry.all_data():
>>>    print(name, datum.metadata, datum)
datum1 {'again': 'more JSON data'} [numpy.ndarray]
# or:
>>> entry.datum1.metadata
{'again': 'more JSON data'}
>>> entry.datum1
[numpy.ndarray]
```

## Writing Data

Create a new dataset:
```python
>>> import jbod
>>> dataset = jbod.DataSet.create_dataset('new_dataset', metadata={...})
```

Then, create entries and data:
```python
>>> entry = dataset.create_entry(metadata={...})
>>> entry.create_datum('datum1', [your data], metadata={...})
>>> entry.create_datum('datum2', [your data], metadata={...})
```

Entries do not have name, and entry directories are random UUIDs. If you want to have human-readable names, supply an `entryformat` to the `DataSet` (a `str.format` string that will be called with the metadata).

## TODO

- [ ] Add search queries to `DataSet.all_entries`
- [X] Write a test suite
- [ ] Implement already-exist checks in `DataSet.create_dataset`/`DataSet.create_entry`/`Entry.create_datum`
- [ ] Implement different file types for `Entry.create_datum`/`Data.__new__` 
  - [X] `npy`
  - [ ] `msgpack`
  - [ ] `csv`
  - [X] `wav`
  - [X] `flac`
  - [X] `ogg`
  - [X] `mat`
- [ ] Implement read-only flag for dataset
- [ ] Implement automatic checksumming when creating data, and post-hoc for the dataset
- [ ] Implement deleting entries/data (but don't change existing entries/data to avoid race conditions)
- [ ] Implement conversion to/from HDF
- [ ] Implement conversion to/from MongoDB
