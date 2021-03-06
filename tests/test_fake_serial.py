import unittest
import sys
from fake_serial import FakeSerial
from serial import SerialException
from itertools import izip

class FakeSerialTestCase(unittest.TestCase):
    
    def setUp(self): 
        FAKE_PORT = 1
        self.serial = FakeSerial(port=FAKE_PORT)

    def tearDown(self):
        if self.serial.is_open:
            self.serial.close()

    def _send_and_respond(self, command):
        self.serial.write(command)
        return self.serial.readline()

    def _compare_all_messages(self, queries, expected_responses):
        for query, expected_response in izip(queries, expected_responses):
            response = self._send_and_respond(query)
            print "QUERY: %s | RESPONSE: %s"%(query, response)
            self.assertEqual(response, expected_response)

    def test_interrogation(self):
        queries = ['CAL ?\n', 'TEMP\n', 'RAD\n', 'UNIT ?\n']
        expected_responses = ['2.0\n', '25.0\n', '0.0\n', 'C\n']
        self._compare_all_messages(queries, expected_responses)

    def test_command(self):
        queries = ['CAL 1.56\n', 'UNIT K\n']
        expected_responses = ['', '']
        self._compare_all_messages(queries, expected_responses)

    def test_aggregation(self):
        queries = ['CAL 3.14\n', 'CAL ?\n', 'UNIT ?\n', 'UNIT F\n', 'UNIT ?\n']
        for query in queries:
            self.serial.write(query)
        self.assertEqual(self.serial.readline(), '3.14\n')
        self.assertEqual(self.serial.readline(), 'C\n')
        self.assertEqual(self.serial.readline(), 'F\n') 

    def test_connection(self):
        self.serial.close()
        self.assertRaises(SerialException, self.serial.write, 'test')
        self.serial.open()
        self.assertTrue(self.serial.is_open)

    def test_invalid_query(self):
        try:
            self.serial.write('CAL')
            self.serial.readline()
        except SerialException:
            pass
        else:
            self.fail('Exception not raised.')

def get_tests():
    tests = ['test_interrogation', 'test_command', 'test_aggregation', 'test_connection', 'test_invalid_query']
    return unittest.TestSuite(map(FakeSerialTestCase, tests))

if __name__ == '__main__':
    sys.exit(unittest.main())
