# -*- coding: utf-8 -*-
"""
Module responsible for the Generalized Lorenz-Mie Theory (GLMT) related
computations. Beam shape coefficients and wave components are calculated
here having the GLMT propositions in mind.

@author: Luiz Felipe Machado Votto
"""

import pathlib
from scipy import special
from scipy.io import mmread
import numpy as np
import pickle

from glmt.constants import (AXICON, WAVE_NUMBER, PERMEABILITY,
                           SPHERE_PERMEABILITY, REFFRACTIVE_INDEX,
                           WAVELENGTH)
from glmt.specials import (_riccati_bessel_j, d2_riccati_bessel_j,
                           legendre_p, legendre_tau, legendre_pi,
                           riccati_bessel_j, riccati_bessel_y,
                           d_riccati_bessel_j, d_riccati_bessel_y,
                           d2_riccati_bessel_j)
from glmt.frozenwave import THETA, COEFF, axicon_omega
from glmt.utils import get_max_it


path = './pickle'
PATH = "../mtx/gnm"
GTE = {}
GTM = {}
MAX_IT = 600
SHAPE = 'mtx'
DEGREES = [-1, 1]


def beam_shape_g(degree, order, axicon=AXICON, mode='TM', max_it=15, shape=SHAPE):
    if shape == 'bessel':
        return beam_shape_bessel(degree, order, axicon=axicon, mode=mode)

    if shape == 'fw':
        return beam_shape_fw(degree, order, mode=mode, max_it=max_it)

    if shape == 'mtx':
        return beam_shape_mtx(degree, order, mode=mode)

    raise ValueError('Shape \"%s\" is not supported' % shape)

def beam_shape_g_exa(degree, axicon=AXICON, bessel=True):
    """ Computes exact BSC from equations referenced by the article
    """
    if bessel:
        return special.j0(float((degree + 1/2) * np.sin(axicon)))

    return (1 + np.cos(axicon)) / (2 * degree * (degree + 1)) \
            * (legendre_tau(degree, 1, np.cos(axicon)) \
               + legendre_pi(degree, 1, np.cos(axicon)))

def beam_shape_bessel(degree, order, axicon=AXICON, mode='TM'):
    """ Computes BSC in terms of degree and order
    """
    if mode == 'TM':
        if order in [-1, 1]:
            return beam_shape_g_exa(degree, axicon=axicon) / 2
        else:
            return 0

    if mode == 'TE':
        retval = 1j * beam_shape_g_exa(degree, axicon=axicon) / 2
        if order == 1:
            return -retval
        elif order == -1:
            return retval
        else:
            return 0

    raise ValueError('Beam shape coefficients only work either for TM or TE modes.')

def beam_shape_fw(degree, order, mode='TM', max_it=15):
    """ Calculates BSCs given specific frozen wave parameters """
    if order not in [-1, 1]:
        return 0

    global GTE
    global GTM

    try:
        if mode == 'TM':
            return GTM[degree, order]

        if mode == 'TE':
            return GTE[degree, order]

    except KeyError:
        # We need to add the new coefficient to a cache.
        result = 0
        for q in range(-max_it, max_it):
            increment = COEFF[q] \
                        * special.j0(axicon_omega(degree, THETA[q]))
            result += increment
        if mode == 'TM':
            GTM[degree, order] = result / 2
            GTM[degree, -order] = GTM[degree, order]
            return GTM[degree, order]

        if mode == 'TE':
            GTE[degree, order] = -np.sign(order) \
                                 * 1j / 2 \
                                 * result
            GTE[degree, -order] = -GTE[degree, order]
            return GTE[degree, order]

    raise ValueError('Mode \"%s\" is not supported. Only \"TM\" or \"TE\".' % mode)

