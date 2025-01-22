#!/bin/bash

pwd=$PWD

if [ ! -d Data/BAMDataset ]; then
    mkdir -p Data/BAMDataset
fi

ZENODOID=1234567

wget https://zenodo.org/record/$ZENOOID/files-archive -O Data/BAMDataset/$ZENODOID.zip

cd Data/BAMDataset

ls -tral

if [ -f $ZENODOID.zip ]; then
  echo " uncompressing $ZENODOID.zip"
  unzip $ZENODOID.zip
else
    echo "File $ZENODOID.zip does not exist"
fi


cd $pwd
exit 1
