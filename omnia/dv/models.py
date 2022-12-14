""" Mongo's models """
import datetime
import platform

from comoda import a_logger
from mongoengine import (
    DateTimeField,
    Document,
    IntField,
    ListField,
    StringField,
)

from omnia import log_file
from omnia.utils import compute_sha256, get_file_size, guess_mimetype


class DataObject(Document):
    prefixes = ("posix", "s3", "https")

    checksum = StringField()
    collections = ListField(StringField(max_length=30))
    date_modified = DateTimeField(default=datetime.datetime.now())
    description = StringField(max_length=200)
    file_size = IntField()
    host = StringField(required=True, unique_with="path")
    mimetype = StringField()
    path = StringField(required=True)
    prefix = StringField(choices=prefixes)
    tags = ListField(StringField(max_length=30))

    meta = {"allow_inheritance": True}


class PosixDataObject:
    def __init__(
        self,
        logger=None,
        logfile=log_file,
        loglevel="INFO",
        mec=None,
        path=None,
        host=None,
        collections=None,
    ):
        _prefix = "posix"
        _host = host if host is not None else platform.node()
        self.logger = logger
        if logger is None:
            self.logger = a_logger(
                self.__class__.__name__, level=loglevel, filename=logfile
            )

        self.mec = mec
        self.dobj = DataObject(
            collections=collections, path=path, prefix=_prefix, host=_host
        )
        self.dobj._meta["db_alias"] = self.mec.alias

    @property
    def id(self):
        return self.dobj.id

    @property
    def checksum(self):
        return self.dobj.checksum

    @checksum.setter
    def checksum(self, c):
        self.dobj.checksum = c

    @property
    def collections(self):
        return self.dobj.collections

    @collections.setter
    def collections(self, cs):
        for c in cs:
            if c not in self.dobj.collections:
                self.dobj.collections.append(c)

    @property
    def file_size(self):
        return self.dobj.file_size

    @file_size.setter
    def file_size(self, s):
        self.dobj.file_size = s

    @property
    def mimetype(self):
        return self.dobj.mimetype

    @mimetype.setter
    def mimetype(self, m):
        self.dobj.mimetype = m

    @property
    def tags(self):
        return self.dobj.tags

    @tags.setter
    def tags(self, tags):
        for tag in tags:
            if tag not in self.dobj.tags:
                self.dobj.tags.append(tag)

    @property
    def unique_key(self):
        return ":".join([self.dobj.host, self.dobj.path])

    @property
    def is_mapped(self):
        with self.mec:
            objs = DataObject.objects(path=self.dobj.path, host=self.dobj.host)
            return (
                False if (objs.count()) <= 0 or self.dobj.id is None else True
            )

    @property
    def is_connected(self):
        return False if self.mec is None else True

    def compute(self):
        """
        Retrieve object's detail
        """
        self.dobj.checksum = compute_sha256(self.dobj.path)
        self.dobj.file_size = get_file_size(self.dobj.path)
        self.dobj.mimetype = guess_mimetype(self.dobj.path)

        self.logger.debug(
            "computed: {}, {}, {}".format(
                self.dobj.file_size, self.dobj.mimetype, self.dobj.checksum
            )
        )

    def delete(self, **kwargs):
        """
        Delete the Document from the database and unmap the local object.
        This will only take effect if the document has been previously saved.
        """
        if self.ensure_is_mapped("delete"):
            with self.mec:
                self.dobj.delete(**kwargs)
                self.logger.info("{} deleted".format(self.unique_key))
            self.dobj.id = None

    def ensure_is_mapped(self, op=None):
        if self.map():
            return True
        else:
            self.logger.warning(
                "Document {} does not exist on remote, "
                "skipping {} operation".format(self.unique_key, op)
            )
            return False

    def map(self):
        with self.mec:
            objs = DataObject.objects(path=self.dobj.path, host=self.dobj.host)
            if (objs.count()) == 1:
                msg = "mapping, {} DataObject found".format(len(objs))
                self.logger.debug(msg)
                self.dobj.id = objs[0].id
                return True
            return False

    def reload(self, **kwargs):
        """
        Reloads all attributes from the database.
        """
        if self.ensure_is_mapped("reload"):
            with self.mec:
                self.dobj.reload(**kwargs)
            self.logger.info("{} reloaded".format(self.unique_key))

    def modify(self, **kwargs):
        """
        Perform an atomic update of the document in the database and
        reload the document object using updated version.

        Returns True if the document has been updated or False if the document
        in the database doesn???t match the query.
        """
        result = False
        if self.ensure_is_mapped("modify"):
            if len(kwargs) > 0:
                with self.mec:
                    result = self.dobj.modify(**kwargs)
                    self.logger.info("{} modified".format(self.unique_key))
            else:
                self.logger.warning(
                    "No update parameters, " "skipping the operation"
                )
        return result

    def view(self):
        """
        Return object's detail in JSON format
        """
        desc = []
        if self.ensure_is_mapped("view"):
            with self.mec:
                desc = DataObject.objects(id=self.id).as_pymongo()
                self.logger.debug(desc)
        return desc

    def save(self, **kwargs):
        """
        Save the Document to the database. If the document already exists,
        it will be updated, otherwise it will be created.
        Returns the saved object instance.
        :param kwargs:
        :return: DataObject
        """
        if not self.is_mapped:
            self.map()
        with self.mec:
            self.dobj.save(**kwargs)
        self.logger.info("{} saved".format(self.dobj.id))
