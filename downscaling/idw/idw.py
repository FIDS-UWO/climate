from netCDF4 import num2date, date2num
from datetime import datetime
import xarray as xr
import pandas as pd
import numpy as np


def idw(file, varname, stations, extent=None, period=None,
        alpha=2, k=4, **kwargs):
    """
    Extract inverse distance weighting interpolated time series from netcdf
    file for a list of stations.

    Parameters
    ----------
    file : str or list
        file path to netcdf file. A list can be used to load multiple files
        that are to be combined.
    varname : str
        Name of the variable in the netcdf file to be used.
    stations : dict
        A python dictionary containing key : value pairs, where the key is the
        station name, and the value is a tuple containing (lat, lon) , where
        lat is measured in degrees north and lon is measured in 0 to +
        360 degrees from Greenwich.
    extent : list, optional
        A list describing the spatial domain for which the
        interpolation will take place. This should look like
        `[north, east, south, west]`. This can greatly reduce the amount of
        resources required for interpolation.
    period : tuple, optional
        The time period for which the interpolation will take place. For
        example, `[(1950, 1, 1), (1975, 1, 1)]')` will first extract the data
        for this time period. Date formats must be in yyyy-mm-dd. This can also
        greatly reduce interpolation time and RAM usage.
    alpha : float, default 2
        The coefficient with which to calculate the inverse distance of the
        neighboring points of a given station.
    k : int, default 4
        Number of closest data points to use in the interpolation.

    Returns
    -------
    result : pandas.DataFrame
        A pandas data frame containing columns for each station with
        interpolated data along the rows. Index labels are Year, Month, Day.

    Notes
    -----
    1. Ensure that the spatial extent is large enough to encapsulate all
       stations of interest.
    """
    # Load the data
    data, lat, lon, dates = load_data(file, varname, extent, period, **kwargs)

    # Convert points tuple to array
    points = np.array(list(stations.values()))

    # Do the interpolation
    interpolated = inv_dist(data, lat, lon, points, k=k, alpha=alpha)

    # Put together index and columns for output DataFrame
    idx = pd.MultiIndex.from_tuples([(d.year, d.month, d.day) for d in dates])
    col = pd.MultiIndex.from_tuples([(varname, s) for s in stations])

    result = pd.DataFrame(interpolated, index=idx, columns=col)
    result.index.names = ['Y', 'M', 'D']
    result.columns.names = ['Variable', 'Station']

    return result.sort_index(axis=1)


def load_data(file, varname, extent=None, period=None, **kwargs):
    """
    Loads netCDF files and extracts data given a spatial extend and time period
    of interest.
    """
    # Open either single or multi-file data set depending if list of wildcard
    if "*" in file or isinstance(file, list):
        ds = xr.open_mfdataset(file, decode_times=False)
    else:
        ds = xr.open_dataset(file, decode_times=False)

    # Construct condition based on spatial extents
    if extent:
        n, e, s, w = extent
        ds = ds.sel(lat=(ds.lat >= s) & (ds.lat <= n))
        # Account for extent crossing Greenwich
        if w > e:
            ds = ds.sel(lon=(ds.lon >= w) | (ds.lon <= e))
        else:
            ds = ds.sel(lon=(ds.lon >= w) & (ds.lon <= e))

    # Construct condition base on time period
    if period:
        t1 = date2num(datetime(*period[0]), ds.time.units, ds.time.calendar)
        t2 = date2num(datetime(*period[1]), ds.time.units, ds.time.calendar)
        ds = ds.sel(time=(ds.time >= t1) & (ds.time <= t2))

    # Extra keyword arguments to select from additional dimensions (e.g. plev)
    if kwargs:
        ds = ds.sel(**kwargs)

    # Load in the data to a numpy array
    dates = num2date(ds.time, ds.time.units, ds.time.calendar)
    arr = ds[varname].values
    lat = ds.lat.values
    lon = ds.lon.values

    # Convert pr units to mm/day
    if ds[varname].units == 'kg m-2 s-1':
        arr *= 86400
    # Convert tas units to degK
    elif ds[varname].units == 'K':
        arr -= 273.15

    return arr, lat, lon, dates


def inv_dist(data, lat, lon, points, k=4, alpha=2):
    """
    Inverse distance point interpolation function from grid.

    Parameters
    ----------
    data : ndarray
        array of data with shape (n, m, l).
    lat : ndarray
        latitude array of shape (l,).
    lon : ndarray
        longitude array of shape (m,).
    points : ndarray
        array consisting of lon,lat points with shape (q, 2).
    k : int, default 4
        p closest points to use in inverse distance calculation.
    alpha : float, default 2
        coefficient with which to calculate the inverse distance of the
        neighboring points of a given station.

    Returns
    -------
    result : ndarray
        interpolated result of shape (n, q).
    """
    n, m, l = data.shape
    # Pre-allocate memory to resulting array
    result = np.zeros((n, points.shape[0]))

    # Get lon, lat grid
    xx, yy = np.meshgrid(lon, lat)

    for q, (x0, y0) in enumerate(points):
        # Calculate distance of each grid point
        dist = np.sqrt((xx - x0)**2 + (yy - y0)**2)

        # Rank distances for each point
        rank = np.argsort(dist, axis=None).reshape(m, l)

        # Mask for k closest points
        ma = rank > (rank.max() - k)

        # Calculate weighting of each of the grid points
        weights = dist[ma]**-alpha / np.sum(dist[ma]**-alpha)

        # Get the interpolated result
        result[:, q] = data[:, ma] @ weights

    return result
