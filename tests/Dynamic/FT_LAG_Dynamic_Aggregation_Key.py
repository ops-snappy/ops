# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.


"""
OpenSwitch Test for vlan related configurations.
"""

# from pytest import mark
# from re import search
from pytest import set_trace
import time
import re

LOCAL_STATE = 'local_state'
REMOTE_STATE = 'remote_state'
ACTOR = 'Actor'
PARTNER = 'Partner'

TOPOLOGY = """
# +-------+     +-------+
# |  sw1  |-----|  sw2  |
# +-------+     +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=openswitch name="Switch 2"] sw2

# Links
sw1:1 -- sw2:1
sw1:2 -- sw2:2
sw1:3 -- sw2:3
sw1:4 -- sw2:4
sw1:5 -- sw2:6
sw1:6 -- sw2:7
sw1:7 -- sw2:5
"""


def create_lag_active(sw, lag_id):
    with sw.libs.vtysh.ConfigInterfaceLag(lag_id) as ctx:
        ctx.lacp_mode_active()


def create_lag_passive(sw, lag_id):
    with sw.libs.vtysh.ConfigInterfaceLag(lag_id) as ctx:
        ctx.lacp_mode_passive()


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


def validate_local_key(map_lacp, lag_id):
    assert map_lacp['local_key'] == lag_id,\
        "Actor Key is not the same as the LAG ID"


def validate_remote_key(map_lacp, lag_id):
    assert map_lacp['remote_key'] == lag_id,\
        "Partner Key is not the same as the LAG ID"


def validate_lag_name(map_lacp, lag_id):
    assert map_lacp['lag_id'] == lag_id,\
        "LAG ID should be " + lag_id


def validate_lag_state_sync(map_lacp, state):
    assert map_lacp[state]['active'] is True,\
        "LAG state should be active"
    assert map_lacp[state]['long_timeout'] is True,\
        "LAG state should have long timeout"
    assert map_lacp[state]['aggregable'] is True,\
        "LAG state should have aggregable enabled"
    assert map_lacp[state]['in_sync'] is True,\
        "LAG state should be In Sync"
    assert map_lacp[state]['collecting'] is True,\
        "LAG state should be in collecting"
    assert map_lacp[state]['distributing'] is True,\
        "LAG state should be in distributing"


def validate_lag_state_out_of_sync(map_lacp, state):
    assert map_lacp[state]['active'] is True,\
        "LAG state should be active"
    assert map_lacp[state]['in_sync'] is False,\
        "LAG state should be out of sync"
    assert map_lacp[state]['aggregable'] is True,\
        "LAG state should have aggregable enabled"
    assert map_lacp[state]['collecting'] is False,\
        "LAG state should not be in collecting"
    assert map_lacp[state]['distributing'] is False,\
        "LAG state should not be in distributing"
    assert map_lacp[state]['out_sync'] is True,\
        "LAG state should not be in distributing"


def get_device_mac_address(sw, interface):
    assert not sw('ip netns exec swns bash'.format(**locals()),
                  shell='bash')

    cmd_output = sw('ifconfig'.format(**locals()),
                    shell='bash')
    mac_re = (r'' + interface + '\s*Link\sencap:Ethernet\s*HWaddr\s'
              r'(?P<mac_address>([0-9A-Fa-f]{2}[:-]){5}'
              r'[0-9A-Fa-f]{2})')

    re_result = re.search(mac_re, cmd_output)
    assert re_result

    result = re_result.groupdict()
    print(result)

    return result['mac_address']


