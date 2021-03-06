# -*- coding: utf-8 -*-
# pylint: disable=invalid-name

"""Copyright 2015 Roger R Labbe Jr.

FilterPy library.
http://github.com/rlabbe/filterpy

Documentation at:
https://filterpy.readthedocs.org

Supporting book at:
https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python

This is licensed under an MIT license. See the readme.MD file
for more information.
"""

import numpy as np
from filterpy.common import pretty_str


class MMAEFilterBank(object):
    """
    Implements the fixed Multiple Model Adaptive Estimator (MMAE). This
    is a bank of independent Kalman filters. This estimator computes the
    likelihood that each filter is the correct one, and blends their state
    estimates weighted by their likelihood to produce the state estimate.

    Parameters
    ----------

    filters : list of Kalman filters
        List of Kalman filters.

    p : list-like of floats
       Initial probability that each filter is the correct one. In general
       you'd probably set each element to 1./len(p).

    dim_x : float
        number of random variables in the state X

    H : Measurement matrix


    Examples
    --------

    ..code:
        ca = make_ca_filter(dt, noise_factor=0.6)
        cv = make_ca_filter(dt, noise_factor=0.6)
        cv.F[:,2] = 0 # remove acceleration term
        cv.P[2,2] = 0
        cv.Q[2,2] = 0

        filters = [cv, ca]
        bank = MMAEFilterBank(filters, p=(0.5, 0.5), dim_x=3)

        for z in zs:
            bank.predict()
            bank.update(z)

    Also, see my book Kalman and Bayesian Filters in Python
    https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python

    References
    ----------

    Zarchan and Musoff. "Fundamentals of Kalman filtering: A Practical
    Approach." AIAA, third edition.

    """

    def __init__(self, filters, p, dim_x, H=None):
        if len(filters) != len(p):
            raise ValueError('length of filters and p must be the same')

        if dim_x < 1:
            raise ValueError('dim_x must be >= 1')

        self.filters = filters
        self.p = np.asarray(p)
        self.dim_x = dim_x
        self.H = H[:]

        # try to form a reasonable initial values, but good luck!
        try:
            self.z = filters[0].z[:]
            self.x = filters[0].x[:]
            self.P = filters[0].P[:]

        except AttributeError:
            self.z = 0
            self.x = None
            self.P = None


    def predict(self, u=0):
        """
        Predict next position using the Kalman filter state propagation
        equations for each filter in the bank.

        Parameters
        ----------

        u : np.array
            Optional control vector. If non-zero, it is multiplied by B
            to create the control input into the system.
        """

        for f in self.filters:
            f.predict(u)


    def update(self, z, R=None, H=None):
        """
        Add a new measurement (z) to the Kalman filter. If z is None, nothing
        is changed.

        Parameters
        ----------

        z : np.array
            measurement for this update.

        R : np.array, scalar, or None
            Optionally provide R to override the measurement noise for this
            one call, otherwise  self.R will be used.

        H : np.array,  or None
            Optionally provide H to override the measurement function for this
            one call, otherwise  self.H will be used.
        """

        if H is None:
            H = self.H

        # new probability is recursively defined as prior * likelihood
        for i, f in enumerate(self.filters):
            f.update(z, R, H)
            self.p[i] *= f.likelihood

        self.p /= sum(self.p) # normalize

        # compute estimated state and covariance of the bank of filters.
        self.P = np.zeros(self.filters[0].P.shape)

        # state can be in form [x,y,z,...] or [[x, y, z,...]].T
        is_row_vector = (self.filters[0].x.ndim == 1)
        if is_row_vector:
            self.x = np.zeros(self.dim_x)
            for f, p in zip(self.filters, self.p):
                self.x += np.dot(f.x, p)
        else:
            self.x = np.zeros((self.dim_x, 1))
            for f, p in zip(self.filters, self.p):
                self.x = np.zeros((self.dim_x, 1))
                self.x += np.dot(f.x, p)

        for x, f, p in zip(self.x, self.filters, self.p):
            y = f.x - x
            self.P += p*(np.outer(y, y) + f.P)

        try:
            self.z = z[:]
        except IndexError:
            self.z = z


    def __repr__(self):
        return '\n'.join([
            'MMAEFilterBank object',
            pretty_str('dim_x', self.dim_x),
            pretty_str('x', self.x),
            pretty_str('P', self.P),
            pretty_str('log-p', self.p),
            ])
