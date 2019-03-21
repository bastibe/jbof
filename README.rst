JBOF - A Dataset from Just a Bunch of Files
===========================================

Many datasets consist of large collections of disjointed files, often
with various levels of metadata. Managing such a dataset is finicky
and error-prone. JBOF standardizes the creation and access to such a
dataset.

JBOF is available for Python and Matlab (read-only). It includes a
partial implementation of Numpy's NPY format for Matlab.

JBOF is free software under the terms of the GPL v3 license.


Design Notes
------------

DataSets are commonly stored as loose collections of data files and
metadata, or as monolithic archives as HDF or MAT files. The former is
hard to work with, since every dataset has its own formatting
conventions and file encodings. The latter is hard to explore without
thorough documentation, and often significantly slower than the
former.

Specifically, I was struggling with HDF files full of audio data and
audio-related features. Being a single file, it was hard for multiple
processes to access such an archive. Due to its internal structure,
metadata access was unnecessarily slow, which made searching the
archive a chore. Furthermore, audio data is easily compressible, but
no such compression methods could be used in HDF.

JBOF solves this problem for me, by storing audio data and metadata as
audio and JSON files, in a clean, HDF-like file structure. The file
structure is easily explorable with a file browser, an audio player,
and a text editor. It is also fast to access from any program that can
read JSON and audio files. For non-audio data, other file formats such
as ``npy`` and ``mat`` are supported as well.

A JBOF `DataSet` is organized as a flat list of `Items`,
which contain `Arrays`. Both the DataSet, the Items, and the
Arrays can have metadata attached, which are stored as simple JSON
files. Every action is thread-safe, in that every add/delete
Item/Array only ever touches files within the Item/Array in question,
and does not interfere with other concurrent actions.

Sometimes, it is beneficial to save a DataSet as a single file. To
enable this, DataSets can be exported as HDF and ZIP files. These
HDF/ZIP files can still be opened as DataSets, albeit only in
read-only mode. JBOF provides convenience methods for converting
DataSets to/from HDF. To convert to/from ZIP, simply zip/unzip the
directory. HDF datasets are significantly slower than plain files, and
often bigger due to lack of audio-specific file encodings. Both ZIP
and HDF files might be slower to read with multiple processes.


Structure
---------

In JBOF, a dataset consists of many *Items*, each of which may contain
many *Arrays*. The dataset, each item, and each array can have
arbitrary metadata, serialized as ``.json`` files. Arrays are Numpy
arrays, stored as ``.npy``-files, or as various other file formats
(``.mat``, ``.wav``, ``.ogg``, ``.flac``).

On disk, a dataset in JBOF might look like this:

.. code::

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


This structure is meant to be both simple to parse, and
human-readable.

- The *dataset* directory contains its own metadata as
  *_metadata.json*, and sub-directories for each *item*.
- Each *item* directory contains its own metadata as *_metadata.json*,
  and pairs of files for each *array*.
- Each *array* is a pair of files, one for metadata *array.json*, and
  one containing the actual data *array.npy*.

By making sure that each operation on the dataset and items is atomic,
multiple processes can read/write the dataset concurrently without
fear of data corruption or race conditions.


Reading Data
------------

To load a dataset, you can either import it, or load it from a URI:

.. code:: python

    # either:
    >>> from dataset import dataset
    # or
    >>> import jbof
    >>> dataset = jbof.DataSet('dataset')

When opening a dataset like this, it is read-only (set
``readonly=False`` to make it writeable).

Access the dataset's metadata:

.. code:: python

    # get all metadata:
    >>> dataset.metadata
    {'license': 'GPL v3'}

Metadata is stored as a JSON file, and can be any JSON-serializable
data.

Access the dataset's items and items' metadata:

.. code:: python

    >>> for item in dataset.all_items():
    >>>     print(item.metadata)
    {'timestamp': '2018-01-25 15:20'}
    {'timestamp': '2018-01-25 15:25'}

You can search for items that match criteria:

.. code:: python

    >>> for item in dataset.find_items(timestamp='2018-01-25 15:20'):
    >>>    print(item.metadata)
    {'timestamp': '2018-01-25 15:20'}

There are a few more search criteria, such as providing multiple valid
matches, or only returning a single search result.

Access each item's arrays:

.. code:: python

    # either use `all_arrays`:
    >>> for name, array in item.all_arrays():
    >>>    print(name, array.metadata, array)
    array1 {'timestamp': '2018-01-25 15:20'} [numpy.ndarray data]
    # or access a single array:
    >>> item.array1.metadata
    {'timestamp': '2018-01-25 15:20'}
    >>> item.array1
    [numpy.ndarray data]


Writing Data
------------

Create a new, writeable dataset:

.. code:: python

    >>> import jbof
    >>> dataset = jbof.create_dataset('new_dataset', metadata={...})

Then, add items and data:

.. code:: python

    >>> item = dataset.add_item(name="...", metadata={...})
    >>> item.add_array('array1', [your data], metadata={...})
    >>> item.add_array('array2', [your data], metadata={...})

If you don't name items, they are assigned random UUIDs.
Alternatively, you can supply an ``itemformat`` to the ``DataSet``,
which will generate item names from the item metadata.

You can delete arrays and Items with ``Item.delete_array`` and
``DataSet.delete_item``, and the whole dataset with
``delete_dataset``.
