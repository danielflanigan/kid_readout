"""
This module is the core of the measurement subpackage. See __init__.py for documentation.
"""
import copy_reg
import re
import logging
import inspect
import keyword
import importlib
from numbers import Number
from collections import OrderedDict

import numpy as np
import pandas as pd

from kid_readout.measurement import classes

CLASS_NAME = '_class'  # This is the string used by IO objects to save class names.
VERSION = '_version'  # This is the string used by IO objects to save class versions.
METADATA = '_metadata'  # This is the string used by IO objects to save metadata dictionaries.

# TODO: decide which names really need to be reserved, and clean this up after add_legacy_origin is refactored.
# These names cannot be used for attributes because they are used as part of the public DataFrame interface.
IO_CLASS_NAME = 'io_class'  # This is the fully-qualified name of the IO class used to read a measurement from disk.
ROOT_PATH = 'root_path'  # This is the root file or directory from which a measurement was read from disk.
NODE_PATH = 'node_path'  # This is the node path from the root node to the measurement node.
NUMBER = 'number'  # This is the index of a single measurement slice from an array-like measurement.

# IO_MODULE = 'io_module'  # This is the full-qualified name of the module used to read and write legacy data.
RESERVED = [IO_CLASS_NAME, ROOT_PATH, NODE_PATH, NUMBER]  # io_node_path is included here
# These strings have a corresponding private attribute.
PRIVATE = ['io_node_path']

# This character separates nodes in a node path.
NODE_PATH_SEPARATOR = '/'

logger = logging.getLogger(__name__)


class Node(object):
    """
    This is an abstract class that represents a node in the tree data structure used to save data.
    """

    _version = 0

    def __init__(self):
        """
        Set internal state variables.

        :return: a new Node instance.
        """
        self._parent = None
        self._io = None
        self._io_node_path = None

    @classmethod
    def class_name(cls):
        """
        Return the name of the class that should be used to load this object from disk. Usually, this will simply be the
        name of the class, but this can be overridden if necessary. The return value from this method will be stored on
        disk and used to recreate the object as an instance of the class with this name.

        The purpose of this method is to allow classes to recommend some other class that should be used to load their
        data. For example, the IOList class cannot be instantiated using the data that it writes to disk, so its
        class_name() returns MeasurementList, which is a class that can load the data.

        Returns
        -------
        str
           The class name.
        """
        return cls.__name__

    @property
    def io_node_path(self):
        """
        Return a string representing the node path last used to write or read this node.

        When a node is written to or read from disk it is tagged with the path used by the IO object to write or read
        it, and that path will be the return value until it is updated by another save or load.

        Returns
        -------
        str
            The node path of this Node on disk.
        """
        return self._io_node_path

    @property
    def current_node_path(self):
        """
        Return a string representing the node path of this node according to the current structure of its tree. This
        path is always relative to the top-level node, which is always a Node and never an IO object.

        For example, if this node is the Stream stored at index 3 in the list of Streams in the Sweep of a SweepStream,
        this would return '/sweep/streams/3' regardless of whether some or all of these measurements have been written
        to disk. Thus, it will always differ from `io_node_path`.

        Because this function has to traverse the contents of each parent, it could be slow for large structures.

        Returns
        -------
        str
            The node path of this Node.
        """
        if self._parent is None:
            return NODE_PATH_SEPARATOR
        else:
            return join(self._parent.current_node_path, self._parent._locate(self))

    def add_origin(self, dataframe):
        """
        Add to the given dataframe enough information to load the data from which it was created.

        This method adds columns named for the IO_CLASS_NAME, ROOT_PATH, and NODE_PATH variables in this module; the
        columns contain the IO class, the path to the root file or directory, and the node path to this node. The
        from_series() function in this module can use this information to load the original data.

        If this node was not loaded from disk then it has no origin information and the values of the above will all be
        None. If this is the case, this method will attempt to add origin information for each child node, using the
        attribute name as a prefix. For example, if a measurement has an attribute `child`, then this function will
        create columns
        `io_class_name`: None
        etc., because the top-level node has no origin information, and will also create columns
        `child.io_class_name`: NCFile
        and so on. The from_series() function will be able to load the child measurements once the prefix is stripped.

        Parameters
        ----------
        dataframe : pandas.DataFrame
            The dataframe to which this method will add origin information.
        """
        try:
            dataframe[IO_CLASS_NAME] = self._io.__class__.__name__
            dataframe[ROOT_PATH] = self._io.root_path
            dataframe[NODE_PATH] = self._io_node_path
        except AttributeError:  # This node has not been read from or written to disk, so try its children.
            dataframe[IO_CLASS_NAME] = None
            dataframe[ROOT_PATH] = None
            dataframe[NODE_PATH] = None
            for key, value in self.__dict__.items():
                if not key.startswith('_') and isinstance(value, Node):
                    try:
                        dataframe['.'.join((key, IO_CLASS_NAME))] = value._io.__class__.__name__
                        dataframe['.'.join((key, ROOT_PATH))] = value._io.root_path
                        dataframe['.'.join((key, NODE_PATH))] = value._io_node_path
                    except AttributeError:
                        dataframe['.'.join((key, IO_CLASS_NAME))] = None
                        dataframe['.'.join((key, ROOT_PATH))] = None
                        dataframe['.'.join((key, NODE_PATH))] = None

    def _locate(self, node):
        """
        Subclasses should implement this method to enable nodes to discover their location in the node tree:
        self._parent._locate(self)
        returns the node path relative to the parent node.

        Parameters
        ----------
        node : Node
            The node to locate.

        Returns
        -------
        str
            The node name of the given node; depending on how it is stored in the current node, this could be an
            attribute name, a dictionary key, or string representation of an integer sequence index.

        Raises
        ------
        AttributeError
            If the given node is not contained in this node.
        """
        pass

    def __setattr__(self, key, value):
        """
        This differs from object.__setattr__() only in that it sets the _parent attribute of public Node instances.
        The goal is to ensure that child nodes always have a link to their parent. If a node is set as an attribute of
        multiple nodes, its _parent will be the node to which it was most recently added.

        Parameters
        ----------
        key : str
            The attribute name to set.
        value : object
            The attribute value to set.

        Returns
        -------
        None
        """
        if not key.startswith('_') and isinstance(value, Node):
            value._parent = self
        super(Node, self).__setattr__(key, value)


