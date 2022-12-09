#!/bin/bash

touch "$DATA_FOLDER"/users.txt
touch "$DATA_FOLDER"/groups.txt

/usr/local/bin/pipenv run python3 main.py