def tcpdump_capture_interface(sw, interface_id, wait_time):
    assert not sw('ip netns exec swns bash'.format(**locals()),
                  shell='bash')

    cmd_output = sw('tcpdump -D'.format(**locals()),
                    shell='bash')
    interface_re = (r'(?P<linux_interface>\d)\.' + interface_id +
                    r'\s[\[Up, Running\]]')
    re_result = re.search(interface_re, cmd_output)
    assert re_result
    result = re_result.groupdict()

    sw('tcpdump -ni ' + result['linux_interface'] +
        ' -e ether proto 0x8809 -vv'
        '> /tmp/interface.cap 2>&1 &'.format(**locals()),
        shell='bash')

    time.sleep(wait_time)

    sw('killall tcpdump'.format(**locals()),
        shell='bash')

    capture = sw('cat /tmp/interface.cap'.format(**locals()),
                 shell='bash')

    sw('rm /tmp/interface.cap'.format(**locals()),
       shell='bash')

    return capture


def get_info_from_packet_capture(capture, switch_side, sw_mac):
    packet_re = (r'[\s \S]*' + sw_mac.lower() + '\s\>\s01:80:c2:00:00:02\,'
                 r'[\s \S]*'
                 r'' + switch_side + '\sInformation\sTLV\s\(0x\d*\)'
                 r'\,\slength\s\d*\s*'
                 r'System\s(?P<system_id>([0-9A-Fa-f]{2}[:-]){5}'
                 r'[0-9A-Fa-f]{2})\,\s'
                 r'System\sPriority\s(?P<system_priority>\d*)\,\s'
                 r'Key\s(?P<key>\d*)\,\s'
                 r'Port\s(?P<port_id>\d*)\,\s'
                 r'Port\sPriority\s(?P<port_priority>\d*)')

    re_result = re.search(packet_re, capture)
    assert re_result

    result = re_result.groupdict()

    return result


def lacp_aggregation_key_case_1(topology):
    """
    Case 1:
        Verify aggregation key functionality when
        interface is moved to another LAG in one of
        the switches from the topology
        Initial Topology:
            SW1>
                LAG100 -> Interfaces: 1,2
            SW2>
                LAG100 -> Interfaces: 1,2
        Final Topology:
            SW1>
                LAG200 -> Interfaces: 1,3
                LAG100 -> Interfaces: 2,4
            SW2>
                LAG100 -> Interfaces: 1,2
        Expected behaviour:
            Interface 1 should not be in Collecting/Distributing
            state in neither switch. State:
    """
    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')
    sw1_lag_id = '100'
    sw1_lag_id_2 = '200'
    sw2_lag_id = '100'

    assert sw1 is not None
    assert sw2 is not None

    p11 = sw1.ports['1']
    p12 = sw1.ports['2']
    p13 = sw1.ports['3']
    p14 = sw1.ports['4']
    p21 = sw2.ports['1']
    p22 = sw2.ports['2']
    p23 = sw2.ports['3']
    p24 = sw2.ports['4']

    print("Turning on all interfaces used in this test")
    ports_sw1 = [p11, p12, p13, p14]
    for port in ports_sw1:
        turn_on_interface(sw1, port)

    ports_sw2 = [p21, p22, p23, p24]
    for port in ports_sw2:
        turn_on_interface(sw2, port)

    print("Create LAG in both switches")
    create_lag_active(sw1, sw1_lag_id)
    create_lag_active(sw2, sw2_lag_id)

    print("Associate interfaces [1,2] to lag in both switches")
    associate_interface_to_lag(sw1, p11, sw1_lag_id)
    associate_interface_to_lag(sw1, p12, sw1_lag_id)
    associate_interface_to_lag(sw2, p21, sw2_lag_id)
    associate_interface_to_lag(sw2, p22, sw2_lag_id)

    time.sleep(30)
    print("Get information for LAG in interface 1 with both switches")
    map_lacp_sw1 = sw1.libs.vtysh.show_lacp_interface(p11)
    map_lacp_sw2 = sw2.libs.vtysh.show_lacp_interface(p21)

    print("Validate the LAG was created in both switches")
    validate_lag_name(map_lacp_sw1, sw1_lag_id)
    validate_local_key(map_lacp_sw1, sw1_lag_id)
    validate_remote_key(map_lacp_sw1, sw2_lag_id)
    validate_lag_state_sync(map_lacp_sw1, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw1, REMOTE_STATE)

    validate_lag_name(map_lacp_sw2, sw2_lag_id)
    validate_local_key(map_lacp_sw2, sw2_lag_id)
    validate_remote_key(map_lacp_sw2, sw1_lag_id)
    validate_lag_state_sync(map_lacp_sw2, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw2, REMOTE_STATE)

    print("Changing interface 1 to lag 200 in switch 1")
    create_lag_active(sw1, sw1_lag_id_2)
    associate_interface_to_lag(sw1, p11, sw1_lag_id_2)
    associate_interface_to_lag(sw1, p13, sw1_lag_id_2)
    associate_interface_to_lag(sw1, p14, sw1_lag_id)

    # TODO: If this timer is set, then the switch1 gets InSync
    # which in theory, it shouldn't
    # time.sleep(15)

    print("Get information from LAG in interface 1 with both switches")
    map_lacp_sw1 = sw1.libs.vtysh.show_lacp_interface(p11)
    map_lacp_sw2 = sw2.libs.vtysh.show_lacp_interface(p21)

    print("Validate lag is out of sync in interface 1 in both switches")
    validate_lag_name(map_lacp_sw1, sw1_lag_id_2)
    validate_local_key(map_lacp_sw1, sw1_lag_id_2)
    validate_remote_key(map_lacp_sw1, sw2_lag_id)
    validate_lag_state_out_of_sync(map_lacp_sw1, LOCAL_STATE)
    validate_lag_state_out_of_sync(map_lacp_sw1, REMOTE_STATE)

    validate_lag_name(map_lacp_sw2, sw2_lag_id)
    validate_local_key(map_lacp_sw2, sw2_lag_id)
    validate_remote_key(map_lacp_sw2, sw1_lag_id_2)
    validate_lag_state_out_of_sync(map_lacp_sw2, LOCAL_STATE)
    validate_lag_state_out_of_sync(map_lacp_sw2, REMOTE_STATE)

    print("Cleaning configuration")
    for port in ports_sw1:
        turn_off_interface(sw1, port)

    for port in ports_sw2:
        turn_off_interface(sw2, port)

    delete_lag(sw1, sw1_lag_id)
    delete_lag(sw1, sw1_lag_id_2)
    delete_lag(sw2, sw2_lag_id)


