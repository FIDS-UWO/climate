import pandas as pd
import numpy as np


def cfm(his, fut, obs, method, bins=25):
    """
    Apply change factor methodology to scale hist data using fut and
    hist climate models.

    Parameters
    ----------
    his : pandas.DataFrame
        Historical GCM data
    fut : pandas.DataFrame
        Future GCM data
    obs : pandas.DataFrame
        Observed data
    method : int
        A 1d numpy array containing 0's and 1's to indicate the scaling method
        to use.
        * 0 - Apply additive scaling
        * 1 - Apply multiplicative scaling
    bins : int
        The number of bins to apply scaling separately for.

    Returns
    -------
    obs : pandas.DataFrame
       A future-scaled version of the observed dataset.
    """
    # Copy the data to a new DataFrame
    obs = obs.copy()
    # Define the bins
    q = np.linspace(0, 1, bins)
    # Define scaling functions
    scale = [lambda x, d: x + d[x.name],
             lambda x, d: x * d[x.name]]

    his_month = his.index.get_level_values(1)
    fut_month = fut.index.get_level_values(1)
    obs_month = obs.index.get_level_values(1)

    for c in obs.columns:
        for m in range(1, 12 + 1):
            # Find rows corresponding to month "m"
            ai = his_month == m
            bi = fut_month == m
            ci = obs_month == m

            if method == 1:
                # Account for zero precipitation
                ai &= his[c] > 0.01
                bi &= fut[c] > 0.01
                ci &= obs[c] > 0.01

            # Extract values for calendar month "m" and column "c"
            Am = his.loc[ai, c]
            Bm = fut.loc[bi, c]
            Cm = obs.loc[ci, c]

            # Calculate bins for each percentile range
            Ab = pd.cut(Am, Am.quantile(q), labels=False, include_lowest=True)
            Bb = pd.cut(Bm, Bm.quantile(q), labels=False, include_lowest=True)
            Cb = pd.cut(Cm, Cm.quantile(q), labels=False, include_lowest=True)

            # Group data based on bins
            Ag = Am.groupby(Ab)
            Bg = Bm.groupby(Bb)
            Cg = Cm.groupby(Cb)

            # Apply scaling transformation
            if method == 0:
                delta = Bg.mean() - Ag.mean()
            elif method == 1:
                delta = Bg.mean() / Ag.mean()

            obs.loc[ci, c] = Cg.transform(scale[method], delta)

    return obs
