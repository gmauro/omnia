import json
import urllib

from bson import json_util
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient


def create_app(mongo_uri: str, database_name: str):
    app = FastAPI()

    def parse_uri(uri: str) -> tuple[str, str, str]:
        try:
            parsed = urllib.parse.urlparse(uri)
            scheme, netloc, path = parsed.scheme, parsed.netloc, parsed.path
            if scheme in ["http", "https"]:
                path = path.strip("/")
            return scheme, netloc, path
        except ValueError as e:
            raise ValueError(f"Invalid URI: {uri}") from e

    scheme, netloc, path = parse_uri(mongo_uri)
    # Connect to MongoDB
    uri = "://".join([scheme, netloc])
    database_name = path.strip("/")
    client = MongoClient(uri)
    db = client[database_name]

    @app.get("/collections")
    async def get_collections():
        collections = db["data_catalogs"]  # db.list_collection_names()
        documents = list(collections.find({}, {"name": 1, "_id": 0}))
        return json.loads(json_util.dumps(documents))  # {"collections": collections}

    @app.get("/collections/{collection_name}")
    async def get_collection(collection_name: str):
        collection = db["data_catalogs"]
        documents = list(
            collection.find(
                {"name": collection_name},
                {"name": 1, "type": 1, "keywords": 1, "date_created": 1, "date_modified": 1, "_id": 0},
            )
        )  #
        return json.loads(json_util.dumps(documents))

    # @app.get("/collections/{collection_name}/contents")
    # async def get_documents(collection_name: str):
    #     collection_dc = db['data_catalogs']
    #     documents_dc = collection_dc.find({"name": collection_name})
    #
    #     collection_ds = db['datasets']
    #     documents_ds = list(collection_ds.find({"included_in_datacatalog": documents_dc}))
    #
    #
    #     return json.loads(json_util.dumps(documents_dc))

    # @app.get("/collections/{collection_name}/contents")
    # async def get_data_objects_by_catalog_name(catalog_name: str):
    #     """Get all data objects included in a data catalog by catalog name."""
    #     # Find the data catalog by name
    #     catalog = Datacatalog.objects(name=catalog_name).first()
    #
    #     if not catalog:
    #         raise HTTPException(status_code=404, detail="Data catalog not found")
    #
    #     # Find all data objects included in the data catalog
    #     data_objects = Dataset.objects(included_in_datacatalog=catalog)
    #
    #     # Convert the datasets to a list of dictionaries
    #     result = []
    #     for dataset in data_objects:
    #         result.append({
    #             "id": str(dataset.id),
    #             "uk": dataset.uk,
    #             "path": dataset.path,
    #             "protocol": dataset.protocol,
    #             "host": dataset.host,
    #             "size": dataset.size,
    #             "encoding_format": dataset.encoding_format,
    #             "date_created": dataset.date_created.isoformat() if dataset.date_created else None,
    #             "date_modified": dataset.date_modified.isoformat() if dataset.date_modified else None
    #         })
    #
    #     return result

    # @app.post("/collections/{collection_name}")
    # async def insert_document(collection_name: str, request: Request):
    #     collection = db[collection_name]
    #     data = await request.json()
    #     result = collection.insert_one(data)
    #     return {"inserted_id": str(result.inserted_id)}
    #
    # @app.put("/collections/{collection_name}/{document_id}")
    # async def update_document(collection_name: str, document_id: str, request: Request):
    #     collection = db[collection_name]
    #     data = await request.json()
    #     result = collection.update_one({"_id": ObjectId(document_id)}, {"$set": data})
    #     if result.modified_count == 0:
    #         raise HTTPException(status_code=404, detail="Document not found")
    #     return {"modified_count": result.modified_count}
    #
    # @app.delete("/collections/{collection_name}/{document_id}")
    # async def delete_document(collection_name: str, document_id: str):
    #     collection = db[collection_name]
    #     result = collection.delete_one({"_id": ObjectId(document_id)})
    #     if result.deleted_count == 0:
    #         raise HTTPException(status_code=404, detail="Document not found")
    #     return {"deleted_count": result.deleted_count}

    @app.get("/collections/{collection_name}/path/{path:path}")
    async def get_document_by_path(collection_name: str, path: str):
        collection = db[collection_name]
        document = collection.find_one({"path": path}, {"path": 1, "mimetype": 1, "_id": 0})
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return json.loads(json_util.dumps(document))

    return app