def lacp_aggregation_key_packet_validation(topology):
    """
    Aggregation Key packet validation:
        Capture LACPDUs packets and validate the aggregation
        key is set correctly for both switches
    """
    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')
    sw1_lag_id = '100'
    sw2_lag_id = '200'

    p11 = sw1.ports['1']
    p12 = sw1.ports['2']
    p21 = sw2.ports['1']
    p22 = sw2.ports['2']

    print("Turning on all interfaces used in this test")
    ports_sw1 = [p11, p12]
    for port in ports_sw1:
        turn_on_interface(sw1, port)

    ports_sw2 = [p21, p22]
    for port in ports_sw2:
        turn_on_interface(sw2, port)

    print("Create LAG in both switches")
    create_lag_active(sw1, sw1_lag_id)
    create_lag_passive(sw2, sw2_lag_id)

    print("Associate interfaces [1,2] to lag in both switches")
    associate_interface_to_lag(sw1, p11, sw1_lag_id)
    associate_interface_to_lag(sw1, p12, sw1_lag_id)
    associate_interface_to_lag(sw2, p21, sw2_lag_id)
    associate_interface_to_lag(sw2, p22, sw2_lag_id)

    sw1_mac = get_device_mac_address(sw1, p11)
    sw2_mac = get_device_mac_address(sw2, p21)
    print(sw2_mac)

    print("Take capture from interface 1 in switch 1")
    capture = tcpdump_capture_interface(sw1, p11, 80)
    tcpdump_capture_interface(sw1, p12, 80)

    print("Validate actor and partner key from sw1 packets")
    sw1_actor = get_info_from_packet_capture(capture, ACTOR, sw1_mac)

    assert sw1_actor['key'] == sw1_lag_id,\
        'Packet is not sending the correct actor key in sw1'

    sw1_partner = get_info_from_packet_capture(capture, PARTNER, sw1_mac)

    assert sw1_partner['key'] == sw2_lag_id,\
        'Packet is not sending the correct partner key in sw1'

    print("Cleaning configuration")
    for port in ports_sw1:
        turn_off_interface(sw1, port)

    for port in ports_sw2:
        turn_off_interface(sw2, port)

    delete_lag(sw1, sw1_lag_id)
    delete_lag(sw2, sw2_lag_id)


