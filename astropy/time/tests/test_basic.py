# Licensed under a 3-clause BSD style license - see LICENSE.rst

# TEST_UNICODE_LITERALS

import copy
import functools
import sys

from datetime import datetime, tzinfo, timedelta

import numpy as np

from ...tests.helper import pytest
from .. import Time, ScaleValueError, erfa_time, TIME_SCALES
from ...coordinates import EarthLocation


allclose_jd = functools.partial(np.allclose, rtol=2. ** -52, atol=0)
allclose_jd2 = functools.partial(np.allclose, rtol=2. ** -52,
                                 atol=2. ** -52)  # 20 ps atol
allclose_sec = functools.partial(np.allclose, rtol=2. ** -52,
                                 atol=2. ** -52 * 24 * 3600)  # 20 ps atol
allclose_year = functools.partial(np.allclose, rtol=2. ** -52,
                                  atol=0.)  # 14 microsec at current epoch


class TestBasic():
    """Basic tests stemming from initial example and API reference"""

    def test_simple(self):
        times = ['1999-01-01 00:00:00.123456789', '2010-01-01 00:00:00']
        t = Time(times, format='iso', scale='utc')
        assert (repr(t) == "<Time object: scale='utc' format='iso' "
                "value=['1999-01-01 00:00:00.123' '2010-01-01 00:00:00.000']>")
        assert allclose_jd(t.jd1, np.array([2451179.5, 2455197.5]))
        assert allclose_jd2(t.jd2, np.array([1.4288980208333335e-06,
                                             0.00000000e+00]))

        # Set scale to TAI
        t = t.tai
        assert (repr(t) == "<Time object: scale='tai' format='iso' "
                "value=['1999-01-01 00:00:32.123' '2010-01-01 00:00:34.000']>")
        assert allclose_jd(t.jd1, np.array([2451179.5, 2455197.5]))
        assert allclose_jd2(t.jd2, np.array([0.00037179926839122024, 0.00039351851851851852]))

        # Get a new ``Time`` object which is referenced to the TT scale
        # (internal JD1 and JD1 are now with respect to TT scale)"""

        assert (repr(t.tt) == "<Time object: scale='tt' format='iso' "
                "value=['1999-01-01 00:01:04.307' '2010-01-01 00:01:06.184']>")

        # Get the representation of the ``Time`` object in a particular format
        # (in this case seconds since 1998.0).  This returns either a scalar or
        # array, depending on whether the input was a scalar or array"""

        assert allclose_sec(t.cxcsec, np.array([31536064.307456788, 378691266.18400002]))

    def test_different_dimensions(self):
        """Test scalars, vector, and higher-dimensions"""
        # scalar
        val, val1 = 2450000.0, 0.125
        t1 = Time(val, val1, format='jd')
        assert t1.isscalar is True and t1.shape == ()
        # vector
        val = np.arange(2450000., 2450010.)
        t2 = Time(val, format='jd')
        assert t2.isscalar is False and t2.shape == val.shape
        # explicitly check broadcasting for mixed vector, scalar.
        val2 = 0.
        t3 = Time(val, val2, format='jd')
        assert t3.isscalar is False and t3.shape == val.shape
        val2 = (np.arange(5.)/10.).reshape(5, 1)
        # now see if broadcasting to two-dimensional works
        t4 = Time(val, val2, format='jd')
        assert t4.isscalar is False
        assert t4.shape == np.broadcast(val, val2).shape

    def test_copy_time(self):
        """Test copying the values of a Time object by passing it into the
        Time initializer.
        """
        t = Time(2455197.5, format='jd', scale='utc')

        t2 = Time(t, copy=False)
        assert t.jd - t2.jd == 0
        assert (t - t2).jd == 0
        assert t._time.jd1 is t2._time.jd1
        assert t._time.jd2 is t2._time.jd2

        t2 = Time(t, copy=True)
        assert t.jd - t2.jd == 0
        assert (t - t2).jd == 0
        assert t._time.jd1 is not t2._time.jd1
        assert t._time.jd2 is not t2._time.jd2

        # Include initializers
        t2 = Time(t, format='iso', scale='tai', precision=1)
        assert t2.value == '2010-01-01 00:00:34.0'
        t2 = Time(t, format='iso', scale='tai', out_subfmt='date')
        assert t2.value == '2010-01-01'

    def test_getitem(self):
        """Test that Time objects holding arrays are properly subscriptable,
        set isscalar as appropriate, and also subscript delta_ut1_utc, etc."""

        mjd = np.arange(50000, 50010)
        t = Time(mjd, format='mjd', scale='utc', location=('45d', '50d'))
        t1 = t[3]
        assert t1.isscalar is True
        assert t1._time.jd1 == t._time.jd1[3]
        assert t1.location is t.location
        t1a = Time(mjd[3], format='mjd', scale='utc')
        assert t1a.isscalar is True
        assert np.all(t1._time.jd1 == t1a._time.jd1)
        t1b = Time(t[3])
        assert t1b.isscalar is True
        assert np.all(t1._time.jd1 == t1b._time.jd1)
        t2 = t[4:6]
        assert t2.isscalar is False
        assert np.all(t2._time.jd1 == t._time.jd1[4:6])
        assert t2.location is t.location
        t2a = Time(t[4:6])
        assert t2a.isscalar is False
        assert np.all(t2a._time.jd1 == t._time.jd1[4:6])
        t2b = Time([t[4], t[5]])
        assert t2b.isscalar is False
        assert np.all(t2b._time.jd1 == t._time.jd1[4:6])
        t2c = Time((t[4], t[5]))
        assert t2c.isscalar is False
        assert np.all(t2c._time.jd1 == t._time.jd1[4:6])
        t.delta_tdb_tt = np.arange(len(t))  # Explicitly set (not testing .tdb)
        t3 = t[4:6]
        assert np.all(t3._delta_tdb_tt == t._delta_tdb_tt[4:6])
        t4 = Time(mjd, format='mjd', scale='utc',
                  location=(np.arange(len(mjd)), np.arange(len(mjd))))
        t5 = t4[3]
        assert t5.location == t4.location[3]
        t6 = t4[4:6]
        assert np.all(t6.location == t4.location[4:6])
        # check it is a view
        # (via ndarray, since quantity setter problematic for structured array)
        allzeros = np.array((0., 0., 0.), dtype=t4.location.dtype)
        assert t6.location.view(np.ndarray)[-1] != allzeros
        assert t4.location.view(np.ndarray)[5] != allzeros
        t6.location.view(np.ndarray)[-1] = allzeros
        assert t4.location.view(np.ndarray)[5] == allzeros
        # Test subscription also works for two-dimensional arrays.
        frac = np.arange(0., 0.999, 0.2)
        t7 = Time(mjd[:, np.newaxis] + frac, format='mjd', scale='utc',
                  location=('45d', '50d'))
        assert t7[0, 0]._time.jd1 == t7._time.jd1[0, 0]
        assert t7[0, 0].isscalar is True
        assert np.all(t7[5]._time.jd1 == t7._time.jd1[5])
        assert np.all(t7[5]._time.jd2 == t7._time.jd2[5])
        assert np.all(t7[:, 2]._time.jd1 == t7._time.jd1[:, 2])
        assert np.all(t7[:, 2]._time.jd2 == t7._time.jd2[:, 2])
        assert np.all(t7[:, 0]._time.jd1 == t._time.jd1)
        assert np.all(t7[:, 0]._time.jd2 == t._time.jd2)


    def test_properties(self):
        """Use properties to convert scales and formats.  Note that the UT1 to
        UTC transformation requires a supplementary value (``delta_ut1_utc``)
        that can be obtained by interpolating from a table supplied by IERS.
        This will be included in the package later."""

        t = Time('2010-01-01 00:00:00', format='iso', scale='utc')
        t.delta_ut1_utc = 0.3341  # Explicitly set one part of the xform
        assert allclose_jd(t.jd, 2455197.5)
        assert t.iso == '2010-01-01 00:00:00.000'
        assert t.tt.iso == '2010-01-01 00:01:06.184'
        assert t.tai.iso == '2010-01-01 00:00:34.000'
        assert allclose_jd(t.utc.jd, 2455197.5)
        assert allclose_jd(t.ut1.jd, 2455197.500003867)
        assert t.tcg.isot == '2010-01-01T00:01:06.910'
        assert allclose_sec(t.unix, 1262304000.0)
        assert allclose_sec(t.cxcsec, 378691266.184)
        assert allclose_sec(t.gps, 946339215.0)
        assert t.datetime == datetime(2010, 1, 1)

    def test_precision(self):
        """Set the output precision which is used for some formats.  This is
        also a test of the code that provides a dict for global and instance
        options."""

        t = Time('2010-01-01 00:00:00', format='iso', scale='utc')
        # Uses initial class-defined precision=3
        assert t.iso == '2010-01-01 00:00:00.000'

        # Set global precision = 5  XXX this uses private var, FIX THIS
        Time._precision = 5
        assert t.iso == '2010-01-01 00:00:00.00000'

        # Set instance precision to 9
        t.precision = 9
        assert t.iso == '2010-01-01 00:00:00.000000000'
        assert t.tai.utc.iso == '2010-01-01 00:00:00.000000000'

        # Restore global to original default of 3, instance is still at 9
        Time._precision = 3
        assert t.iso == '2010-01-01 00:00:00.000000000'

        # Make a new time instance and confirm precision = 3
        t = Time('2010-01-01 00:00:00', format='iso', scale='utc')
        assert t.iso == '2010-01-01 00:00:00.000'

    def test_transforms(self):
        """Transform from UTC to all supported time scales (TAI, TCB, TCG,
        TDB, TT, UT1, UTC).  This requires auxilliary information (latitude and
        longitude)."""

        lat = 19.48125
        lon = -155.933222
        t = Time('2006-01-15 21:24:37.5', format='iso', scale='utc',
                 precision=6, location=(lon, lat))
        t.delta_ut1_utc = 0.3341  # Explicitly set one part of the xform
        assert t.utc.iso == '2006-01-15 21:24:37.500000'
        assert t.ut1.iso == '2006-01-15 21:24:37.834100'
        assert t.tai.iso == '2006-01-15 21:25:10.500000'
        assert t.tt.iso == '2006-01-15 21:25:42.684000'
        assert t.tcg.iso == '2006-01-15 21:25:43.322690'
        assert t.tdb.iso == '2006-01-15 21:25:42.684373'
        assert t.tcb.iso == '2006-01-15 21:25:56.893952'

    def test_location(self):
        """Check that location creates an EarthLocation object, and that
        such objects can be used as arguments.
        """
        lat = 19.48125
        lon = -155.933222
        t = Time(['2006-01-15 21:24:37.5'], format='iso', scale='utc',
                 precision=6, location=(lon, lat))
        assert isinstance(t.location, EarthLocation)
        location = EarthLocation(lon, lat)
        t2 = Time(['2006-01-15 21:24:37.5'], format='iso', scale='utc',
                  precision=6, location=location)
        assert isinstance(t2.location, EarthLocation)
        assert t2.location == t.location
        t3 = Time(['2006-01-15 21:24:37.5'], format='iso', scale='utc',
                  precision=6, location=(location.x, location.y, location.z))
        assert isinstance(t3.location, EarthLocation)
        assert t3.location == t.location

    def test_location_array(self):
        """Check that location arrays are checked for size and used
        for the corresponding times.  Also checks that erfa_time.d_tdb_tt
        can handle array-valued locations, and can broadcast these if needed.
        """

        lat = 19.48125
        lon = -155.933222
        t = Time(['2006-01-15 21:24:37.5']*2, format='iso', scale='utc',
                 precision=6, location=(lon, lat))
        assert np.all(t.utc.iso == '2006-01-15 21:24:37.500000')
        assert np.all(t.tdb.iso[0] == '2006-01-15 21:25:42.684373')
        t2 = Time(['2006-01-15 21:24:37.5']*2, format='iso', scale='utc',
                  precision=6, location=(np.array([lon, 0]),
                                         np.array([lat, 0])))
        assert np.all(t2.utc.iso == '2006-01-15 21:24:37.500000')
        assert t2.tdb.iso[0] == '2006-01-15 21:25:42.684373'
        assert t2.tdb.iso[1] != '2006-01-15 21:25:42.684373'
        with pytest.raises(ValueError):  # 1 time, but two locations
            Time('2006-01-15 21:24:37.5', format='iso', scale='utc',
                 precision=6, location=(np.array([lon, 0]),
                                        np.array([lat, 0])))
        with pytest.raises(ValueError):  # 3 times, but two locations
            Time(['2006-01-15 21:24:37.5']*3, format='iso', scale='utc',
                 precision=6, location=(np.array([lon, 0]),
                                        np.array([lat, 0])))
        # multidimensional
        mjd = np.arange(50000., 50008.).reshape(4, 2)
        t3 = Time(mjd, format='mjd', scale='utc', location=(lon, lat))
        assert t3.shape == (4, 2)
        assert t3.location.shape == ()
        assert t3.tdb.shape == (4, 2)
        t4 = Time(mjd, format='mjd', scale='utc',
                  location=(np.array([lon, 0]), np.array([lat, 0])))
        assert t4.shape == (4, 2)
        assert t4.location.shape == (2,)
        assert t4.tdb.shape == (4, 2)
        t5 = Time(mjd, format='mjd', scale='utc',
                  location=(np.array([[lon], [0], [0], [0]]),
                            np.array([[lat], [0], [0], [0]])))
        assert t5.shape == (4, 2)
        assert t5.location.shape == (4, 1)
        assert t5.tdb.shape == (4, 2)

    def test_all_transforms(self):
        """Test that all transforms work.  Does not test correctness,
        except reversibility [#2074]"""
        lat = 19.48125
        lon = -155.933222
        for scale1 in TIME_SCALES:
            t1 = Time('2006-01-15 21:24:37.5', format='iso', scale=scale1,
                      location=(lon, lat))
            for scale2 in TIME_SCALES:
                t2 = getattr(t1, scale2)
                t21 = getattr(t2, scale1)
                assert allclose_jd(t21.jd, t1.jd)

    def test_creating_all_formats(self):
        """Create a time object using each defined format"""
        Time(2000.5, format='decimalyear')
        Time(100.0, format='cxcsec')
        Time(100.0, format='unix')
        Time(100.0, format='gps')
        Time(1950.0, format='byear', scale='tai')
        Time(2000.0, format='jyear', scale='tai')
        Time('B1950.0', format='byear_str', scale='tai')
        Time('J2000.0', format='jyear_str', scale='tai')
        Time('2000-01-01 12:23:34.0', format='iso', scale='tai')
        Time('2000-01-01 12:23:34.0Z', format='iso', scale='utc')
        Time('2000-01-01T12:23:34.0', format='isot', scale='tai')
        Time('2000-01-01T12:23:34.0Z', format='isot', scale='utc')
        Time(2400000.5, 51544.0333981, format='jd', scale='tai')
        Time(0.0, 51544.0333981, format='mjd', scale='tai')
        Time('2000:001:12:23:34.0', format='yday', scale='tai')
        Time('2000:001:12:23:34.0Z', format='yday', scale='utc')
        dt = datetime(2000, 1, 2, 3, 4, 5, 123456)
        Time(dt, format='datetime', scale='tai')
        Time([dt, dt], format='datetime', scale='tai')

    def test_datetime(self):
        """
        Test datetime format, including guessing the format from the input type
        by not providing the format keyword to Time.
        """
        dt = datetime(2000, 1, 2, 3, 4, 5, 123456)
        dt2 = datetime(2001, 1, 1)
        t = Time(dt, scale='utc', precision=9)
        assert t.iso == '2000-01-02 03:04:05.123456000'
        assert t.datetime == dt
        assert t.value == dt
        t2 = Time(t.iso, scale='utc')
        assert t2.datetime == dt

        t = Time([dt, dt2], scale='utc')
        assert np.all(t.value == [dt, dt2])

        t = Time('2000-01-01 01:01:01.123456789', scale='tai')
        assert t.datetime == datetime(2000, 1, 1, 1, 1, 1, 123457)

        # broadcasting
        dt3 = (dt + (dt2-dt)*np.arange(12)).reshape(4, 3)
        t3 = Time(dt3, scale='utc')
        assert t3.shape == (4, 3)
        assert t3[2, 1].value == dt3[2, 1]
        assert t3[2, 1] == Time(dt3[2, 1])
        assert np.all(t3.value == dt3)
        assert np.all(t3[1].value == dt3[1])
        assert np.all(t3[:, 2] == Time(dt3[:, 2]))
        assert Time(t3[2, 0]) == t3[2, 0]

    def test_epoch_transform(self):
        """Besselian and julian epoch transforms"""
        jd = 2457073.05631
        t = Time(jd, format='jd', scale='tai', precision=6)
        assert allclose_year(t.byear, 2015.1365941020817)
        assert allclose_year(t.jyear, 2015.1349933196439)
        assert t.byear_str == 'B2015.136594'
        assert t.jyear_str == 'J2015.134993'
        t2 = Time(t.byear, format='byear', scale='tai')
        assert allclose_jd(t2.jd, jd)
        t2 = Time(t.jyear, format='jyear', scale='tai')
        assert allclose_jd(t2.jd, jd)

        t = Time('J2015.134993', scale='tai', precision=6)
        assert np.allclose(t.jd, jd, rtol=1e-10, atol=0)  # J2015.134993 has 10 digit precision
        assert t.byear_str == 'B2015.136594'

    def test_input_validation(self):
        """Wrong input type raises error"""
        times = [10, 20]
        with pytest.raises(ValueError):
            Time(times, format='iso', scale='utc')
        with pytest.raises(ValueError):
            Time('2000:001', format='jd', scale='utc')
        with pytest.raises(ValueError):
            Time([50000.0], ['bad'], format='mjd', scale='tai')
        with pytest.raises(ValueError):
            Time(50000.0, 'bad', format='mjd', scale='tai')
        with pytest.raises(ValueError):
            Time('2005-08-04T00:01:02.000Z', scale='tai')

    def test_utc_leap_sec(self):
        """Time behaves properly near or in UTC leap second.  This
        uses the 2012-06-30 leap second for testing."""

        # Start with a day without a leap second and note rollover
        t1 = Time('2012-06-01 23:59:60.0', scale='utc')
        assert t1.iso == '2012-06-02 00:00:00.000'

        # Leap second is different
        t1 = Time('2012-06-30 23:59:59.900', scale='utc')
        assert t1.iso == '2012-06-30 23:59:59.900'

        t1 = Time('2012-06-30 23:59:60.000', scale='utc')
        assert t1.iso == '2012-06-30 23:59:60.000'

        t1 = Time('2012-06-30 23:59:60.999', scale='utc')
        assert t1.iso == '2012-06-30 23:59:60.999'

        t1 = Time('2012-06-30 23:59:61.0', scale='utc')
        assert t1.iso == '2012-07-01 00:00:00.000'

        # Delta time gives 2 seconds here as expected
        t0 = Time('2012-06-30 23:59:59', scale='utc')
        t1 = Time('2012-07-01 00:00:00', scale='utc')
        assert allclose_sec((t1 - t0).sec, 2.0)

    def test_init_from_time_objects(self):
        """Initialize from one or more Time objects"""
        t1 = Time('2007:001', scale='tai')
        t2 = Time(['2007-01-02', '2007-01-03'], scale='utc')
        # Init from a list of Time objects without an explicit scale
        t3 = Time([t1, t2])
        # Test that init appropriately combines a scalar (t1) and list (t2)
        # and that scale and format are same as first element.
        assert len(t3) == 3
        assert t3.scale == t1.scale
        assert t3.format == t1.format  # t1 format is yday
        assert np.all(t3.value == np.concatenate([[t1.yday], t2.tai.yday]))

        # Init from a single Time object without a scale
        t3 = Time(t1)
        assert t3.isscalar
        assert t3.scale == t1.scale
        assert t3.format == t1.format
        assert np.all(t3.value == t1.value)

        # Init from a single Time object with scale specified
        t3 = Time(t1, scale='utc')
        assert t3.scale == 'utc'
        assert np.all(t3.value == t1.utc.value)

        # Init from a list of Time object with scale specified
        t3 = Time([t1, t2], scale='tt')
        assert t3.scale == 'tt'
        assert t3.format == t1.format  # yday
        assert np.all(t3.value == np.concatenate([[t1.tt.yday], t2.tt.yday]))

        # OK, how likely is this... but might as well test.
        mjd = np.arange(50000., 50006.)
        frac = np.arange(0., 0.999, 0.2)
        t4 = Time(mjd[:, np.newaxis] + frac, format='mjd', scale='utc')
        t5 = Time([t4[:2], t4[4:5]])
        assert t5.shape == (3, 5)


