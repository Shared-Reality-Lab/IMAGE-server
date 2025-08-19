"""
Simple validator module for IMAGE project components.
Provides a lightweight validator class for JSON schema validation.
"""

import json
import logging
import jsonschema

PREPROCESSOR_RESPONSE_SCHEMA = './schemas/preprocessor-response.schema.json'
DEFINITIONS_SCHEMA = './schemas/definitions.json'
REQUEST_SCHEMA = './schemas/request.schema.json'


class Validator:
    """Lightweight validator for schema validation with consistent logging."""

    def __init__(
        self,
        data_schema: str,
        request_schema: str = REQUEST_SCHEMA,
        response_schema: str = PREPROCESSOR_RESPONSE_SCHEMA,
        definitions_schema: str = DEFINITIONS_SCHEMA
    ):
        self.data_schema_path = data_schema
        self.request_schema_path = request_schema
        self.response_schema_path = response_schema
        self.definitions_schema_path = definitions_schema

        self._load_schemas()
        self._setup_resolver()

    def _load_schemas(self):
        """Load all required schemas."""
        try:
            with open(self.data_schema_path) as f:
                self.data_schema = json.load(f)

            with open(self.response_schema_path) as f:
                self.response_schema = json.load(f)

            with open(self.request_schema_path) as f:
                self.request_schema = json.load(f)

            with open(self.definitions_schema_path) as f:
                self.definitions_schema = json.load(f)

            logging.debug("All schemas loaded successfully")

        except FileNotFoundError as e:
            logging.error(f"Schema file not found: {e}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in schema file: {e}")
            raise

    def _setup_resolver(self):
        """Setup JSON schema resolver for handling $ref references."""
        schema_store = {
            self.response_schema['$id']: self.response_schema,
            self.definitions_schema['$id']: self.definitions_schema,
            self.request_schema['$id']: self.request_schema,
            self.data_schema['$id']: self.data_schema
        }

        self.resolver = jsonschema.RefResolver.from_schema(
            self.response_schema, store=schema_store
        )
        logging.debug("Schema resolver initialized")

    def validate_request(self, data):
        """
        Validate request data.

        Args:
            data: Request data to validate

        Raises:
            jsonschema.exceptions.ValidationError: If validation fails
        """
        try:
            validator = jsonschema.Draft7Validator(
                self.request_schema,
                resolver=self.resolver
                )
            validator.validate(data)
            logging.debug("Request validation successful")
        except jsonschema.exceptions.ValidationError as e:
            logging.error("Validation failed for incoming request")
            logging.pii(f"Validation error: {e.message} | Data: {data}")
            raise

    def validate_data(self, data):
        """
        Validate processed data.

        Args:
            data: Processed data to validate

        Raises:
            jsonschema.exceptions.ValidationError: If validation fails
        """
        try:
            validator = jsonschema.Draft7Validator(self.data_schema)
            validator.validate(data)
            logging.debug("Data validation successful")
        except jsonschema.exceptions.ValidationError as e:
            logging.error("Validation failed for output data")
            logging.pii(f"Validation error: {e.message} | Data: {data}")
            raise

    def validate_response(self, data):
        """
        Validate final response.

        Args:
            data: Response data to validate

        Raises:
            jsonschema.exceptions.ValidationError: If validation fails
        """
        try:
            validator = jsonschema.Draft7Validator(
                self.response_schema,
                resolver=self.resolver
                )
            validator.validate(data)
            logging.debug("Response validation successful")
        except jsonschema.exceptions.ValidationError as e:
            logging.error("Validation failed for full response")
            logging.pii(f"Validation error: {e.message} | Response: {data}")
            raise