class Measurement(Node):
    """
    This class represents a measurement. A measurement specifies a data format on disk, and can contain analysis code
    for that data format. To create a new measurement, write a subclass that obeys the restrictions described in the
    module docstring and below.

    Array dimensions.
    Each measurement has a dimensions class attribute that contains metadata for its array dimensions. This is
    necessary for the netCDF4 IO class to handle the array dimensions correctly, and it also allows the classes to
    check the dimensions of their arrays on instantiation through the _validate_dimensions() method. The format of the
    an entry in the dimensions OrderedDict is 'array_name': dimension_tuple, where dimension tuple is a tuple of strings
    that are the names of the dimensions. To pass validation, each dimension name must correspond to an attribute or
    property of the class that is a 1-D array with size equal to the corresponding element of array.shape. Thus, arrays
    that have a given dimension must all have the same length along that dimension. For example, if there is an entry
    's21_raw': ('time', 'frequency)
    and another entry
    'frequency': ('frequency',)
    then
    s21_raw.shape[1] == frequency.size
    must be True. If the array corresponding to some dimension is not intended to be saved, it can be implemented as a
    property. For example, in the case above, the 'time' dimension could be implemented as a property. The instance
    would still pass validation as long as
    s21_raw.shape[0] == time.size
    were True.

    Content restrictions.
    Measurements store state information in a dictionary. (They actually use a subclass called StateDict, which has
    extra access features and validation.) Supporting multiple


    """

    _version = 0

    dimensions = OrderedDict()

    def __init__(self, state=None, description='', validate=True):
        """
        Return a new Measurement instance.

        Setting validate=False allows improperly-formed measurements to be created in special cases. Note that such a
        measurement may not be saved correctly -- or at all -- by the IO classes.

        Parameters
        ----------
        state : dict
            A dictionary of state information that should be valid throughout the measurement period.
        description : str
            A verbose description of the measurement.
        validate : bool
            If true, verify that the array shapes are correctly described by the dimensions OrderedDict.

        Raises
        ------
        ValueError
            If the array shapes do not pass validation.
        """
        super(Measurement, self).__init__()
        if state is None:
            state = {}
        self.state = StateDict(state)
        self.description = description
        if validate:
            self._validate_dimensions()

    def as_class(self, class_):
        public = dict([(k, v) for k, v in self.__dict__.items() if not k.startswith('_')])
        return class_(**public)

    def to_dataframe(self):
        """
        This method should return a pandas DataFrame containing state information and analysis products, such as fit
        parameters, but not large objects such as time-ordered data.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing data from this measurement.
        """
        return pd.DataFrame({'description': self.description}, index=[0])

    # TODO: decide how to implement this, if at all.
    """
    def add_legacy_origin(self, dataframe):
        dataframe['io_module'] = 'kid_readout.measurement.legacy'
        dataframe['root_path'] = self._root_path
    """

    def _validate_dimensions(self):
        for name, dimension_tuple in self.dimensions.items():
            if not getattr(self, name).shape == tuple(getattr(self, dimension).size for dimension in dimension_tuple):
                raise ValueError("Shape of {} does not match size of {}.".format(name, dimension_tuple))

    def _locate(self, node):
        for key, value in self.__dict__.items():
            if node is value:
                return key
        raise AttributeError("Node {} is not contained in {}.".format(repr(Node), repr(self)))

    def __eq__(self, other):
        """
        Recursively compare two measurements. At each level, the function tests that both instances have the same public
        attributes (meaning those that do not start with an underscore), that all these attributes are equal,
        and that the classes of the measurements are equal. Because the data we store mixes booleans and numbers,
        boolean values stored as attributes are compared using identity, not equality. Note that this is not done
        within containers.

        The function does not compare private attributes, and does not even check whether the instances have the same
        private attributes.

        Parameters
        ----------
        other : Measurement
            The measurement to compare to self.

        Returns
        -------
        bool
            True if self compares equal with other, and False if not.
        """
        try:
            keys_s = ['__class__'] + [k for k in self.__dict__ if not k.startswith('_')]
            keys_o = ['__class__'] + [k for k in other.__dict__ if not k.startswith('_')]
            assert set(keys_s) == set(keys_o)
            for key in keys_s:
                value_s = getattr(self, key)
                value_o = getattr(other, key)
                if issubclass(value_s.__class__, Measurement):
                    assert value_s.__eq__(value_o)
                elif issubclass(value_s.__class__, MeasurementList):
                    assert len(value_s) == len(value_o)
                    for meas_s, meas_o in zip(value_s, value_o):
                        assert meas_s.__eq__(meas_o)
                # This allows arrays to contain NaN and be equal.
                elif isinstance(value_s, np.ndarray) or isinstance(value_o, np.ndarray):
                    assert np.all(np.isnan(value_s) == np.isnan(value_o))
                    assert np.all(value_s[~np.isnan(value_s)] == value_o[~np.isnan(value_o)])
                else:  # This will fail for NaN or sequences that contain any NaN values.
                    if isinstance(value_s, bool) or isinstance(value_o, bool):
                        assert value_s is value_o
                    else:
                        assert value_s == value_o
        except AssertionError:
            return False
        return True

    def __ne__(self, other):
        """The Python object model recommends implementing this if __eq__() is implemented."""
        return not self.__eq__(other)

    # Recommended by the Python object model docs.
    __hash__ = None


