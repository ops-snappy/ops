# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

##########################################################################
# Name:        test_static_lag_ft_shutdown_no_shutdown.py
#
# Objective:   To verify that packets are no passing if LAG is un shutdown
#
# Topology:    2 switches connected by 2 interfaces and 2 hosts connected
#              by 1 interface
#
##########################################################################

import time

TOPOLOGY = """
# +-------+                                 +-------+
# |       |     +-------+     +-------+     |       |
# |  hs1  <----->  sw1  <----->  sw2  <----->  hs2  |
# |       |     +-------+     +-------+     |       |
# +-------+                                 +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=openswitch name="Switch 2"] sw2
[type=host name="Host 1"] hs1
[type=host name="Host 2"] hs2

# Links
hs1:1 -- sw1:3
sw1:1 -- sw2:1
sw1:2 -- sw2:2
sw2:3 -- hs2:1
"""


def create_lag_off(sw, lag_id):
    with sw.libs.vtysh.ConfigInterfaceLag(lag_id) as ctx:
        ctx.no_routing()


def delete_lag(sw, lag_id):
    with sw.libs.vtysh.Configure() as ctx:
        ctx.no_interface_lag(lag_id)


def associate_interface_to_lag(sw, interface, lag_id):
    with sw.libs.vtysh.ConfigInterface(interface) as ctx:
        ctx.lag(lag_id)


def turn_on_interface(sw, interface):
    with sw.libs.vtysh.ConfigInterface(interface) as ctx:
        ctx.no_shutdown()


def turn_off_interface(sw, interface):
    with sw.libs.vtysh.ConfigInterface(interface) as ctx:
        ctx.shutdown()


def is_interface_up(sw, interface):
    interface_status = sw('show interface {interface}'.format(**locals()))
    lines = interface_status.split('\n')
    for line in lines:
        if "Admin state" in line and "up" in line:
            return True
    return False


def create_vlan(sw, vlan_id):
    with sw.libs.vtysh.ConfigVlan(vlan_id) as ctx:
        ctx.no_shutdown()


def associate_vlan_to_lag(sw, vlan_id, lag_id):
    with sw.libs.vtysh.ConfigInterfaceLag(lag_id) as ctx:
        ctx.vlan_access(vlan_id)


def associate_vlan_to_l2_interface(sw, vlan_id, interface):
    with sw.libs.vtysh.ConfigInterface(interface) as ctx:
        ctx.no_routing()
        ctx.vlan_access(vlan_id)


def check_connectivity_between_hosts(h1, h1_ip, h2, h2_ip, success):
    ping = h1.libs.ping.ping(1, h2_ip)
    if success:
        assert ping['transmitted'] == ping['received'] == 1,\
            'Ping between ' + h1_ip + ' and ' + h2_ip + ' failed'
    else:
        assert not ping['transmitted'] == ping['received'] == 1,\
            'Ping between ' + h1_ip + ' and ' + h2_ip + ' success'

    ping = h2.libs.ping.ping(1, h1_ip)
    if success:
        assert ping['transmitted'] == ping['received'] == 1,\
            'Ping between ' + h2_ip + ' and ' + h1_ip + ' failed'
    else:
        assert not ping['transmitted'] == ping['received'] == 1,\
            'Ping between ' + h2_ip + ' and ' + h1_ip + ' success'


def enable_lag_shutdown(sw, lag_id, enabled):
    with sw.libs.vtysh.ConfigInterfaceLag(lag_id) as ctx:
        if enabled:
            ctx.shutdown()
        else:
            ctx.no_shutdown()


