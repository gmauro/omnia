import datetime
import json
from typing import Any

from mongoengine.errors import NotUniqueError
from mongoengine.queryset.visitor import Q

from omnia import logger


def find_item(obj: dict, key: str) -> Any:
    """
    Recursively search for a specific key in a dictionary.

    Args:
        obj (Dict): The dictionary to search in.
        key (str): The key to search for.

    Returns:
        Any: The value associated with the key if found, otherwise None.

    Notes:
        This function searches for the key in the dictionary and its nested dictionaries.
        If the key is found, the function returns the associated value.
        If the key is not found, the function returns None.

    """
    if key in obj:
        return obj[key]
    else:
        for _k, v in obj.items():
            if isinstance(v, dict):
                result = find_item(v, key)
                if result is not None:
                    return result
        return None


class MongoMixin:
    def __init_subclass__(cls, **kwargs):
        required_attrs = ["mdb_obj", "klass", "pk", "unique_key", "unique_key_dict"]
        missing_attrs = [attr for attr in required_attrs if not hasattr(cls, attr)]
        if missing_attrs:
            raise AttributeError(f"Class {cls.__name__} is missing required attributes: {', '.join(missing_attrs)}")
        super().__init_subclass__(**kwargs)

    @property
    def is_mapped(self) -> bool:
        count = self.klass.objects(**self.unique_key_dict).count()
        if count == 1:
            logger.debug(f" {count} {self.klass.__name__} found")
            return True
        logger.debug(f" {count} {self.klass.__name__} found")
        return False

    def delete(self) -> None:
        """
        Delete the Document from the database and unmap the local object.
        This will only take effect if the document has been previously saved.
        """
        if self.is_mapped:
            self.mdb_obj.delete()
            logger.info(f"{self.unique_key} deleted")
            self.mdb_obj.id = None

    def map(self):
        """
        Maps the current object to an existing object in the database if found.

        Returns:
            The current object if a unique match is found, otherwise None.
        """
        objs = self.klass.objects(**self.unique_key_dict)
        #  len() is much slower than count()
        count = objs.count()
        if count == 1:
            logger.debug(f"Mapping, {count} {self.klass.__name__} found")

            # Reload object fields from the db object
            obj_fields = {key: getattr(objs[0], key) for key, value in self.mdb_obj._fields.items()}

            for key, value in obj_fields.items():
                logger.debug(f"Setting read-only field: {key}")
                setattr(self.mdb_obj, key, value)

            return self
        return None

    def save(self, **kwargs):
        """
        Save the Document to the database. If the document already exists,
        it will be updated, otherwise it will be created.
        force_update – Update an existing document

        Returns the saved object instance.
        """
        force_update = kwargs.pop("force_update", False)
        try:
            self.mdb_obj.save(**kwargs)
            logger.info(f"{self.unique_key} saved")
        except NotUniqueError:
            if force_update:
                if self.update():
                    logger.warning(f"{self.unique_key} updated, as it was not a unique ID")
            else:
                logger.error(f"{self.unique_key} already exists. Did you mean to edit it?")

    def view(self) -> dict:
        """
        Return object's detail in JSON format
        """
        detail = {}
        if self.ensure_is_mapped("view"):
            detail = self.klass.objects(id=self.pk).as_pymongo()[0]
            logger.debug(detail)
        return detail

    def query(self, case_sensitive=False, **kwargs) -> list[dict]:
        """
        Queries the database based on the provided keyword arguments.

        Args:
            case_sensitive (bool, optional): Whether the query should be case-sensitive. Defaults to True.
            **kwargs: Additional keyword arguments to filter the query results.

        Returns:
            list: A list of query results.
        """
        operators = {"case_insensitive": ["iexact", "icontains"], "case_sensitive": ["exact", "contains"]}
        exact_op, contains_op = operators["case_sensitive" if case_sensitive else "case_insensitive"]

        docs = []
        if not kwargs:
            return []

        jds = {field: kwargs.pop(field, {}) for field in self.klass.json_dict_fields() if field in kwargs}

        # Compose queries from data_ids list, if any.
        queries = [Q(**{f"data_id__{exact_op}": value}) for value in kwargs.pop("data_ids", [])]

        # Compose queries from regular key value pairs in the yaml file.
        query_fields_exact = {f"{key}__{exact_op}": value for key, value in kwargs.items()}
        if query_fields_exact:
            queries.append(Q(**query_fields_exact))
        logger.debug(queries)

        if len(jds.keys()) > 0:
            for jdk, jdv in jds.items():
                query_fields_contains = {f"{jdk}__{contains_op}.{key}": value for key, value in jdv.items()}

                for key, value in query_fields_contains.items():
                    query_field_contains = key.split(".")[0]
                    queries.append(Q(**{query_field_contains: value}))

                # Use & operator to combine all the queries with AND logic
                # query_args = reduce(lambda x, y: x & y, queries)
                query_args = Q()
                for q in queries:
                    query_args = query_args & q
                logger.debug(query_args)
                docs.extend(
                    qr
                    for qr in self.klass.objects(query_args).as_pymongo()
                    if value.casefold() in find_item(json.loads(qr[jdk]), key.split(".").pop()).casefold()
                )
        else:
            for query_arg in queries:
                logger.debug(query_arg)
                docs.extend(qr for qr in self.klass.objects(query_arg).as_pymongo())
        logger.debug(f"found {len(docs)} documents")

        return docs

    def update(self) -> bool:
        """
        Perform an atomic update of the document in the database and reload the document
        using the updated version.

        Returns:
            bool: True if the document was updated successfully, False if the document
                  in the database doesn't match the query or if mapping is not ensured.
        """
        if not self.is_mapped:
            logger.debug(f"Mapping not ensured, cannot update document {self.unique_key}")
            return False

        self.mdb_obj.modification_date = datetime.datetime.now()
        update_result = self.mdb_obj.save()

        if update_result:
            logger.info(f"{self.unique_key} modified")
        else:
            logger.info(f"Failed to update document {self.unique_key}")

        return update_result
