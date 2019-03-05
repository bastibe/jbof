.. JBOF documentation master file, created by
   sphinx-quickstart on Tue Mar  5 11:11:36 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. include:: ../README.rst

API Documentation
=================

.. autofunction:: jbof.delete_dataset
.. autofunction:: jbof.create_dataset
.. autoclass:: jbof.DataSet
   :members:
   :undoc-members:
.. autoclass:: jbof.Item
   :members:
   :undoc-members:
.. autoclass:: jbof.Array

   .. attribute:: metadata

      The Array's metadata dict.

   .. attribute:: _filename

      The Array's file name.

.. autofunction:: jbof.dataset_to_hdf
.. autofunction:: jbof.hdf_to_dataset

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
