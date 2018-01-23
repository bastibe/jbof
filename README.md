# JBOF - A Dataset from Just a Bunch of Files

Many datasets consist of large collections of disjointed files, often with various levels of metadata. Managing such a dataset is finicky and error-prone. JBOF standardizes the creation and access to such a dataset.

JBOF is free software under the terms of the GPL v3 license.

## Structure


In JBOF, a dataset consists of many *items*, each of which may contain many *arrays*. The dataset, each item, and each array can have arbitrary metadata (as long as it is serializable as JSON). Arrays are Numpy arrays, stored as `.npy`-files, or as various other file formats (`.mat`, `.wav`, `.ogg`, `.flac`, `.msgpack`, `.csv`).

On disk, a dataset in JBOF is organized as follows:
```
dataset
├── __init__.py
├── _metadata.json
├── item1
│   ├── _metadata.json
│   ├── array1.json
│   ├── array1.npy
│   ├── array2.json
│   └── array2.npy
└── item2
    ├── _metadata.json
    ├── array1.json
    └── array1.npy
```


This structure is meant to be both simple and human-readable.

- The *dataset* directory contains its own metadata as *_metadata.json*, and sub-directories for each *item*.
- Each *item* directory contains its own metadata as *_metadata.json*, and pairs of files for each *array*.
- Each *array* is a pair of files, one for metadata *array.json*, and one containing the actual data *array.npy*.

By making sure that each operation on the dataset and items is atomic, multiple processes can read/write the dataset concurrently without fear of data corruption or race conditions.

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

Access the dataset's items:
```python
>>> for item in dataset.all_items():
>>>     print(item.metadata)
{'again': 'arbitrary JSON data'}
```

Access each item's arrays:
```python
# either:
>>> for name, array in item.all_arrays():
>>>    print(name, array.metadata, array)
array1 {'again': 'more JSON data'} [numpy.ndarray]
# or:
>>> item.array1.metadata
{'again': 'more JSON data'}
>>> item.array1
[numpy.ndarray]
```

## Writing Data

Create a new dataset:
```python
>>> import jbod
>>> dataset = jbod.DataSet.create_dataset('new_dataset', metadata={...})
```

Then, add items and data:
```python
>>> item = dataset.add_item(metadata={...})
>>> item.add_array('array1', [your data], metadata={...})
>>> item.add_array('array2', [your data], metadata={...})
```

Items do not have name, and item directories are random UUIDs. If you want to have human-readable names, supply an `itemformat` to the `DataSet` (a `str.format` string that will be called with the metadata).

## TODO

- [X] Add search queries to `DataSet.all_items`
- [X] Write a test suite
- [X] Implement already-exist checks in `DataSet.create_dataset`/`DataSet.add_item`/`Item.add_array`
- [ ] Implement different file types for `Item.add_array`/`Array.__new__`
  - [X] `npy`
  - [ ] `msgpack`
  - [ ] `csv`
  - [X] `wav`
  - [X] `flac`
  - [X] `ogg`
  - [X] `mat`
- [X] Implement importing existing files in `Item.add_array`
- [ ] Implement read-only flag for dataset
- [ ] Implement automatic checksumming when creating data, and post-hoc for the dataset
- [X] Implement deleting items/data (but don't change existing items/data to avoid race conditions)
- [ ] Implement conversion to/from HDF
- [ ] Implement conversion to/from MongoDB
