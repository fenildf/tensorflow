"""Class to represent a device."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import copy


class Device(object):
  """Represents a Device."""

  def __init__(self, job=None, replica=None, task=None, device_type=None,
               device_index=None):
    """Create a new device object.

    Args:
      job: string.  Optional device job name.
      replica: int.  Optional replica index.
      task: int.  Optional task index.
      device_type: Optional device type string (e.g. "CPU" or "GPU")
      device_index: int.  Optional device index.  If left
        unspecified, device represents 'any' device_index.
    """
    self.job = job
    self.replica = replica
    self.task = task
    if device_type == "cpu" or device_type == "gpu":
      # For backwards compatibility only, we support lowercase variants of
      # cpu and gpu but turn them into uppercase here.
      self.device_type = device_type.upper()
    else:
      self.device_type = device_type
    self.device_index = device_index

  def _clear(self):
    self._job = None
    self._replica = None
    self._task = None
    self.device_type = None
    self.device_index = None

  @property
  def job(self):
    return self._job

  @job.setter
  def job(self, job):
    if job is not None:
      self._job = str(job)
    else:
      self._job = None

  @property
  def replica(self):
    return self._replica

  @replica.setter
  def replica(self, replica):
    if replica is not None:
      self._replica = int(replica)
    else:
      self._replica = None

  @property
  def task(self):
    return self._task

  @task.setter
  def task(self, task):
    if task is not None:
      self._task = int(task)
    else:
      self._task = None

  def parse_from_string(self, spec):
    """Parse a Device name into its components.

    Args:
      spec: a string of the form
       /job:<name>/replica:<id>/task:<id>/device:CPU:<id>
      or
       /job:<name>/replica:<id>/task:<id>/device:GPU:<id>
      as cpu and gpu are mutually exclusive.
      All entries are optional.

    Returns:
      The Device, for convenience.

    Raises:
      ValueError: if the spec was not valid.
    """
    self._clear()
    splits = [x.split(":") for x in spec.split("/")]
    for y in splits:
      ly = len(y)
      if y:
        # NOTE(touts): we use the property getters here.
        if ly == 2 and y[0] == "job":
          self.job = y[1]
        elif ly == 2 and y[0] == "replica":
          self.replica = y[1]
        elif ly == 2 and y[0] == "task":
          self.task = y[1]
        elif ((ly == 1 or ly == 2) and
              ((y[0].upper() == "GPU") or (y[0].upper() == "CPU"))):
          if self.device_type is not None:
            raise ValueError("Cannot specify multiple device types: %s" % spec)
          self.device_type = y[0].upper()
          if ly == 2 and y[1] != "*":
            self.device_index = int(y[1])
        elif ly == 3 and y[0] == "device":
          if self.device_type is not None:
            raise ValueError("Cannot specify multiple device types: %s" % spec)
          self.device_type = y[1]
          if y[2] != "*":
            self.device_index = int(y[2])
        elif ly and y[0] != "":  # pylint: disable=g-explicit-bool-comparison
          raise ValueError("Unknown attribute: '%s' in '%s'" % (y[0], spec))

    return self

  def merge_from(self, dev):
    """Merge the properties of "dev" into this Device.

    Args:
      dev: a Device.
    """
    if dev.job is not None:
      self.job = dev.job
    if dev.replica is not None:
      self.replica = dev.replica
    if dev.task is not None:
      self.task = dev.task
    if dev.device_type is not None:
      self.device_type = dev.device_type
    if dev.device_index is not None:
      self.device_index = dev.device_index

  def to_string(self):
    """Return a Device specification string.

    Returns:
      a string of the form /job:<name>/replica:<id>/task:<id>/device:cpu:<id>
      or /job:<name>/replica:<id>/task:<id>/device:cpu:<id>.
    """
    dev = ""
    if self.job is not None:
      dev += "/job:" + self.job
    if self.replica is not None:
      dev += "/replica:" + str(self.replica)
    if self.task is not None:
      dev += "/task:" + str(self.task)
    if self.device_type is not None:
      device_index_string = "*"
      if self.device_index is not None:
        device_index_string = str(self.device_index)
      dev += "/device:%s:%s" % (self.device_type, device_index_string)
    return dev


def from_string(spec):
  """Construct a Device from a string.

  Args:
    spec: a string of the form
     /job:<name>/replica:<id>/task:<id>/device:CPU:<id>
    or
     /job:<name>/replica:<id>/task:<id>/device:GPU:<id>
    as cpu and gpu are mutually exclusive.
    All entries are optional.

  Returns:
    A Device.
  """
  return Device().parse_from_string(spec)


def check_valid(spec):
  """Check that a device spec is valid.

  Args:
    spec: a string.

  Raises:
    An exception if the spec is invalid.
  """
  # Construct a device.  It will assert a failure if spec is invalid.
  from_string(spec)


def merge_device(spec):
  """Returns a device function that merges devices specifications.

  This can be used to merge partial specifications of devices. The
  innermost setting for a device field takes precedence. For example:

    with tf.Device(MergeDevice("/device:GPU:0"))
      # Nodes created here have device "/device:GPU:0"
      with tf.Device(MergeDevice("/job:worker")):
        # Nodes created here have device "/job:worker/device:GPU:0"
        with tf.Device(MergeDevice("/device:CPU:0")):
          # Nodes created here have device "/job:worker/device:CPU:0"
          with tf.Device(MergeDevice("/job:ps")):
            # Nodes created here have device "/job:ps/device:CPU:0"

  Args:
    spec: A device or a device spec string (partially) describing the
      device that should be used for all nodes created in the scope of
      the returned device function's with block.

  Returns:
    A device function with the above-described behavior.

  Raises:
    ValueError: if the spec was not valid.
  """
  if not isinstance(spec, Device):
    spec = from_string(spec or "")
  def _device_function(node_def):
    current_device = from_string(node_def.device or "")
    copy_spec = copy.copy(spec)
    copy_spec.merge_from(current_device)  # current_device takes precedence.
    return copy_spec
  return _device_function
