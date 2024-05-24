#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def send_bdpu_every_sec():
    while True:
        # # TODO Send BDPU every second if necessary
        # if root_bridge_ID == own_bridge_ID:
        #     bpdu = create_bpdu(own_bridge_ID, root_bridge_ID, root_path_cost)
        #     for o in interfaces:
        #         if interface_type[get_interface_name(o)] == 'T':
        #             print("Am trimis bpdu pe portul", get_interface_name(o))
        #             print("bpdu", bpdu)
        #             send_bpdu(o, bpdu, 36)
        time.sleep(1)


def is_unicast(mac):
    return mac != 'ff:ff:ff:ff:ff:ff'


def init_stp_process(interfaces, interface_type, stp_int_state, switch_priority):
    for o in interfaces:
        if interface_type[get_interface_name(o)] == 'T':
            stp_int_state[get_interface_name(o)] = 'BP'
    
    own_bridge_ID =  switch_priority
    root_bridge_ID = own_bridge_ID
    root_path_cost = 0

    if own_bridge_ID == root_bridge_ID:
        for o in interfaces:
            if interface_type[get_interface_name(o)] == 'T':
                stp_int_state[get_interface_name(o)] = 'DP'
    return own_bridge_ID, root_bridge_ID, root_path_cost, stp_int_state

 
def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]
 
    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)
 
    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    MAC_Table = {}
    interface_type = {}
    stp_int_state = {}
    
    config_file = open(f"configs/switch{switch_id}.cfg", "r")
    
    # read switch priority
    line = config_file.readline()
    switch_priority = line
    
    # read interfaces and their type
    line = config_file.readline()
    while line:
        line = line.split()
        if (line[1] == "T"):
            interface_type[line[0]] = "T"
        else:
            interface_type[line[0]] = int(line[1])
        line = config_file.readline()
    config_file.close()

    own_bridge_ID, root_bridge_ID, root_path_cost, stp_int_state = init_stp_process(interfaces, interface_type, stp_int_state, switch_priority)
 
    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec)
    t.start()

    while True:
 
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()
 
        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)
 
        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)
 
        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]
 
        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')
 
        print("Received frame of size {} on interface {}".format(length, interface), flush=True)
 
        # TODO: Implement forwarding with learning
 
        # Cadrul F este primit pe portul P
        # MAC_Table : Tabela MAC ce face maparea adresa MAC -> port
        # Ports : lista tuturor porturilor de pe switch
        src = src_mac
        dst = dest_mac
        # Am aflat portul pentru adresa MAC src
 
    #Asta e suficient pentru primul subpunct, de 3/10
 
        MAC_Table[src] = interface

        # bdpu = b'\x01\x80\xc2\x00\x00\x00' + src + struct.pack(own_bridge_ID) + struct.pack(root_bridge_ID) + struct.pack(root_path_cost)
        # for o in interfaces:
        #     if interface_type[get_interface_name(o)] == 'T':
        #         print("Am trimis bpdu pe portul", get_interface_name(o))
        #         print("bpdu", bdpu)
        #         send_to_link(o, bdpu, 36)

        if is_unicast(dst):
            if dst in MAC_Table:
                dst_vlan = interface_type[get_interface_name(MAC_Table[dst])]
                src_vlan = interface_type[get_interface_name(interface)]
                # if the source and destination are access and on the same vlan, send the frame
                if ((src_vlan != 'T') & (dst_vlan != 'T') & (src_vlan == dst_vlan)):
                    send_to_link(MAC_Table[dst], data, length)
                # if the source and destination are trunk, send the frame
                elif ((src_vlan == 'T') & (dst_vlan == 'T')):
                    send_to_link(MAC_Table[dst], data, length)
                # if the source is access and the destination is trunk, add the tag and send the frame
                elif ((src_vlan != 'T') & (dst_vlan == 'T')):
                    tag = create_vlan_tag(int(src_vlan))
                    data1 = data[0:12] + tag + data[12:]
                    send_to_link(MAC_Table[dst], data1, length + 4)
                # if the source is trunk and the destination is access, and the vlan is the same as the source vlan,
                #  remove the tag and send the frame
                elif ((src_vlan == 'T') & (dst_vlan != 'T') & (vlan_id == dst_vlan)):
                    data1 = data[0:12] + data[16:]
                    send_to_link(MAC_Table[dst], data1, length)
            else:
                # send the frame on all the other ports
                for o in interfaces:
                    if o != interface:
                        dst_vlan = interface_type[get_interface_name(o)]
                        src_vlan = interface_type[get_interface_name(interface)]
                        # if the source and destination are access and on the same vlan, send the frame
                        if ((src_vlan != 'T') & (dst_vlan != 'T') & (src_vlan == dst_vlan)):
                            send_to_link(o, data, length)
                        # if the source and destination are trunk, send the frame
                        elif ((src_vlan == 'T') & (dst_vlan == 'T')):
                            send_to_link(o, data, length)
                        # if the source is access and the destination is trunk, add the tag and send the frame
                        elif ((src_vlan != 'T') & (dst_vlan == 'T')):
                            tag = create_vlan_tag(int(src_vlan))
                            data1 = data[0:12] + tag + data[12:]
                            send_to_link(o, data1, length + 4)
                        # if the source is trunk and the destination is access, and the vlan is the same as the source vlan,
                        #  remove the tag and send the frame
                        elif ((src_vlan == 'T') & (dst_vlan != 'T') & (vlan_id == dst_vlan)):
                            data1 = data[0:12] + data[16:]
                            send_to_link(o, data1, length)
        else:
            # send the frame on all the other ports
                    for o in interfaces:
                        if o != interface:
                            dst_vlan = interface_type[get_interface_name(o)]
                            src_vlan = interface_type[get_interface_name(interface)]
                            # if the source and destination are access and on the same vlan, send the frame
                            if ((src_vlan != 'T') & (dst_vlan != 'T') & (src_vlan == dst_vlan)):
                                send_to_link(o, data, length)
                            # if the source and destination are trunk, send the frame
                            elif ((src_vlan == 'T') & (dst_vlan == 'T')):
                                send_to_link(o, data, length)
                            # if the source is access and the destination is trunk, add the tag and send the frame
                            elif ((src_vlan != 'T') & (dst_vlan == 'T')):
                                tag = create_vlan_tag(int(src_vlan))
                                data1 = data[0:12] + tag + data[12:]
                                send_to_link(o, data1, length + 4)
                            # if the source is trunk and the destination is access, and the vlan is the same as the source vlan,
                            elif ((src_vlan == 'T') & (dst_vlan != 'T') & (vlan_id == dst_vlan)):
                                data1 = data[0:12] + data[16:]
                                send_to_link(o, data1, length)
        
 
        # TODO: Implement STP support

 
        # data is of type bytes.
        # send_to_link(i, data, length)
 
if __name__ == "__main__":
    main()