class MeasurementList(list, Node):
    """
    This class implements all the list methods. It should contain only Node instances, such as Measurement subclasses.
    Measurements containing lists of Measurements must use instances of this class so that loading and saving are
    handled correctly.
    """

    _version = 0

    def __init__(self, iterable=()):
        super(MeasurementList, self).__init__(iterable)
        Node.__init__(self)
        for item in self:
            item._parent = self

    def _locate(self, node):
        for index, value in enumerate(self):
            if node is value:
                return str(index)
        raise AttributeError("Node {} is not contained in {}.".format(repr(Node), repr(self)))

    def append(self, item):
        item._parent = self
        super(MeasurementList, self).append(item)

    def extend(self, iterable):
        for item in iterable:
            item._parent = self
        super(MeasurementList, self).extend(iterable)

    def insert(self, index, item):
        item._parent = self
        super(MeasurementList, self).insert(index, item)

    def __setitem__(self, key, value):
        value._parent = self
        super(MeasurementList, self).__setitem__(key, value)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, super(MeasurementList, self).__repr__())


class IOList(MeasurementList):
    """
    This class acts like a MeasurementList that writes Measurements to disk as they are added to the list. It can only
    be created empty, and implements only the append() and extend() methods. To use this class, pass it as an argument
    when instantiating a class that normally contains a MeasurementList, save that class to disk, then use the append()
    or extend() methods to save measurements directly to disk instead of storing them in memory. The IO class must
    remain open until writing is finished.
    """

    @classmethod
    def class_name(cls):
        return cls.__base__.__name__

    def __init__(self):
        super(IOList, self).__init__()
        self._len = 0

    def append(self, item):
        self._io.write(item, join(self._io_node_path, str(len(self))))
        self._len += 1

    def extend(self, iterable):
        for item in iterable:
            self.append(item)

    def insert(self, index, item):
        raise NotImplementedError()

    def remove(self, value):
        raise NotImplementedError()

    def pop(self, index=None):
        raise NotImplementedError()

    def index(self, value, start=None, stop=None):
        raise NotImplementedError()

    def count(self, value):
        raise NotImplementedError()

    def sort(self, cmp=None, key=None, reverse=False):
        raise NotImplementedError()

    def reverse(self):
        raise NotImplementedError()

    def __iter__(self):
        """
        Instances of this class appear like empty lists, so iteration stops immediately.

        :return: an empty iterator.
        """
        return iter(())

    def __len__(self):
        return self._len

    def __getitem__(self, item):
        raise NotImplementedError()

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def __repr__(self):
        return '{}({}, {})'.format(self.__class__.__name__, self._io, self._io_node_path)


