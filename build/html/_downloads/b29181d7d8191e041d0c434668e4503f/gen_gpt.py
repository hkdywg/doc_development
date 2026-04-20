#!/usr/bin/env python2

import binascii
import uuid
from struct import pack, unpack

import sys


OS_TYPES = {
    0x00: 'Empty',
    0xEE: 'GPT Protective',
    0xFF: 'UEFI System Partition'
}

PARTITION_TYPE_GUIDS = {
    '024DEE41-33E7-11D3-9D69-0008C781F39F': 'Legacy MBR',
    'C12A7328-F81F-11D2-BA4B-00A0C93EC93B': 'EFI System Partition',
    '21686148-6449-6E6F-744E-656564454649': 'BIOS boot partition',
    '0FC63DAF-8483-4772-8E79-3D69D8477DE4': 'Linux filesystem data',
    '4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709': 'Root partition (x86-64)',
    '0657FD6D-A4AB-43C4-84E5-0933C84B4F4F': 'Swap partition',
    '7C3457EF-0000-11AA-AA11-00306543ECAC': 'Apple APFS'
}

def decode_guid(guid_as_bytes):
    return uuid.UUID(bytes_le=guid_as_bytes)

def nts_to_str(buf):
    s = buf.decode('utf-16')
    return s.split('\0', 1)[0]

def decode_gpt_partition_type_guid(guid):
    if isinstance(guid, uuid.UUID):
        guid = str(guid)

    guid = guid.upper()
    return PARTITION_TYPE_GUIDS.get(guid, "?")

def decode_gpt_partition_entry_attribute(attribute_value):
    r = []
    if (attribute_value & 0x1):
        r.append("Requitted Partition")
    if (attribute_value & 0x2):
        r.append("No Block Io Protocal")
    if (attribute_value & 0x4):
        r.append("Legacy BIOS Bootable")
    return r


def decode_gpt_partition_entry(data):
    (partition_type_guid,
     unique_partition_guid,
     starting_lba,
     ending_lba,
     attributes,
     partition_name) = unpack('< 16s 16s Q Q Q 72s', data[0:128])
    return GPTPartitionEntry(partition_type_guid,
                             unique_partition_guid,
                             starting_lba,
                             ending_lba,
                             attributes,
                             partition_name)

def encode_gpt_partition_entry(gpt_partition_entry):  
    data = pack('<16s 16s Q Q Q 72s',
		gpt_partition_entry.partition_type_guid_raw,
		gpt_partition_entry.unique_partition_guid_raw, 
		gpt_partition_entry.starting_lba,        
		gpt_partition_entry.ending_lba,        
		gpt_partition_entry.attributes_raw,
		gpt_partition_entry.partition_name_raw)
    return data



def encode_gpt_partition_entry_array(gpt_partition_entries, size, count):
    data  = bytearray()
    for i in range(0, count):
        d = encode_gpt_partition_entry(gpt_partition_entries[i])
        data.extend(d)
        if len(d) < size:
            data.extend(bytearray(size - len(d)))
    return bytes(data)

def calculate_partition_entry_array_crc32(data):
    return binascii.crc32(data) & 0xffffffff


class GPTPartitionEntry():
    def __init__(
        self,
        partition_type_guid,
        unique_partition_guid,
        starting_lba,
        ending_lba,
        attributes,
        partition_name):
        self.partition_type_guid_raw = partition_type_guid
        self.partition_type_guid = decode_guid(partition_type_guid)
        self.partition_type = decode_gpt_partition_type_guid(self.partition_type_guid)
        self.unique_partition_guid_raw = unique_partition_guid
        self.unique_partition_guid = decode_guid(unique_partition_guid)
        self.starting_lba = starting_lba
        self.ending_lba = ending_lba
        self.attributes_raw = attributes
        self.attributes = decode_gpt_partition_entry_attribute(attributes)
        self.partition_name_raw =  partition_name
        self.partition_name = nts_to_str(partition_name)

    def is_empty(self):
        return all(x == 0 for x in self.partition_type_guid_raw)