def test_lag_shutdown_by_default(topology):
    """Test LAG with shutdown by default ('no shutdown').

    By default a new LAG will be configured with 'no shutdown'. IPv4 pings
    from both clients must be successful.
    """

    print('\n############################################')
    print('Test lag shutdown (By default)')
    print('############################################')

    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')
    hs1 = topology.get('hs1')
    hs2 = topology.get('hs2')

    sw1_lag_id = '100'
    sw2_lag_id = '200'
    h1_ip_address = '10.0.0.1'
    h2_ip_address = '10.0.0.2'
    vlan = 100
    mask = '/24'

    assert sw1 is not None
    assert sw2 is not None
    assert hs1 is not None
    assert hs2 is not None

    print("Configure IP and bring UP in host 1")
    hs1.libs.ip.interface('1', addr=h1_ip_address + mask, up=True)

    print("Configure IP and bring UP in host 2")
    hs2.libs.ip.interface('1', addr=h2_ip_address + mask, up=True)

    p11 = sw1.ports['1']
    p12 = sw1.ports['2']
    p13 = sw1.ports['3']
    p21 = sw2.ports['1']
    p22 = sw2.ports['2']
    p23 = sw2.ports['3']

    print("Turning on all interfaces used in this test")
    ports_sw1 = [p11, p12, p13]
    for port in ports_sw1:
        turn_on_interface(sw1, port)

    ports_sw2 = [p21, p22, p23]
    for port in ports_sw2:
        turn_on_interface(sw2, port)

    print("Create LAG in both switches")
    create_lag_off(sw1, sw1_lag_id)
    create_lag_off(sw2, sw2_lag_id)

    print("Configure vlan and switch interfaces")
    create_vlan(sw1, vlan)
    create_vlan(sw2, vlan)

    print("Associate vlan with lag in both switches")
    associate_vlan_to_lag(sw1, vlan, sw1_lag_id)
    associate_vlan_to_lag(sw2, vlan, sw2_lag_id)

    print("Associate vlan with l2 interfaces in both switches")
    associate_vlan_to_l2_interface(sw1, vlan, p13)
    associate_vlan_to_l2_interface(sw2, vlan, p23)

    print("Associate interfaces [1,2] to lag in both switches")
    associate_interface_to_lag(sw1, p11, sw1_lag_id)
    associate_interface_to_lag(sw1, p12, sw1_lag_id)
    associate_interface_to_lag(sw2, p21, sw2_lag_id)
    associate_interface_to_lag(sw2, p22, sw2_lag_id)

    print("Waiting some time for the interfaces to be up")
    time.sleep(60)

    print("Verify all interface are up")
    for port in ports_sw1:
        assert is_interface_up(sw1, port),\
            "Interface " + port + " should be up"
    for port in ports_sw2:
        assert is_interface_up(sw2, port),\
            "Interface " + port + " should be up"

    check_connectivity_between_hosts(hs1, h1_ip_address, hs2, h2_ip_address,
                                     True)

    print("Cleaning configuration")
    for port in ports_sw1:
        turn_off_interface(sw1, port)

    for port in ports_sw2:
        turn_off_interface(sw2, port)

    delete_lag(sw1, sw1_lag_id)
    delete_lag(sw2, sw2_lag_id)

    hs1.libs.ip.remove_ip('1', addr=(h1_ip_address + mask))
    hs2.libs.ip.remove_ip('1', addr=(h2_ip_address + mask))

    print('\n############################################')
    print('Test lag shutdown (By default) DONE')
    print('############################################')