def test_lacp_aggregation_key_case_2(topology):
    """
    Case 2:
        Verify only interfaces associated with the same
        aggregation key get to Collecting/Distributing state
        Initial Topology:
            SW1>
                LAG150 -> Interfaces: 1,2,3,4
            SW2>
                LAG300 -> Interfaces: 1,2
                LAG400 -> Interfaces: 3,4
        Expected behaviour:
            Interfaces 1 and 2 in both switches get state Active, InSync,
            Collecting and Distributing. Interfaces 3 and 4 should get state
            Active, OutOfSync, Collecting and Distributing
    """
    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')
    sw1_lag_id = '150'
    sw2_lag_id = '150'
    sw2_lag_id_2 = '400'

    assert sw1 is not None
    assert sw2 is not None

    p11 = sw1.ports['1']
    p12 = sw1.ports['2']
    p13 = sw1.ports['3']
    p14 = sw1.ports['4']
    p21 = sw2.ports['1']
    p22 = sw2.ports['2']
    p23 = sw2.ports['3']
    p24 = sw2.ports['4']

    print("Turning on all interfaces used in this test")
    ports_sw1 = [p11, p12, p13, p14]
    for port in ports_sw1:
        turn_on_interface(sw1, port)

    ports_sw2 = [p21, p22, p23, p24]
    for port in ports_sw2:
        turn_on_interface(sw2, port)

    print("Create LAG in both switches")
    create_lag_active(sw1, sw1_lag_id)
    create_lag_active(sw2, sw2_lag_id)
    create_lag_active(sw2, sw2_lag_id_2)

    print("Associate interfaces to lag in both switches")
    for interface in ports_sw1:
        associate_interface_to_lag(sw1, interface, sw1_lag_id)

    for interface in ports_sw2[0:2]:
        associate_interface_to_lag(sw2, interface, sw2_lag_id)

    for interface in ports_sw2[2:4]:
        associate_interface_to_lag(sw2, interface, sw2_lag_id_2)

    time.sleep(50)
    print("Get information for LAG in interface 1 with both switches")
    map_lacp_sw1_p11 = sw1.libs.vtysh.show_lacp_interface(p11)
    map_lacp_sw1_p12 = sw1.libs.vtysh.show_lacp_interface(p12)
    map_lacp_sw1_p13 = sw1.libs.vtysh.show_lacp_interface(p13)
    map_lacp_sw1_p14 = sw1.libs.vtysh.show_lacp_interface(p14)
    map_lacp_sw2_p21 = sw2.libs.vtysh.show_lacp_interface(p21)
    map_lacp_sw2_p22 = sw2.libs.vtysh.show_lacp_interface(p22)
    map_lacp_sw2_p23 = sw2.libs.vtysh.show_lacp_interface(p23)
    map_lacp_sw2_p24 = sw2.libs.vtysh.show_lacp_interface(p24)

    set_trace()
    print("Validate the LAG was created in both switches")
    validate_lag_state_sync(map_lacp_sw1_p11, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw1_p12, LOCAL_STATE)
    validate_lag_state_out_of_sync(map_lacp_sw1_p13, LOCAL_STATE)
    validate_lag_state_out_of_sync(map_lacp_sw1_p14, LOCAL_STATE)

    validate_lag_state_sync(map_lacp_sw2_p21, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw2_p22, LOCAL_STATE)
    validate_lag_state_out_of_sync(map_lacp_sw2_p23, LOCAL_STATE)
    validate_lag_state_out_of_sync(map_lacp_sw2_p24, LOCAL_STATE)

    print("Cleaning configuration")
    for port in ports_sw1:
        turn_off_interface(sw1, port)

    for port in ports_sw2:
        turn_off_interface(sw2, port)

    delete_lag(sw1, sw1_lag_id)
    delete_lag(sw2, sw2_lag_id)
    delete_lag(sw2, sw2_lag_id_2)


