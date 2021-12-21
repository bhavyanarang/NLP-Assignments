# -*- coding: utf-8 -*-
"""NLP_Assignment4_Question2.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/138opgiDc6PrfYIctUcL3xIaV17nesmi9
"""

from google.colab import drive
drive.mount('gdrive')

!nvidia-smi

cd /content/gdrive/MyDrive/Aspect-Term-Extraction-and-Analysis/data/

!pip install transformers

import pandas as pd
import numpy as np
import sklearn.metrics
import torch
from transformers import BertModel,BertTokenizer
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset, DataLoader, ConcatDataset
from sklearn.metrics import classification_report,confusion_matrix
from sklearn.metrics import accuracy_score

class ABSA(torch.nn.Module):
    def __init__(self, pretrain_model):
        super(ABSA, self).__init__()
        self.bert = BertModel.from_pretrained(pretrain_model)
        self.cnn = torch.nn.Conv1d(self.bert.config.hidden_size, 3, 1)

    def forward(self, idt, labt, masks, segt):
        _, pooled_outputs = self.bert(input_ids=idt, attention_mask=masks, token_type_ids=segt, return_dict = False)
        cnn_outputs = self.cnn(pooled_outputs.view(pooled_outputs.shape[0], pooled_outputs.shape[1], 1))
        if labt is not None:
            loss = torch.nn.CrossEntropyLoss()(cnn_outputs, labt.view(labt.shape[0], 1))
            return loss
        else:
            return cnn_outputs

class dataset(Dataset):
    def __init__(self, df, tokenizer):
        self.df = df
        self.tokenizer = tokenizer

    def __getitem__(self, idx):
        tokens, tags, polarity = self.df.iloc[idx, :3].values
        tokens,tags, polarity = tokens.replace("'", "").strip("][").split(', '),tags.strip('][').split(', '),polarity.strip('][').split(', ')
        bert_tokens,bert_att,polarity_label = [],[],0
        stop=len(tokens)
        i=0
        while(i<stop):
            tok=tokens[i]
            t = self.tokenizer.tokenize(tok)
            bert_tokens += t
            if int(polarity[i]) != -1:
                bert_att += t
                polarity_label = int(polarity[i])
            i+=1
        tok_len=len(bert_tokens)
        at_len=len(bert_att)
        segment_tensor = [0]*(tok_len+1) + [1]*(at_len+1)
        bert_tokens = ['[cls]'] + bert_tokens + ['[sep]'] + bert_att
        ids_tensor,polarity_tensor,segment_tensor = torch.tensor(self.tokenizer.convert_tokens_to_ids(bert_tokens)),torch.tensor(polarity_label),torch.tensor(segment_tensor)

        return bert_tokens, ids_tensor, segment_tensor, polarity_tensor

    def __len__(self):
        return len(self.df)

DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = ABSA("bert-base-uncased").to(DEVICE)
optimizer = torch.optim.Adam(model.parameters(), lr=2e-5)

samplez1=1500
samplez2=1000

restaurants_train, restaurants_test = dataset(pd.read_csv("restaurants_train.csv")[:samplez1], tokenizer), dataset(pd.read_csv("restaurants_test.csv")[:samplez1], tokenizer)
laptops_train, laptops_test = dataset(pd.read_csv("laptops_train.csv")[:samplez2], tokenizer), dataset(pd.read_csv("laptops_test.csv")[:samplez2], tokenizer)
train, test = ConcatDataset([laptops_train, restaurants_train]),  ConcatDataset([laptops_test, restaurants_test])

def mini_batch(samples):
    idt = pad_sequence([s[1] for s in samples], batch_first=True)
    seg= pad_sequence([s[2] for s in samples], batch_first=True)
    label_ids = torch.stack([s[3] for s in samples])
    masks = torch.zeros(idt.shape, dtype=torch.long).masked_fill(idt != 0, 1)
    return idt, seg, masks, label_ids

train_loader = DataLoader(train, batch_size=50, collate_fn=mini_batch, shuffle = True)
test_loader = DataLoader(test, batch_size=200, collate_fn=mini_batch, shuffle = True)

def train_model(loader, epochs):
    all_data = len(loader)
    for epoch in range(epochs):
        lv,losses,correct_predictions = 0,[],0
        for data in loader:
            idt, segt, masks, label_ids = data
            idt,segt,label_ids,masks = idt.to(DEVICE),segt.to(DEVICE),label_ids.to(DEVICE),masks.to(DEVICE)
            loss = model(idt=idt, labt=label_ids, masks=masks, segt=segt)
            losses.append(loss.item())
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            lv += 1
            print('Epoch:', epoch, "\t loss:", np.mean(losses), "\t Batch:", lv, "/" , all_data)

train_model(train_loader, 6)

torch.save(model.state_dict(), '/content/gdrive/My Drive/Aspect-Term-Extraction-and-Analysis/data/AscpectBasedSentimentAnalysis.pkl')

pred , y = [] , []
with torch.no_grad():
    for i in test_loader:
        idt, segt, masks, label_ids = i
        idt, segt, masks = idt.to(DEVICE),segt.to(DEVICE), masks.to(DEVICE)
        _, preds = torch.max(model(idt=idt, labt=None, masks =masks, segt=segt), dim=1)
        pred += list([int(pr) for pr in preds])
        y += list([int(li) for li in label_ids])

print("Accuracy is "+str(accuracy_score(pred, y)))

import os
os.getcwd()

PATH='/content/gdrive/My Drive/Aspect-Term-Extraction-and-Analysis/data/AscpectBasedSentimentAnalysis.pkl'
model = ABSA("bert-base-uncased")
model.load_state_dict(torch.load(PATH))
model = model.to(DEVICE)

pred , y = [] , []
with torch.no_grad():
    for i in test_loader:
        idt, segt, masks, label_ids = i
        idt, segt, masks = idt.to(DEVICE),segt.to(DEVICE), masks.to(DEVICE)
        _, preds = torch.max(model(idt=idt, labt=None, masks =masks, segt=segt), dim=1)
        pred += list([int(pr) for pr in preds])
        y += list([int(li) for li in label_ids])

print("Accuracy is "+str(accuracy_score(pred, y)))