class TestVal2():
    """Tests related to val2"""

    def test_val2_ignored(self):
        """Test that val2 is ignored for string input"""
        t = Time('2001:001', 'ignored', scale='utc')
        assert t.yday == '2001:001:00:00:00.000'

    def test_val2(self):
        """Various tests of the val2 input"""
        t = Time([0.0, 50000.0], [50000.0, 0.0], format='mjd', scale='tai')
        assert t.mjd[0] == t.mjd[1]
        assert t.jd[0] == t.jd[1]

    def test_val_broadcasts_against_val2(self):
        mjd = np.arange(50000., 50007.)
        frac = np.arange(0., 0.999, 0.2)
        t = Time(mjd[:, np.newaxis], frac, format='mjd', scale='utc')
        assert t.shape == (7, 5)
        with pytest.raises(ValueError):
            Time([0.0, 50000.0], [0.0, 1.0, 2.0], format='mjd', scale='tai')


class TestSubFormat():
    """Test input and output subformat functionality"""

    def test_input_subformat(self):
        """Input subformat selection"""
        # Heterogeneous input formats with in_subfmt='*' (default)
        times = ['2000-01-01', '2000-01-01 01:01',
                 '2000-01-01 01:01:01', '2000-01-01 01:01:01.123']
        t = Time(times, format='iso', scale='tai')
        assert np.all(t.iso == np.array(['2000-01-01 00:00:00.000',
                                         '2000-01-01 01:01:00.000',
                                         '2000-01-01 01:01:01.000',
                                         '2000-01-01 01:01:01.123']))

        # Heterogeneous input formats with in_subfmt='date_*'
        times = ['2000-01-01 01:01',
                 '2000-01-01 01:01:01', '2000-01-01 01:01:01.123']
        t = Time(times, format='iso', scale='tai',
                 in_subfmt='date_*')
        assert np.all(t.iso == np.array(['2000-01-01 01:01:00.000',
                                         '2000-01-01 01:01:01.000',
                                         '2000-01-01 01:01:01.123']))

    def test_input_subformat_fail(self):
        """Failed format matching"""
        with pytest.raises(ValueError):
            Time('2000-01-01 01:01', format='iso', scale='tai',
                 in_subfmt='date')

    def test_bad_input_subformat(self):
        """Non-existent input subformat"""
        with pytest.raises(ValueError):
            Time('2000-01-01 01:01', format='iso', scale='tai',
                 in_subfmt='doesnt exist')

    def test_output_subformat(self):
        """Input subformat selection"""
        # Heterogeneous input formats with in_subfmt='*' (default)
        times = ['2000-01-01', '2000-01-01 01:01',
                 '2000-01-01 01:01:01', '2000-01-01 01:01:01.123']
        t = Time(times, format='iso', scale='tai',
                 out_subfmt='date_hm')
        assert np.all(t.iso == np.array(['2000-01-01 00:00',
                                         '2000-01-01 01:01',
                                         '2000-01-01 01:01',
                                         '2000-01-01 01:01']))

    def test_yday_format(self):
        """Year:Day_of_year format"""
        # Heterogeneous input formats with in_subfmt='*' (default)
        times = ['2000-12-01', '2001-12-01 01:01:01.123']
        t = Time(times, format='iso', scale='tai')
        t.out_subfmt = 'date_hm'
        assert np.all(t.yday == np.array(['2000:336:00:00',
                                          '2001:335:01:01']))
        t.out_subfmt = '*'
        assert np.all(t.yday == np.array(['2000:336:00:00:00.000',
                                          '2001:335:01:01:01.123']))

    def test_scale_input(self):
        """Test for issues related to scale input"""
        # Check case where required scale is defined by the TimeFormat.
        # All three should work.
        t = Time(100.0, format='cxcsec', scale='utc')
        assert t.scale == 'utc'
        t = Time(100.0, format='unix', scale='tai')
        assert t.scale == 'tai'
        t = Time(100.0, format='gps', scale='utc')
        assert t.scale == 'utc'

        # Check that bad scale is caught when format is specified
        with pytest.raises(ScaleValueError):
            Time(1950.0, format='byear', scale='bad scale')

        # Check that bad scale is caught when format is auto-determined
        with pytest.raises(ScaleValueError):
            Time('2000:001:00:00:00', scale='bad scale')

    def test_scale_default(self):
        """Test behavior when no scale is provided"""
        # These first three are TimeFromEpoch and have an intrinsic time scale
        t = Time(100.0, format='cxcsec')
        assert t.scale == 'tt'
        t = Time(100.0, format='unix')
        assert t.scale == 'utc'
        t = Time(100.0, format='gps')
        assert t.scale == 'tai'

        for date in ('J2000', '2000:001', '2000-01-01T00:00:00'):
            t = Time(date)
            assert t.scale == 'utc'

        t = Time(2000.1, format='byear')
        assert t.scale == 'utc'

    def test_epoch_times(self):
        """Test time formats derived from EpochFromTime"""
        t = Time(0.0, format='cxcsec', scale='tai')
        assert t.tt.iso == '1998-01-01 00:00:00.000'

        # Create new time object from this one and change scale, format
        t2 = Time(t, scale='tt', format='iso')
        assert t2.value == '1998-01-01 00:00:00.000'

        # Value take from Chandra.Time.DateTime('2010:001:00:00:00').secs
        t = Time(378691266.184, format='cxcsec', scale='utc')
        assert t.yday == '2010:001:00:00:00.000'
        t = Time('2010:001:00:00:00.000', scale='utc')
        assert allclose_sec(t.cxcsec, 378691266.184)
        assert allclose_sec(t.tt.cxcsec, 378691266.184)

        # Value from:
        #   d = datetime.datetime(2000, 1, 1)
        #   matplotlib.pylab.dates.date2num(d)
        t = Time('2000-01-01 00:00:00', scale='utc')
        assert np.allclose(t.plot_date, 730120.0, atol=1e-5, rtol=0)

        # Round trip through epoch time
        for scale in ('utc', 'tt'):
            t = Time('2000:001', scale=scale)
            t2 = Time(t.unix, scale=scale, format='unix')
            assert getattr(t2, scale).iso == '2000-01-01 00:00:00.000'

        # Test unix time.  Values taken from http://en.wikipedia.org/wiki/Unix_time
        t = Time('2013-05-20 21:18:46', scale='utc')
        assert allclose_sec(t.unix, 1369084726.0)
        assert allclose_sec(t.tt.unix, 1369084726.0)

        # Values from issue #1118
        t = Time('2004-09-16T23:59:59', scale='utc')
        assert allclose_sec(t.unix, 1095379199.0)

