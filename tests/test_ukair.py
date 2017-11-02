import unittest

import ukair

class TestCase(unittest.TestCase):
    def setUp(self):
        self.app = ukair.create_app("UKAIR_CONFIG").test_client()

    def test_get(self):
        rv = self.app.get("/")
        assert b"AIRAC: 2018-01-01" in rv.data

    def test_post(self):
        rv = self.app.post("/")
        assert b"AIRAC: 2018-01-01" in rv.data

if __name__ == "__main__":
    unittest.main()
