"""Compatibility shim.

All project metadata lives in ``pyproject.toml``; this file only exists so
that legacy ``python setup.py ...`` invocations keep working.
"""

from setuptools import setup

setup()