def _beam_shape_fw(degree, order, mode='TM', max_it=15):
    """ Calculates BSCs of a specific frozen wave """
    global GTE
    global GTM
    try:
        if mode == 'TM' and GTM:
            return GTM[degree, order]

        if mode == 'TE' and GTE:
            return GTE[degree, order]

    except KeyError:
        pass

    try:
        with open(str(pathlib.Path('../pickles/fw_g_%s.pickle' % mode).absolute()), 'rb') as f:
            pass
    except FileNotFoundError:
        with open(str(pathlib.Path('../pickles/fw_g_%s.pickle' % mode).absolute()), 'wb') as f:
            pickle.dump({}, f)

    with open(str(pathlib.Path('../pickles/fw_g_%s.pickle' % mode).absolute()), 'rb') as f:
        table = pickle.load(f)

    try:
        if mode == 'TM':
            for key in table:
                GTM[key] = table[key]
        if mode == 'TE':
            for key in table:
                GTE[key] = table[key]
        return table[degree, order]

    except KeyError:
        result = 0
        for q in range(-max_it, max_it):
                increment = COEFF[q] \
                            * special.j0(axicon_omega(degree, np.deg2rad(THETA[q])))
                result += increment
        if mode == 'TM':
            table[degree, order] = 1 / 2 * result
        if mode == 'TE':
            table[degree, order] = -np.sign(order) * 1j / 2 * result
        with open(str(pathlib.Path('../pickles/fw_g_%s.pickle' % mode).absolute()), 'wb') as f:
            pickle.dump(table, f)
        return table[degree, order]

    raise ValueError('This program understands only \'TM\' or \'TE\' modes, not %s.' % mode)

def beam_shape_mtx(degree, order, mode='TM', shape='3'):
    """ Get BSCs from .mtx file stored in the mtx directory. """
    global GTE
    global GTM
    path = str(pathlib.Path('../pickles/gfw_g_%s.pickle' % (mode + shape)).absolute())
    if mode == 'TM' and GTM:
        return GTM[degree, order]
    if mode == 'TE' and GTE:
        return GTE[degree, order]

    try:
        with open(path, 'rb') as f:
            pass
    except FileNotFoundError:
        with open(path, 'wb') as f:
            pickle.dump({}, f)

    with open(path, 'rb') as f:
        table = pickle.load(f)
        if mode == 'TM' and table:
            GTM = table
        if mode == 'TE' and table:
            GTE = table

    try:
        return table[degree, order]
    except KeyError:
        with open(str(pathlib.Path(PATH + mode + shape + '.mtx').absolute()), 'rb') as g:
            print("LOADING MATRIX: ", mode, "m = ", order, "n = ", degree)
            matrix = mmread(g)
        for row in matrix:
            table[row[0], row[1]] = row[2] + 1j * row[3]
        with open(path, 'wb') as f:
            pickle.dump(table, f)
        return table[degree, order]

def plane_wave_coefficient(degree, wave_number_k):
    """ Computes plane wave coefficient c_{n}^{pw}
    """
    return (1 / (1j * wave_number_k)) \
            * pow(-1j, degree) \
            * (2 * degree + 1) / (degree * (degree + 1))

def mie_coefficient_a(order, diameter=10E-6, permeability=PERMEABILITY,
                      sp_permeability=SPHERE_PERMEABILITY,
                      wavelength=WAVELENGTH,
                      reffractive=REFFRACTIVE_INDEX):
    alpha = np.pi * diameter / wavelength
    beta = reffractive * alpha
    return ((sp_permeability * riccati_bessel_j(order, alpha)
             * d_riccati_bessel_j(order, beta)
             - permeability * reffractive
             * d_riccati_bessel_j(order, alpha)
             * riccati_bessel_j(order, beta))
            / (sp_permeability * riccati_bessel_y(order, alpha)
               * d_riccati_bessel_j(order, beta)
               - permeability * reffractive
               * d_riccati_bessel_y(order, alpha)
               * riccati_bessel_j(order, beta)))

