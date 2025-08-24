"""FiLe OPerationS"""

import mimetypes
import pathlib

import magic

DEFAULT_BUFSIZE = 4096


def path_exists(fname):
    """
    Whether the path points to an existing file or directory
    :param fname:
    :return:
    """
    return pathlib.Path(fname).exists()


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
