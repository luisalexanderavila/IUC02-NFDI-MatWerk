#!/bin/bash

ZENOOID=1234567

wget https://zenodo.org/record/$ZENOOID/files-archive -O $ZENOOID.zip

unzip data.zip