def mie_coefficient_b(order, diameter=10E-6, permeability=PERMEABILITY,
                      sp_permeability=SPHERE_PERMEABILITY,
                      wavelength=WAVELENGTH,
                      reffractive=REFFRACTIVE_INDEX):
    alpha = np.pi * diameter / wavelength
    beta = reffractive * alpha
    return ((permeability * reffractive
             * riccati_bessel_j(order, alpha)
             * d_riccati_bessel_j(order, beta)
             - sp_permeability
             * d_riccati_bessel_j(order, alpha)
             * riccati_bessel_j(order, beta))
            / (permeability * reffractive
               * riccati_bessel_y(order, alpha)
               * d_riccati_bessel_j(order, beta)
               - sp_permeability
               * d_riccati_bessel_y(order, alpha)
               * riccati_bessel_j(order, beta)))


def radial_electric_i_tm(radial, theta, phi, wave_number_k):
    """ Computes the radial component of inciding electric field in TM mode.
    """
    result = 0
    n = 1

    riccati_bessel_list = _riccati_bessel_j(get_max_it(radial),
                                            wave_number_k * radial)
    riccati_bessel = riccati_bessel_list[0]

    # while n <= get_max_it(radial):
    max_it = get_max_it(radial)
    while n <= max_it:
        for m in DEGREES:
            increment = plane_wave_coefficient(n, wave_number_k) \
                      * beam_shape_g(n, m, mode='TM') \
                      * (d2_riccati_bessel_j(n, wave_number_k * radial) \
                         + riccati_bessel[n]) \
                      * legendre_p(n, abs(m), np.cos(theta)) \
                      * np.exp(1j * m * phi)
            result += increment
        n += 1

    return wave_number_k * result

def theta_electric_i_tm(radial, theta, phi, wave_number_k):
    """ Computes the theta component of inciding electric field in TM mode.
    """
    result = 0
    n = 1
    # Due to possible singularity near origin, we approximate null radial
    # component to a small value.
    radial = radial or 1E-16

    riccati_bessel_list = _riccati_bessel_j(get_max_it(radial),
                                            wave_number_k * radial)
    d_riccati_bessel = riccati_bessel_list[1]
    max_it = get_max_it(radial)
    while n <= max_it:
        for m in DEGREES:
            increment = plane_wave_coefficient(n, wave_number_k) \
                      * beam_shape_g(n, m, mode='TM') \
                      * d_riccati_bessel[n] \
                      * legendre_tau(n, abs(m), np.cos(theta)) \
                      * np.exp(1j * m * phi)
            result += increment
        n += 1
    return result / radial

def theta_electric_i_te(radial, theta, phi, wave_number_k):
    """ Computes the theta component of inciding electric field in TE mode.
    """
    result = 0
    n = 1
    # Due to possible singularity near origin, we approximate null radial
    # component to a small value.
    radial = radial or 1E-16

    riccati_bessel_list = _riccati_bessel_j(get_max_it(radial),
                                            wave_number_k * radial)
    riccati_bessel = riccati_bessel_list[0]
    max_it = get_max_it(radial)
    while n <= max_it:
        for m in DEGREES:
            increment = m \
                      * plane_wave_coefficient(n, wave_number_k) \
                      * beam_shape_g(n, m, mode='TE') \
                      * riccati_bessel[n] \
                      * legendre_pi(n, abs(m), np.cos(theta)) \
                      * np.exp(1j * m * phi)
            result += increment
        n += 1

    return result / radial

def phi_electric_i_tm(radial, theta, phi, wave_number_k):
    """ Computes the phi component of inciding electric field in TM mode.
    """
    result = 0
    n = 1
    # Due to possible singularity near origin, we approximate null radial
    # component to a small value.
    radial = radial or 1E-16

    riccati_bessel_list = _riccati_bessel_j(get_max_it(radial),
                                            wave_number_k * radial)
    d_riccati_bessel = riccati_bessel_list[1]

    max_it = get_max_it(radial)
    while n <= max_it:
        for m in DEGREES:
            increment = m \
                      * plane_wave_coefficient(n, wave_number_k) \
                      * beam_shape_g(n, m, mode='TM') \
                      * d_riccati_bessel[n] \
                      * legendre_pi(n, abs(m), np.cos(theta)) \
                      * np.exp(1j * m * phi)
            result += increment
        n += 1

    return 1j * result / radial

