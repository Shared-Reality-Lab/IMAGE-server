# Copyright (c) 2025 IMAGE Project, Shared Reality Lab, McGill University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

"""
OpenAI-compatible LLM client utilities for the IMAGE project.
Provides a generic interface for all LLM interactions.
"""

import os
import json
import logging
from openai import OpenAI
from typing import Optional, Dict, Any, Union


class LLMClient:
    """Generic wrapper for OpenAI-compatible API clients."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize the LLM client with configuration from environment
        or parameters.

        Args:
            api_key: API key for the LLM service (defaults to env LLM_API_KEY)
            base_url: Base URL for the API (defaults to env LLM_URL)
            model: Model name to use (defaults to env LLM_MODEL)
        """
        self.api_key = api_key or os.environ.get('LLM_API_KEY')
        self.base_url = base_url or os.environ.get('LLM_URL')
        self.model = model or os.environ.get('LLM_MODEL')

        if not self.api_key:
            logging.error("LLM API key not provided or found in environment")
            raise ValueError("LLM_API_KEY environment variable not set")

        logging.debug(f"Using LLM model: {self.model}")
        logging.debug(f"Using LLM base URL: {self.base_url}")
        logging.debug(f"API Key starts with: {self.api_key[:5]}...")

        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logging.debug("OpenAI client initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize OpenAI client: {e}")
            raise

    def chat_completion(
        self,
        prompt: str,
        image_base64: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        schema_name: str = "response-format",
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        system_prompt: Optional[str] = None,
        parse_json: bool = False,
        return_token_info=False,
        **kwargs
    ) -> Union[str, Dict[str, Any], None]:
        """
        Generic chat completion method that handles all LLM interactions.

        Args:
            prompt: The main prompt text
            image_base64: Optional base64 encoded image
                (without data URI prefix)
            json_schema: Optional JSON schema for structured output
                (e.g., from Pydantic model.model_json_schema())
            schema_name: Name for the JSON schema (default: "response-format")
            temperature: Temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format
                (e.g., {"type": "json_object"})
            system_prompt: Optional system message
            parse_json: If True, attempt to parse response as JSON
            return_token_info: If True, return tuple of (response, token_info)
            **kwargs: Additional parameters to pass to the API

        Returns:
            - String response if parse_json=False
            - Parsed dict if parse_json=True and parsing succeeds
            - None if the request fails
        """
        try:
            # compose response format from Pydantic model if provided
            if json_schema:
                # Set up structured output response format
                response_format = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "schema": json_schema
                    }
                }

                # parse output JSON
                parse_json = True

            # Build messages list
            messages = []

            # Add system prompt if provided
            if system_prompt:
                messages.append(
                    {"role": "system",
                     "content": system_prompt}
                     )

            # Build user message content
            user_content = []
            user_content.append({"type": "text", "text": prompt})

            # Add image if provided
            if image_base64:
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                })

            messages.append({"role": "user", "content": user_content})

            logging.pii(messages)

            # Build API call parameters
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature
            }

            # Add optional parameters
            if max_tokens:
                params["max_tokens"] = max_tokens
            if response_format:
                params["response_format"] = response_format

            # Add any additional kwargs
            params.update(kwargs)

            logging.debug(f"Making LLM request to model: {self.model}")
            response = self.client.chat.completions.create(**params)

            # Validate and extract response
            response_text = self._validate_response(response)
            if response_text is None:
                return None

            # Parse JSON if requested
            if parse_json:
                result = self._parse_json_response(response_text)
            else:
                result = response_text

            self.last_token_usage = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }

            if return_token_info:
                return result, self.last_token_usage
            else:
                return result

        except Exception as e:
            logging.error(f"Error in chat_completion: {e}", exc_info=True)
            return None

    def _validate_response(self, response) -> Optional[str]:
        """
        Validates the OpenAI API response and extracts the content.

        Args:
            response: OpenAI API response object

        Returns:
            Extracted content string or None if validation fails
        """
        try:
            if not response.choices:
                logging.error("LLM response missing choices")
                return None

            choice = response.choices[0]

            if choice.finish_reason not in ["stop", "length"]:
                logging.error(
                    f"Generation stopped with reason: {choice.finish_reason}"
                )
                return None

            if not choice.message or not choice.message.content:
                logging.error("LLM response missing message content")
                return None

            logging.debug("LLM response validation successful")
            return choice.message.content

        except Exception as e:
            logging.error(f"Error validating LLM response: {e}")
            return None

    def _parse_json_response(
            self,
            response_text: str
            ) -> Optional[Dict[str, Any]]:
        """
        Parse a JSON response, handling common formatting issues.

        Args:
            response_text: Raw response text from LLM

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        try:
            # Clean up potential markdown formatting
            cleaned_text = response_text.strip()

            # Remove markdown code blocks
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]

            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]

            cleaned_text = cleaned_text.strip()

            # Parse JSON
            parsed_json = json.loads(cleaned_text)
            logging.debug("Successfully parsed JSON response")
            logging.pii(f"Parsed JSON: {parsed_json}")

            return parsed_json

        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON response: {e}")
            logging.pii(f"Response that failed to parse: {response_text}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error parsing JSON: {e}")
            return None

    def warmup(self) -> bool:
        """
        Warm up the LLM with a minimal dummy request.

        Returns:
            True if warmup successful, False otherwise
        """
        try:
            logging.info("Warming up LLM...")

            # Create a minimal dummy image
            import base64
            from PIL import Image
            from io import BytesIO

            dummy_img = Image.new("RGB", (64, 64), color="white")
            buffered = BytesIO()
            dummy_img.save(buffered, format="PNG")
            dummy_base64 = base64.b64encode(
                buffered.getvalue()).decode('utf-8'
                                            )

            # Make a minimal request
            response = self.chat_completion(
                prompt="Describe this image in one word.",
                image_base64=dummy_base64,
                temperature=0.1,
                max_tokens=10
            )

            if response:
                logging.info("LLM warmup successful")
                return True
            else:
                logging.error("LLM warmup failed - no response")
                return False

        except Exception as e:
            logging.error(f"LLM warmup failed with exception: {e}")
            return False
