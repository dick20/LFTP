import socket
import struct
import os
import stat
import re
import sys

BUF_SIZE = 1024+24
CLIENT_PORT = 6666
FILE_SIZE = 1024

# 传送一个包结构，包含序列号，确认号，文件结束标志，数据包
packet_struct = struct.Struct('III1024s')

def lsend(s,server_addr,file_name):
    packet_count = 0
    f = open(file_name,"rb")
    data='ACK'.encode('utf-8')
    s.sendto(data,server_addr)
    while True:
        data = f.read(FILE_SIZE)
        seq = packet_count
        ack = packet_count
        # 文件未传输完成
        if str(data)!="b''":
            end = 0
            s.sendto(packet_struct.pack(*(seq,ack,end,data)), server_addr)
            
        # 文件传输完成，发送结束包
        else:
            data = 'end'.encode('utf-8')
            end = 1
            s.sendto(packet_struct.pack(*(seq,ack,end,data)), server_addr)
            break
        # 等待服务器发送ack
        data, server_address = s.recvfrom(BUF_SIZE)
        print('服务器已接收第',seq,'个包')
        packet_count += 1
    print('文件发送完成，一共发了'+str(packet_count),'个包')
    f.close()

def lget(s,server_addr,file_name):
    packet_count = 0
    f = open(file_name,"wb")
    while True:
        if packet_count==0:
            data='ACK'.encode('utf-8')
            s.sendto(data,server_addr)
        packeted_data,addr = s.recvfrom(BUF_SIZE)
        unpacked_data = packet_struct.unpack(packeted_data)
        seq = unpacked_data[0]
        ack = unpacked_data[1]
        end = unpacked_data[2]
        data = unpacked_data[3]

        print('客户端已接收第',seq,'个包')
        # print(data)
        if end != 1:
            f.write(data)
        else:
            break
        # 接收完毕，发送ACK包
        data='ACK'.encode('utf-8')
        s.sendto(data,addr)
        packet_count+=1

    print('文件接收完成，一共接收了'+str(packet_count),'个包')
    f.close()

def main():
    # 读取输入信息
    op = input('Please enter your operation: LFTP [lsend | lget] myserver mylargefile\n')
    # 正则匹配
    pattern = re.compile(r'(LFTP) (lsend|lget) (\S+) (\S+)')
    match =pattern.match(op)
    if op:
        op = match.group(2)
        server_ip = match.group(3)
        file_name = match.group(4)
    else:
        print('Wrong input!')

    # 三方握手建立连接
    # lsend命令，文件不存在
    if op == 'lsend' and (os.path.exists(file_name) is False):
        print('[lsend] The file cannot be found.')
        exit(0)

    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    data = (op+','+file_name).encode('utf-8')
    server_addr=(server_ip,CLIENT_PORT)
    # 发送请求建立连接
    s.sendto(data,server_addr)
    # 接收连接允许
    print(data.decode('utf-8'))
    data,server_addr = s.recvfrom(BUF_SIZE)
    print('来自服务器', server_addr, '的数据是: ', data.decode('utf-8'))

    if data.decode('utf-8') == 'FileNotFound':
        print('[lget] The file cannot be found.')
        exit(0)

    if op == 'lget':
        lget(s,server_addr,file_name)
    elif op == 'lsend':
        lsend(s,server_addr,file_name)

    s.close()

if __name__ == "__main__":
    main()