def phi_electric_i_te(radial, theta, phi, wave_number_k):
    """ Computes the phi component of inciding electric field in TE mode.
    """
    result = 0
    n = 1
    m = 0
    # Due to possible singularity near origin, we approximate null radial
    # component to a small value.
    radial = radial or 1E-16

    riccati_bessel_list = _riccati_bessel_j(get_max_it(radial),
                                            wave_number_k * radial)
    riccati_bessel = riccati_bessel_list[0]

    max_it = get_max_it(radial)
    while n <= max_it:
        for m in DEGREES:
            increment = plane_wave_coefficient(n, wave_number_k) \
                      * beam_shape_g(n, m, mode='TE') \
                      * riccati_bessel[n] \
                      * legendre_tau(n, abs(m), np.cos(theta)) \
                      * np.exp(1j * m * phi)
            result += increment
        n += 1

    return 1j * result / radial

def abs_theta_electric_i(radial, theta, phi, wave_number_k):
    """ Calculates absolute value of inciding theta component """
    retval = theta_electric_i_tm(radial, theta, phi, wave_number_k) \
             + theta_electric_i_te(radial, theta, phi, wave_number_k)
    return abs(retval)

def abs_phi_electric_i(radial, theta, phi, wave_number_k):
    """ Calculates absolute value of inciding phi component """
    retval = phi_electric_i_tm(radial, theta, phi, wave_number_k) \
             + phi_electric_i_te(radial, theta, phi, wave_number_k)
    return abs(retval)

def square_absolute_electric_i(radial, theta, phi, wave_number_k):
    """ Calculates absolute value of inciding electric wave """
    retval = pow(abs(radial_electric_i_tm(radial, theta, phi, wave_number_k)),
                 2)
    retval += pow(abs_theta_electric_i(radial, theta, phi, wave_number_k), 2)
    retval += pow(abs_phi_electric_i(radial, theta, phi, wave_number_k), 2)
    return retval

def theta_magnetic_i_tm(radial, theta, phi, wave_number_k):
    """ Computes the theta component of inciding magnetic field in TM mode.
    """
    result = 0
    n = 1
    # Due to possible singularity near origin, we approximate null radial
    # component to a small value.
    radial = radial or 1E-16

    riccati_bessel_list = _riccati_bessel_j(get_max_it(radial),
                                            wave_number_k * radial)
    riccati_bessel = riccati_bessel_list[0]

    max_it = get_max_it(radial)
    while n <= max_it:
        for m in DEGREES:
            increment = m \
                      * plane_wave_coefficient(n, wave_number_k) \
                      * beam_shape_g(n, m, mode='TM') \
                      * riccati_bessel[n] \
                      * legendre_pi(n, abs(m), np.cos(theta)) \
                      * np.exp(1j * m * phi)
            result += increment
        n += 1

    return -result / radial

def phi_magnetic_i_tm(radial, theta, phi, wave_number_k):
    """ Computes the phi component of inciding magnetic field in TM mode.
    """
    result = 0
    n = 1
    # Due to possible singularity near origin, we approximate null radial
    # component to a small value.
    radial = radial or 1E-16

    riccati_bessel_list = _riccati_bessel_j(get_max_it(radial),
                                            wave_number_k * radial)
    riccati_bessel = riccati_bessel_list[0]

    max_it = get_max_it(radial)
    while n <= max_it:
        for m in DEGREES:
            increment = plane_wave_coefficient(n, wave_number_k) \
                      * beam_shape_g(n, m, mode='TM') \
                      * riccati_bessel[n] \
                      * legendre_tau(n, abs(m), np.cos(theta)) \
                      * np.exp(1j * m * phi)
            result += increment
        n += 1

    return -1j * result / radial

def radial_magnetic_i_te(radial, theta, phi, wave_number_k):
    """ Computes the radial component of inciding magnetic field in TE mode.
    """
    result = 0
    n = 1


    riccati_bessel_list = _riccati_bessel_j(get_max_it(radial),
                                            wave_number_k * radial)
    riccati_bessel = riccati_bessel_list[0]
    while n <= get_max_it(radial):
        for m in DEGREES:
            increment = plane_wave_coefficient(n, wave_number_k) \
                      * beam_shape_g(n, m, mode='TE') \
                      * (d2_riccati_bessel_j(n, wave_number_k * radial) \
                         + riccati_bessel[n]) \
                      * legendre_p(n, abs(m), np.cos(theta)) \
                      * np.exp(1j * m * phi)
            result += increment
        n += 1

    return wave_number_k * result

