#!/bin/bash

for i in $(seq 1 10)
do

cd two_ubq_$i

for j in 1.00 1.10 1.12
do

cd lambda_${j}
cp ../../prodrun_mdrun.sh .

echo "#!/bin/sh" > temp
echo "#PBS -W group_list=ku_10001 -A ku_10001" >> temp
echo "#PBS -N 2ubq_${i}_${j}_md" >> temp
cat prodrun_mdrun.sh >> temp
mv temp prodrun_mdrun.sh

qsub prodrun_mdrun.sh

cd ..

done

cd ..

done

