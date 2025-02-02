#!/bin/bash

#Description: This file is meant to setup a local environment for modification of HFO
#Note: Change checkout branches to customize configuration.

mkdir shiva
cd shiva

#Get the RCSSSERVER Repo
git clone https://github.com/mehrzadshabez/rcssserver.git
cd rcssserver
# git checkout gen-pt
cd ..

#Get the LIBRCSC Repo
git clone https://github.com/mehrzadshabez/librcsc.git
cd librcsc
# git checkout dev
cd ..


#Get the Robocup-Sigma Repo
git clone https://github.com/mehrzadshabez/Robocup-Sigma.git
cd Robocup-Sigma
#git checkout dev

cd envs/rc_soccer/HFO
bash recompile_start.sh
