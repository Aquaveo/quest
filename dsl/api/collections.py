"""API functions related to Collections

"""
from __future__ import print_function
import datetime
from jsonrpc import dispatcher
from .. import util
import os
import shutil
import yaml

COLLECTION_METADATA_FILE = 'dsl.yml'

@dispatcher.add_method
def get_collections(filters=None):
    """Get list of available collections.

    Collections are folders on the local disk that contain downloaded or created data
    along with associated metadata.

    Returns
    -------
    collections : dict,
        A python dict representation of the list of available collections 
    """
    collections = {}
    for uid, path in _load_collections().iteritems():
        if not os.path.isabs(path):
            path = os.path.join(util.get_data_dir(), path)

        metadata = _load_collection(uid)['metadata']
        metadata.update({
            'uid': uid,
            'absolute_path': path,
        })
        collections[uid] = metadata
    return collections


@dispatcher.add_method     
def new_collection(uid, display_name=None, metadata={}, path=None):
    """Create a new collection

    Create a new collection by creating a new folder and placing a json
    file in the folder for dsl metadata and adding a reference to the 
    master collections metadata folder.

    Parameters
    ----------
    name : str,
        The name of the collection
    metadata : ``dict`` containing optional metadata values
    path: ``None`` or str,
        If ``None`` use default dsl location for collections otherwise use specified path. 

    Returns
    -------
    collection : dict,
        A python dict representation of the collection in the format {uid: metadata}
    """

    uid = uid.lower()
    collections = _load_collections()
    if uid in collections.keys():
        raise ValueError('Collection %s already exists, please use a unique name', uid)

    if path is None:
        path = uid
        abs_path = os.path.join(util.get_data_dir(), path)
    else:
        abs_path = path

    util.mkdir_if_doesnt_exist(abs_path)

    collections.update({uid: path})
    _write_collections(collections)
    
    metadata.update({
        'display_name': metadata.get('display_name', uid),
        'description': metadata.get('description', None),
        'created_on': datetime.datetime.now().isoformat(),
    })
    collection = {'metadata': metadata, 'features': None}
    _write_collection(uid, collection)

    return collection


@dispatcher.add_method
def update_collection(uid, metadata):
    """Update metadata of collection.
    """
    collections = _load_collections()

    if uid not in list(collections.keys()):
        print('Collection not found')
        return {}

    collections[uid].update(metadata)
    _write_collections(collections)
    return collections[uid]


@dispatcher.add_method
def delete_collection(uid, delete_data=False):
    """delete a collection

    Deletes a collection from the collections metadata file.
    Optionally deletes all data under collection.

    Parameters
    ----------
    name : str,
        The name of the collection

    delete_data : bool,
        if True all data in the collection will be deleted

    Returns
    -------
    collections : dict,
        A python dict representation of the list of available collections, 
        the updated collections list is also written to a json file.
    """
    collections = _load_collections()

    if uid not in list(collections.keys()):
        print('Collection not found')
        return collections

    if delete_data:
        path = collections[uid]['path']
        if os.path.exists(path):
            print('deleting all data under path:', path)
            shutil.rmtree(path)

    print('removing %s from collections' % uid)
    del collections[uid]
    _write_collections(collections)
    return collections


def _get_collection_file(uid):
    collections = _load_collections()
    if uid not in collections.keys():
        raise ValueError('Collection %s not found' % uid)

    path = collections[uid]

    if not os.path.isabs(path):
        path = os.path.join(util.get_data_dir(), path)

    return os.path.join(path, 'dsl.yml')


def _load_collection(uid):
    """load collection

    """
    path = _get_collection_file(uid)

    if not os.path.exists(path):
        return {}
    
    with open(path) as f:
        return yaml.safe_load(f)


def _load_collections():
    """load list of collections

    """
    path = util.get_collections_index()

    if not os.path.exists(path):
        return {}

    with open(path) as f:
        return yaml.safe_load(f)


def _write_collection(uid, collection):
    """write collection

    """
    with open(_get_collection_file(uid), 'w') as f:
        yaml.dump(collection, f, default_flow_style=False)


def _write_collections(collections):
    """write list of collections to  file 
    """
    path = util.get_collections_index()
    with open(path, 'w') as f:
        yaml.dump(collections, f, default_flow_style=False)
