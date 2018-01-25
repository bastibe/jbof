# JBOF - A Dataset from Just a Bunch of Files

Many datasets consist of large collections of disjointed files, often with various levels of metadata. Managing such a dataset is finicky and error-prone. JBOF standardizes the creation and access to such a dataset.

JBOF is free software under the terms of the GPL v3 license.


## Design Notes

DataSets, Items, and Arrays are simple files on the file system. The file structure is meant to be easy to understand and inspect, and you should be able to read a DataSet from other programming languages with ease (as long as you save your arrays as non-`npy`).

Every action (add/delete Item, add/delete Array) only touches files within the Item/Array in question, and does not interfere with other concurrent actions. In other words, DataSet is thread-safe.


## Structure

In JBOF, a dataset consists of many *items*, each of which may contain many *arrays*. The dataset, each item, and each array can have arbitrary metadata (as long as it is serializable as JSON). Arrays are Numpy arrays, stored as `.npy`-files, or as various other file formats (`.mat`, `.wav`, `.ogg`, `.flac`).

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

When opening a dataset like this, it is read-only (set `readonly=False` to make it writeable).

Access the dataset's metadata:
```python
# get all metadata:
>>> dataset.metadata
{'license': 'GPL v3'}
```

Metadata is stored as a JSON file, and can be any JSON-serializable data.

Access the dataset's items and items' metadata:
```python
>>> for item in dataset.all_items():
>>>     print(item.metadata)
{'timestamp': '2018-01-25 15:20'}
{'timestamp': '2018-01-25 15:25'}
```

You can search for items that match criteria:
```python
>>> for item in dataset.find_items(timestamp='2018-01-25 15:20'):
>>>    print(item.metadata)
{'timestamp': '2018-01-25 15:20'}
```

There are a few more search criteria, such as providing multiple valid matches, or only returning a single search result.

Access each item's arrays:
```python
# either use `all_arrays`:
>>> for name, array in item.all_arrays():
>>>    print(name, array.metadata, array)
array1 {'timestamp': '2018-01-25 15:20'} [numpy.ndarray data]
# or access a single array:
>>> item.array1.metadata
{'timestamp': '2018-01-25 15:20'}
>>> item.array1
[numpy.ndarray data]
```


## Writing Data

Create a new, writeable dataset:
```python
>>> import jbod
>>> dataset = jbod.DataSet.create_dataset('new_dataset', metadata={...})
```

Then, add items and data:
```python
>>> item = dataset.add_item(name="...", metadata={...})
>>> item.add_array('array1', [your data], metadata={...})
>>> item.add_array('array2', [your data], metadata={...})
```

If you don't name items, they are assigned random UUIDs. Alternatively, you can supply an `itemformat` to the `DataSet`, which will generate item names from the item metadata.

You can delete arrays and Items with `Item.delete_array` and `DataSet.delete_item`, and the whole dataset with `delete_dataset`.


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
- [X] Implement read-only flag for dataset
- [X] Implement checksumming for the dataset  
  This works only for explicit item names and deterministic array filetypes.
- [X] Implement deleting items/data (but don't change existing items/data to avoid race conditions)
- [ ] Implement conversion to/from HDF
- [ ] Implement conversion to/from MongoDB
- [ ] Implement conversion to/from Zip
