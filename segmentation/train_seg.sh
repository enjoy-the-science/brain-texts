python train/train.py -i /data/brain/rs-mhd-dataset-augmented -c /data/brain/checkpoints -e 15
python train/train.py -i /data/brain/rs-mhd-dataset-augmented -c /data/brain/checkpoints -e 15 -l 0.01
python train/train.py -i /data/brain/rs-mhd-dataset-augmented -c /data/brain/checkpoints -e 15 -l 0.01 -d 0.3
python train/train.py -i /data/brain/rs-mhd-dataset-augmented -c /data/brain/checkpoints -e 15 -l 0.0001
python train/train.py -i /data/brain/rs-mhd-dataset-augmented -c /data/brain/checkpoints -e 15 -l 0.0001 -bs 2
python train/train.py -i /data/brain/rs-mhd-dataset-augmented -c /data/brain/checkpoints -e 15 -l 0.0001 -d 0.3
python train/train.py -i /data/brain/rs-mhd-dataset-augmented -c /data/brain/checkpoints -e 15 -l 0.0001 -d 0.3 -bs 2