class MeasurementError(Exception):
    """
    Raised for module-specific errors.
    """
    pass


# ToDo: when a dict is added after construction, it is not converted to a StateDict so there is no type checking
class StateDict(dict):
    """
    This class adds attribute access and some content restrictions to the dict class.

    To support attribute access, keys must be strings that are valid Python attributes The value restrictions are the
    union of the restrictions imposed by the libraries used to write non-array data to disk. (Currently, these are
    netCDF4 for the nc.NCFile class and JSON for the npy.NumpyDirectory class.)



    -basic types, such as numbers, booleans, strings, booleans, and None;
    -sequences, i.e. lists, tuples, and arrays, that contain exactly one of the above basic types except None; sequences
     cannot contain other sequences
    -dictionaries that obey the key and value restrictions.
    Classes that do not obey these restrictions may fail to save or may have missing or corrupted data when read from
    disk.


    Two values that are particularly problematic are None and NaN. None requires a special case because netCDF4
    cannot write it, so it is allowed as an attribute value or dictionary value but not in sequences. NaN is stored
    and retrieved correctly but is not recommended as an indicator of missing state because it causes comparisons to
    fail: float('NaN') == float('NaN') is always False. See Measurement.__eq__() for more.

    Origin of restrictions:
    -JSON has only a single sequence type, so all iterable non-dictionary objects are converted to lists on input;
    -netCDF cannot write None, so it cannot be an element of a sequence;

    """

    __setattr__ = dict.__setitem__
    __getattr__ = dict.__getitem__
    __delattr__ = dict.__delitem__
    __copy__ = lambda self: StateDict(self)
    __getstate__ = lambda: None
    __slots__ = ()

    ALLOWED_VALUE_TYPES = (Number, str, unicode)  #(Number, np.number, str, unicode)

    _invalid_key_type = "Dictionary keys must be strings."
    _invalid_variable_name = "Invalid variable name: {0}"
    _invalid_value = "Key {0} maps to invalid value: {1!s} ({1!r})"
    _invalid_sequence_value = "Key {0} maps to a sequence containing invalid value: {1!s} ({1!r})"

    def __init__(self, *args, **kwargs):
        super(StateDict, self).__init__(*args, **kwargs)
        for key, value in self.items():
            if not isinstance(key, (str, unicode)):
                raise MeasurementError(self._invalid_key_type)
            elif re.match(r'[a-zA-Z_][a-zA-Z0-9_]*$', key) is None or keyword.iskeyword(key) or key in __builtins__:
                raise MeasurementError(self._invalid_variable_name.format(key))
            if isinstance(value, dict):
                self[key] = StateDict(value)
            else:
                # Given that we are testing for sequence-ness using iteration, we have to try value validation first
                # because strings are iterable.
                try:
                    self[key] = self._validate_value(key, value)
                except ValueError as e:
                    try:
                        self[key] = self._validate_list(key, list(value))
                    except TypeError:  # Not iterable, and str would have passed value validation
                        raise e

    def _validate_value(self, key, value):
        if value is None or isinstance(value, self.ALLOWED_VALUE_TYPES):
            return value
        else:
            raise ValueError(self._invalid_value.format(key, value))

    def _validate_list(self, key, list_):
        for index, element in enumerate(list_):
            if not isinstance(element, self.ALLOWED_VALUE_TYPES):
                try:
                    list_[index] = self._validate_list(key, list(element))
                except TypeError:  # Not iterable, and str would have passed value validation
                    raise ValueError(self._invalid_sequence_value.format(key, element))
        return list_

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, super(StateDict, self).__repr__())

    def flatten(self, prefix='', wrap_lists=False):
        results = StateDict()
        for k, v in self.items():
            this_label = k
            if prefix:
                this_label = prefix + '_' + this_label
            if isinstance(v, StateDict):
                results.update(v.flatten(prefix=this_label, wrap_lists=wrap_lists))
            elif wrap_lists and isinstance(v, list):
                results[this_label] = [v]
            else:
                results[this_label] = v
        return results


