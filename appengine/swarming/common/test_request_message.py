# Copyright 2013 The Swarming Authors. All rights reserved.
# Use of this source code is governed by the Apache v2.0 license that can be
# found in the LICENSE file.

"""Defines all the objects used by the Swarming API and its serialization."""

import json
import logging
import urlparse


# The maximum priority value that a runner can have.
MAX_PRIORITY_VALUE = 1000

# The maximum number of instances that can be requested for a single test
# configuration.
MAX_NUM_INSTANCES = 50

# The time (in seconds) to wait after receiving a runner before aborting it.
# This is intended to delete runners that will never run because they will
# never find a matching machine.
SWARM_RUNNER_MAX_WAIT_SECS = 24 * 60 * 60


class Error(Exception):
  """Simple error exception properly scoped here."""
  pass


def Stringize(value, json_readable=False):
  """Properly convert value to a string.

  This is useful for objects deriving from TestRequestMessageBase so that
  we can explicitly convert them to strings instead of getting the
  usual <__main__.XXX object at 0x...>.

  Args:
    value: The value to Stringize.
    json_readable: If true, the string output will be valid to load with
        json.loads().

  Returns:
    The stringized value.
  """
  if isinstance(value, (list, tuple)):
    value = '[%s]' % ', '.join([Stringize(i, json_readable) for i in value])
  elif isinstance(value, dict):
    value = '{%s}' % ', '.join(
        ('%s: %s' % (Stringize(i, json_readable),
                     Stringize(value[i], json_readable)))
        for i in sorted(value))
  elif isinstance(value, TestRequestMessageBase):
    value = value.__str__(json_readable)
  elif isinstance(value, basestring):
    if json_readable:
      value = value.replace('\\', '\\\\')
    value = u'\"%s\"' % value if json_readable else u'\'%s\'' % value
  elif json_readable and value is None:
    value = u'null'
  elif json_readable and isinstance(value, bool):
    value = u'true' if value else u'false'
  else:
    value = unicode(value)
  return value


