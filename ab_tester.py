#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import pandas as pd
import pymc3 as pm
import arviz as az
from itertools import combinations as comb
import pandas as pd
from plotly import graph_objects as go

plt.rcParams['figure.figsize'] = (10,8)
plt.style.use('seaborn-darkgrid')


class ab_tester:
    """
    beta-version
    
    """
    def __init__(self, df, condition):
        
        self.data = df
        self.columns = df.columns.tolist()
        self.condition_list = condition
        self.n_condition = len(condition)
        self.stage_list = list(set(self.columns) - set(self.condition_list))
        self.n_stage = self.data.shape[1] - self.n_condition


        temp = self.stage_list.copy()
        temp_total = [self.data[i].sum() for i in temp] # 개별 stage 개수 
        self.stage_order = []        
        self.stage_total = []

        for i in range(self.n_stage):
            self.stage_order.append(temp[np.argmax(temp_total)])
            self.stage_total.append(np.max(temp_total))
            temp.pop(np.argmax(temp_total))
            temp_total.pop(np.argmax(temp_total))

        self.first = self.stage_order[0]
        self.second = self.stage_order[-1]

        
    def func_mu(self,alpha, beta):
        return alpha/(alpha+beta)
    
    
    def func_var(self,alpha, beta):
        return (alpha*beta)/((alpha+beta+1)*(alpha+beta)**2)
    
            
    def abtest(self,initial,target,criteria):
        
        temp = self.data[[initial,target,criteria]].groupby(criteria).sum()        
        
        conv_ratio = temp[target]/temp[initial]
        print('conversion rate'.center(50))
        for i in range(len(temp)):
            print(f'* group "{conv_ratio.index[i]}": {round(conv_ratio.values[i],4)}')
        
    def beta(self,initial, target, criteria):
        temp = self.data[[initial,target,criteria]].groupby(criteria).sum()
        alpha = (temp + 1).iloc[:,1].values.flatten()
        beta = (-temp).add(temp.iloc[:,0], axis=0).iloc[:,1].values.flatten()
        
        conv_ratio = temp[target]/temp[initial]
        
        mu_list = []
        var_list = []
        for i in range(len(alpha)):
            mu_list.append(self.func_mu(alpha[i], beta[i]))
            var_list.append(self.func_var(alpha[i], beta[i]))
        print('Beta distribution parameters'.center(50))
        for i in range(len(temp)):
            print(f'* group "{conv_ratio.index[i]}": mu = {round(mu_list[i],4)} , var={round(var_list[i],4)}')
        
        self.alpha = alpha
        self.beta = beta
        self.index = conv_ratio.index.tolist()
        
    def absim(self,initial,target, criteria):
        temp = self.data.copy()
        temp = temp.groupby(criteria).sum()
        
        n_crit = len(temp.index)
        name_crit = temp.index
        n_initial = temp[initial].values
        n_target = temp[target].values
        comb_list = comb(range(n_crit), 2)
        
        with pm.Model() as ad_model:
            
            prior = [pm.Beta(f'prior_{name_crit[i]}', alpha=1, beta=1) for i in range(n_crit)]
            likelihood = [pm.Binomial(f'likelihood_{name_crit[i]}', n=n_initial[i], p=prior[i], observed=n_target[i]) for i in range(n_crit)]
            
            diff = [pm.Deterministic(f"diff_{name_crit[i[0]]}_{name_crit[i[1]]}", prior[i[0]] - prior[i[1]] ) for i in comb_list] # 두 '안'의 차이.
            trace = pm.sample(2000, tune=2000)
        
        self.trace = trace
        self.summary = pm.summary(trace)
            
    def plot_posterior(self, trace, var):                    
        
        _ = az.plot_posterior(trace, var_names=[var], ref_val=0, color='#87ceeb')
        
    
    def plot_funnel(self):
        
        data = dict(
        number = self.stage_total,
        colors = ['rgb(32,182,168)', 'rgb(23, 127, 117)', 'rgb(182, 33, 45)', 'rgb(127, 23, 31)'
                 ,'rgb(182,119,33)','rgb(127,84,23)'] ,
        stage = self.stage_order)
        
        fig = go.Figure(go.Funnel(
        y = data['stage'],
        x = data['number'], 
        textinfo = "value+percent initial",
        opacity = 0.8, marker = {"color": data['colors'][:self.n_stage]}
                        ))
        
        fig.update_layout(
        title={
            'text': "Funnel",
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'})

        
        fig.show()
        
        
        
    def funnel(self, condition):

        
        temp = self.data.groupby(condition).sum()[self.stage_order]
        group = self.data.groupby(condition).sum()[self.stage_order].index
        print('Summary'.center(50))
        print(' ')
        print(f'* stage list : {self.stage_order}')
        print(f'* stage size : {self.stage_total}')
        print('* stage portion :' ,['%.2f'%((i/self.stage_total[0])*100) + '%' for i in self.stage_total])
        print(' ')
        print('-----------------------------------------------------')
        print('Number of samples by group'.center(50))
        print(' ')
        for i in range(len(group)):
                print(f'* group "{group[i]}": {temp.values[i]}')        
        print(' ')
        
        stage_ratio = (temp / temp.shift(1,axis=1)).fillna(1)
        target_ratio = temp.apply(lambda x : 1/x).multiply(temp.iloc[:,-1], axis=0)
        print('-----------------------------------------------------')
        print('Stage to stage decay rate'.center(50))
        print(' ')
        for i in range(len(group)):
                print(f'* group "{group[i]}": {np.round(stage_ratio.values[i],3)}')        
            
        print(' ')
        print('-----------------------------------------------------')
        print('Conversion rate in each stage'.center(50))
        print(' ')
        for i in range(len(group)):
                print(f'* group "{group[i]}":' ,['%.2f'%(i*100)+'%' for i in target_ratio.values[i]])


