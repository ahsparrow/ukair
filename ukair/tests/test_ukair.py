# Copyright 2017 Alan Sparrow
#
# This file is part of ukair
#
# ukair is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ukair is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ukair.  If not, see <http://www.gnu.org/licenses/>.

import unittest

import ukair

CONFIG = {'flask': {'YAIXM_FILE': "ukair/tests/data/airspace.json"}}

class TestCase(unittest.TestCase):
    def setUp(self):
        self.app = ukair.create_app(CONFIG).test_client()

    def test_get(self):
        rv = self.app.get("/")
        assert b"AIRAC: 2018-01-01" in rv.data

    def test_post_nodata(self):
        rv = self.app.post("/")
        # ATZ always included
        assert b"AN BOSCOMBE DOWN ATZ" in rv.data
        assert b"AC D" in rv.data

        # Gliding sites excluded
        assert b"AN LASHAM" not in rv.data

        # No-ATZ airfields included
        assert b"AN EASTER" in rv.data

        # Microlight strips excluded
        assert b"AN CLENCH COMMON" not in rv.data

        # LASER excluded
        assert b"AN CAMBRIDGE UNIVERSITY" not in rv.data

        # ILS always included
        assert b"AN BIGGIN HILL" in rv.data

    def test_post_atzctr(self):
        rv = self.app.post("/", data={'atz': "ctr"})
        assert b"AC CTR" in rv.data

    def test_gliding_include(self):
        rv = self.app.post("/", data={'glider': "include"})
        assert b"AN LASHAM" in rv.data

    def test_noatz_exclude(self):
        rv = self.app.post("/", data={'noatz': "exclude"})
        assert b"AN EASTER" not in rv.data

    def test_microlight_include(self):
        rv = self.app.post("/", data={'microlight': "include"})
        assert b"AN CLENCH COMMON" in rv.data

    def test_hgl_include(self):
        rv = self.app.post("/", data={'hgl': "include"})
        assert b"AN CAMBRIDGE UNIVERSITY" in rv.data

    def test_ils_class(self):
        rv = self.app.post("/", data={'ils': "classg", 'noatz': "exclude"})
        assert rv.data.count(b"AC G") == 1

        rv = self.app.post("/", data={'ils': "atz", 'atz': "classd"})
        assert rv.data.count(b"AC D") == 2

        rv = self.app.post("/", data={'ils': "atz", 'atz': "ctr"})
        assert rv.data.count(b"AC CTR") == 2

    def test_obstacle_include(self):
        rv = self.app.post("/", data={'obstacle': "include"})
        assert b"AN RADIO MAST" in rv.data

    def test_trag_include(self):
        rv = self.app.post("/", data={'wave-TRAG ABOYNE': ""})
        assert b"AN TRAG ABOYNE" in rv.data

    def test_trag_unknown(self):
        rv = self.app.post("/", data={'wave-FOOBAR': ""})
        assert b"AN FOOBAR" not in rv.data

    def test_maxlevel(self):
        rv = self.app.post("/", data={'maxlevel': "10500", 'wave-TRAG ABOYNE': ""})
        assert b"AN TRAG ABOYNE" not in rv.data

    def test_north_filter(self):
        rv = self.app.post("/", data={'north': "54", 'wave-TRAG ABOYNE': ""})
        assert b"AN TRAG ABOYNE" not in rv.data

    def test_south_filter(self):
        rv = self.app.post("/", data={'south': "54"})
        assert b"AN BOSCOMBE DOWN ATZ" not in rv.data

    def test_northsouth_null_filter(self):
        rv = self.app.post("/", data={'north': "59", 'south': "48",
                                      'wave-TRAG ABOYNE': ""})
        assert b"AN BOSCOMBE DOWN ATZ" in rv.data
        assert b"AN TRAG ABOYNE" in rv.data

    def test_rat(self):
        rv = self.app.post("/", data={'rat-TEST RAT': ""})
        assert b"AN TEST RAT" in rv.data

if __name__ == "__main__":
    unittest.main()
