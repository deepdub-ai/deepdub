#!/usr/bin/env python
"""
Example demonstrating basic usage of the DeepDub API client.
"""
import logging
from deepdub import DeepdubClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Initialize the client
client = DeepdubClient()

voices = client.list_voices()
logger.info(voices)