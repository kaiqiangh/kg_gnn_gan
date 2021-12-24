#!/bin/sh

#SBATCH --job-name=ucf_1400
#SBATCH --account=tud01
#SBATCH --mem=65536
#SBATCH --partition GpuQ
#SBATCH --nodes 1
#SBATCH --time=02-00
#SBATCH --cpus-per-task=8
#SBATCH --mail-user=kaiqiang.x.huang@mytudublin.ie
#SBATCH --mail-type=ALL,TIME_LIMIT_80
#SBATCH --output=res_dual_ucf101_1400.out

module load conda/2
module load cuda/11.2

source activate /ichec/home/users/kaiqiang/py39

echo "Dual GAN with different classifier for UCF101 (multi-GPU)"
echo "The number of syn_data is 1400"

time python ./dual/run_ucf101_tfvaegan_dual.py