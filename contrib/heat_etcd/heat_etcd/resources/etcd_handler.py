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

import six
import uuid
import pprint

from heat.common.i18n import _
from heat.engine import attributes
from heat.engine import constraints
from heat.engine import properties
from heat.engine import resource
from heat.openstack.common import log as logging

LOG = logging.getLogger(__name__)

ETCD_INSTALLED = False
# conditionally import so tests can work without having the dependency
# satisfied
try:
    import etcd
    ETCD_INSTALLED = True
except ImportError:
    etcd = None


class Etcd(resource.Resource):

    PROPERTIES = (
        ENDPOINT,ROOT_NAME, IMAGE, TIMEOUT, INSTANCE_ID,
     ) = (
        'endpoint','root_name','image','timeout','instance_id',
    )

    

    properties_schema = {
        ENDPOINT: properties.Schema(
            properties.Schema.STRING,
            _('etcd daemon endpoint (by default there is no etcd server).'),
            required=True
        ),
        ROOT_NAME: properties.Schema(
            properties.Schema.STRING,
            _('etcd daemon endpoint (by default backends will be adopted).'),
            default='backends'
        ),
        TIMEOUT: properties.Schema(
            properties.Schema.NUMBER,
            _('max seconds to wait for a read. default is 60 sec.'),
        ),
        IMAGE: properties.Schema(
            properties.Schema.STRING,
            _('The ID or name of the image to boot with.'),
            constraints=[
                constraints.CustomConstraint('glance.image')
            ],
            update_allowed=True
        ),
        INSTANCE_ID: properties.Schema(
            properties.Schema.STRING,
            _('The ID of an existing instance to use to '
              'record to etcd server.'),
            # constraints=[
            #     constraints.CustomConstraint("nova.server")
            # ]
        ),
    }
    ATTRIBUTES = (
        VALUE,
    ) = (
        'value',
    )

    attributes_schema = {
        VALUE: attributes.Schema(
            _('The random string generated by this resource. This value is '
              'also available by referencing the resource.'),
        ),
    }
    # default_client_name = 'nova'

    def get_client(self):
        client = None
        endpoint = self.properties.get(self.ENDPOINT)
        if endpoint:
            port = 4001
            host = None
            if ":" in endpoint:
                host,port = endpoint.split(":")

            if host:
                timeout = self.properties.get(self.TIMEOUT)
                client = etcd.Client(host=host, port=int(port), read_timeout=int(timeout))
        return client

    def handle_create(self):

        rootname = self.properties[self.ROOT_NAME]
        timeout = self.properties[self.TIMEOUT]
        server_id = self.properties[self.INSTANCE_ID]

        image = self.properties.get(self.IMAGE)
        if image:
            image = self.glance().images.get(image).name

        etcd_client = self.get_client()
        try:
            etcd_client.read("%s" % rootname)
        except:
            etcd_client.write("%s" % rootname, None, dir=True)
            pass

        stack_id = self.stack.identifier().stack_path()
        server = self.nova().servers.get(server_id)


        if not etcd_client:
            raise exception.NotFound(_('Failed to find client'))

        base = "%s/%s/%s" % (rootname,image.replace("/","-"),server.id)


        LOG.info("stack id:%s, tenant:%s" % (stack_id,server.tenant_id))

        etcd_client.write("/%s/stack" % base, stack_id)
        etcd_client.write("/%s/tenant" % base, server.tenant_id)
        etcd_client.write("/%s/port" % base, None)
        etcd_client.write("/%s/container" % base, None)
        etcd_client.write("/%s/monitor" % base, None)

        return base,server.id

    def check_create_complete(self, tup):

        etcd_client = self.get_client()
        path = etcd_client.read("%s" % tup[0]).key.split("/")
        
        if path[3] == tup[1]:
            return True
        return False


    def _resolve_attribute(self, name):
        if name == self.VALUE:
            return self.data().get(self.VALUE)    

def resource_mapping():
    return {
        'CHT::Etcd::Node': Etcd,
    }


def available_resource_mapping():
    if ETCD_INSTALLED:
        return resource_mapping()
    else:
        LOG.warn(_("Etcd plug-in loaded, but python etcd lib not installed."))
        return {}