class TestRequestMessageBase(object):
  """A Test Request Message base class to provide generic methods.

  It uses the __dict__ of the class to reset it using a new text message
  or to dump it to text when going the other way. So the objects deriving from
  it should have no other instance data members then the ones that are part of
  the Test Request Format.
  """
  def __init__(self, **kwargs):
    if kwargs:
      # Cheezy but this will go away with SerializableModelMixin.
      logging.warning('Ignored arguments: %r', kwargs)

  def __str__(self, json_readable=False):
    """Returns the request text after validating it.

    If the request isn't valid, an empty string is returned.

    Args:
      json_readable: If true, the string output will be valid to load with
        json.loads().

    Returns:
      The text string representing the request.
    """
    request_text_entries = ['{']
    # We sort the dictionary to ensure the string is always printed the same.
    for item in sorted(self.__dict__):
      request_text_entries.extend([
          Stringize(item, json_readable), ': ',
          Stringize(self.__dict__[item], json_readable), ','])

    # The json format doesn't allow trailing commas.
    if json_readable and request_text_entries[-1] == ',':
      request_text_entries.pop()

    request_text_entries.append('}')
    return ''.join(request_text_entries)

  def __eq__(self, other):
    """Returns a deep compare for equal.

    The default implementation for == does a shallow pointer compare only.
    If the pointers are not the same, it looks for __eq__ for a more specific
    compare, which we want to use to identify identical requests.

    Args:
      other: The other object we must compare too.

    Returns:
      True if other contains the same data as self does.
    """
    return type(self) == type(other) and self.__dict__ == other.__dict__

  def ValidateValues(self, value_keys, value_type, required=False):
    """Raises if any of the values at the given keys are not of the right type.

    Args:
      value_keys: The key names of the values to validate.
      value_type: The type that all the values should be.
      required: An optional flag identifying if the value is required to be
          non-empty. Defaults to False.
    """
    for value_key in value_keys:
      if value_key not in self.__dict__:
        raise Error(
            '%s must have a value for %s' %
            (self.__class__.__name__, value_key))

      value = self.__dict__[value_key]
      # Since 0 is an acceptable required value, but (not 0 == True), we
      # explicity check against 0.
      if required and (not value and value != 0):
        raise Error('%s must have a non-empty value' % value_key)
      # If the value is not required, it could be None, which would
      # not likely be of the value_type. If it is required and None, we would
      # have returned False above.
      if value is not None and not isinstance(value, value_type):
        raise Error('Invalid %s: %s' % (value_key, self.__dict__[value_key]))

  def ValidateLists(self, list_keys, value_type, required=False):
    """Raises if any of the values at the given list keys are not of the right
    type.

    Args:
      list_keys: The key names of the value lists to validate.
      value_type: The type that all the values in the lists should be.
      required: An optional flag identifying if the list is required to be
          non-empty. Defaults to False.
    """
    self.ValidateValues(list_keys, list, required)

    for value_key in list_keys:
      if self.__dict__[value_key]:
        for value in self.__dict__[value_key]:
          if not isinstance(value, value_type):
            raise Error('Invalid entry in list %s: %s' % (value_key, value))
      elif required:
        raise Error('Missing required %s' % value_key)

  def ValidateDicts(self, list_keys, key_type, value_type, required=False):
    """Raises if any of the values at the given list keys are not of the right
    type.

    Args:
      list_keys: The key names of the value lists to validate.
      key_type: The type that all the keys in the dict should be.
      value_type: The type that all the values in the dict should be.
      required: An optional flag identifying if the dict is required to be
          non-empty. Defaults to False.
    """
    self.ValidateValues(list_keys, dict, required)

    for value_key in list_keys:
      if self.__dict__[value_key]:
        for key, value in self.__dict__[value_key].iteritems():
          if (not isinstance(key, key_type) or
              not isinstance(value, value_type)):
            raise Error('Invalid entry in dict %s: %s' % (value_key, value))
      elif required:
        raise Error('Missing required %s' % value_key)

  def ValidateObjectLists(self, list_keys, object_type, required=False):
    """Raises if any of the objects of the given lists are not valid.

    Args:
      list_keys: The key names of the value lists to validate.
      object_type: The type of object to validate.
      required: An optional flag identifying if the list is required to be
          non-empty. Defaults to False.
    """
    self.ValidateLists(list_keys, object_type, required)
    for list_key in list_keys:
      for object_value in self.__dict__[list_key]:
        object_value.Validate()

  @staticmethod
  def ValidateUrl(url):
    """Raises if the given value is not a valid URL."""
    if not isinstance(url, basestring):
      raise Error('Unsupported url type, %s, must be a string' % url)

    url_parts = urlparse.urlsplit(url)
    if url_parts[0] not in ('http', 'https'):
      raise Error('Unsupported url scheme, %s' % url_parts[0])

  def ValidateUrls(self, url_keys):
    """Raises if any of the value at value_key are not a valid URL."""
    for url_key in url_keys:
      self.ValidateUrl(self.__dict__[url_key])

  def ValidateUrlLists(self, list_keys, required=False):
    """Raises if any of the values in the given lists is not a valid url.

    Args:
      list_keys: The key names of the value lists to validate.
      required: An optional flag identifying if the list is required to be
          non-empty. Defaults to False.
    """
    self.ValidateValues(list_keys, list, required)

    for list_key in list_keys:
      if self.__dict__[list_key]:
        for value in self.__dict__[list_key]:
          self.ValidateUrl(value)
      elif required:
        raise Error('Missing list %s' % list_key)

  def ValidateDataLists(self, list_keys, required=False):
    """Raises if any of the values in the given lists are not valid 'data'.

    Valid data is a list of tuple (valid url, local file name).

    Args:
      list_keys: The key names of the value lists to validate.
      required: An optional flag identifying if the list is required to be
          non-empty. Defaults to False.
    """
    self.ValidateValues(list_keys, list, required)

    for list_key in list_keys:
      if self.__dict__[list_key]:
        for value in self.__dict__[list_key]:
          if not isinstance(value, (list, tuple)):
            raise Error(
                'Data list wrong type, must be tuple, got %s' % type(value))

          if len(value) != 2:
            raise Error(
                'Incorrect length, should be 2 but is %d' % len(value))
          self.ValidateUrl(value[0])
          if not isinstance(value[1], basestring):
            raise Error(
                'Local path should be of type basestring, got %s' %
                type(value[1]))
      elif required:
        raise Error('Missing list %s' % list_key)

  @staticmethod
  def ValidateEncoding(encoding):
    """Raises if the given encoding is not valid."""
    try:
      unicode('0', encoding)
    except LookupError:
      raise Error('Invalid encoding %s' % encoding)

  def Validate(self):
    """Raises if the current content is not valid."""
    raise NotImplementedError()

  @classmethod
  def FromJSON(cls, data):
    """Parses the given JSON encoded data into an object instance.

    Raises:
      Error: If the data has syntax or type errors.
    """
    try:
      data = json.loads(data)
    except (TypeError, ValueError) as e:
      raise Error('Invalid json: %s' % e)
    return cls.FromDict(data)

  @classmethod
  def FromDict(cls, dictionary):
    """Converts a dictionary to an object instance.

    Args:
      dictionary: The dictionary to convert to objects.

    Returns:
      An object of the specified type.

    Raises:
      Error: If the dictionary has type errors. The text of the Error exception
          will be set with the type error text message.
    """
    try:
      out = cls(**dictionary)
      out.Validate()
      return out
    except (TypeError, ValueError) as e:
      raise Error('Failed to create %s: %s\n%s' % (cls.__name__, e, dictionary))

  @classmethod
  def FromDictList(cls, dict_list):
    """Convert all dictionaries in the given list to an object instance.

    Args:
      dict_list: The list of dictionaries to convert to objects.
      cls: The type of objects the list entries must be converted to. This type
          of object must expose a FromDict() method.
    """
    return [cls.FromDict(d) for d in dict_list]