def pickle_state(s):
    return StateDict, (dict(s),)

copy_reg.pickle(StateDict, pickle_state)


class IO(object):
    """
    This is an abstract class that specifies the IO interface.

    Implementations should implement the abstract methods and should be able to store large numpy arrays efficiently, as
    well as the following objects:
    -basic types, such as numbers, booleans, strings, and None;
    -sequences, i.e. lists, tuples, and arrays, that contain exactly one of the above basic types; sequences
     cannot contain None or other sequences, and all input sequences are returned as lists on read.
    -dictionaries whose keys are strings and whose values are dictionaries, sequences, or basic types; the contained
     dictionaries and sequences have the same requirements as above.
    Classes that do not obey these restrictions may fail to save or may have missing or corrupted data when read from
    disk. See StateDict for details.
    """

    # Subclasses can define a conventional extension for files or directories they create.
    EXTENSION = ''

    def __init__(self, root_path, metadata=None):
        """
        Return a new IO object that will read to or write from the given root directory or file. If the root does not
        exist, it should be created. Implementations should never clobber an existing file and should make it difficult
        to overwrite data, though appending to or modifying existing data may be useful.

        Parameters
        ----------
        root_path : str
            The path to the root directory or file.
        metadata : dict
            If the root does not exist, write this dict to the root node.
        """
        self.root_path = root_path
        if self._root_path_exists(self.root_path):
            if metadata is not None:
                raise ValueError("Cannot set metadata for an existing root: {}".format(root_path))
            self._root = self._open_existing(self.root_path)
            try:
                metadata = self.read_other('/', METADATA)
                if metadata is not None:
                    self.metadata = StateDict(metadata)
                else:
                    self.metadata = None
            except ValueError:
                self.metadata = None
        else:
            self._root = self._create_new(self.root_path)
            self.write_other('/', METADATA, metadata)
            self.metadata = metadata

    # These private methods must be implemented by subclasses.

    def _root_path_exists(self, root_path):
        return False

    def _open_existing(self, root_path):
        return None

    def _create_new(self, root_path):
        return None

    # These public methods should work.

    @property
    def closed(self):
        """
        Returns
        -------
        bool
            True if all files on disk are closed.
        """
        return True

    def default_name(self, node):
        """
        Return a name for the given Node subclass or instance that is guaranteed to be unique at the root level.

        Parameters
        ----------
        node : Node
            An instance or subclass.

        Returns
        -------
        str
            A string consisting of the class name and a number that is one plus the number of nodes already stored at
            the root level, guaranteeing uniqueness.
        """
        return node.class_name() + str(len(self.node_names()))

    def write(self, node, node_path=None):
        """
        Write the node to disk at the given node path. If no node path is specified, write at the root level using the
        name given by self.default_name(). If a node path is specified, all but the final node must already exist.

        Parameters
        ----------
        node : Node
            The instance to write to disk.
        node_path : str
             The node path to the node that will contain this object.
        """
        if node_path is None:
            node_path = self.default_name(node)
        elif node_path == NODE_PATH_SEPARATOR:
            raise MeasurementError("Nothing may be written to the IO root.")
        validate_node_path(node_path)
        if node_path.startswith(NODE_PATH_SEPARATOR):
            absolute_node_path = node_path
        else:
            absolute_node_path = NODE_PATH_SEPARATOR + node_path
        self._write_node(node, absolute_node_path)
        logger.info("Wrote {} to node path {}".format(node.__class__.__name__, absolute_node_path))

    def read(self, node_path, translate=None, force=False):
        """
        Read a measurement from disk and return it.

        The `force` keyword is intended for inspecting measurements for which the data on disk does not match the class
        structure; see _instantiate().

        Parameters
        ----------
        node_path : str
            The path to the node to be loaded, in the form 'node0/node1/node2' or '/node0/node1/node2'.
        translate : dict
            A dictionary with entries 'original_class': 'new_class'; class names must be fully-qualified.
        force : bool
            If True, attempt to create the classes specified on disk even if the variables do not match.

        Returns
        -------
        Measurement
            The data stored to the given node, including all other measurements it contains.
        """
        validate_node_path(node_path)
        if node_path == NODE_PATH_SEPARATOR:
            raise MeasurementError("Nothing may be read from the IO root.")
        if not node_path.startswith(NODE_PATH_SEPARATOR):
            absolute_node_path = NODE_PATH_SEPARATOR + node_path
        else:
            absolute_node_path = node_path
        if translate is None:
            translate = {}
        return self._read_node(node_path=absolute_node_path, translate=translate, force=force)

    # The remaining public methods should be implemented by subclasses.
    # TODO: update comments, especially with exceptions raised and handling of private variables.

    def close(self):
        """
        Close open files.
        """
        pass

    def create_node(self, node_path):
        """
        Create a node at the end of the given path; all but the final node in the path must already exist.
        """
        pass

    def write_other(self, node_path, key, value):
        """
        Write value to node_path with name key; value should not be a numpy array.
        """
        pass

    def write_array(self, node_path, key, value, dimensions):
        """
        Write value, a numpy array, to node_path with name key.
        """
        pass

    def read_array(self, node_path, key):
        """
        Read array key from node_path.
        """
        pass

    def read_other(self, node_path, key):
        """
        Read non-array object with name key from node_path.
        """
        pass

    def node_names(self, node_path='/'):
        """
        Return the names of all nodes contained in the node at node_path.
        """
        pass

    def array_names(self, node_path):
        """
        Return the names of all arrays contained in the node at node_path.
        """
        pass

    def other_names(self, node_path):
        """
        Return the names of all other variables contained in the node at node_path.
        """
        pass

    # Private methods

    def __getattr__(self, item):
        if item in self.node_names():
            return self.read(item)
        else:
            raise AttributeError("Node name not found: {}".format(item))

    def __dir__(self):
        attrs = dir(self.__class__) + self.__dict__.keys() + self.node_names()
        return list(set([attr for attr in attrs if not attr.startswith('_')]))

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.root_path))

    def _write_node(self, node, node_path):
        """
        Write the data in node to a new node at the given node path.

        Parameters
        ----------
        node : Node
            This will usually be a subclass of Measurement or MeasurementList.
        node_path : str
            The path of the new node into which the instance will be written.
        """
        self.create_node(node_path)
        self.write_other(node_path, CLASS_NAME, node.class_name())
        if hasattr(node, '_version'):
            self.write_other(node_path, VERSION, getattr(node, '_version'))
        else:
            self.write_other(node_path, VERSION, None)
        for key, value in node.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, Node):
                    self._write_node(value, join(node_path, key))
                elif hasattr(node, 'dimensions') and key in node.dimensions:
                    pass  # Skip array writing on the first pass so that the dimensions can be created in order.
                else:
                    self.write_other(node_path, key, value)
        if isinstance(node, MeasurementList):
            for index, child in enumerate(node):
                self._write_node(child, join(node_path, str(index)))
        # Saving arrays in order allows the netCDF group to create the dimensions.
        if hasattr(node, 'dimensions'):
            for array_name, dimensions in node.dimensions.items():
                self.write_array(node_path, array_name, getattr(node, array_name), dimensions)
        # Update the node with information about how it was saved.
        node._io = self
        node._io_node_path = node_path

    def _read_node(self, node_path, translate, force):
        saved_class_name = self.read_other(node_path, CLASS_NAME)
        try:
            version = self.read_other(node_path, VERSION)
        except ValueError:
            version = None
        full_class_name = translate.get(saved_class_name, classes.full_name(saved_class_name, version))
        class_ = get_class(full_class_name)
        measurement_names = self.node_names(node_path)
        if issubclass(class_, MeasurementList):
            # Use the name of each measurement, which is an int, to restore the order in the sequence.
            contents = [self._read_node(join(node_path, measurement_name), translate, force)
                        for measurement_name in sorted(measurement_names, key=int)]
            node = class_(contents)
        else:
            variables = {}
            for measurement_name in measurement_names:
                variables[measurement_name] = self._read_node(join(node_path, measurement_name), translate, force)
            array_names = self.array_names(node_path)
            for array_name in array_names:
                variables[array_name] = self.read_array(node_path, array_name)
            for other_name in self.other_names(node_path):
                variables[other_name] = self.read_other(node_path, other_name)
            node = _instantiate(class_, variables, force)
        # Update the node with information about how it was loaded.
        node._io = self
        node._io_node_path = node_path
        return node


