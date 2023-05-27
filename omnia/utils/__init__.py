"""
Generic Utilities
=================
Generic utilities used by other modules.
"""

import hashlib
import mimetypes
import pathlib
import re

import magic

DEFAULT_BUFSIZE = 4096


def path_exists(fname):
    """
    Whether the path points to an existing file or directory
    :param fname:
    :return:
    """
    return pathlib.Path(fname).exists()


# https://docs.python.org/3/library/hashlib.html#file-hashing
def compute_sha256(fname, bufsize=DEFAULT_BUFSIZE):
    """
    Computes file's hash using sha256 algorithm
    """
    sha256 = hashlib.sha256()
    with open(fname, "rb") as fi:
        s = fi.read(bufsize)
        while s:
            sha256.update(s)
            s = fi.read(bufsize)
    return sha256.hexdigest()


def guess_mimetype(fname):
    """
    Identifies file types
    :param fname: filename
    :return: mimetype and encoding as strings
    """
    mime_type, encoding = mimetypes.guess_type(fname)
    if mime_type is None:
        mime_type = magic.from_file(fname, mime=True)
    return mime_type


def get_file_size(fname):
    """
    Gets file's size
    :param fname: filename as string
    :return: file's size as integer
    """
    return pathlib.PosixPath(fname).stat().st_size


def is_a_valid_identifier(prefix, identifier):
    regex = "^{}[_][0-9]+".format(prefix)
    if not re.match(regex, identifier):
        raise ValueError("{} is not a valid identifier".format(identifier))
    return identifier