def lacp_aggregation_key_case_3(topology):
    """
    Case 3:
        Verify LAGs should be formed independent of port ids as long
        as long as aggregation key is the same
        Initial Topology:
            SW1>
                LAG150 -> Interfaces: 1,5
                LAG250 -> Interfaces: 2,6
                LAG350 -> Interfaces: 3,7
            SW2>
                LAG150 -> Interfaces: 1,6
                LAG250 -> Interfaces: 2,7
                LAG350 -> Interfaces: 3,5
        Expected behaviour:
        All interfaces in all LAGs should be InSync, Collecting
        and Distributing state
    """
    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')

    lag_id_1 = '150'
    lag_id_2 = '250'
    lag_id_3 = '350'
    sw_lag_id = [lag_id_1, lag_id_2, lag_id_3]

    assert sw1 is not None
    assert sw2 is not None

    p11 = sw1.ports['1']
    p12 = sw1.ports['2']
    p13 = sw1.ports['3']
    p15 = sw1.ports['5']
    p16 = sw1.ports['6']
    p17 = sw1.ports['7']
    p21 = sw2.ports['1']
    p22 = sw2.ports['2']
    p23 = sw2.ports['3']
    p25 = sw2.ports['5']
    p26 = sw2.ports['6']
    p27 = sw2.ports['7']

    print("Turning on all interfaces used in this test")
    ports_sw1 = [p11, p12, p13, p15, p16, p17]
    for port in ports_sw1:
        turn_on_interface(sw1, port)

    ports_sw2 = [p21, p22, p23, p25, p26, p27]
    for port in ports_sw2:
        turn_on_interface(sw2, port)

    print("Create LAG in both switches")
    for lag in sw_lag_id:
        create_lag_active(sw1, lag)
        create_lag_active(sw2, lag)

    print("Associate interfaces with LAG in switch1")
    associate_interface_to_lag(sw1, p11, lag_id_1)
    associate_interface_to_lag(sw1, p15, lag_id_1)
    associate_interface_to_lag(sw1, p12, lag_id_2)
    associate_interface_to_lag(sw1, p16, lag_id_2)
    associate_interface_to_lag(sw1, p13, lag_id_3)
    associate_interface_to_lag(sw1, p17, lag_id_3)

    print("Associate interfaces with LAG in switch2")
    associate_interface_to_lag(sw2, p21, lag_id_1)
    associate_interface_to_lag(sw2, p26, lag_id_1)
    associate_interface_to_lag(sw2, p22, lag_id_2)
    associate_interface_to_lag(sw2, p27, lag_id_2)
    associate_interface_to_lag(sw2, p23, lag_id_3)
    associate_interface_to_lag(sw2, p25, lag_id_3)

    time.sleep(30)

    print("Get information for LAG")
    map_lacp_sw1_5 = sw1.libs.vtysh.show_lacp_interface(p15)
    map_lacp_sw1_6 = sw1.libs.vtysh.show_lacp_interface(p16)
    map_lacp_sw1_7 = sw1.libs.vtysh.show_lacp_interface(p17)
    map_lacp_sw2_5 = sw2.libs.vtysh.show_lacp_interface(p25)
    map_lacp_sw2_6 = sw2.libs.vtysh.show_lacp_interface(p26)
    map_lacp_sw2_7 = sw2.libs.vtysh.show_lacp_interface(p27)

    print("Validate correct lag name in switch1")
    validate_lag_name(map_lacp_sw1_5, lag_id_1)
    validate_lag_name(map_lacp_sw1_6, lag_id_2)
    validate_lag_name(map_lacp_sw1_7, lag_id_3)

    print("Validate correct state in switch1 for interfaces 5,6,7")
    validate_lag_state_sync(map_lacp_sw1_5, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw1_6, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw1_7, LOCAL_STATE)

    print("Validate correct lag name in switch2")
    validate_lag_name(map_lacp_sw2_5, lag_id_3)
    validate_lag_name(map_lacp_sw2_6, lag_id_1)
    validate_lag_name(map_lacp_sw2_7, lag_id_2)

    print("Validate correct state in switch2 for interfaces 5,6,7")
    validate_lag_state_sync(map_lacp_sw2_5, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw2_6, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw2_7, LOCAL_STATE)

    print("Cleaning configuration")
    for port in ports_sw1:
        turn_off_interface(sw1, port)

    for port in ports_sw2:
        turn_off_interface(sw2, port)

    for lag in sw_lag_id:
        delete_lag(sw1, lag)
        delete_lag(sw2, lag)


