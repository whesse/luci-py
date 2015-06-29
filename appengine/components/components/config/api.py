# Copyright 2015 The Swarming Authors. All rights reserved.
# Use of this source code is governed by the Apache v2.0 license that can be
# found in the LICENSE file.

"""Contains functions to access configs.

Uses remote.Provider or fs.Provider to load configs, depending on whether config
service hostname is configured in common.ConfigSettings.
See _get_config_provider().

Provider do not do type conversion, api.py does.
"""

import logging

from google.appengine.ext import ndb

from . import common
from . import fs
from . import remote


class Error(Exception):
  """Config component-related error."""


class CannotLoadConfigError(Error):
  """A config could not be loaded."""


def _get_config_provider():  # pragma: no cover
  """Returns a config provider to load configs.

  There are two config provider implementations: remote.Provider and
  fs.Provider. Both implement get_async(), get_project_configs_async(),
  get_ref_configs_async() with same signatures.
  """
  return remote.get_provider() or fs.get_provider()


@ndb.tasklet
def get_async(
    config_set, path, dest_type=None, revision=None, store_last_good=False):
  """Reads a revision and contents of a config.

  If |store_last_good| is True (default is False), does not make remote calls,
  but consults datastore only, so the call is faster, less likely to fail and
  resilient to config service outages. A request for a certain config with
  store_last_good==True, instructs Cron job to start checking it periodically.
  If a config was not requested for a week, it is deleted from the datastore and
  not updated anymore. If the Cron job receives an invalid config, it is
  ignored, so get_async with store_last_good=True is guaranteed to always return
  valid configs as long as validation code is not changed in a non-backward
  compatible way.

  Args:
    config_set (str): config set to read a config from.
    path (str): path to the config file within the config set.
    dest_type (type): if specified, config content will be converted to
      |dest_type|. Only protobuf messages are supported.
    revision (str): a revision of the config set. Defaults to the latest
      revision.
    store_last_good (bool): if True, store configs in the datastore. Detaults
      to True if latest revision of self config is requested, otherwise False.
      See above for more details.

  Returns:
    Tuple (revision, config), where config is converted to |dest_type|.

  Raises:
    NotImplementedError if |dest_type| is not supported.
    ValueError on invalid parameter.
    ConfigFormatError if config could not be converted to |dest_type|.
    CannotLoadConfigError if could not load a config.
  """
  assert config_set
  assert path
  common._validate_dest_type(dest_type)

  if store_last_good:
    if revision:  # pragma: no cover
      raise ValueError(
          'store_last_good parameter cannot be set to True if revision is '
          'specified')

  try:
    revision, config = yield _get_config_provider().get_async(
        config_set, path, revision=revision, store_last_good=store_last_good)
  except Exception as ex:
    raise CannotLoadConfigError(
        'Could not load config %s:%s, revision %r: %s' % (
            config_set,
            path,
            revision,
            ex,
        ))

  raise ndb.Return((revision, common._convert_config(config, dest_type)))


def get(*args, **kwargs):
  """Blocking version of get_async."""
  return get_async(*args, **kwargs).get_result()


def get_self_config_async(*args, **kwargs):
  """A shorthand for get_async with config set for the current appid."""
  return get_async(common.self_config_set(), *args, **kwargs)


def get_self_config(*args, **kwargs):
  """Blocking version of get_self_config_async."""
  return get_self_config_async(*args, **kwargs).get_result()


def get_project_config_async(project_id, *args, **kwargs):
  """A shorthand for get_async for a project config set."""
  return get_async('projects/%s' % project_id, *args, **kwargs)


def get_project_config(*args, **kwargs):
  """Blocking version of get_project_config_async."""
  return get_project_config_async(*args, **kwargs).get_result()


def get_ref_config_async(project_id, ref, *args, **kwargs):
  """A shorthand for get_async for a project ref config set."""
  assert ref and ref.startswith('refs/'), ref
  return get_async('projects/%s/%s' % (project_id, ref), *args, **kwargs)


def get_ref_config(*args, **kwargs):
  """Blocking version of get_ref_config_async."""
  return get_ref_config_async(*args, **kwargs).get_result()


@ndb.tasklet
def get_project_configs_async(path, dest_type=None):
  """Returns configs at |path| in all projects.

  Args:
    path (str): path to configuration files. Files at this path will be
      retrieved from all projects.
    dest_type (type): if specified, config contents will be converted to
      |dest_type|. Only protobuf messages are supported. If a config could not
      be converted, the exception will be logged, but not raised.

  Returns:
    {project_id -> (revision, config)} map. In file system mode, revision is
    None.
  """
  assert path
  common._validate_dest_type(dest_type)

  configs = yield _get_config_provider().get_project_configs_async(path)
  result = {}
  for config_set, (revision, content) in configs.iteritems():
    assert config_set and config_set.startswith('projects/'), config_set
    project_id = config_set[len('projects/'):]
    assert project_id
    try:
      config = common._convert_config(content, dest_type)
    except common.ConfigFormatError:
      logging.exception(
          'Could not parse config at %s in config set %s: %r',
          path, config_set, content)
      continue
    result[project_id] = (revision, config)
  raise ndb.Return(result)


def get_project_configs(path, dest_type=None):
  """Blocking version of get_project_configs_async."""
  return get_project_configs_async(path, dest_type).get_result()


@ndb.tasklet
def get_ref_configs_async(path, dest_type=None):
  """Returns config at |path| in all refs of all projects.

  Args:
    path (str): path to configuration files. Files at this path will be
      retrieved from all refs of all projects.
    dest_type (type): if specified, config contents will be converted to
      |dest_type|. Only protobuf messages are supported. If a config could not
      be converted, the exception will be logged, but not raised.

  Returns:
    A map {project -> {ref -> (revision, config)}}. Here ref is a str that
    always starts with 'ref/'. In file system mode, revision is None.
  """
  assert path
  common._validate_dest_type(dest_type)
  configs = yield _get_config_provider().get_ref_configs_async(path)
  result = {}
  for config_set, (revision, content) in configs.iteritems():
    assert config_set and config_set.startswith('projects/'), config_set
    project_id, ref = config_set.split('/', 2)[1:]
    assert project_id
    assert ref
    try:
      config = common._convert_config(content, dest_type)
    except common.ConfigFormatError:
      logging.exception(
          'Could not parse config at %s in config set %s: %r',
          path, config_set, content)
      continue
    result.setdefault(project_id, {})[ref] = (revision, config)
  raise ndb.Return(result)


def get_ref_configs(path, dest_type=None):
  """Blocking version of get_ref_configs_async."""
  return get_ref_configs_async(path, dest_type).get_result()


def get_config_set_location_async(config_set):  # pragma: no cover
  """Returns URL of where configs for a given config set are stored.

  It is a heavy call that always makes an RPC to the config service. Cache
  results appropriately.

  Args:
    config_set: name of the config set, e.g 'service/<id>' or 'projects/<id>'.

  Returns:
    URL or None if no such config set. In file system mode always None.
  """
  return _get_config_provider().get_config_set_location_async(config_set)


def get_config_set_location(config_set):  # pragma: no cover
  """Blocking version of get_config_set_location_async."""
  return get_config_set_location_async(config_set).get_result()
