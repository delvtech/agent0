"""
Setup barebones logging without a handler for users to adapt to their needs.
"""
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())
