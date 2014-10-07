# Copyright 2013 The Swarming Authors. All rights reserved.
# Use of this source code is governed by the Apache v2.0 license that can be
# found in the LICENSE file.

"""Returns a swarming bot dimensions and setups automatic startup if needed.

This file is uploaded the swarming server so the swarming bots can declare their
dimensions and startup method easily.
"""

import os_utilities


def get_attributes():
  """Returns the attributes for this bot."""
  # The bot id will be automatically selected based on the hostname. If you want
  # something more special, specify it in your start_slave.py. You can upload a
  # new version via /restricted/upload_start_slave.
  return os_utilities.get_attributes(None)


def setup_bot():
  """Does one time initialization for this bot.

  Returns True if it's fine to start the bot right away. Otherwise, the calling
  script should exit.

  Example: making this script starts automatically on user login via
  os_utilities.set_auto_startup_win() or os_utilities.set_auto_startup_osx().
  """
  return True