# Class-related functions

def get_class(full_class_name):
    module_name, class_name = full_class_name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


# ToDo: look at effect of None in number field, and handle it here
def from_series(series):
    io_class = get_class(classes.full_name(class_name=series[IO_CLASS_NAME], version=None))
    io = io_class(series[ROOT_PATH])
    node = io.read(series[NODE_PATH])
    if NUMBER in series and pd.notnull(series[NUMBER]):
        return node[series[NUMBER]]
    else:
        return node


def _instantiate(class_, variables, force):
    """
    Return a new instance of `class_` using the `variables` dict.

    If `force == True`, variables required by __init__() that are not present will be passed as None, and variables on
    disk that are not in the instantiation signature will be monkey-patched in after instantiation. Additionally,
    for measurements that have the `validate` argument (as all measurements that directly contain arrays should),
    it will be set to False to reduce the chance of errors. While this should work in many cases, it is not
    guaranteed to load arbitrary data successfully.

    If a forced instantiation still fails, many different errors could be raised.

    Parameters
    ----------
    class_ : type
        The class to instantiate.
    variables : dict
        A mapping from argument name to argument value.
    force : bool
        If True, attempt to force the measurement to instantiate; see IO.read().

    Raises
    ------
    MeasurementError
        If `force == False` and the keys of `variables` do not match the __init__() signature.

    Returns
    -------
    class_
        A new instance.
    """
    # The Measurement framework does not support varargs or keywords, so these should be None.
    args, varargs, keywords, defaults = inspect.getargspec(class_.__init__)
    # Populate this list from last to first.
    arg_values = []
    for arg, default in zip(reversed(args), reversed(defaults)):
        if arg == 'validate' and force:
            arg_values.append(False)  # Skip validation to increase the chances of success.
        else:
            arg_values.append(variables.get(arg, default))
    for arg in reversed(args[1:-len(defaults)]):  # Skip the first arg, which is 'self'.
        try:
            arg_values.append(variables[arg])
        except KeyError:
            if force:
                arg_values.append(None)
            else:
                raise MeasurementError("A required argument is not present on disk: {}".format(arg))
    instance = class_(*reversed(arg_values))
    extras = set(variables.keys()) - set(args)
    if force:
        for key in extras:
            setattr(instance, key, variables[key])  # Monkey-patch.
    else:
        if extras:
            raise MeasurementError("Extra values are present on disk: {}".format(extras))
    return instance

