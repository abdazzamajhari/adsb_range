#from enum import Enum
from datetime import datetime

# http://www.homepages.mcb.net/bones/SBS/Article/Barebones42_Socket_Data.htm
def _parse_datetime(datestr, timestr):
	date = datetime.strptime(datestr, '%Y/%m/%d')

	timestr, separator, millisstr = timestr.rpartition('.')
	time = datetime.strptime(timestr, '%H:%M:%S')

	seconds = float(separator + millisstr)
	time = time.replace(microsecond=int(seconds*1000000))

	return datetime.combine(date.date(), time.time())

def _parse_bool(str):
	if str.lower() in ('true', 'y', 'yes', 'on', '1'):
		return True
	elif str.lower() in ('false', 'n', 'no', 'off', '0'):
		return False

def _dump_datetime(time):
	str = datetime.strftime(time, '%Y/%m/%d,%H:%M:%S')
	str += '.{:03d}'.format(int(time.microsecond/1000))
	return str

def _dump_bool(value):
	if value == True:
		return '1'
	else:
		return '0'

def _dump_or_none(value, func=str):
	if value is None:
		return ''
	else:
		return func(value)

class Message:
	"""Abstract representation of the information contained in a BaseStation line.

	The fields are listed in the order of appearance in the format. A sample line looks like this: ::

		MSG,3,111,11111,3C49CC,111111,2015/05/01,17:06:55.370,2015/05/01,17:06:55.326,,24400,,,50.65931,6.67709,,,,,,0

	This message contains the coordinates (50.65931, 6.67709) and altitude of 24400ft of an aircraft with the ADS-B hexident 3C49CC.
	The third, fourth and sixth fields have been set to '111...' which indicates that the demodulator did not support these fields.

	The attributes of this object will be set according to their values or left at None if no information is available.

	To create an instance of this object, use :py:meth:`Message.from_string`. To serialize back into a BaseStation string, use
	:py:meth:`Message.to_string`.

	See Also:
		`John Woodsides	SBS Station Tutorial <http://avphotosonline.org.uk/Bones/SBS/Article/Barebones42_Socket_Data.htm>`_
			Source of most of the information provided about the socket format here.

	Attributes:
		message_type (str): The message type: MSG, STA, ID, AIR, SEL or CLK. Usually only messages of type MSG (transmission messages)
			are of interest. Most softwares (e.g. :program:`dump1090`) do not even support any other message types.

			====    =========================    ==========================================================================================
			ID      Type                         Description
			====    =========================    ==========================================================================================
			SEL     SELECTION CHANGE MESSAGE     Generated when the user changes the selected aircraft in BaseStation.
			ID      NEW ID MESSAGE               Generated when an aircraft being tracked sets or changes its callsign.
			AIR     NEW AIRCRAFT MESSAGE         Generated when the SBS picks up a signal for an aircraft that it isn't currently tracking.
			STA     STATUS CHANGE MESSAGE        Generated when an aircraft's status changes according to the timeout values in the Data
			                                     Settings menu.
			CLK     CLICK MESSAGE                Generated when the user doubleclicks (or presses return) on an aircraft (i.e. to bring
			                                     up the aircraft details window).
			MSG     TRANSMISSION MESSAGE         Generated by the aircraft. There are eight different MSG types.
			====    =========================    ==========================================================================================


		transmission_type (int): Message subtype 1-8. Only used for transmission messages (MSG):

			=====    ============    ==========================================================================================
			Value    Spec            Description
			=====    ============    ==========================================================================================
			1        DF17 BDS 0,8    ES Identification and Category
			2        DF17 BDS 0,6    ES Surface Position Message (Triggered by nose gear squat switch.)
			3        DF17 BDS 0,5    ES Airborne Position Message
			4        DF17 BDS 0,9    ES Airborne Velocity Message
			5        DF4, DF20       Surveillance Alt Message (Triggered by ground radar. Not CRC secured.)
			6        DF5, DF21       Surveillance ID Message (Triggered by ground radar. Not CRC secured.)
			7        DF16            Air To Air Message (Triggered from TCAS)
			8        DF11            All Call Reply (Broadcast but also triggered by ground radar)
			=====    ============    ==========================================================================================

			Transmission messages of type 5 and 6 will only be output if the aircraft has previously sent a MSG 1, 2, 3, 4 or 8 signal.

			Abbr.: DF = Downlink Format, BDS = Binary Data Store, TCAS = Traffic Alert and Collision Avoidance System

		session_id (int): Database Session record number.

		aircraft_id (int): Database Aircraft record number.

		hexident (str): Aircraft Mode S hexadecimal code, given in upper case.

		flight_id (str): Database Flight record number, given in upper case.

		generation_time (datetime.datetime): Generation time of the message.

		record_time (datetime.datetime): Recording time of the message.

		callsign (str): An eight digit flight ID - can be flight number or registration (or even nothing).

		altitude (int): Mode C altitude. Height relative to 1013.2mb (Flight Level). Not height above MSL (mean sea level).

		ground_speed (float): Speed over ground (not indicated airspeed) in knots (use `helpers.knots_to_kmh` or `helpers.knots_to_mps` to convert).

		track (float): Track of aircraft (not heading), in degrees. Derived from the velocity E/W and velocity N/S.

		latitude (float): Latitude in degrees, North and East positive. Airborne valid for 4 decimal places (about 5.1m), on ground valid for 5
			places (about 1.25m). Since not all positions can be encoded, some information has to be added by the client. This is not implemented in
			py1090 yet.

		longitude (float): Longitude in degrees, South and West negative. For accuracy information see `latitude`.

		vertical_rate (int): Vertical velocity in ft/s, 64ft/s resolution.

		squawk (str): Assigned Mode A squawk code.

		squawk_alert (bool): Flag to indicate squawk has changed.

		emergency (bool): Flag to indicate emergency code has been set.

		spi (bool): Special Purpose identification. Flag to indicate transponder ident has been activated.

		on_ground (bool): Flag to indicate ground squat switch is active.
	"""

	def __init__(self):
		self.message_type = None
		self.transmission_type = None
		self.session_id = None
		self.aircraft_id = None
		self.hexident = None
		self.flight_id = None
		self.generation_time = None
		self.record_time = None
		self.callsign = None
		self.altitude = None
		self.ground_speed = None
		self.track = None
		self.latitude = None
		self.longitude = None
		self.vertical_rate = None
		self.squawk = None
		self.squawk_alert = None
		self.emergency = None
		self.spi = None
		self.on_ground = None


	def parse_string(self, string):
		parts = string.strip().split(',')

		if parts[0]:
			self.message_type = parts[0].upper()

		if parts[1]:
			self.transmission_type = int(parts[1])

		if parts[2] and parts[2] != '111':
			self.session_id = int(parts[2])

		if parts[3] and parts[3] != '11111':
			self.aircraft_id = int(parts[3])

		if parts[4]:
			self.hexident = parts[4].upper()

		if parts[5] and parts[5] != '111111':
			self.flight_id = parts[5].upper()

		if len(parts[6]) > 0 and len(parts[7]) > 0:
			self.generation_time = _parse_datetime(parts[6], parts[7])

		if len(parts[8]) > 0 and len(parts[8]) > 0:
			self.record_time = _parse_datetime(parts[8], parts[9])

		if len(parts) > 10 and parts[10]:
			self.callsign = parts[10].upper()

		if self.message_type == 'MSG':
			if parts[11]:
				self.altitude = int(parts[11])

			# This is a workaround for a bug for rtl1090 output.
			# For subtype 7, only 21 fields are sent, and only altitude and on_ground is set.
			if self.transmission_type == 7 and len(parts) == 21:
				if parts[-1]:
					self.on_ground = _parse_bool(parts[-1])
				return

			if parts[12]:
				self.ground_speed = float(parts[12])

			if parts[13]:
				self.track = float(parts[13])

			if parts[14]:
				self.latitude = float(parts[14])

			if parts[15]:
				self.longitude = float(parts[15])

			if parts[16]:
				self.vertical_rate = int(parts[16])

			if parts[17]:
				self.squawk = int(parts[17])

			if parts[18]:
				self.squawk_alert = _parse_bool(parts[18])

			if parts[19]:
				self.emergency = _parse_bool(parts[19])

			if parts[20]:
				self.spi = _parse_bool(parts[20])

			if parts[21]:
				self.on_ground = _parse_bool(parts[21])


	def to_string(self):
		"""Serializes the message into the BaseStation format.

		:rtype: str
		"""
		format_coordinates = lambda x: '{:.5f}'.format(x)

		return ','.join((
			_dump_or_none(self.message_type),
			_dump_or_none(self.transmission_type),
			_dump_or_none(self.session_id),
			_dump_or_none(self.aircraft_id),
			_dump_or_none(self.hexident),
			_dump_or_none(self.flight_id),
			_dump_or_none(self.generation_time, _dump_datetime),
			_dump_or_none(self.record_time, _dump_datetime),
			_dump_or_none(self.callsign),
			_dump_or_none(self.altitude),
			_dump_or_none(self.ground_speed),
			_dump_or_none(self.track),
			_dump_or_none(self.latitude, format_coordinates),
			_dump_or_none(self.longitude, format_coordinates),
			_dump_or_none(self.vertical_rate),
			_dump_or_none(self.squawk),
			_dump_or_none(self.squawk_alert, _dump_bool),
			_dump_or_none(self.emergency, _dump_bool),
			_dump_or_none(self.spi, _dump_bool),
			_dump_or_none(self.on_ground, _dump_bool),
		)) + '\n'

	@classmethod
	def from_string(cls, string):
		"""Creates a new message from a BaseStation format line.

		:param str string: String to parse.
		:rtype: `Message`
		"""
		message = cls()
		message.parse_string(string)
		return message

	@staticmethod
	def iter_messages(iterator):
		"""Iterates an through an iterator and yields one message per line ::

			for message in Message.iter_messages(file):
				print(message)

		:param iterable iterator:
		"""
		for item in iterator:
			yield Message.from_string(item)
