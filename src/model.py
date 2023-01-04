import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from tqdm import tqdm
import os


class transitionDataset(torch.utils.data.Dataset):
    def __init__(self, M_g, M_c, M_p, if_train):
        """
        Args:
            M_g : a concept ordering transition matrix derived from the concept ordering of the given sentences in the Commongen dataset
            M_c : a concept ordering transition matrix derived from the number of paths between concepts in the conceptnet
            M_p : which transtion between concepts would be considered
            if_train (boolean): if is in training or validation
        """        
        self.M_g = M_g
        self.M_c = M_c
        self.M_p = M_p
        self.dataset = []

        if if_train:
            for i in range(self.M_g.shape[0]):
                for j in range(self.M_g.shape[1]):
                    if M_p[i][j]==1 :
                    #if M_g[i][j] !=0 or M_c[i][j] !=0:
                        self.dataset.append((i, j))
        else:
             for i in range(self.M_g.shape[0]):
                for j in range(self.M_g.shape[1]):
                    if M_p[i][j]==1:
                        self.dataset.append((i, j))
    

    def __len__(self):
        return len(self.dataset)


    def __getitem__(self, index):
        (i, j) = self.dataset[index]
        #Here we return items are 
        return i, j, torch.tensor(self.M_g[i][j], dtype=torch.float), torch.tensor(self.M_c[i][j], dtype=torch.float)


class transitionModel(nn.Module):
    def __init__(self, vocab_size, embed_size, pretrained_emb):
        super(transitionModel,self).__init__()
        self.vocab_size = vocab_size
        self.embed_size = embed_size
        self.pretrained_emb = pretrained_emb

        # v, w embedding
        self.v = nn.Embedding.from_pretrained(pretrained_emb,freeze=False)
        self.w = nn.Embedding.from_pretrained(pretrained_emb,freeze=False)

        self.hidden1 = nn.Linear(self.embed_size, 128)
        self.hidden2 = nn.Linear(128, 128)
        self.hidden3 = nn.Linear(128, 64)
        
        

    def forward(self, i, j):
        #embedding
        vi = self.v(i)
        wj = self.w(j)
        
        vi = torch.tanh(self.hidden1(vi))
        #vi = torch.tanh(self.hidden2(vi))
        vi = self.hidden2(vi)

        
        wj = torch.tanh(self.hidden1(wj))
        #wj = torch.tanh(self.hidden2(wj))
        wj = (self.hidden2(wj))
        
        
        o = torch.mul(vi,wj) 
        o = torch.sum(o, dim=1)
        
        return o
    
    def loss_func(self, output, Mg_p, Mc_p):
        """The loss function in the training
         
        Args:
            output : o is the output generated by forward function
            Mg_p : The transition probability from concept i to concept j in the Mg
            Mc_p : he transition probability from concept i to concept j in the Mc
        Returns:
            _type_: Mean squared loss as shown in Eq 7
        """        
        alpha = 0.5
        
        l_c =  torch.pow(output - Mc_p, 2)
        l_g = torch.pow(output - Mg_p, 2)
        loss = alpha * l_c + (1-alpha) * l_g
        return loss.mean()
    

    
    
    def valid_loss(self, output, Mg_p):
        """The loss function in validation, we here only use the probability from M_g as in shown in Eq 10
        Args:
            output : o is the output generated by forward function
            Mg_p : The transition probability from concept i to concept j in the Mg
        Returns:
            _type_: Mean squared loss as shown in Eq 10, we return the sum because we would devide in the main function
        """        
        loss = torch.pow(output - Mg_p, 2)
        return loss.mean()
     

    
    def get_matrix(self):
        #Return the learnt matrix
        o = torch.zeros((self.vocab_size,self.vocab_size))
        res_v = self.v.weight.data
        res_w = self.w.weight.data
        
        res_v = torch.tanh(self.hidden1(res_v))
        #res_v = torch.tanh(self.hidden2(res_v))
        res_v = self.hidden2(res_v)

        
        res_w = torch.tanh(self.hidden1(res_w))
        #res_w = torch.tanh(self.hidden2(res_w))
        res_w = self.hidden2(res_w)

        
        o = res_v @ res_w.T 
        #o = o + res_bv
        #o = (o.T +res_bw).T

        return o.data.cpu().numpy()