# Node-related functions

def join(node_path, *node_paths):
    """
    Join the given node paths into a single path. The code is copied from os.path.join().

    Note that the last path in *node_paths that is absolute will replace node_path as the base, and subsequent paths
    will be appended to it. This function does not test validity of either the inputs or output.

    Parameters
    ----------
    node_path : str
        The base of the node path.
    node_paths : iterable of str
        Additional node paths to join to the base.

    Returns
    -------
    str
        The joined node path.
    """
    path = node_path
    for p in node_paths:
        if p.startswith(NODE_PATH_SEPARATOR):
            path = p
        elif path == '' or path.endswith(NODE_PATH_SEPARATOR):
            path += p
        else:
            path += NODE_PATH_SEPARATOR + p
    return path


def split(node_path):
    """
    Split the given node path into a (head, tail) tuple, either element of which may be empty. The code is copied from
    os.path.split().
    Examples:
    split('one/two/three') ->  ('one/two', 'three')
    split('/one') -> ('/', 'one')
    split('/') -> ('/', '')
    This function does not test validity of either the inputs or outputs.

    Parameters
    ----------
    node_path : str
        The node path to split.

    Returns
    -------
    (str, str)
        head, tail are respectively the path except for the last node and the last node.
    """
    last_separator_index = node_path.rfind(NODE_PATH_SEPARATOR) + 1
    head, tail = node_path[:last_separator_index], node_path[last_separator_index:]
    if head and head != NODE_PATH_SEPARATOR * len(head):
        head = head.rstrip(NODE_PATH_SEPARATOR)
    return head, tail


