"""Compare the output of Skyfield with the same routines from NOVAS."""

from itertools import product
from numpy import array, einsum
from unittest import TestCase

from skyfield import (angles, coordinates, earthlib, framelib, nutationlib,
                      planets, precessionlib, starlib, timescales)

# Since some users might run these tests without having installed our
# test dependencies, we detect import errors and skip these tests if the
# resources they need are not available.

try:
    import de405
except ImportError:
    de405 = None

try:
    import novas
    import novas_de405
except ImportError:
    novas = None
else:
    import novas.compat as c
    import novas.compat.eph_manager

    jd_start, jd_end, number = c.eph_manager.ephem_open()  # needs novas_de405

    c_nutation = c.nutation
    import novas.compat.nutation  # overwrites nutation() function with module!

    T0 = timescales.T0
    TA = c.julian_date(1969, 7, 20, 20. + 18./60.)  # arbitrary test date
    TB = c.julian_date(2012, 12, 21)                # arbitrary test date

    A0 = array([T0])
    AA = array([TA])
    AB = array([TB])

tau = angles.tau
degree = tau / 360.0
arcminute = degree / 60.0
arcsecond = arcminute / 60.0
meter = 1.0 / earthlib.AU_KM

planet_codes = {
    'mercury': 1,
    'venus': 2,
    'mars': 4,
    'jupiter': 5,
    'saturn': 6,
    'uranus': 7,
    'neptune': 8,
    'pluto': 9,
    'sun': 10,
    'moon': 11,
    }

planets_to_test = planet_codes.keys()

