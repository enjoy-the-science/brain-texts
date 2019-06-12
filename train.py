import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, SequentialSampler, SubsetRandomSampler
from torch.utils.data import Subset

import utils
from data_utils import BertFeaturesDataset, train_val_holdout_split
from models.unet import UNet
from models.vgg import VGG, VGG11
from models.text_net import BrainLSTM
from models.fuse import EarlyFusion


def main():
    parser = argparse.ArgumentParser()

# Required parameters
# parser.add_argument("--imgs_folder", default=None, type=str, required=True)
# parser.add_argument("--texts_file", default=None, type=str, required=True)
# parser.add_argument("--labels_file", default=None, type=str, required=True)
# parser.add_argument("--bert_model", default=None, type=str, required=True,
#                     help="Bert pre-trained model selected in the list: "
#                          "bert-base-uncased, bert-large-uncased,"
#                          "bert-base-cased, bert-base-multilingual,"
#                          "bert-base-chinese.")

    # Other parameters
    parser.add_argument("-e", "--epochs", default=3, type=int,
                        help="Epochs to train. Default: 3")
    parser.add_argument("-lr", "--lr", type=float, default=0.001,
                        help="Learning rate. Default: 0.001")
    parser.add_argument("--batch-size", default=4, type=int,
                        help="Batch size for predictions. Default: 4")
    parser.add_argument('--max-seq-length', default=256, type=int,
                        help="Seq size for texts embeddings. Default: 256")
    parser.add_argument('--no-cuda', action='store_true')

    args = parser.parse_args()

    dev = torch.device(
        "cuda" if torch.cuda.is_available() and not args.no_cuda else "cpu"
    )
    n_gpu = torch.cuda.device_count()

    ###
    imgs_folder = '/data/brain/rs-mhd-dataset/net_out_masks_torch/'
    input_text_file = '/data/brain/rs-mhd-dataset/annotations.txt'
    labels_file = '/data/brain/rs-mhd-dataset/brain-labels.csv'
    bert_model = 'bert-base-uncased'
    ###

    data = BertFeaturesDataset(imgs_folder, input_text_file,
                               labels_file, bert_model,
                               max_seq_length=args.max_seq_length,
                               batch_size=args.batch_size,
                               bert_device='cpu',
                               resize_to=64)
    
    np.random.seed(0)  # TODO: saving indices for test phase
    train_inds, val_inds, test_inds = train_val_holdout_split(
        data, ratios=[0.6, 0.4, 0]
    )
    print('INDS', train_inds, val_inds, test_inds)
    train_sampler = SubsetRandomSampler(train_inds)
    val_sampler = SubsetRandomSampler(val_inds)
    test_sampler = Subset(data, test_inds)

    train_loader = DataLoader(data, batch_size=args.batch_size,
                              sampler=train_sampler)
    val_loader = DataLoader(data, batch_size=args.batch_size * 2,
                            sampler=val_sampler)
    test_loader = DataLoader(test_sampler)

    # vgg = VGG11(combine_dim=2)
    # vgg = vgg.to(dev)
    # lstm = BrainLSTM(embed_dim=768, hidden_dim=256, num_layers=1,
    #                  context_size=2, combine_dim=2, dropout=0)
    # lstm = lstm.to(dev)

    # model = EarlyFusion(combine_dim=4096)
    model = VGG11(combine_dim=2)
    model = model.to(dev)

    model_name = utils.get_model_name(model)
    prefix = "%s_lr=%s_bs=%s" % (model_name, args.lr, args.batch_size)

    # if torch.cuda.device_count() > 1:
    #     print(f"Using {n_gpu} CUDAs")
    #     # dim = 0 [30, ...] -> [10, ...], [10, ...], [10, ...] on 3 GPUs
    #     lstm = nn.DataParallel(lstm)

    opt = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=5e-2)
    # lambda2 = lambda epoch: 0.95 ** epoch
    # schedlr = torch.optim.lr_scheduler.LambdaLR(opt,
    #                                             lr_lambda=[lambda2])

    loss_func = nn.CrossEntropyLoss()

    # TRAINING
    print(f'\n===== BEGIN TRAINING {model_name} WITH {str(dev).upper()} =====')
    loss_train = []
    loss_val, acc_val = [], []
    for epoch in range(args.epochs):
        model.train()
        train_loss = 0
        for batch in train_loader:

            labels = batch['label'].long().to(dev).squeeze(1)
            images = batch['image'].to(dev)
            embeddings = batch['embedding'].to(dev)

            # out = vgg(images)
            # pred = lstm(embeddings)
            out = model(images)  # embeddings, 

            loss = loss_func(out, labels)
            loss.backward()

            utils.plot_grad_flow(model.named_parameters(),
                                 epoch, 'grad_flow_plots')
            train_loss += np.sqrt(loss.cpu().item())

            opt.step()
            opt.zero_grad()

        train_loss /= len(train_loader)
        loss_train.append(train_loss)
        if epoch % 1 == 0:
            print('Epoch: %03d Train loss: %.4f' % (epoch, train_loss))

        # VALIDATION
        if epoch % 1 == 0:
            model.eval()
            val_loss = 0
            correct, total = 0, 0
            with torch.no_grad():
                for batch in val_loader:

                    labels = batch['label'].long().to(dev).squeeze(1)
                    images = batch['image'].to(dev)
                    embeddings = batch['embedding'].to(dev)

                    pred = model(images)  # embeddings, 

                    val_loss += loss_func(pred, labels)
                    pred = pred.data.max(1)[1]
                    correct += pred.eq(labels.data.view_as(pred)).cpu().sum()
                    total += labels.size(0)

                val_loss /= len(val_loader)
                loss_val.append(val_loss)
                acc = 100. * correct / total
                acc_val.append(acc)

                print('Epoch: %03d Valid loss: %.4f Acc: %.2f' % (epoch, val_loss.item(), acc))

                torch.save(
                    model.state_dict(),
                    f'/data/brain/checkpoints/{prefix}_ep_{epoch}.pth'
                )

    plots_path = 'train_plots'
    utils.draw_plots(args.epochs, plots_path, prefix,
                     loss_train, loss_val, acc_val)


if __name__ == "__main__":
    main()
