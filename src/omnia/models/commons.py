import json

from mongoengine import StringField, ValidationError

PROTOCOLS = ("posix", "s3", "https")


class JSONField(StringField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_mongo(self, value):
        if value is not None:
            try:
                return json.dumps(value)
            except TypeError as e:
                raise ValidationError(f"Invalid JSON value: {e}") from e
        return value

    def to_python(self, value):
        if value is not None and isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON string: {e}") from e
        return value

    def validate(self, value):
        if value is not None and not isinstance(value, str | dict | list):
            raise ValidationError("Invalid JSON value")
