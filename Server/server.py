import socket
import struct
import threading
import os
import sys

# 传送一个包结构，包含序列号，确认号，文件结束标志，数据包
packet_struct = struct.Struct('III1024s')

# 循环接收客户端发送数据，并将数据发回
BUF_SIZE = 1024+24
FILE_SIZE = 1024
IP = '127.0.0.1'
SERVER_PORT = 6666

print('Bind UDP on 6666...')

# 服务器接收函数
def lget(s,client_addr,file_name):
    print('服务器正在发送',file_name,'到客户端',client_addr)
    # 暂时固定文件目录
    f = open(file_name,"rb")
    packet_count = 0

    while True:
        seq = packet_count
        ack = packet_count
        data = f.read(FILE_SIZE)
        if str(data) != "b''":
            end = 0
            s.sendto(packet_struct.pack(*(seq,ack,end,data)),client_addr)
            # print sys.getsizeof(packet_struct.pack(*(seq,ack,end,data)))
            # print(data)
        else:
            end = 1
            data = 'end'.encode('utf-8')
            s.sendto(packet_struct.pack(*(seq,ack,end,data)),client_addr)
            break

        # 发送成功，等待ack
        data,client_addr = s.recvfrom(BUF_SIZE)
        print('接受自',client_addr,'收到数据为：',data.decode('utf-8'),' seq = ', seq)
        packet_count += 1

    print('文件发送完成，一共发了'+str(packet_count),'个包')
    f.close()

# 服务器发送函数
def lsend(s,client_addr,file_name):
    print('服务器正在接收',file_name,'从客户端',client_addr)
    # 暂时固定文件目录
    f = open(file_name,"wb")
    packet_count = 0

    while True:
        data,client_addr = s.recvfrom(BUF_SIZE)
        unpacked_data = packet_struct.unpack(data)
        seq = unpacked_data[0]
        ack = unpacked_data[1]
        end = unpacked_data[2]
        data = unpacked_data[3]

        if end != 1:
            f.write(data)
        else:
            break

        # 接收成功，发送ack
        print('发送方已发送第',seq,'个包')
        data = 'ACK'.encode('utf-8')
        s.sendto(data,client_addr)
        packet_count += 1

    print('文件接收完成，一共收了'+str(packet_count),'个包')
    f.close()

def server_thread(client_addr,string):
    # 处理传输过来的str，得到文件名，命令
    order = ''
    try:
        order = string.decode('utf-8').split(',')[0]
        file_name = string.decode('utf-8').split(',')[1]
    except Exception as e:
        return
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if order == 'lget':
        # 处理文件不存在的情况
        if os.path.exists(file_name) is False:
            data = 'FileNotFound'.encode('utf-8')
            s.sendto(data, client_addr)
            # 关闭socket
            s.close()
            return
        
        # 文件存在，返回确认信号
        s.sendto('连接就绪'.encode('utf-8'),client_addr)
        data,client_addr = s.recvfrom(BUF_SIZE)
        print('来自',client_addr,'的数据是：',data.decode('utf-8'))
        lget(s,client_addr,file_name)
    elif order == 'lsend':
        s.sendto('是否可以连接'.encode('utf-8'),client_addr)
        # 等待确认
        data,client_addr = s.recvfrom(BUF_SIZE)
        print('来自',client_addr,'的数据是：',data.decode('utf-8'))
        lsend(s,client_addr,file_name)

    s.close()


def main():
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    # 绑定端口:
    s.bind(('', SERVER_PORT))

    while True:
        data,client_addr = s.recvfrom(BUF_SIZE)

        # 多线程处理
        my_thread = threading.Thread(target=server_thread,args=(client_addr,data))
        my_thread.start()

if __name__ == "__main__":
    main()