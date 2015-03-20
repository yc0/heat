#
# Copyright (c) 2013 Docker, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
from oslo.utils import importutils

from heat.common import exception
from heat.common import template_format
from heat.engine import resource
from heat.engine import scheduler
from heat.tests.common import HeatTestCase
from heat.tests import utils

from testtools import skipIf

from ..resources import docker_container  # noqa
from .fake_docker_client import FakeDockerClient  # noqa

docker = importutils.try_import('docker')


template = '''
{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Test template",
    "Parameters": {},
    "Resources": {
        "Blog": {
            "Type": "DockerInc::Docker::Container",
            "Properties": {
                "image": "samalba/wordpress",
                "env": [
                    "FOO=bar"
                ]
            }
        }
    }
}
'''


class EtcdTest(HeatTestCase):

    def setUp(self):
        super(DockerContainerTest, self).setUp()
        for res_name, res_class in docker_container.resource_mapping().items():
            resource._register_class(res_name, res_class)
        self.addCleanup(self.m.VerifyAll)

    def create_container(self, resource_name):
        t = template_format.parse(template)
        stack = utils.parse_stack(t)
        resource = docker_container.DockerContainer(
            resource_name,
            stack.t.resource_definitions(stack)[resource_name], stack)
        self.m.StubOutWithMock(resource, 'get_client')
        resource.get_client().MultipleTimes().AndReturn(FakeDockerClient())
        self.assertIsNone(resource.validate())
        self.m.ReplayAll()
        scheduler.TaskRunner(resource.create)()
        self.assertEqual((resource.CREATE, resource.COMPLETE),
                         resource.state)
        return resource


    def test_resource_create(self):
        container = self.create_container('Blog')
        self.assertTrue(container.resource_id)
        running = self.get_container_state(container)['Running']
        self.assertIs(True, running)
        client = container.get_client()
        self.assertEqual(['samalba/wordpress'], client.pulled_images)
        self.assertIsNone(client.container_create[0]['name'])