# this test fails because it uses the  erfa_time.pyx cal2jd, which doesn't raise
# an error on a "bad day".  Can just eliminate the test if we don't care about
# this anymore
@pytest.mark.xfail
class TestSofaErrors():
    """Test that erfa_time.pyx handles erfa status return values correctly"""

    def test_bad_time(self):
        iy = np.array([2000], dtype=np.intc)
        im = np.array([2000], dtype=np.intc)  # bad month
        id = np.array([2000], dtype=np.intc)  # bad day
        djm0 = np.array([0], dtype=np.double)
        djm = np.array([0], dtype=np.double)
        with pytest.raises(ValueError):  # bad month, fatal error
            djm0, djm= erfa_time.cal2jd(iy, im, id)

        # Set month to a good value so now the bad day just gives a warning
        im[0] = 2
        djm0, djm = erfa_time.cal2jd(iy, im, id)
        assert allclose_jd(djm0, [2400000.5])
        assert allclose_jd(djm, [53574.])

        # How do you test for warnings in pytest?  Test that dubious year for
        # UTC works.


class TestCopyReplicate():
    """Test issues related to copying and replicating data"""

    def test_immutable_input(self):
        """Internals are never mutable."""
        jds = np.array([2450000.5], dtype=np.double)
        t = Time(jds, format='jd', scale='tai')
        assert allclose_jd(t.jd, jds)
        jds[0] = 2458654
        assert not allclose_jd(t.jd, jds)

        mjds = np.array([50000.0], dtype=np.double)
        t = Time(mjds, format='mjd', scale='tai')
        assert allclose_jd(t.jd, [2450000.5])
        mjds[0] = 0.0
        assert allclose_jd(t.jd, [2450000.5])

    def test_replicate(self):
        """Test replicate method"""
        t = Time('2000:001', format='yday', scale='tai',
                 location=('45d', '45d'))
        t_yday = t.yday
        t_loc_x = t.location.x.copy()
        t2 = t.replicate()
        assert t.yday == t2.yday
        assert t.format == t2.format
        assert t.scale == t2.scale
        assert t.location == t2.location
        # This is not allowed publicly, but here we hack the internal time
        # and location values to show that t and t2 are sharing references.
        t2._time.jd1 += 100.0
        assert t.yday == t2.yday
        assert t.yday != t_yday  # prove that it changed
        t2_loc_x_view = t2.location.x
        t2_loc_x_view[()] = 0  # use 0 to avoid having to give units
        assert t2.location.x == t2_loc_x_view
        assert t.location.x == t2.location.x
        assert t.location.x != t_loc_x  # prove that it changed

    def test_copy(self):
        """Test copy method"""
        t = Time('2000:001', format='yday', scale='tai',
                 location=('45d', '45d'))
        t_yday = t.yday
        t_loc_x = t.location.x.copy()
        t2 = t.copy()
        assert t.yday == t2.yday
        # This is not allowed publicly, but here we hack the internal time
        # and location values to show that t and t2 are not sharing references.
        t2._time.jd1 += 100.0
        assert t.yday != t2.yday
        assert t.yday == t_yday  # prove that it did not change
        t2_loc_x_view = t2.location.x
        t2_loc_x_view[()] = 0  # use 0 to avoid having to give units
        assert t2.location.x == t2_loc_x_view
        assert t.location.x != t2.location.x
        assert t.location.x == t_loc_x  # prove that it changed


