#!/bin/sh

#SBATCH --job-name=hmdb_gzsl_od_600
#SBATCH --account=tucom002c
#SBATCH --mem=65536
#SBATCH --partition GpuQ
#SBATCH --nodes 1
#SBATCH --time=02-00
#SBATCH --cpus-per-task=8
#SBATCH --mail-user=kaiqiang.x.huang@mytudublin.ie
#SBATCH --mail-type=ALL,TIME_LIMIT_80
#SBATCH --output=res_hmdb51_gzsl_od_600_class_w2v_sp_10_30.out

module load conda/2
module load cuda/11.2

source activate /ichec/work/tucom002c/py39

echo "GZSL OD: Single GAN without FREE for HMDB51"
echo "The number of syn_data is 600"

time python ./scripts/run_hmdb51_tfvaegan.py