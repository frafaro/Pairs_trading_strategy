import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import coint

'''
The idea is to identify when the price relationship between
two potentially related financial assets deviates from its historical level, 
then take positions expecting that relationship to revert toward its mean.

NB: cointegration is not the same as correlation.
Two stocks can move together in the short run without maintaining
a stable long-run relationship. Cointegration attempts to capture this factor.
'''

#### Download of two potentially cointegrated assets ####
tickers = ['SPY', 'IVV'] #both are etf on SP500
data = yf.download(tickers, start='2021-01-01', end='2026-01-01', progress=False, auto_adjust= False)['Close']
data.dropna(inplace=True)

#### Test for cointegration ####
'''
The function coint() implements the Engle–Granger two-step cointegration test.
We are testing the relationship in the form of: P_spy = alpha + beta * P_ivv + epsilon

epsilon is the residuals,and this function tests whether the residual series is stationary.

If both price series are individually nonstationary but their estimated 
linear combination is stationary, that supports cointegration.

The hypotheses of the test are:
- H0 : no cointegration (high p_value)
- H1 : cointegration (small p_value)

we test a benchmark of 5% for the p_value 
'''
score, p_value, _ = coint(data['SPY'], data['IVV'])
print(f'Cointegration p-value: {p_value:.4f}')
print(f'Cointegrated at 5%: {p_value < 0.05}')

#### Spread and z-score ####

lookback = 60 #rolling window of 60 observations, approximately 12 trading weeks
# A shorter window reacts faster to recent market conditions; a longer window produces smoother estimates but can adapt more slowly to structural changes.

# new columns of the dataset
data['spread'] = data['SPY'] - data['IVV'] #diff between prices 
data['spread_mean'] = data['spread'].rolling(lookback).mean() #spread mean over the previos 60 days
data['spread_std']  = data['spread'].rolling(lookback).std()  #spread vol over 
data['z_score']     = (data['spread'] - data['spread_mean']) / data['spread_std'] # z-score with canonical formula (x-x_mean)/std(x)
'''
interpretation of the Z-score:
- Z = 0 : The spread equals its rolling mean.
- Z = + or - 1 : The spread is one standard deviation above/below its mean.
- Z = + or - 2 : The spread is two standard deviations above/below its mean
'''

#### Signal generation ####
'''
idea:
- when Z = 2  : short spy and buy ivv
- when Z = -2 : buy spy and short ivv

we need to create a new column for the signal
'''
entry, exit_thresh = 2.0, 0.5 # hyperparameters of the strategy
data['signal'] = np.nan 

# when Z > 2 then write -1 or Nan for other values
data['signal'] = np.where(data['z_score'] > entry,
                            -1, data['signal'])

#when Z < -2 write 1 or nan for other values 
data['signal'] = np.where(data['z_score'] < -entry,
                            1, data['signal'])

# 0 for all values [-0.5 ; 0.5]
data['signal'] = np.where(abs(data['z_score']) < exit_thresh,
                            0, data['signal'])

# we fill up all the postions that are nan
'''
IMPORTANT: right now only values exceding the threesholds have a signal values but we
want to keep the position until this value change otherwise we enter a postion and immediatly 
exit the day after.
'''
data['signal'] = data['signal'].ffill().fillna(0)


#### Returns ####
'''
the full strategy can be improved by:
- adding trx costs ie: 0.001
- we are assuming equal weight of the returns

'''
data['SPY_ret'] = data['SPY'].pct_change()
data['IVV_ret']  = data['IVV'].pct_change()
data['strategy_return'] = data['signal'].shift(1) * (data['SPY_ret'] - data['IVV_ret']) # diff of the returns
# we move the signal by 1 in order to use at day t the signal from day 1
data.dropna(inplace=True)

#### Performance Metrics ####

ann_return = data['strategy_return'].mean() * 252
sharpe = ann_return / (data['strategy_return'].std() * np.sqrt(252))
print(f'Annualised Return: {ann_return:.2%}')
print(f'Sharpe Ratio: {sharpe:.2f}')

#### plot for the startegy ####
'''
upper chart shows the spread line 
lower chart shows the z-score
'''
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
fig.patch.set_facecolor('#0D1B2A')
for ax in [ax1, ax2]:
    ax.set_facecolor('#0D1B2A')
    ax.tick_params(colors='white')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#4a5a6a')
    ax.spines['left'].set_color('#4a5a6a')

data['spread'].plot(ax=ax1, color='#00D4FF')
data['spread_mean'].plot(ax=ax1, color='white', alpha=0.6, linestyle='--')
ax1.set_title('Spread Between SPY and IVV', color='white', fontweight='bold')

data['z_score'].plot(ax=ax2, color='#00D4FF')
ax2.axhline(entry, color='red', linestyle='--', alpha=0.7)
ax2.axhline(-entry, color='#4ade80', linestyle='--', alpha=0.7)
ax2.axhline(0, color='white', linestyle='--', alpha=0.3)
ax2.set_title('Z-Score of Spread', color='white', fontweight='bold')

plt.tight_layout()
plt.savefig('pairs_trading.png', dpi=150, bbox_inches='tight', facecolor='#0D1B2A')
plt.show()