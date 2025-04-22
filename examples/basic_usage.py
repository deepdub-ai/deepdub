#!/usr/bin/env python
"""
Example demonstrating basic usage of the DeepDub API client.
"""
from deepdub import DeepdubClient

# Initialize the client
client = DeepdubClient()

voices = client.list_voices()
print(voices)