class GPTheader():
    def __init__(self,
                signature,
                revision,
                header_size,
                header_crc32,
                reserved,
                my_lba,
                alternate_lba,
                first_usable_lba,
                last_usable_lba,
                disk_guid,
                partition_entry_lba,
                number_of_partition_entries,
                size_of_partition_entry,
                partition_entry_array_crc32):
        self.signature = signature
        self.revision = revision
        self.header_size = header_size
        self.header_crc32 = header_crc32
        self.reserved = reserved
        self.my_lba = my_lba
        self.alternate_lba = alternate_lba
        self.first_usable_lba = first_usable_lba
        self.last_usable_lba = last_usable_lba
        self.disk_guid = disk_guid
        self.partition_entry_lba = partition_entry_lba
        self.number_of_partition_entries = number_of_partition_entries
        self.size_of_partition_entry = size_of_partition_entry
        self.partition_of_entry_array_crc32 = partition_entry_array_crc32 

    def is_valid(self):
        return self.signature == 'EFI PART'.encode('ascii')

    def calculate_header_crc32(self):
        header_crc32_input = pack('<8s 4s I I 4s Q Q Q Q 16s Q I I I',
                                      self.signature,
                                      self.revision,
                                      self.header_size,
                                      0,
                                      self.reserved,
                                      self.my_lba,
                                      self.alternate_lba,
                                      self.first_usable_lba,
                                      self.last_usable_lba,
                                      self.disk_guid,
                                      self.partition_entry_lba,
                                      self.number_of_partition_entries,
                                      self.size_of_partition_entry,
                                      self.partition_entry_array_crc32)
        return binascii.crc32(header_crc32_input) & 0xffffffff


def encode_gpt_header(gpt_header):
    data = pack(
                '< 8s 4s I I 4s Q Q Q Q 16s Q I I I',
                gpt_header.signature,
                gpt_header.revision,
                gpt_header.header_size,
                gpt_header.header_crc32,
                gpt_header.reserved,
                gpt_header.my_lba,
                gpt_header.alternate_lba,
                gpt_header.first_usable_lba,
                gpt_header.last_usable_lba,
                gpt_header.disk_guid,
                gpt_header.partition_entry_lba,
                gpt_header.number_of_partition_entries,
                gpt_header.size_of_partition_entry,
                gpt_header.partition_entry_array_crc32)
    return data

def decode_gpt_header(gpt_header):
    (signature,
     revision,
     header_size,
     header_crc32,
     reserved,
     my_lba,
     alternate_lba,
     first_usable_lba,
     last_usable_lba,
     disk_guid,
     partition_entry_lba,
     number_of_partition_entrires,
     size_of_partition_entry,
     partition_entry_array_crc32) = unpack(
         '< 8s 4s I I 4s Q Q Q Q 16s Q I I I',
         data[0:92]
     )
    gpt_header = GPTheader(signature,
                            revision,      
		            header_size,      
			    header_crc32,
                            reserved,
                            my_lba,
                            alternate_lba,
                            first_usable_lba,
                            last_usable_lba,
                            disk_guid,
                            partition_entry_lba,      
			    number_of_partition_entries,
                            size_of_partition_entry,
                            partition_entry_array_crc32)
    return gpt_header

def create_empty_gpt_entry():
    partition_type_guid = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    unique_partition_guid = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    starting_lba = 0
    ending_lba = 0
    attributes = 0
    partition_name = "\x00\x00".encode('utf-16')[2:]
    print(partition_name)

    entry = GPTPartitionEntry(partition_type_guid, unique_partition_guid,
                                starting_lba,
                                ending_lba,
                                attributes,
                                partition_name)
    return entry

def create_gpt_entry(start_lba, end_lba, name):
    partition_type_guid = uuid.uuid4().bytes
    unique_partition_guid = uuid.uuid4().bytes
    starting_lba = start_lba
    ending_lba = end_lba
    attributes = 0
    partition_name = name.decode("utf-8").encode('utf-16')[2:]

    entry = GPTPartitionEntry(partition_type_guid,
                              unique_partition_guid,
                              starting_lba,
                              ending_lba,
                              attributes,
                              partition_name)
    return entry


def complete_gpt_entries(entrylist):
    an = create_empty_gpt_entry()
    for i  in range(len(entrylist), 0x80, 1):
        entrylist.append(an)

def create_gpt_header(current_lba):
    signature = b"EFI PART"
    revision = b"\x00\x00\x01\x00"
    header_size = 0x5c
    header_crc32 = 0
    reserved = b"\x00\x00\x00\x00"
    my_lba = current_lba
    alternate_lba = 0
    first_usable_lba = 34
    last_usable_lba = 0
    disk_guid = uuid.uuid4().bytes
    partition_entry_lba = 2
    number_of_partition_entries = 0x80
    size_of_partition_entry = 0x80
    partition_entry_array_crc32 = 0
    hdr = GPTheader(signature, revision, header_size, header_crc32, reserved, my_lba,
                    alternate_lba, first_usable_lba, last_usable_lba, disk_guid,
                   partition_entry_lba, number_of_partition_entries, size_of_partition_entry,
                   partition_entry_array_crc32)

    return hdr

