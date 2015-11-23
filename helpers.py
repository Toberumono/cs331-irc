import sys

class ThreeStateLogger():
	def __init__(self, verbosity):
		verbosity = (0 if verbosity < 0 else (3 if verbosity > 3 else verbosity)) if type(verbosity) == int else 0
		self.verbosity = verbosity
		self.error = lambda *message: print("ERROR:", *message, file=sys.stderr) if self.verbosity > 0 else lambda *message: None
		self.warning = lambda *message: print("WARNING:", *message, file=sys.stderr) if self.verbosity > 1 else lambda *message: None
		self.info = lambda *message: print("INFO:", *message, file=sys.stdout) if self.verbosity > 2 else lambda *message: None

	def logError(self, *message):
		self.error(*message)

	def logWarning(self, *message):
		self.warning(*message)

	def logInfo(self, *message):
		self.info(*message)

	'''
	Prints the message at the given level, which is either 'error', 'warning', or 'info'. Defaults to 'error'
	'''
	def log(self, *message, level='error'):
		{"warning" : self.logWarning, "info" : self.logInfo}.get(level.strip().lower(), self.logError)(*message)

	def getVerbosity():
		return self.verbosity

class TestableRange():
	def getRangeTest(self, inclusive):
		inclusive = inclusive.strip().lower()
		ranges = {
				"neither" : lambda x: (self.getLowerBound() < x and x < self.getUpperBound()) and (x - self.getLowerBound()) % self.getStep() == 0,
				"lower" : lambda x: (self.getLowerBound() <= x and x < self.getUpperBound()) and (x - self.getLowerBound()) % self.getStep() == 0,
				"upper" : lambda x: (self.getLowerBound() < x and x <= self.getUpperBound()) and (x - self.getLowerBound()) % self.getStep() == 0
			}
		return (ranges[inclusive], inclusive) if inclusive in ranges else \
			(lambda x: (self.getLowerBound() <= x and x <= self.getUpperBound()) and (x - self.getLowerBound()) % self.getStep() == 0, 'both')

	'''
	Constructs a new TestableRange, defaults to [0.0, 1.0].
	inclusive can be 'both', 'lower', 'upper', or 'neither', and defaults to 'both'
	'''
	def __init__(self, lower=0.0, upper=1.0, inclusive='both', step=1.0, valueType=None):
		if valueType != None:
			TestableRange.checkType('lower', valueType, lower)
			TestableRange.checkType('upper', valueType, upper)
			TestableRange.checkType('step', valueType, step)
		self.lower = lower
		self.upper = upper
		self.step = step
		self.test, self.inclusive = self.getRangeTest(inclusive)

	def checkType(varname, expected, value):
		if not isinstance(value, expected):
			raise TypeError("Expected " + varname + " to be an instance of " + expected + ".  Got " + type(value) + " instead.")

	def __contains__(self, item):
		return self.test(item)

	def toGenerator(self):
		start = self.getLowerBound() + (0 if self.getInclusivity() == 'lower' or self.getInclusivity == 'both' else self.getStep())
		end = self.getUpperBound() + (self.getStep() if self.getInclusivity() == 'upper' or self.getInclusivity == 'both' else 0)
		x = start
		while x < end:
			yield x
			x += self.getStep()

	def __iter__(self):
		return self.toGenerator()

	def getLowerBound(self):
		return self.lower

	def getUpperBound(self):
		return self.upper

	def getStep(self):
		return self.step

	def getInclusivity(self):
		return self.inclusive

	def getTest(self):
		return self.test

class Validator():
	'''
	Validate is a function that takes one argument and returns True
	if that argument is valid.
	'''
	def __init__(self, validate):
		self.validate = validate

class ValidatorIter():
	def __init__(self, item, validators):
		self.__item = item
		self.__validators = validators

	def toGenerator(self):
		for validator in self.__validators:
			yield validator.validate(self.__item)

	def __iter__(self):
		return self.toGenerator()