def test_lag_shutdown_disabled(topology):
    """Test LAG with shutdown enabled.

    By default a new LAG is configured as 'no shutdown', so this case will
    test to execute 'no shutdown' on both switches and connectivity must
    remain working and IPv4 pings between both clients must be successful.
    """

    print('\n############################################')
    print('Test lag shutdown (\'no shutdown\')')
    print('############################################')

    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')
    hs1 = topology.get('hs1')
    hs2 = topology.get('hs2')

    sw1_lag_id = '100'
    sw2_lag_id = '200'
    h1_ip_address = '10.0.0.1'
    h2_ip_address = '10.0.0.2'
    vlan = 100
    mask = '/24'

    assert sw1 is not None
    assert sw2 is not None
    assert hs1 is not None
    assert hs2 is not None

    print("Configure IP and bring UP in host 1")
    hs1.libs.ip.interface('1', addr=h1_ip_address + mask, up=True)

    print("Configure IP and bring UP in host 2")
    hs2.libs.ip.interface('1', addr=h2_ip_address + mask, up=True)

    p11 = sw1.ports['1']
    p12 = sw1.ports['2']
    p13 = sw1.ports['3']
    p21 = sw2.ports['1']
    p22 = sw2.ports['2']
    p23 = sw2.ports['3']

    print("Turning on all interfaces used in this test")
    ports_sw1 = [p11, p12, p13]
    for port in ports_sw1:
        turn_on_interface(sw1, port)

    ports_sw2 = [p21, p22, p23]
    for port in ports_sw2:
        turn_on_interface(sw2, port)

    print("Create LAG in both switches")
    create_lag_off(sw1, sw1_lag_id)
    create_lag_off(sw2, sw2_lag_id)

    print("Configure vlan and switch interfaces")
    create_vlan(sw1, vlan)
    create_vlan(sw2, vlan)

    print("Associate vlan with lag in both switches")
    associate_vlan_to_lag(sw1, vlan, sw1_lag_id)
    associate_vlan_to_lag(sw2, vlan, sw2_lag_id)

    print("Associate vlan with l2 interfaces in both switches")
    associate_vlan_to_l2_interface(sw1, vlan, p13)
    associate_vlan_to_l2_interface(sw2, vlan, p23)

    print("Associate interfaces [1,2] to lag in both switches")
    associate_interface_to_lag(sw1, p11, sw1_lag_id)
    associate_interface_to_lag(sw1, p12, sw1_lag_id)
    associate_interface_to_lag(sw2, p21, sw2_lag_id)
    associate_interface_to_lag(sw2, p22, sw2_lag_id)

    print("Waiting some time for the interfaces to be up")
    time.sleep(60)

    print("Verify all interface are up")
    for port in ports_sw1:
        assert is_interface_up(sw1, port),\
            "Interface " + port + " should be up"
    for port in ports_sw2:
        assert is_interface_up(sw2, port),\
            "Interface " + port + " should be up"

    # 'no shutdown' on switch 1
    check_connectivity_between_hosts(hs1, h1_ip_address, hs2, h2_ip_address,
                                     True)
    enable_lag_shutdown(sw1, sw1_lag_id, False)
    check_connectivity_between_hosts(hs1, h1_ip_address, hs2, h2_ip_address,
                                     True)

    # 'no shutdown' on switch 2
    check_connectivity_between_hosts(hs1, h1_ip_address, hs2, h2_ip_address,
                                     True)
    enable_lag_shutdown(sw2, sw2_lag_id, False)
    check_connectivity_between_hosts(hs1, h1_ip_address, hs2, h2_ip_address,
                                     True)

    print("Cleaning configuration")
    for port in ports_sw1:
        turn_off_interface(sw1, port)

    for port in ports_sw2:
        turn_off_interface(sw2, port)

    delete_lag(sw1, sw1_lag_id)
    delete_lag(sw2, sw2_lag_id)

    hs1.libs.ip.remove_ip('1', addr=(h1_ip_address + mask))
    hs2.libs.ip.remove_ip('1', addr=(h2_ip_address + mask))

    print('\n############################################')
    print('Test lag shutdown (\'no shutdown\') DONE')
    print('############################################')