class NOVASTests(TestCase):

    @classmethod
    def setUpClass(cls):
        if de405 is None or novas is None:
            cls.__unittest_skip__ = True
            return
        cls.e = planets.Ephemeris(de405)

    def setUp(self):
        self.delta = 0.0

    def eq(self, first, second, delta=None):
        if delta is None:
            delta = self.delta
        if hasattr(first, 'shape') or hasattr(second, 'shape'):
            failed = abs(first - second).max() > delta
        else:
            failed = abs(first - second) > delta
        if failed:
            appendix = ('\nbecause the difference is\n%r\ntimes too big'
                        % (abs(first - second) / delta)) if delta else ''
            raise AssertionError(
                '%r\ndoes not equal\n%r\nwithin the error bound\n%r%s'
                % (first, second, delta, appendix))

    # Tests of generating a stellar position.

    def TODO_test_star_deflected_by_jupiter(self):
        for jd in [T0, TA, TB]:
            star = c.make_cat_entry(
                star_name=b'Star', catalog=b'cat', star_num=101,
                ra=1.59132070233, dec=8.5958876464,
                pm_ra=0.0, pm_dec=0.0,
                parallax=0.0, rad_vel=0.0,
                )
            ra, dec = c.app_star(jd, star)

            earth = self.e.earth
            star = starlib.Star(
                ra=1.59132070233, dec=8.5958876464,
                pm_ra=0.0, pm_dec=0.0,
                parallax=0.0, rad_vel=0.0,
                )
            g = earth(jd).observe(star).apparent()

            self.eq(ra * tau / 24.0, g.ra, 0.001 * arcsecond)
            self.eq(dec * tau / 360.0, g.dec, 0.001 * arcsecond)

    # Tests of generating a full position or coordinate.

    def test_astro_planet(self):

        for t, name in product([T0, TA, TB], planets_to_test):
            obj = c.make_object(0, planet_codes[name], b'planet', None)
            ra, dec, dis = c.astro_planet(t, obj)

            earth = self.e.earth
            planet = getattr(self.e, name)
            g = earth(t).observe(planet).astrometric()

            self.eq(ra * tau / 24.0, g.ra, 0.001 * arcsecond)
            self.eq(dec * tau / 360.0, g.dec, 0.001 * arcsecond)
            self.eq(dis, g.distance, 0.1 * meter)

    def test_app_planet(self):

        for t, name in product([T0, TA, TB], planets_to_test):
            obj = c.make_object(0, planet_codes[name], b'planet', None)
            ra, dec, dis = c.app_planet(t, obj)

            earth = self.e.earth
            planet = getattr(self.e, name)
            g = earth(t).observe(planet).apparent()

            self.eq(ra * tau / 24.0, g.ra, 0.001 * arcsecond)
            self.eq(dec * tau / 360.0, g.dec, 0.001 * arcsecond)
            self.eq(dis, g.distance, 0.1 * meter)

    def test_topo_planet(self):
        position = c.make_on_surface(45.0, -75.0, 0.0, 10.0, 1010.0)
        ggr = coordinates.Topos('75 W', '45 N', 0.0,
                                temperature=10.0, pressure=1010.0)
        ggr.earth = self.e.earth
        ggr.ephemeris = self.e
        delta_t = 0

        for t, name in product([T0, TA, TB], planets_to_test):
            obj = c.make_object(0, planet_codes[name], b'planet', None)
            ra, dec, dis = c.topo_planet(t, delta_t, obj, position)

            planet = getattr(self.e, name)
            g = ggr(t).observe(planet).apparent()

            self.eq(ra * tau / 24.0, g.ra, 0.001 * arcsecond)
            self.eq(dec * tau / 360.0, g.dec, 0.001 * arcsecond)
            self.eq(dis, g.distance, 0.1 * meter)  # TODO: improve this?

    # Tests of basic functions.

    def test_cal_date(self):
        for jd in 0.0, 2414988.5, 2415020.31352, 2442249.5, 2456335.2428472:
            assert c.cal_date(jd) == timescales.cal_date(jd)

    def test_earth_rotation_angle(self):
        self.delta = 1e-12

        a0 = c.era(T0)
        aA = c.era(TA)
        aB = c.era(TB)

        t = array([T0, TA, TB])
        v = timescales.earth_rotation_angle(t)
        self.eq(v, [a0, aA, aB])

    def test_earth_tilt(self):
        self.delta = 1e-14

        vars0 = c.e_tilt(T0)
        vars1 = c.e_tilt(TA)
        vars2 = c.e_tilt(TB)

        t = array([T0, TA, TB])
        v = nutationlib.earth_tilt(t)
        for i in range(len(v)):
            self.eq(v[i], [vars0[i], vars1[i], vars2[i]])

    def test_equation_of_the_equinoxes_complimentary_terms(self):
        self.delta = 1e-23

        e0 = c.ee_ct(T0, 0.0, 0)
        eA = c.ee_ct(TA, 0.0, 0)
        eB = c.ee_ct(TB, 0.0, 0)

        t = array([T0, TA, TB])
        v = nutationlib.equation_of_the_equinoxes_complimentary_terms(t)
        self.eq(v, [e0, eA, eB])

    def test_frame_tie(self):
        self.delta = 1e-15
        v = array([1, 2, 3])

        self.eq(c.frame_tie(v, 0), v.dot(framelib.ICRS_to_J2000))
        self.eq(c.frame_tie(v, -1), v.dot(framelib.J2000_to_ICRS))

    def test_fundamental_arguments(self):
        self.delta = 1e-12

        args0 = c.fund_args(jcentury(T0))
        argsA = c.fund_args(jcentury(TA))
        argsB = c.fund_args(jcentury(TB))

        t = array([T0, TA, TB])
        v = nutationlib.fundamental_arguments(jcentury(t))
        self.eq(v.T, [args0, argsA, argsB])

    def test_geocentric_position_and_velocity(self):
        self.delta = 1e-13

        delta_t = 0.0
        observer = c.make_observer_on_surface(45.0, -75.0, 0.0, 10.0, 1010.0)

        pos0, vel0 = c.geo_posvel(T0, delta_t, observer)
        posA, velA = c.geo_posvel(TA, delta_t, observer)

        topos = coordinates.Topos('75 W', '45 N', elevation=0.0,
                                  temperature=10.0, pressure=1010.0)

        t = array([T0, TA])
        posv, velv = earthlib.geocentric_position_and_velocity(topos, t)
        self.eq(posv.T, [pos0, posA])
        self.eq(velv.T, [vel0, velA])

    def test_iau2000a(self):
        self.delta = 1e-19

        psi0, eps0 = c.nutation.iau2000a(T0, 0.0)
        psiA, epsA = c.nutation.iau2000a(TA, 0.0)
        psiB, epsB = c.nutation.iau2000a(TB, 0.0)

        t = array([T0, TA, TB])
        psi, eps = nutationlib.iau2000a(t)
        self.eq(psi, [psi0, psiA, psiB])
        self.eq(eps, [eps0, epsA, epsB])

    def test_julian_date(self):
        for args in (
              (-4712, 1, 1, 0.0),
              (-4712, 3, 1, 0.0),
              (-4712, 12, 31, 0.5),
              (-241, 3, 25, 19.0),
              (530, 9, 27, 23.5),
              (1976, 3, 7, 12.5),
              (2000, 1, 1, 0.0),
              ):
            self.eq(c.julian_date(*args), timescales.julian_date(*args))

    def test_mean_obliq(self):
        self.delta = 0

        m0 = c.mean_obliq(T0)
        mA = c.mean_obliq(TA)
        mB = c.mean_obliq(TB)

        t = array([T0, TA, TB])
        v = nutationlib.mean_obliquity(t)
        self.eq(v, [m0, mA, mB])

    def test_nutation(self):
        self.delta = 1e-15
        v = array([1, 2, 3])

        v0 = c_nutation(T0, v, direction=0)
        va = c_nutation(TA, v, direction=0)
        vb = c_nutation(TB, v, direction=0)

        dates = array([T0, TA, TB])
        v = einsum('i,ijk->jk', v, nutationlib.compute_nutation(dates))

        self.eq(v0, v[:,0])
        self.eq(va, v[:,1])
        self.eq(vb, v[:,2])

    def test_precession(self):
        self.delta = 1e-15
        v = array([1, 2, 3])

        va = c.precession(T0, v, TA)
        vb = c.precession(T0, v, TB)

        ab = array([TA, TB])
        vab = einsum('i,ijk->jk', v, precessionlib.compute_precession(ab))

        self.eq(va, vab[:,0])
        self.eq(vb, vab[:,1])

    def test_sidereal_time(self):
        delta_t = 0.0
        self.delta = 1e-13

        st0 = c.sidereal_time(T0, 0.0, delta_t, False, True)
        stA = c.sidereal_time(TA, 0.0, delta_t, False, True)
        stB = c.sidereal_time(TB, 0.0, delta_t, False, True)

        t = array([T0, TA, TB])
        v = timescales.sidereal_time(t, delta_t)
        self.eq(v, [st0, stA, stB])

    def test_terra(self):
        self.delta = 1e-18

        observer = c.make_on_surface(45.0, -75.0, 0.0, 10.0, 1010.0)

        class Topos(object):
            latitude = 45.0 * angles.DEG2RAD
            longitude = -75.0 * angles.DEG2RAD
            elevation = 0.0
        topos = Topos()

        pos0, vel0 = array(c.terra(observer, 11.0))
        pos1, vel1 = array(c.terra(observer, 23.9))

        posn, veln = earthlib.terra(topos, array([11.0, 23.9]))

        self.eq(pos0, posn[:,0])
        self.eq(pos1, posn[:,1])
        self.eq(vel0, veln[:,0])
        self.eq(vel1, veln[:,1])

    def test_tdb2tt(self):
        self.delta = 1e-16

        tt0 = c.tdb2tt(T0)[1]
        ttA = c.tdb2tt(TA)[1]
        ttB = c.tdb2tt(TB)[1]

        t = array([T0, TA, TB])
        v = timescales.tdb_minus_tt(t)
        self.eq(v, [tt0, ttA, ttB])

def jcentury(t):
    return (t - T0) / 36525.0