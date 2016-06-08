# Copyright 2016 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

import collections


# Parsed value of JSON at path specified by 'SWARMING_AUTH_PARAMS' env var.
AuthParams = collections.namedtuple('AuthParams', [
  # Dict with HTTP headers to use when calling Swarming backend (specifically).
  # They identify the bot to the Swarming backend. Ultimately generated by
  # 'get_authentication_headers' in bot_config.py.
  'swarming_http_headers',
])


def prepare_auth_params_json(bot):
  """Returns a dict to put into JSON file at SWARMING_AUTH_PARAMS.

  This JSON file contains various tokens and configuration parameters that allow
  Swarming tasks to make authenticated calls to backends using security context
  of whoever posted the task.

  The file is managed by bot_main.py (main Swarming bot process) and consumed by
  task_running.py and its subprocesses that are aware of Swarming bot
  authentication.

  It lives it the task work directory.

  Args:
    bot: instance of bot.Bot.
  """
  return {
    'swarming_http_headers': bot.remote.get_authentication_headers(),
  }


def process_auth_params_json(val):
  """Takes a dict loaded from SWARMING_AUTH_PARAMS and validates it.

  Args:
    val: decoded JSON value read from SWARMING_AUTH_PARAMS file.

  Returns:
    AuthParams tuple.

  Raises:
    ValueError if val has invalid format.
  """
  if not isinstance(val, dict):
    raise ValueError('Expecting dict, got %r' % (val,))

  headers = val.get('swarming_http_headers') or {}
  if not isinstance(headers, dict):
    raise ValueError(
        'Expecting "swarming_http_headers" to be dict, got %r' % (headers,))

  # The headers must be ASCII for sure, so don't bother with picking the
  # correct unicode encoding, default would work. If not, it'll raise
  # UnicodeEncodeError, which is subclass of ValueError.
  headers = {str(k): str(v) for k, v in headers.iteritems()}

  return AuthParams(headers)