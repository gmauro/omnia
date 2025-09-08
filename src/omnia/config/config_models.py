from pydantic import BaseModel, Field, ValidationInfo, field_validator


class MongoDBOptions(BaseModel):
    connectTimeoutMS: int = Field(..., description="Connection timeout in milliseconds")
    socketTimeoutMS: int = Field(..., description="Socket timeout in milliseconds")
    retryWrites: str = Field(..., description="Whether to retry writes")
    w: str | None = Field(None, description="Write concern")
    appName: str | None = Field(None, description="Application name")


class MongoDBProfile(BaseModel):
    prefix: str = Field(..., description="MongoDB connection prefix")
    host: str = Field(..., description="MongoDB host")
    port: int | None = Field(None, description="MongoDB port")
    username: str | None = Field(None, description="MongoDB username")
    password: str | None = Field(None, description="MongoDB password")
    database: str = Field(..., description="MongoDB database name")
    options: MongoDBOptions = Field(..., description="MongoDB connection options")


class Configuration(BaseModel):
    default_profile: str = Field(..., description="Default profile to use")
    profiles: dict[str, "MongoDBProfile"] = Field(..., description="Dictionary of MongoDB profiles")

    @field_validator("default_profile")
    def validate_default_profile(cls, v: str, info: "ValidationInfo") -> str:
        if (
            hasattr(info, "data")
            and info.data is not None
            and "profiles" in info.data
            and v not in info.data["profiles"]
        ):
            raise ValueError(f"Default profile '{v}' not found in profiles")
        return v
