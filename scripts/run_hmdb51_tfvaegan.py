import os
# Need to check: zsl/gzsl, nz/attSize, nclass_all, nepoch

os.system('''python /content/kg_gnn_gan/train_tfvaegan.py \
--nclass_all 51 --dataset hmdb51 --zsl \
--dataroot /content/drive/MyDrive/colab_data/action_datasets \
--splits_path hmdb51_semantics --split 3 \
--action_embedding i3d --class_embedding wv \
--nepoch 3 --batch_size 64 \
--syn_num 600 --preprocessing --cuda --gammaD 10 --gammaG 10 \
--ngh 4096 --ndh 4096 --lambda1 10 --critic_iter 5 \
--nz 300 --attSize 300 --resSize 8192 --lr 0.0001 \
--encoded_noise --workers 8 \
--recons_weight 0.1 --feedback_loop 2 --a2 1 --a1 1 --feed_lr 0.00001 --dec_lr 0.0001''')
