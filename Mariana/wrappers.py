from collections import OrderedDict
import theano
import sys

import Mariana.candies as MCAN

TYPE_TEST = 'test'
TYPE_TRAIN = 'train'
DEVICE_IS_GPU = theano.config.device.find("gpu") > -1

class TheanoFunction(object) :
	"""
	This class encapsulates a Theano function.
	TheanoFunction objects should be defined as self attributes in the setCustomTheanoFunctions() function of output layers.
	It will also generate custom error messages whose verbosity depends on Mariana.settings.VERBOSE. Set it to False to get quieter
	error messages. 
	"""

	def __init__(self, name, applicationType, outputLayer, output_expressions, additional_input_expressions = {}, updates = [], **kwargs) :
		"""
		:param str name: name of the function
		:param Output outputLayer: the output layer the function should be applied to
		:param list output_expressions: list of the symbolic expressions you want as output
		:param dict additional_input_expressions: additional inputs needed to compute the expressions
		:param list updates: list of tuples (shared variable, symbolic expression of the update to be applied to it)
		:param dict **kwargs: additional arguments to passed to the real theano function underneath
		"""
		self.cast_warning_told = False

		self.name = name
		self.outputLayer = outputLayer
		self.applicationType = applicationType.lower()

		self.inputs = OrderedDict()
		self.tmpInputs = OrderedDict()
		for inp in self.outputLayer.network.inputs.itervalues() :
			if self.applicationType == TYPE_TEST :
				self.inputs[inp.name] = inp.test_outputs
			elif self.applicationType == TYPE_TRAIN :
				self.inputs[inp.name] = inp.outputs
			else :
				raise AttributeError('Unknow applicationType %s' % applicationType)

		self.inputs.update(additional_input_expressions)
		
		for i in self.inputs :
			self.tmpInputs[i] = None
		
		self.additional_input_expressions = additional_input_expressions
		self.outputs = output_expressions
		self.updates = updates
		
		self.theano_fct = theano.function(inputs = list(set(self.inputs.values())), outputs = self.outputs, updates = self.updates, **kwargs)

		if any([x.__class__.__name__.lower().find("gpu") for x in self.theano_fct.maker.fgraph.toposort()]):
			device = "GPU"
		else:
			device = "CPU"

		MCAN.friendly("Run device", "I will use the [-%s-] to run the *%s* type function '%s' of layer '%s'!" % (device, self.applicationType, name, outputLayer.name))

	def printGraph(self) :
		"""Print the theano graph of the function"""
		theano.printing.debugprint(self.theano_fct)

	def run(self, **kwargs) :
		for k in kwargs :
			# print DEVICE_IS_GPU, kwargs[k].dtype.name, theano.config.floatX, kwargs[k].dtype.name != theano.config.floatX 
			if DEVICE_IS_GPU and kwargs[k].dtype != theano.config.floatX :
				if not self.cast_warning_told :
					MCAN.friendly("Casting: Trying to save the day",
						"""The GPU max size for a flaot is 32, your data for '%s' in function '%s' is '%s'.
I will try to cast the inputs at every iterration before computation.
Please cast your data to '%s' next time, that would certainly speed up the whole computation."""  % (k, self.name, kwargs[k].dtype, theano.config.floatX))
					self.cast_warning_told = True

				self.tmpInputs[k] = kwargs[k].astype(theano.config.floatX)
			else :
				self.tmpInputs[k] = kwargs[k]

		try :
			return self.theano_fct(*self.tmpInputs.values())	
		except Exception as e :
			sys.stderr.write("!!=> Error in function '%s' for layer '%s':\n" % (self.name, self.outputLayer.name))
			sys.stderr.write("\t!!=> the arguments were:\n %s\n" % (kwargs))
			raise e

	def __call__(self, **kwargs) :
		return self.run(**kwargs)

	def __repr__(self) :
		return "<Mariana Theano Fct '%s'>" % self.name

	def __str__(self) :
		return "<Mariana Theano Fct '%s': %s>" % (self.name, self.theano_fct)