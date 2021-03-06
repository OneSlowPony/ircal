import re
from time import sleep
from functools import wraps
from random import randint
from serial import Serial, SerialException

class Responder():
    """Generates mock KT/CT output given environment information."""

    def __init__(self):
        """Create a mock KT/CT response generator."""
        self.device_values = {
            'temp': '25.0',
            'rad': '0.0',
            'unit': 'C',
            'calibration_factor': '2.0',
        }

        # Add new commands here. Each command is supported by the syntax <regex>: <response function>. Values, like temperature, can be parsed using the settings.group() function.
        self.language = {
            'CAL \?': (lambda settings: self.device_values['calibration_factor']),
            'CAL (\d+[.]\d*)': (lambda settings: self.device_values.update({'calibration_factor': settings.group(1)})),
            'TEMP': (lambda settings: self.device_values['temp']),
            'RAD': (lambda settings: self.device_values['rad']),
            'UNIT \?': (lambda settings: self.device_values['unit']),
            'UNIT ([K|C|F])': (lambda settings: self.device_values.update({'unit': settings.group(1)}))
        }
        self.query = []

    def _timeout(self):
        """Simulates latency in serial device response.
            :returns: True if the message was delivered, False otherwise.
            :rtype: bool
        """
        sleep(randint(50, 500)/1000.0)
        return True

    def ask(self, query):
        """Simulates receiving and processing an input query.
            :returns: True if the query was accepted, False if an error was found.
            :rtype: bool
        """
        del self.query[:]
        if self._timeout():
            for token in query:
                if ord(token) > 127: # KT/CT only accepts ASCII characters.
                    break
                self.query.append(token)
            else:
                if len(query) <= 40: # KT/CT has a 40-character input buffer.
                    return True
        return False

    def respond(self):
        """Simulates the corresponding KT/CT response for a given query.
            :returns: The expected KT/CT output according to the Heitronics spec.
            :rtype: String
        """
        for command, response in self.language.items():
            settings = re.match(command, ''.join(self.query))
            if settings:
                res = response(settings)
                if res:
                    return res + '\n'
                return ''
        raise SerialException("ERROR 19: CAN'T DO IT")

class FakeSerial(Serial):
    """Simulates generic serial device behavior.
       This class does not mock serial.tools.list_ports.comports behavior,
       since that function call is expected to function regardless of whether a KT/CT is plugged in.
    """

    def __init__(self, port, baudrate=9600, timeout=0.2):
        """Create a mock serial object.
            :param port: Serial port, we don't really care what format.
            :type port: String
        """
        super(FakeSerial, self).__init__()
        self.name, self.port = port, port
        self.responder = Responder() # Delegate generating KT/CT-like responses to a separate object. Whenever mock KT/CT command output is desired, a call to self.responder should be made.
        self.output_buffer, self.input_buffer = [], []
        self.baudrate = baudrate
        self.timeout = timeout
        self.is_open = True

    def check_connection(func):
        """Checks whether this connection is open prior to any member/function call.
           This is less invasive than checking for self._is_open in every function call.
        """
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.is_open:
                raise SerialException("Cannot write, serial connection is not open.")
            else:
                return func(self, *args, **kwargs)
        return wrapper

    @check_connection
    def readline(self):
        """Provide a mock response from the serial object.
            :returns: Fake response corresponding to the input query specified by a write().
            :rtype: String
        """
        if self.output_buffer:
            eol = self.output_buffer.index('\n') + 1
            response, self.output_buffer = self.output_buffer[:eol], self.output_buffer[eol:]
            return ''.join(response)
        sleep(self.timeout) # Just like a real serial connection, block until EOF/EOL or timeout elapsed.
        return ''

    @check_connection
    def write(self, query):
        """Accept a query and generate potential responses, to be consumed in readline().
            :param query: Input string usually sent to a serial object.
            :type query: String
        """
        self.input_buffer.extend(list(query))
        if self.responder.ask(self.input_buffer):
            self.output_buffer.extend(list(self.responder.respond()))
            del self.input_buffer[:]
        else:
            del self.input_buffer[:]
            raise SerialException("Invalid input query.")
    
    @check_connection
    def open(self):
        """Pretends to open a serial connection."""
        self._is_open = True

    @check_connection
    def close(self):
        """Pretends to close a serial connection."""
        self._is_open = False