def lacp_aggregation_key_case_4(topology):
    """
    Case 4:
        Verify LAGs with different names from switches can
        get connected as long as all interfaces connected have
        same aggregation key
        Initial Topology:
            SW1>
                LAG10 -> Interfaces: 1,2
            SW2>
                LAG20 -> Interfaces: 1,2
        Expected behaviour:
        All interfaces in all LAGs should be InSync, Collecting
        and Distributing state
    """
    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')

    sw1_lag_id = '10'
    sw2_lag_id = '20'

    assert sw1 is not None
    assert sw2 is not None

    p11 = sw1.ports['1']
    p12 = sw1.ports['2']
    p21 = sw2.ports['1']
    p22 = sw2.ports['2']

    print("Turning on all interfaces used in this test")
    ports_sw1 = [p11, p12]
    for port in ports_sw1:
        turn_on_interface(sw1, port)

    ports_sw2 = [p21, p22]
    for port in ports_sw2:
        turn_on_interface(sw2, port)

    print("Create LAG in both switches")
    create_lag_active(sw1, sw1_lag_id)
    create_lag_active(sw2, sw2_lag_id)

    print("Associate interfaces 1,2 to the lag in both switches")
    associate_interface_to_lag(sw1, p11, sw1_lag_id)
    associate_interface_to_lag(sw1, p12, sw1_lag_id)
    associate_interface_to_lag(sw2, p21, sw2_lag_id)
    associate_interface_to_lag(sw2, p22, sw2_lag_id)

    time.sleep(30)

    print("Get information for LAG in interface 1 with both switches")
    map_lacp_sw1_1 = sw1.libs.vtysh.show_lacp_interface(p11)
    map_lacp_sw1_2 = sw1.libs.vtysh.show_lacp_interface(p12)
    map_lacp_sw2_1 = sw2.libs.vtysh.show_lacp_interface(p21)
    map_lacp_sw2_2 = sw2.libs.vtysh.show_lacp_interface(p21)

    print("Validate the LAG was created in swith1")
    validate_lag_state_sync(map_lacp_sw1_1, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw1_1, REMOTE_STATE)
    validate_lag_state_sync(map_lacp_sw1_2, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw1_2, REMOTE_STATE)

    print("Validate the LAG was created in swith2")
    validate_lag_state_sync(map_lacp_sw2_1, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw2_1, REMOTE_STATE)
    validate_lag_state_sync(map_lacp_sw2_2, LOCAL_STATE)
    validate_lag_state_sync(map_lacp_sw2_2, REMOTE_STATE)

    print("Cleaning configuration")
    for port in ports_sw1:
        turn_off_interface(sw1, port)

    for port in ports_sw2:
        turn_off_interface(sw2, port)

    delete_lag(sw1, sw1_lag_id)
    delete_lag(sw2, sw2_lag_id)
