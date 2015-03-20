Etcd plugin for OpenStack Heat
================================

This plugin enable using Etcd shared configuration as resources in a Heat template.

[python-etcd](https://github.com/jplana/python-etcd) A python client for Etcd

### 1. Install the Docker plugin in Heat

NOTE: These instructions assume the value of heat.conf plugin_dirs includes the
default directory /usr/lib/heat.

To install the plugin, from this directory run:
    sudo python ./setup.py install

### 2. Restart heat

Only the process "heat-engine" needs to be restarted to load the new installed
plugin.


### 3. Example of Heat_Etcd

the following exampl are represented as HOT format

```sample
etcd_record:
  type : CHT::Etcd:Node
  properties:
    endpoint : {get_param: host_url}    // host_url : 192.168.254.254:4001
    root_name : {get_param: rootname}
    timeout : {get_param: etcd_timeout}
    image : {get_param: etcd_retry}
    instance_id : {get_resource: docker_container}
```