import torch
import torch.nn as nn
from torch.autograd import Variable
import torch.optim as optim
import util
import numpy as np
import copy
from sklearn.metrics import confusion_matrix


class CLASSIFIER:
    def __init__(self, _train_X, _train_Y, data_loader, _nclass, _cuda, _lr=0.001, _beta1=0.5, _nepoch=50,
                 _batch_size=64, generalized=False, netDec=None, dec_size=4096, dec_hidden_size=4096):
        self.train_X = _train_X.clone()
        self.train_Y = _train_Y.clone()
        self.test_seen_feature = data_loader.test_seen_feature.clone()
        self.test_seen_label = data_loader.test_seen_label

        self.test_unseen_feature = data_loader.test_unseen_feature.clone()
        self.test_unseen_label = data_loader.test_unseen_label
        self.seenclasses = data_loader.seenclasses
        self.unseenclasses = data_loader.unseenclasses
        self.batch_size = _batch_size
        self.nepoch = _nepoch
        self.nclass = _nclass
        self.input_dim = _train_X.size(1)
        self.cuda = _cuda
        self.model = LINEAR_LOGSOFTMAX_CLASSIFIER(self.input_dim, self.nclass)
        self.netDec = netDec
        if self.netDec:
            self.netDec.eval()
            self.input_dim = self.input_dim + dec_size
            self.input_dim += dec_hidden_size
            self.model = LINEAR_LOGSOFTMAX_CLASSIFIER(self.input_dim, self.nclass)
            self.train_X = self.compute_dec_out(self.train_X, self.input_dim)
            self.test_unseen_feature = self.compute_dec_out(self.test_unseen_feature, self.input_dim)
            # No need for init exp. (zsl setting)
            self.test_seen_feature = self.compute_dec_out(self.test_seen_feature, self.input_dim)
        self.model.apply(util.weights_init)
        self.criterion = nn.NLLLoss()
        self.input = torch.FloatTensor(_batch_size, self.input_dim)
        self.label = torch.LongTensor(_batch_size)
        self.lr = _lr
        self.beta1 = _beta1
        self.optimizer = optim.Adam(self.model.parameters(), lr=_lr, betas=(_beta1, 0.999))
        # self.test_on_seen = test_on_seen
        if self.cuda:
            self.model.cuda()
            self.criterion.cuda()
            self.input = self.input.cuda()
            self.label = self.label.cuda()
        self.index_in_epoch = 0
        self.epochs_completed = 0
        self.ntrain = self.train_X.size()[0]
        if generalized:
            # gzsl
            self.acc_seen, self.acc_per_seen, self.acc_unseen, self.acc_per_unseen, \
                self.H, self.best_model = self.fit()
        else:
            # zsl
            self.acc, self.acc_per_class, self.best_model, self.cm = self.fit_zsl()

    def fit_zsl(self):
        best_acc = 0
        mean_loss = 0
        acc_per_class = []
        best_cm = []
        last_loss_epoch = 1e8
        best_model = copy.deepcopy(self.model)
        for epoch in range(self.nepoch):
            for i in range(0, self.ntrain, self.batch_size):
                self.model.zero_grad()
                batch_input, batch_label = self.next_batch(self.batch_size)
                self.input.copy_(batch_input)
                self.label.copy_(batch_label)

                inputv = Variable(self.input)
                labelv = Variable(self.label)
                output = self.model(inputv)
                loss = self.criterion(output, labelv)
                mean_loss += loss.data
                loss.backward()
                self.optimizer.step()
            self.model.eval()
            # print('Training classifier loss= ', loss.data[0])
            acc, acc_per_class, cm = self.val(self.test_unseen_feature, self.test_unseen_label, self.unseenclasses)
            # print('acc %.4f' % (acc))
            if acc > best_acc:
                best_acc = acc
                best_acc_per_class = acc_per_class
                best_model = copy.deepcopy(self.model)
                best_cm = cm
        return best_acc, best_acc_per_class, best_model, best_cm

    def fit(self):
        best_H = 0
        best_seen = 0
        best_unseen = 0
        best_acc_per_seen = []
        best_acc_per_useen = []
        best_cm = []
        best_model = copy.deepcopy(self.model)
        # early_stopping = EarlyStopping(patience=20, verbose=True)

        for epoch in range(self.nepoch):
            #print("Start Final Discriminative Classifier Training at epoch: ", epoch)
            for i in range(0, self.ntrain, self.batch_size):
                self.model.zero_grad()
                batch_input, batch_label = self.next_batch(self.batch_size)
                self.input.copy_(batch_input)
                self.label.copy_(batch_label)
                inputv = Variable(self.input)
                labelv = Variable(self.label)
                output = self.model(inputv)
                loss = self.criterion(output, labelv)
                loss.backward()
                self.optimizer.step()
            # Set evaluation mode
            self.model.eval()
            acc_seen, acc_per_seen = self.val_gzsl(self.test_seen_feature, self.test_seen_label, self.seenclasses)
            acc_unseen, acc_per_unseen = self.val_gzsl(self.test_unseen_feature, self.test_unseen_label, self.unseenclasses)
            H = 2 * acc_seen * acc_unseen / (acc_seen + acc_unseen)
            if H > best_H:
                best_seen = acc_seen
                best_acc_per_seen = acc_per_seen
                best_acc_per_useen = acc_per_unseen
                best_unseen = acc_unseen
                best_H = H
                best_model = copy.deepcopy(self.model)
        return best_seen, best_acc_per_seen, best_unseen, best_acc_per_useen, best_H, best_model

    def val_gzsl(self, test_X, test_label, target_classes):
        start = 0
        ntest = test_X.size()[0]
        predicted_label = torch.LongTensor(test_label.size())
        for i in range(0, ntest, self.batch_size):
            end = min(ntest, start + self.batch_size)
            if self.cuda:
                with torch.no_grad():
                    inputX = Variable(test_X[start:end].cuda())
            else:
                with torch.no_grad():
                    inputX = Variable(test_X[start:end])
            output = self.model(inputX)
            _, predicted_label[start:end] = torch.max(output.data, 1)
            start = end

        acc, acc_per_class = self.compute_per_class_acc_gzsl(test_label, predicted_label, target_classes)
        return acc, acc_per_class

    def compute_per_class_acc_gzsl(self, test_label, predicted_label, target_classes):
        acc_per_class = []
        n = 0
        for i in target_classes:
            idx = (test_label == i)
            acc = torch.sum(test_label[idx] == predicted_label[idx]) / torch.sum(idx)
            acc_per_class = np.append(acc_per_class, acc)
        #acc_per_class /= target_classes.size(0)
            acc_mean = acc_per_class.mean()
            n += 1
        return acc_mean, acc_per_class

    # Parameter: test_label is integer
    def val(self, test_X, test_label, target_classes):
        start = 0
        ntest = test_X.size()[0]
        predicted_label = torch.LongTensor(test_label.size())
        for i in range(0, ntest, self.batch_size):
            end = min(ntest, start + self.batch_size)
            if self.cuda:
                with torch.no_grad():
                    inputX = Variable(test_X[start:end].cuda())
            else:
                with torch.no_grad():
                    inputX = Variable(test_X[start:end])
            output = self.model(inputX)
            _, predicted_label[start:end] = torch.max(output.data, 1)
            start = end

        acc, acc_per_class = self.compute_per_class_acc(util.map_label(test_label, target_classes),
                                                        predicted_label, target_classes.size(0))

        cm = self.compute_confusion_matrix(util.map_label(test_label, target_classes),
                                           predicted_label, target_classes.size(0))
        return acc, acc_per_class, cm

    def compute_per_class_acc(self, test_label, predicted_label, nclass):
        acc_per_class = torch.FloatTensor(nclass).fill_(0)
        for i in range(nclass):
            idx = (test_label == i)
            acc_per_class[i] = torch.sum(test_label[idx] == predicted_label[idx]) / torch.sum(idx)
            acc_mean = acc_per_class.mean()
        return acc_mean, acc_per_class

    # New function: get confusion matrix
    def compute_confusion_matrix(self, test_label, predicted_label, nclass):
        return confusion_matrix(test_label, predicted_label)

    def compute_dec_out(self, test_X, new_size):
        start = 0
        ntest = test_X.size()[0]
        new_test_X = torch.zeros(ntest, new_size)
        for i in range(0, ntest, self.batch_size):
            end = min(ntest, start + self.batch_size)
            if self.cuda:
                with torch.no_grad():
                    inputX = Variable(test_X[start:end].cuda())
            else:
                with torch.no_grad():
                    inputX = Variable(test_X[start:end])
            feat1 = self.netDec(inputX)
            feat2 = self.netDec.getLayersOutDet()
            new_test_X[start:end] = torch.cat([inputX, feat1, feat2], dim=1).data.cpu()
            start = end
        return new_test_X

    def next_batch(self, batch_size):
        start = self.index_in_epoch
        # shuffle the data at the first epoch
        if self.epochs_completed == 0 and start == 0:
            perm = torch.randperm(self.ntrain)
            self.train_X = self.train_X[perm]
            self.train_Y = self.train_Y[perm]
        # the last batch
        if start + batch_size > self.ntrain:
            self.epochs_completed += 1
            rest_num_examples = self.ntrain - start
            if rest_num_examples > 0:
                X_rest_part = self.train_X[start:self.ntrain]
                Y_rest_part = self.train_Y[start:self.ntrain]
            # shuffle the data
            perm = torch.randperm(self.ntrain)
            self.train_X = self.train_X[perm]
            self.train_Y = self.train_Y[perm]
            # start next epoch
            start = 0
            self.index_in_epoch = batch_size - rest_num_examples
            end = self.index_in_epoch
            X_new_part = self.train_X[start:end]
            Y_new_part = self.train_Y[start:end]
            # print(start, end)
            if rest_num_examples > 0:
                return torch.cat((X_rest_part, X_new_part), 0), torch.cat((Y_rest_part, Y_new_part), 0)
            else:
                return X_new_part, Y_new_part
        else:
            self.index_in_epoch += batch_size
            end = self.index_in_epoch
            # print(start, end)
            # from index start to index end-1
            return self.train_X[start:end], self.train_Y[start:end]


class LINEAR_LOGSOFTMAX_CLASSIFIER(nn.Module):
    def __init__(self, input_dim, nclass):
        super(LINEAR_LOGSOFTMAX_CLASSIFIER, self).__init__()
        self.fc = nn.Linear(input_dim, nclass)
        self.logic = nn.LogSoftmax(dim=1)

    def forward(self, x):
        o = self.logic(self.fc(x))
        return o
