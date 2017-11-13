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
        assert b"BOSCOMBE DOWN ATZ" in rv.data
        assert b"AC D" in rv.data

        # Gliding sites excluded
        assert b"LASHAM" not in rv.data

        # No-ATZ airfields included
        assert b"EASTER" in rv.data

        # Microlight strips excluded
        assert b"CLENCH COMMON" not in rv.data

        # LASER excluded
        assert b"CAMBRIDGE UNIVERSITY" not in rv.data

        # ILS always included
        assert b"BIGGIN HILL" in rv.data

    def test_post_atzctr(self):
        rv = self.app.post("/", data={'atz': "ctr"})
        assert b"AC CTR" in rv.data

    def test_gliding_include(self):
        rv = self.app.post("/", data={'glider': "include"})
        assert b"LASHAM" in rv.data

    def test_noatz_exclude(self):
        rv = self.app.post("/", data={'noatz': "exclude"})
        assert b"EASTER" not in rv.data

    def test_microlight_include(self):
        rv = self.app.post("/", data={'microlight': "include"})
        assert b"CLENCH COMMON" in rv.data

    def test_hgl_include(self):
        rv = self.app.post("/", data={'hgl': "include"})
        assert b"CAMBRIDGE UNIVERSITY" in rv.data

    def test_ils_class(self):
        rv = self.app.post("/", data={'ils': "classg", 'noatz': "exclude"})
        assert rv.data.count(b"AC G") == 1

        rv = self.app.post("/", data={'ils': "atz", 'atz': "classd"})
        assert rv.data.count(b"AC D") == 2

        rv = self.app.post("/", data={'ils': "atz", 'atz': "ctr"})
        assert rv.data.count(b"AC CTR") == 2

    def test_obstacle_include(self):
        rv = self.app.post("/", data={'obstacle': "include"})
        assert b"RADIO MAST" in rv.data

    def test_trag_include(self):
        rv = self.app.post("/", data={'wave-TRAG ABOYNE': ""})
        assert b"TRAG ABOYNE" in rv.data

    def test_trag_unknown(self):
        rv = self.app.post("/", data={'wave-FOOBAR': ""})
        assert b"FOOBAR" not in rv.data

    def test_fl105_exclude(self):
        rv = self.app.post("/", data={'fl105': "", 'wave-TRAG ABOYNE': ""})
        assert b"TRAG ABOYNE" not in rv.data

    def test_north_filter(self):
        rv = self.app.post("/", data={'north': "54", 'wave-TRAG ABOYNE': ""})
        assert b"TRAG ABOYNE" not in rv.data

    def test_south_filter(self):
        rv = self.app.post("/", data={'south': "54"})
        assert b"BOSCOMBE DOWN ATZ" not in rv.data

    def test_northsouth_null_filter(self):
        rv = self.app.post("/", data={'north': "59", 'south': "48",
                                      'wave-TRAG ABOYNE': ""})
        assert b"BOSCOMBE DOWN ATZ" in rv.data
        assert b"TRAG ABOYNE" in rv.data

if __name__ == "__main__":
    unittest.main()
