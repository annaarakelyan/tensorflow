# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Test runner for TensorFlow tests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import os
import shlex
import sys

from google.protobuf import json_format
from google.protobuf import text_format

from tensorflow.core.util import test_log_pb2
from tensorflow.python.platform import app
from tensorflow.python.platform import gfile
from tensorflow.python.platform import test
from tensorflow.python.platform import tf_logging
from tensorflow.tools.test import run_and_gather_logs_lib

# pylint: disable=g-import-not-at-top
# pylint: disable=g-bad-import-order
# pylint: disable=unused-import
# Note: cpuinfo and psutil are not installed for you in the TensorFlow
# OSS tree.  They are installable via pip.
try:
  import cpuinfo
  import psutil
except ImportError as e:
  tf_logging.error("\n\n\nERROR: Unable to import necessary library: {}.  "
                   "Issuing a soft exit.\n\n\n".format(e))
  sys.exit(0)
# pylint: enable=g-bad-import-order
# pylint: enable=unused-import

FLAGS = None


def gather_build_configuration():
  build_config = test_log_pb2.BuildConfiguration()
  build_config.mode = FLAGS.compilation_mode
  # Include all flags except includes
  cc_flags = [
      flag for flag in shlex.split(FLAGS.cc_flags) if not flag.startswith("-i")
  ]
  build_config.cc_flags.extend(cc_flags)
  return build_config


def main(unused_args):
  name = FLAGS.name
  test_name = FLAGS.test_name
  test_args = FLAGS.test_args
  test_results, _ = run_and_gather_logs_lib.run_and_gather_logs(name, test_name,
                                                                test_args)

  # Additional bits we receive from bazel
  test_results.build_configuration.CopyFrom(gather_build_configuration())

  serialized_test_results = text_format.MessageToString(test_results)

  if not FLAGS.test_log_output:
    print(serialized_test_results)
    return

  if FLAGS.test_log_output_use_tmpdir:
    tmpdir = test.get_temp_dir()
    output_path = os.path.join(tmpdir, FLAGS.test_log_output)
  else:
    output_path = os.path.abspath(FLAGS.test_log_output)
  gfile.GFile(output_path, "w").write(serialized_test_results)
  # Also write test results in JSON, used by the datastore uploader.
  json_test_results = json_format.MessageToJson(test_results)
  gfile.GFile(output_path + ".json", "w").write(json_test_results)
  tf_logging.info("Test results written to: %s" % output_path)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.register(
      "type", "bool", lambda v: v.lower() in ("true", "t", "y", "yes"))
  parser.add_argument(
      "--name", type=str, default="", help="Benchmark target identifier.")
  parser.add_argument(
      "--test_name", type=str, default="", help="Test target to run.")
  parser.add_argument(
      "--test_args",
      type=str,
      default="",
      help="Test arguments, space separated.")
  parser.add_argument(
      "--test_log_output", type=str, default="", help="Filename to write logs.")
  parser.add_argument(
      "--test_log_output_use_tmpdir",
      type="bool",
      nargs="?",
      const=True,
      default=False,
      help="Store the log output into tmpdir?")
  parser.add_argument(
      "--compilation_mode",
      type=str,
      default="",
      help="Mode used during this build (e.g. opt, dbg).")
  parser.add_argument(
      "--cc_flags",
      type=str,
      default="",
      help="CC flags used during this build.")
  FLAGS, unparsed = parser.parse_known_args()
  app.run(main=main, argv=[sys.argv[0]] + unparsed)
