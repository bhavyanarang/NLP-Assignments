# -*- coding: utf-8 -*-
"""NLP_Assignment4_Question1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/124uhOtQFcOwhZ2k8aRBbNSBBtO0AlJRD
"""

from google.colab import drive
drive.mount('gdrive')

!nvidia-smi

cd /content/gdrive/MyDrive/Aspect-Term-Extraction-and-Analysis/data

import os
os.listdir()

!pip install transformers

import pandas as pd
import numpy as np
import sklearn.metrics
import torch
from transformers import BertModel,BertTokenizer
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset, DataLoader, ConcatDataset
from sklearn.metrics import classification_report,confusion_matrix

class AspectTermExtraction(torch.nn.Module):
    def __init__(self, pretrain_model):
        super(AspectTermExtraction, self).__init__()
        self.bert = BertModel.from_pretrained(pretrain_model)
        self.lstm = torch.nn.Linear(self.bert.config.hidden_size, 3)
        # self.lstm = torch.nn.LSTM(self.bert.config.hidden_size,3)

    def forward(self, ids, aspect, masks):
        bert_outputs,_ = self.bert(input_ids=ids, attention_mask=masks, return_dict = False)
        lstm_outputs= self.lstm(bert_outputs)
        # lstm_outputs,_= self.lstm(bert_outputs)
        if aspect is not None:
            asp, lstm_outputs = aspect.view(-1), lstm_outputs.view(-1,3)
            loss = torch.nn.CrossEntropyLoss()(lstm_outputs, asp)
            return loss
        else:
            return lstm_outputs

class dataset(Dataset):
    def __init__(self, df, tokenizer):
        self.dataframe = df
        self.tokenizer = tokenizer

    def __getitem__(self, idx):
        tokens, aspect, polarity = self.dataframe.iloc[idx, :3].values
        tokens, aspect, polarity = tokens.replace("'", "").strip("][").split(', '), aspect.strip('][').split(', '), polarity.strip('][').split(', ')
        bert_tokens, bert_aspect, bert_polarity = [], [], []
        for i in range(len(tokens)):
            t = self.tokenizer.tokenize(tokens[i])
            l=len(t)
            bert_tokens += t
            ba = [int(aspect[i])]*l
            bert_aspect += ba
            bp = [int(polarity[i])]*l
            bert_polarity += bp
        bert_ids = self.tokenizer.convert_tokens_to_ids(bert_tokens)
        return bert_tokens, torch.tensor(bert_ids), torch.tensor(bert_aspect), torch.tensor(bert_polarity)

    def __len__(self):
        return len(self.dataframe)

DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = AspectTermExtraction("bert-base-uncased").to(DEVICE)
optimizer = torch.optim.Adam(model.parameters(), lr=2e-5)

samplez1=1500
samplez2=1000

restaurants_train, restaurants_test = dataset(pd.read_csv("restaurants_train.csv")[:samplez1], tokenizer), dataset(pd.read_csv("restaurants_test.csv")[:samplez1], tokenizer)
laptops_train, laptops_test = dataset(pd.read_csv("laptops_train.csv")[:samplez2], tokenizer), dataset(pd.read_csv("laptops_test.csv")[:samplez2], tokenizer)
train, test = ConcatDataset([laptops_train, restaurants_train]),  ConcatDataset([laptops_test, restaurants_test])

def mini_batch(samples):
    lis=[]
    for i in range(3):
      a = [s[i+1] for s in samples]
      a = pad_sequence(a, batch_first=True)
      lis.append(a)
    masks = torch.zeros(lis[0].shape, dtype=torch.long)
    masks = masks.masked_fill(lis[0] != 0, 1)   

    return lis[0], lis[1], lis[2], masks

train_loader = DataLoader(train, batch_size=50, collate_fn=mini_batch, shuffle = True)
test_loader = DataLoader(test, batch_size=200, collate_fn=mini_batch, shuffle = True)

def train_model(loader, epochs):
    all_data = len(loader)
    for epoch in range(epochs):
        lv, losses, correct_predictions= 0, [], 0
        for data in loader:
            ids, aspect, _, masks = data
            ids, aspect, masks = ids.to(DEVICE), aspect.to(DEVICE), masks.to(DEVICE)
            loss = model(ids=ids, aspect=aspect, masks=masks)
            losses.append(loss.item())
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            lv += 1
            print('Epoch:', epoch, "\t loss:", np.mean(losses), "\t Batch:", lv, "/" , all_data)

train_model(train_loader, 3)

torch.save(model.state_dict(), '/content/gdrive/My Drive/Aspect-Term-Extraction-and-Analysis/data/AspectTermExtraction.pkl')

pred, y = [], []
tn=['class0','class1','class2']
with torch.no_grad():
    for i in test_loader:
        ids, aspect, _, x = i
        ids, aspect, x= ids.to(DEVICE), aspect.to(DEVICE), x.to(DEVICE)
        dimension=2
        _, preds = torch.max(model(ids=ids, aspect=None, masks=x), dim=dimension)
        pred += list([int(j) for k in preds for j in k ])
        y += list([int(j) for k in aspect for j in k ])
result=classification_report(pred, y, target_names=tn)
print(result)

os.getcwd()

PATH='/content/gdrive/My Drive/Aspect-Term-Extraction-and-Analysis/data/AspectTermExtraction.pkl'
model = AspectTermExtraction("bert-base-uncased")
model.load_state_dict(torch.load(PATH))
model = model.to(DEVICE)

pred, y = [], []
tn=['class0','class1','class2']
with torch.no_grad():
    for i in test_loader:
        ids, aspect, _, x = i
        ids, aspect, x= ids.to(DEVICE), aspect.to(DEVICE), x.to(DEVICE)
        dimension=2
        _, preds = torch.max(model(ids=ids, aspect=None, masks=x), dim=dimension)
        pred += list([int(j) for k in preds for j in k ])
        y += list([int(j) for k in aspect for j in k ])
result=classification_report(pred, y, target_names=tn)
print(result)