class TestObject(TestRequestMessageBase):
  """Describes a command to run, including the command line.

  A 'task' as described by TestCase can include multiple commands to run. The
  user provides an instance of this class inside a TestCase.

  Attributes:
    action: The command line to run.
    decorate_output: The output decoration flag of this test object.
    hard_time_out: The maximum time this test can take.
    io_time_out: The maximum time this test can take (resetting anytime the test
        writes to stdout).
  """

  def __init__(self, action=None, decorate_output=True, hard_time_out=3600.0,
               io_time_out=1200.0, **kwargs):
    super(TestObject, self).__init__(**kwargs)
    self.action = action[:] if action else []
    self.decorate_output = decorate_output
    self.hard_time_out = hard_time_out
    self.io_time_out = io_time_out
    self.Validate()

  def Validate(self):
    """Raises if the current content is not valid."""
    self.ValidateLists(['action'], basestring, required=True)
    self.ValidateValues(['hard_time_out', 'io_time_out'], (int, long, float))


class TestConfiguration(TestRequestMessageBase):
  """Describes how to choose swarming bot to execute a requests.

  It defines the dimensions that are required and the number of swarming bot
  instances that are going to be used to run this list of 'tests', which is
  actually a task. The user provides an instance of this class inside a
  TestCase.

  Attributes:
    deadline_to_run: An optional value that specifies how long the test can
        wait before it is aborted (in seconds). Defaults to
        SWARM_RUNNER_MAX_WAIT_SECS.
    priority: The priority of this configuartion, used to determine execute
        order (a lower number is higher priority). Defaults to 10, the
        acceptable values are [0, MAX_PRIORITY_VALUE].
    dimensions: A dictionary of strings or list of strings for dimensions.
  """
  def __init__(self, deadline_to_run=SWARM_RUNNER_MAX_WAIT_SECS, priority=100,
               dimensions=None, **kwargs):
    super(TestConfiguration, self).__init__(**kwargs)
    self.deadline_to_run = deadline_to_run
    self.priority = priority
    self.dimensions = dimensions.copy() if dimensions else {}
    self.Validate()

  def Validate(self):
    """Raises if the current content is not valid."""
    # required=True to make sure the caller doesn't set it to None.
    self.ValidateValues(
        ['deadline_to_run', 'priority'], (int, long), required=True)

    if (self.deadline_to_run < 0 or
        self.priority < 0 or self.priority > MAX_PRIORITY_VALUE):
      raise Error('Invalid TestConfiguration: %s' % self.__dict__)

    if not isinstance(self.dimensions, dict):
      raise Error(
          'Invalid TestConfiguration dimension type: %s' %
          type(self.dimensions))
    for values in self.dimensions.values():
      if not isinstance(values, (list, tuple)):
        values = [values]
      for value in values:
        if not value or not isinstance(value, basestring):
          raise Error('Invalid TestConfiguration dimension value: %s' % value)