def test_lag_shutdown_enabled(topology):
    """Test LAG with shutdown enabled.

    IPv4 ping must be unsuccessful before disabling configured LAG, after
    that IPv4 ping must be successful


    Steps:
        - Disable LAG 1 from switch 1
        - Execute pings from clients (connectivity must be broken)
        - Disable LAG 1 from switch 2
        - Execute pings from clients (Connectivity must be still broken)
        - Enable LAG 1 on both switches
        - Execute pings from clients (Connectivity must be working)
    """

    print('\n############################################')
    print('Test lag shutdown (\'shutdown\')')
    print('############################################')

    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')
    hs1 = topology.get('hs1')
    hs2 = topology.get('hs2')

    sw1_lag_id = '100'
    sw2_lag_id = '200'
    h1_ip_address = '10.0.0.1'
    h2_ip_address = '10.0.0.2'
    vlan = 100
    mask = '/24'

    assert sw1 is not None
    assert sw2 is not None
    assert hs1 is not None
    assert hs2 is not None

    print("Configure IP and bring UP in host 1")
    hs1.libs.ip.interface('1', addr=h1_ip_address + mask, up=True)

    print("Configure IP and bring UP in host 2")
    hs2.libs.ip.interface('1', addr=h2_ip_address + mask, up=True)

    p11 = sw1.ports['1']
    p12 = sw1.ports['2']
    p13 = sw1.ports['3']
    p21 = sw2.ports['1']
    p22 = sw2.ports['2']
    p23 = sw2.ports['3']

    print("Turning on all interfaces used in this test")
    ports_sw1 = [p11, p12, p13]
    for port in ports_sw1:
        turn_on_interface(sw1, port)

    ports_sw2 = [p21, p22, p23]
    for port in ports_sw2:
        turn_on_interface(sw2, port)

    print("Create LAG in both switches")
    create_lag_off(sw1, sw1_lag_id)
    create_lag_off(sw2, sw2_lag_id)

    print("Configure vlan and switch interfaces")
    create_vlan(sw1, vlan)
    create_vlan(sw2, vlan)

    print("Associate vlan with lag in both switches")
    associate_vlan_to_lag(sw1, vlan, sw1_lag_id)
    associate_vlan_to_lag(sw2, vlan, sw2_lag_id)

    print("Associate vlan with l2 interfaces in both switches")
    associate_vlan_to_l2_interface(sw1, vlan, p13)
    associate_vlan_to_l2_interface(sw2, vlan, p23)

    print("Associate interfaces [1,2] to lag in both switches")
    associate_interface_to_lag(sw1, p11, sw1_lag_id)
    associate_interface_to_lag(sw1, p12, sw1_lag_id)
    associate_interface_to_lag(sw2, p21, sw2_lag_id)
    associate_interface_to_lag(sw2, p22, sw2_lag_id)

    print("Waiting some time for the interfaces to be up")
    time.sleep(60)

    print("Verify all interface are up")
    for port in ports_sw1:
        assert is_interface_up(sw1, port),\
            "Interface " + port + " should be up"
    for port in ports_sw2:
        assert is_interface_up(sw2, port),\
            "Interface " + port + " should be up"

    # 'shutdown' on switch 1
    enable_lag_shutdown(sw1, sw1_lag_id, True)
    check_connectivity_between_hosts(hs1, h1_ip_address, hs2, h2_ip_address,
                                     False)

    # 'no shutdown' on switch 2
    enable_lag_shutdown(sw2, sw2_lag_id, True)
    check_connectivity_between_hosts(hs1, h1_ip_address, hs2, h2_ip_address,
                                     False)

    # 'no shutdown' on both switches
    enable_lag_shutdown(sw1, sw1_lag_id, False)
    enable_lag_shutdown(sw2, sw2_lag_id, False)
    check_connectivity_between_hosts(hs1, h1_ip_address, hs2, h2_ip_address,
                                     True)

    print("Cleaning configuration")
    for port in ports_sw1:
        turn_off_interface(sw1, port)

    for port in ports_sw2:
        turn_off_interface(sw2, port)

    delete_lag(sw1, sw1_lag_id)
    delete_lag(sw2, sw2_lag_id)

    hs1.libs.ip.remove_ip('1', addr=(h1_ip_address + mask))
    hs2.libs.ip.remove_ip('1', addr=(h2_ip_address + mask))

    print('\n############################################')
    print('Test lag shutdown (\'shutdown\') DONE')
    print('############################################')
