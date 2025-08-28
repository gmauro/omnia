import json
import urllib

from bson import ObjectId, json_util
from fastapi import FastAPI, HTTPException, Request
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
        collections = db.list_collection_names()
        return {"collections": collections}

    @app.get("/collections/{collection_name}")
    async def get_documents(collection_name: str):
        collection = db[collection_name]
        documents = list(collection.find({}, {"path": 1, "mimetype": 1, "_id": 0}))
        return json.loads(json_util.dumps(documents))

    @app.post("/collections/{collection_name}")
    async def insert_document(collection_name: str, request: Request):
        collection = db[collection_name]
        data = await request.json()
        result = collection.insert_one(data)
        return {"inserted_id": str(result.inserted_id)}

    @app.put("/collections/{collection_name}/{document_id}")
    async def update_document(collection_name: str, document_id: str, request: Request):
        collection = db[collection_name]
        data = await request.json()
        result = collection.update_one({"_id": ObjectId(document_id)}, {"$set": data})
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"modified_count": result.modified_count}

    @app.delete("/collections/{collection_name}/{document_id}")
    async def delete_document(collection_name: str, document_id: str):
        collection = db[collection_name]
        result = collection.delete_one({"_id": ObjectId(document_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"deleted_count": result.deleted_count}

    @app.get("/collections/{collection_name}/path/{path:path}")
    async def get_document_by_path(collection_name: str, path: str):
        collection = db[collection_name]
        document = collection.find_one({"path": path}, {"path": 1, "mimetype": 1, "_id": 0})
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return json.loads(json_util.dumps(document))

    return app
