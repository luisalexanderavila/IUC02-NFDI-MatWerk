#!/bin/bash

pwd=$PWD

if [ ! -d Data/BAMDataset ]; then
    mkdir -p Data/BAMDataset
fi

ZENODOID=13937987

if [ ! -f Data/BAMDataset/$ZENODOID.zip ]; then
    echo "Downloading $ZENODOID.zip"
    wget https://zenodo.org/api/records/$ZENODOID/files-archive -O Data/BAMDataset/$ZENODOID.zip
else
    echo "File $ZENODOID.zip already exists"
fi

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