def test_python_builtin_copy():
    t = Time('2000:001', format='yday', scale='tai')
    t2 = copy.copy(t)
    t3 = copy.deepcopy(t)

    assert t.jd == t2.jd
    assert t.jd == t3.jd


def test_now():
    """
    Tests creating a Time object with the `now` class method.
    """

    now = datetime.utcnow()
    t = Time.now()

    assert t.format == 'datetime'
    assert t.scale == 'utc'

    dt = t.datetime - now  # a datetime.timedelta object

    # this gives a .1 second margin between the `utcnow` call and the `Time`
    # initializer, which is really way more generous than necessary - typical
    # times are more like microseconds.  But it seems safer in case some
    # platforms have slow clock calls or something.

    # py < 2.7 doesn't have `total_seconds`
    if sys.version_info[:2] < (2, 7):
        total_secs = lambda td: (td.microseconds + (
            td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 6.
    else:
        total_secs = lambda td: td.total_seconds()
    assert total_secs(dt) < 0.1


def test_decimalyear():
    t = Time('2001:001', format='yday')
    assert t.decimalyear == 2001.0

    t = Time(2000.0, [0.5, 0.75], format='decimalyear')
    assert np.all(t.value == [2000.5, 2000.75])

    jd0 = Time('2000:001').jd
    jd1 = Time('2001:001').jd
    d_jd = jd1 - jd0
    assert np.all(t.jd == [jd0 + 0.5 * d_jd,
                           jd0 + 0.75 * d_jd])


def test_dir():
    t = Time('2000:001', format='yday', scale='tai')
    assert 'utc' in dir(t)


def test_TimeFormat_scale():
    """guard against recurrence of #1122, where TimeFormat class looses uses
    attributes (delta_ut1_utc here), preventing conversion to unix, cxc"""
    t = Time('1900-01-01', scale='ut1')
    t.delta_ut1_utc = 0.0
    t.unix
    assert t.unix == t.utc.unix

def test_scale_conversion():
    with pytest.raises(ScaleValueError):
        t = Time(Time.now().cxcsec, format='cxcsec', scale='ut1')


def test_byteorder():
    """Ensure that bigendian and little-endian both work (closes #2942)"""
    mjd = np.array([53000.00,54000.00])
    big_endian = mjd.astype('>f8')
    little_endian = mjd.astype('<f8')
    time_mjd = Time(mjd, format='mjd')
    time_big = Time(big_endian, format='mjd')
    time_little = Time(little_endian, format='mjd')
    assert np.all(time_big == time_mjd)
    assert np.all(time_little == time_mjd)


def test_datetime_tzinfo():
    """
    Test #3160 that time zone info in datetime objects is respected.
    """
    class TZm6(tzinfo):
        def utcoffset(self, dt):
            return timedelta(hours=-6)

    d = datetime(2002, 1, 2, 10, 3, 4, tzinfo=TZm6())
    t = Time(d)
    assert t.value == datetime(2002, 1, 2, 16, 3, 4)
