#!/usr/bin/env python

# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
#
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from opstestfw import *
from opstestfw.switch.CLI import *
from opstestfw.switch.OVS import *

from utils.keys import *


def host_configure_ip(host, config):
    for ip in config:
        retStruct = False

        LogOutput('info',
                  "Configuring host IP on Interface %s" %
                  ip[IP_INTF])

        if KEY_IPV6 in ip:
            LogOutput('info', "Configuring IPv6 Address")
            retStruct = host.Network6Config(
                                ipAddr=ip[IP_ADDR],
                                netMask=ip[IP_MASK],
                                interface=host.linkPortMapping[ip[IP_INTF]],
                                broadcast=ip[IP_BROADCAST],
                                config=ip[IP_ENABLE])
        else:
            LogOutput('info', "Configuring IPv4 Address")
            retStruct = host.NetworkConfig(
                                ipAddr=ip[IP_ADDR],
                                netMask=ip[IP_MASK],
                                interface=host.linkPortMapping[ip[IP_INTF]],
                                broadcast=ip[IP_BROADCAST],
                                config=ip[IP_ENABLE])

    assert not retStruct.returnCode(), "Failed to configure an IP address"


def host_configure_static_route(host, config):
    for route in config:

        retStruct = False

        if KEY_IPV6 in route:
            LogOutput('info', "Configuring IPv6 route for host")
            retStruct = host.IPRoutesConfig(destNetwork=route[ROUTE_DST],
                                            netMask=route[ROUTE_MASK],
                                            gateway=route[ROUTE_GATEWAY],
                                            ipv6Flag=route[ROUTE_IPV6],
                                            config=route[ROUTE_ENABLE])
        else:
            LogOutput('info', "Configuring IPv4 route for host")
            retStruct = host.IPRoutesConfig(destNetwork=route[ROUTE_DST],
                                            netMask=route[ROUTE_MASK],
                                            gateway=route[ROUTE_GATEWAY],
                                            config=route[ROUTE_ENABLE])

        assert not retStruct.returnCode(), \
            "Failed to configure IP address static route"


def configure_host(host, config):
    """Used for host basic configuration

    The idea of this function is to simplify device configuration, prevent
    multiple failure points across the test, it also to improve legibility when
    you are debugging. All host configuration values will be defined in a
    single variable, not across the test setup.

    Params:

        host:
            Device to be configured

        config:
            Dictionary with values to be configured

    The logic of how a device should be configured must be written here.
    """
    LogOutput('info', "Starting host configuration!")

    if KEY_IP in config:
        host_configure_ip(host, config[KEY_IP])

    if KEY_ROUTE in config:
        host_configure_static_route(host, config[KEY_ROUTE])

    LogOutput('info', "Host configuration DONE!")
