from __future__ import with_statement
import unittest, amcattest, amcatlogging, ticker

class TestLogging(amcattest.AmcatTestCase):

    def testTickerModule(self):
        with amcatlogging.collect() as log:
            ticker.warn("Starting ticking", estimate=1000)
            for i in range(200):
                ticker.tick()
        self.assertEqual(len(log), 3)
        self.assertIn("test/test_ticker.py:10",  amcatlogging.format(log))
        self.assertIn("INFO] [   100/  1000]", amcatlogging.format(log))

    def testTickerClass(self):
        t = ticker.Ticker(interval=100)
        with amcatlogging.collect() as log:
            for i in range(200):
                t.tick()
        self.assertEqual(len(log), 2)
        self.assertIn("test/test_ticker.py:19",  amcatlogging.format(log))
        self.assertIn("INFO] [   100]", amcatlogging.format(log))

    def testTickerate(self):
        
        with amcatlogging.collect() as log:
            for i in ticker.tickerate(range(100)):
                pass
        self.assertEqual(len(log), 11)
        self.assertIn("test/test_ticker.py:27",  amcatlogging.format(log))
        self.assertIn("INFO] [   100/   100]", amcatlogging.format(log))


if __name__ == '__main__':
    unittest.main()