def theta_magnetic_i_te(radial, theta, phi, wave_number_k):
    """ Computes the theta component of inciding magnetic field in TE mode.
    """
    result = 0
    n = 1
    # Due to possible singularity near origin, we approximate null radial
    # component to a small value.
    radial = radial or 1E-16

    riccati_bessel_list = _riccati_bessel_j(get_max_it(radial),
                                            wave_number_k * radial)
    d_riccati_bessel = riccati_bessel_list[1]

    max_it = get_max_it(radial)
    while n <= max_it:
        for m in DEGREES:
            increment = plane_wave_coefficient(n, wave_number_k) \
                      * beam_shape_g(n, m, mode='TE') \
                      * d_riccati_bessel[n] \
                      * legendre_tau(n, abs(m), np.cos(theta)) \
                      * np.exp(1j * m * phi)
            result += increment
        n += 1

    return result / radial

def phi_magnetic_i_te(radial, theta, phi, wave_number_k):
    """ Computes the phi component of inciding magnetic field in TE mode.
    """
    result = 0
    n = 1
    # Due to possible singularity near origin, we approximate null radial
    # component to a small value.
    radial = radial or 1E-16

    riccati_bessel_list = _riccati_bessel_j(get_max_it(radial),
                                            wave_number_k * radial)
    d_riccati_bessel = riccati_bessel_list[1]

    max_it = get_max_it(radial)
    while n <= max_it:
        for m in DEGREES:
            increment = m \
                      * plane_wave_coefficient(n, wave_number_k) \
                      * beam_shape_g(n, m, mode='TE') \
                      * d_riccati_bessel[n] \
                      * legendre_pi(n, abs(m), np.cos(theta)) \
                      * np.exp(1j * m * phi)
            result += increment
        n += 1

    return 1j * result / radial

def abs_theta_magnetic_i(radial, theta, phi, wave_number_k):
    """ Calculates absolute value of inciding theta component """
    retval = theta_magnetic_i_tm(radial, theta, phi, wave_number_k) \
             + theta_magnetic_i_te(radial, theta, phi, wave_number_k)
    return abs(retval)

def abs_phi_magnetic_i(radial, theta, phi, wave_number_k):
    """ Calculates absolute value of inciding phi component """
    retval = phi_magnetic_i_tm(radial, theta, phi, wave_number_k) \
             + phi_magnetic_i_te(radial, theta, phi, wave_number_k)
    return abs(retval)

def square_absolute_magnetic_i(radial, theta, phi, wave_number_k):
    """ Calculates absolute value of inciding magnetic wave """
    retval = pow(abs(radial_magnetic_i_te(radial, theta, phi, wave_number_k)),
                 2)
    retval += pow(abs_theta_magnetic_i(radial, theta, phi, wave_number_k), 2)
    retval += pow(abs_phi_magnetic_i(radial, theta, phi, wave_number_k), 2)
    return retval

def radial_electric_tm_increment(max_it,
                                 radial,
                                 theta=np.pi/2,
                                 phi=0,
                                 wave_number_k=WAVE_NUMBER):
    result = 0
    riccati_bessel_list = _riccati_bessel_j(get_max_it(radial),
                                            wave_number_k * radial)
    riccati_bessel = riccati_bessel_list[0]
    for n in range(1, max_it):
        for m in DEGREES:
            increment = plane_wave_coefficient(n, wave_number_k) \
                      * beam_shape_g(n, m, mode='TM') \
                      * (d2_riccati_bessel_j(n, wave_number_k * radial) \
                         + riccati_bessel[n]) \
                      * legendre_p(n, abs(m), np.cos(theta)) \
                      * np.exp(1j * m * phi)
            result += increment
    return abs(wave_number_k * result)