def explode(node_path):
    """
    Return a list of the node names in the given node path with the node separator removed. Empty names are dropped.
    Examples:
    explode('one/two/three') -> ['one', 'two', 'three']
    explode('/one') -> ['one']
    explode('//') -> []


    Parameters
    ----------
    node_path : str
       The node path to explode into individual nodes.

    Returns
    -------
    list
       A list of strings that are the individual nodes in the path.
    """
    if node_path.startswith(NODE_PATH_SEPARATOR):  # Avoid an empty string at the start for valid absolute paths.
        node_path = node_path[1:]
    if not node_path:
        return []
    else:
        return node_path.split(NODE_PATH_SEPARATOR)


def validate_node_path(node_path):
    """
    Raise an exception if the given node path is not correctly formed. A valid node path is a string sequence of zero or
    more valid node names separated by slashes; an otherwise valid node path may or may not also begin with a slash. A
    valid node name is either a valid Python variable or a nonnegative integer.

    Note that, unlike a unix path, a valid node path may not end with the node path separator unless it is the root.

    Parameters
    ----------
    node_path : str
        The node path to validate.

    Returns
    -------
    None

    Raises
    ------
    MeasurementError
        if the given node path is not valid.
    """
    if not node_path:
        raise MeasurementError("Empty node path.")
    if node_path != NODE_PATH_SEPARATOR:
        for node in explode(node_path):
            if not node:
                raise MeasurementError("Empty node in {}".format(node_path))
            elif re.match(r'[0-9]*$|[_a-zA-Z][_a-zA-Z0-9]*$', node) is None:
                raise MeasurementError("Invalid node {} in {}".format(node, node_path))