class TestCase(TestRequestMessageBase):
  """Describes a task to run.

  It defines the inputs and outputs to run a task on a single swarming bot. The
  task is a list of TestObject commands to run in order. The user provides an
  instance of this class to trigger a Swarming task.

  Attributes:
    test_case_name: The name of this test case.
    requestor: The id of the user requesting this test (generally an email
        address).
    env_vars: An optional dictionary for environment variables.
    configurations: A list of configurations for this test case.
    data: An optional 'data list' for this configuration.
    tests: An list of TestObject to run for this task.
    verbose: An optional boolean value that specifies if logging should be
        verbose.
  """
  def __init__(self, test_case_name=None, requestor=None, env_vars=None,
               configurations=None, data=None, tests=None, verbose=False,
               **kwargs):
    super(TestCase, self).__init__(**kwargs)
    self.test_case_name = test_case_name
    # TODO(csharp): Stop using a default so test requests that don't give a
    # requestor are rejected.
    self.requestor = requestor or 'unknown'
    self.env_vars = env_vars.copy() if env_vars else {}
    self.configurations = configurations[:] if configurations else []
    self.data = data[:] if data else []
    self.tests = tests[:] if tests else []
    self.verbose = verbose
    self.Validate()

  def Validate(self):
    """Raises if the current content is not valid."""
    self.ValidateValues(['test_case_name'], basestring, required=True)
    self.ValidateValues(['requestor'], basestring)
    self.ValidateDicts(['env_vars'], basestring, basestring)
    self.ValidateObjectLists(
        ['configurations'], TestConfiguration, required=True)
    if len(self.configurations) != 1:
      raise Error('Currently only support 1 configuration')
    self.ValidateDataLists(['data'])
    self.ValidateObjectLists(['tests'], TestObject)

    # self.verbose doesn't need to be validated since we only need
    # to evaluate them to True/False which can be done with any type.

  @classmethod
  def FromDict(cls, dictionary):
    """Converts a dictionary to an object instance.

    We override the base class behavior to create instances of TestOjbects and
    TestConfiguration.
    """
    dictionary = dictionary.copy()
    dictionary['tests'] = TestObject.FromDictList(dictionary.get('tests', []))
    dictionary['configurations'] = TestConfiguration.FromDictList(
        dictionary.get('configurations', []))
    return super(TestCase, cls).FromDict(dictionary)


class TestRun(TestRequestMessageBase):
  """Contains results of a task execution.

  TODO(maruel): Contains a lot of duplicated fields from TestCase, even if it
  reference them via 'tests'. Should be refactored.

  The Swarming server generates instance of this class for consumption by
  local_test_runner.py. The user does not interact with this API.

  Attributes:
    env_vars: An optional dictionary for environment variables.
    configuration: An optional configuration object for this test run.
    data: An optional 'data list' for this test run.
    tests: optional(!?) list of TestObject for this test run.
    result_url: The URL where to post the results of this test run.
    ping_url: The URL that tells the test run where to ping to let the server
        know that it is still active.
    ping_delay: The amount of time to wait between pings (in seconds).
  """
  def __init__(self, env_vars=None, configuration=None, data=None, tests=None,
               result_url=None, ping_url=None, ping_delay=None, **kwargs):
    super(TestRun, self).__init__(**kwargs)
    self.env_vars = env_vars.copy() if env_vars else {}
    self.configuration = configuration
    self.data = data[:] if data else []
    self.tests = tests[:] if tests else []
    self.result_url = result_url
    self.ping_url = ping_url
    self.ping_delay = ping_delay
    self.Validate()

  def Validate(self):
    """Raises if the current content is not valid."""
    self.ValidateDicts(['env_vars'], basestring, basestring)
    self.ValidateUrl(self.result_url)
    self.ValidateUrl(self.ping_url)
    self.ValidateValues(['ping_delay'], (int, long), required=True)
    self.ValidateDataLists(['data'])
    self.ValidateObjectLists(['tests'], TestObject)
    self.ValidateValues(
        ['result_url', 'ping_url'], basestring)

    if (not self.configuration or
        not isinstance(self.configuration, TestConfiguration) or
        self.ping_delay < 0):
      raise Error('Invalid TestRun: %s' % self.__dict__)

    self.configuration.Validate()

  @classmethod
  def FromDict(cls, dictionary):
    """Converts a dictionary to an object instance.

    We override the base class behavior to create instances of TestOjbects and
    TestConfiguration.
    """
    dictionary = dictionary.copy()
    dictionary['tests'] = TestObject.FromDictList(dictionary.get('tests', []))
    dictionary['configuration'] = TestConfiguration.FromDict(
        dictionary.get('configuration', {}))
    return super(TestRun, cls).FromDict(dictionary)