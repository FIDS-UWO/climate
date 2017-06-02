import pandas as pd
import numpy as np

from numba import njit


class KNN:
    def __init__(self, X, P, w=14, B=10, interp=0.9):
        """
        Function to idw_run the KNN Weather Generator algorithm. Adapted from
        King et al. (2012) to use euclidean distance for L nearest neighbor
        selection as opposed to mahalanobis distance along 1st principal
        component.

        Parameters
        ----------
        X: pandas.DataFrame
            Input data following prescribed formatting.
        P: 1d array
            Assigns the perturbation type for each column in `X`.\n
            * 0 - No perturbation
            * 1 - Normal perturbation
            * 2 - Log-normal perturbation
        w: int
            Window size for the determination of the L and K nearest neighbors.
        B: int
            Block size for the block boostrap resampling.
        interp: float
            Level of influence of perturbation to be applied. 1 represents full
            perturbation while 0 represents no perturbation.

        Returns
        -------
        result: pandas.DataFrame
            `result` is returned as a DataFrame with the same number of columns
            as `X` and length equal to `runs` multiplied by that of `X`.

        """
        self.X = X
        self.P = P
        self.w = w
        self.B = B
        self.interp = interp

        # Standardize columns of input data
        self.Xn = (X - X.mean()) / X.std()
        # Group columns of like variables
        self.Xt = self.Xn.groupby(level=0, axis=1).mean()
        # Get year, month, and day from index
        year, mon, day = np.array(list(zip(*X.index.values)), dtype=np.uint32)

        if mon[0] != 1 or day[0] != 1 or mon[-1] != 12 or day[-1] != 31:
            raise ValueError("Data must start at Jan 1 and end at Dec 31")

        # Get day of year for all days
        self.doy = day_of_year(mon, day)

    def bootstrap(self, run_id):
        Xt = self.Xt.values
        X = self.X.values

        n, m = self.X.shape
        # Pre-allocate results array
        Xsim = np.zeros((n, m))

        # Determine K
        N = np.sum(self.doy == self.doy[0])
        L = N * (self.w + 1) - 1
        K = int(round(np.sqrt(L)))

        # Get L nearest neighbors indices for each day of the year
        lp1nn_idx = lnn_algorithm(self.doy, self.w, L)

        # Generate cumulative probability distribution
        pn = (np.ones(K) / np.arange(1, K + 1)).cumsum()
        pn /= pn.max()

        # Random selection of the first day
        day1_idx, = np.where(self.doy == self.doy[0])

        start = np.random.choice(day1_idx)

        Xsim[:self.B] = X[start: start+self.B]

        # Loop through each block of size B
        for i in range(self.B, n, self.B):
            # Randomly select the day before or after leap day
            if self.doy[i] < 0:
                t = i + np.random.choice([-1, 1])
            else:
                t = i

            # Get L + 1 nearest neighbors for current day of the year
            lp1nn_t = lp1nn_idx[self.doy[t]]

            # Remove current day from L + 1 nearest neighbor indices
            lnn_idx = lp1nn_t[lp1nn_t != t]

            # Get euclidean distance of current day from L nearest neighbours
            dist = np.linalg.norm(Xt[lnn_idx] - Xt[t], axis=1)

            # Take the K nearest neighbours
            knn_idx = lnn_idx[dist.argsort()][:K]

            # Randomly draw K nearest neighbor from distribution
            nn = (abs(pn - np.random.rand())).argmin()

            # Set starting index of sampled block
            j = knn_idx[nn]

            # Adjust block size if at end of input series
            B = n - i if i + self.B > n else self.B
            # Adjust selected block if at end of series
            j = n - B if j + B > n else j

            # Obtain K and L nearest neighbors for non-spatially averaged data
            X_knn = X[knn_idx]
            X_lnn = X[lnn_idx]

            # Apply perturbation for each day in block for each variable
            Xsim[i: i+B] = perturb(X[j: j+B].copy(),
                                   X_knn,
                                   X_lnn,
                                   self.P,
                                   self.interp)

        df = pd.DataFrame(Xsim, self.X.index, self.Xn.columns)
        df['Run'] = run_id
        df.set_index('Run', append=True, inplace=True)
        df = df.reorder_levels(['Run', 'Year', 'Month', 'Day'])

        return df


@njit
def perturb(A, knn, lnn, P, interp):
    n, m = A.shape
    # Go through each day in block
    for i in range(n):
        z = np.random.randn()
        # Go through each variable in day
        for j in range(m):
            # Calculate random variate
            if P[j] == 0:
                continue
            elif P[j] == 1:
                std_knn = np.sqrt(var_i(knn, j))
                z_j = np.random.normal(A[i, j], std_knn)
            else:
                if A[i, j] < 0.001:
                    continue
                else:
                    var_lnn = var_i_nonzero(lnn, j)
                    bm = np.sqrt(np.log10(var_lnn / A[i, j] + 1))
                    am = np.log10(A[i, j]) - 0.5 * bm
                    z_j = np.exp(am + bm * z)
            # Apply perturbation
            A[i, j] = interp * A[i, j] + (1 - interp) * z_j

    return A


def lnn_algorithm(doy, w, L):
    """
    Function to obtain the indices of the L+1 (includes current day) nearest
    neighbors given the day of year, window size, and value of L.

    Parameters
    ----------
    doy : ndarray
        An array consisting of the day of year for all data points. February
        29th should be marked as a negative number as it will not be considered
        for the L nearest neighbors.
    w : int
        Window size for number of days surrounding current day in the L nearest
        neighbors. This should be an even number.
    L : int
        The value of L. Calculated from L = N * (w + 1) - 1 where N is the
        number of years in the historical data.

    Returns
    -------
    lnnp1 : ndarray
        Output of shape (365, L + 1) corresponds to the indices of the L + 1
        nearest neighbors for each day of the year.
    """

    lnnp1 = np.zeros((365, L + 1), dtype=np.uint32)

    for i in range(365):
        # Set left and right bounds for window day of year (DOY)
        w_l = i - w // 2
        w_r = i + w // 2

        # Adjust bounds for DOY less than 0 and greater than 364
        if w_l < 0:
            w_l += 365
        if w_r > 364:
            w_r -= 365

        # Obtain indices of days falling within window for current DOY
        if (w_r - w_l) != w:
            lnnp1[i], = np.where(((w_l <= doy) | (w_r >= doy)) & (doy >= 0))
        else:
            lnnp1[i], = np.where((w_l <= doy) & (w_r >= doy))

    return lnnp1


@njit
def day_of_year(mon, day):
    doy = np.zeros(day.size, dtype=np.int32)
    count = 0
    for i, d in enumerate(day):
        if mon[i] == 2 and day[i] == 29:
            doy[i] = -1
        else:
            doy[i] = count % 365
            count += 1

    return doy


@njit
def var_i(arr, j):
    n = arr.shape[0]
    sum_i = 0
    for i in range(n):
        sum_i += arr[i, j]
    mean_i = sum_i / n
    var = 0
    for i in range(n):
        var += (arr[i, j] - mean_i) ** 2

    return var


@njit
def var_i_nonzero(arr, j):
    n = arr.shape[0]
    sum_i = 0
    for i in range(n):
        if arr[i, j] >= 0.001:
            sum_i += arr[i, j]
    mean_i = sum_i / n
    var = 0
    for i in range(n):
        if arr[i, j] >= 0.001:
            var += (arr[i, j] - mean_i) ** 2

    return var
