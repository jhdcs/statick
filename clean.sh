#!/bin/bash

rm -rf build/ dist/ output-py* .pytest_cache statick.egg-info/ statick_output/* .tox/
find . -type d -name .mypy_cache -exec rm -rf {} \;
find . -type d -name __pycache__ -exec rm -rf {} \;
