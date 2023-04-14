#!/bin/bash
source /ccs/home/mojia/.bashrc

storage_dir=OUTPUTDIR

# from MaCh3 install directory
cd /gpfs/alpine/phy171/proj-shared/mojia/MaCh3/MaCh3 
source setup.sh
#NVME

export OMP_NUM_THREADS=THREADSNUM
#CHAINS

#WAIT