class MBRfilling():
    def __init__(self, boot_indicator, start_head, start_sector, start_cylinder, partion_type, 
                 end_head, end_sector, end_cylinder, partition_reset, partition_sectors):
        self.boot_indicator = boot_indicator
        self.start_head = start_head
        self.start_sector = start_sector
        self.start_cylinder = start_cylinder
        self.partion_type = partion_type
        self.end_head = end_head
        self.end_sector = end_sector
        self.end_cylinder = end_cylinder
        self.partition_reset = partition_reset
        self.partition_sectors = partition_sectors
        

def encode_mbr_pack(mbr_pack):
    data = pack('< B B B B B B B B I I',
                mbr_pack.boot_indicator, mbr_pack.start_head, mbr_pack.start_sector, mbr_pack.start_cylinder,
                mbr_pack.partion_type, mbr_pack.end_head, mbr_pack.end_sector, mbr_pack.end_cylinder, mbr_pack.partition_reset, mbr_pack.partition_sectors
                )
    return data

def mbr_partition_pack(sectors):
    boot_indicator = 0x00
    start_head = 0x00
    start_sector = 0x02
    start_cylinder = 0x00
    partion_type = 0xee
    end_head = 0xff
    end_sector = 0xff
    end_cylinder = 0xff
    partition_reset = 0x0001
    partition_sectors = sectors
    mbr_pack = MBRfilling(boot_indicator, start_head, start_sector, start_cylinder, partion_type,
                          end_head, end_sector, end_cylinder, partition_reset, partition_sectors)

    data = encode_mbr_pack(mbr_pack)
    return data


def create_mbr():
    mbr_data = bytearray()    
    mbr_data.extend(bytearray(0x1be))
    mbr_partition_data = mbr_partition_pack(0x01dacbff)
    mbr_data.extend(mbr_partition_data)
    mbr_data.extend(bytearray(48))
    end_data = pack('< B B', 0x55, 0xaa)
    mbr_data.extend(end_data)
    return mbr_data    


def create(back_lba, alternate_lba, entrylist):
    complete_gpt_entries(entrylist)

    entriesdata = encode_gpt_partition_entry_array(entrylist, 0x80, 0x80)

    hdr = create_gpt_header(1)
    hdr.alternate_lba = alternate_lba 
    hdr.last_usable_lba = alternate_lba - 33
    hdr.partition_entry_array_crc32 = calculate_partition_entry_array_crc32(entriesdata)
    hdr.header_crc32 = hdr.calculate_header_crc32()


    gptdata = encode_gpt_header(hdr)

    mbrdata = create_mbr()
    #gpt main
    maindata = bytearray()
    #mbr
    #maindata.extend(bytearray(0x200))
    maindata.extend(mbrdata)
    #gpt header
    maindata.extend(gptdata)
    maindata.extend(bytearray(0x200 - len(gptdata)))
    #gpt rable
    maindata.extend(entriesdata)

    hdr.my_lba = alternate_lba 
    hdr.alternate_lba = 1
    hdr.partition_entry_array_crc32 = calculate_partition_entry_array_crc32(entriesdata)
    hdr.header_crc32 = hdr.calculate_header_crc32()

    gptdata = encode_gpt_header(hdr)
    #gpt backup
    backdata = bytearray()
    backdata.extend(entriesdata)
    #gpt header
    backdata.extend(gptdata)
    backdata.extend(bytearray(0x200 - len(gptdata)))
    #gpt table

    
    return (bytes(maindata), bytes(backdata))

def parse_conf(path, entrylist):
    maxsize = 0
    partition_num = 0
    with open(path, "rb") as f:
         items = f.readlines()

    for item in items:
        (ispart, name, fstype, starts, stops, crop) = item.split(b':')
        if int(ispart) == 1:
            partition_num = partition_num + 1
            if name.find('/') != -1:
                name = name[:name.find(b'/')]

            entry = create_gpt_entry(int(starts[:-1]), int(stops[:-1]), name)
            entrylist.append(entry)
            maxsize = stops[:-1]
    return (int(maxsize)+33, int(partition_num))

                                              

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Error: args number is not 3")
        print("Usage: sys.argv[0] gpt.conf main_img")
        sys.exit(1)

    path = sys.argv[1]
    main_img = sys.argv[2]
    back_img = sys.argv[3]
    entrylist = []
    (alternate_lba, back_lba)  = parse_conf(path, entrylist)
    print(alternate_lba)
    print(back_lba)
    (main_data, back_data) = create(back_lba, alternate_lba, entrylist)

    create_mbr()
    with open(main_img, "wb") as f:
        f.write(main_data)
    with open(back_img, "wb") as f:
        f.write(back_data)
