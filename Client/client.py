import socket
import struct
import os
import stat
import re
import sys
import time
import random

BUF_SIZE = 1024+24
CLIENT_PORT = 7777
FILE_SIZE = 1024


# 传送一个包的结构，包含序列号，确认号，文件结束标志，数据包
packet_struct = struct.Struct('III1024s')

# 接收后返回的信息结构，包括ACK确认，rwnd
feedback_struct = struct.Struct('II')

def lsend(s,server_addr,file_name):
    packet_count = 1
    f = open(file_name,"rb")
    data='ACK'.encode('utf-8')
    s.sendto(data,server_addr)

    # 判断rwnd是否为0
    rwnd_zero_flag = False
    # 判断是否需要重传
    retransmit_flag = False
    # 下一个需要传的包的序号seq
    current_packet = 1

    # 添加BUFFER暂时存储上一个发送过的包，当丢包发生时执行重传操作
    packet_buffer = ['hello']

    while True:
        seq = packet_count
        ack = packet_count
        # 阻塞窗口未满，正常发送
        if rwnd_zero_flag == False:
            # 不需要重传
            if retransmit_flag == False:
                data = f.read(FILE_SIZE)
            # 需要重传
            else:
                ack -= 1
                seq -= 1
                packet_count -= 1
                print('需要重传的包序号为 seq = ',seq)
                data = packet_buffer[0]

            del packet_buffer[0]
            # 暂存下要传输的包，用于重传机制
            packet_buffer.append(data)
            current_packet = seq

            # 文件未传输完成
            if str(data)!="b''":
                end = 0
                s.sendto(packet_struct.pack(*(seq,ack,end,data)), server_addr)
                
            # 文件传输完成，发送结束包
            else:
                data = 'end'.encode('utf-8')
                end = 1
                packet_count += 1
                s.sendto(packet_struct.pack(*(seq,ack,end,data)), server_addr)
                print('end packet:',seq)
                # 发送成功，等待ack
                packeted_data,server_address = s.recvfrom(BUF_SIZE)
                unpacked_data = feedback_struct.unpack(packeted_data)
                rwnd = unpacked_data[1]
                ack = unpacked_data[0]
                print('接受自',server_addr,'收到数据为：','rwnd = ', rwnd,' ack = ', ack)
                break
        
        # 阻塞窗口满了，发确认rwnd的包
        else:
            # 不需要重传
            if retransmit_flag == False:
                seq = 0
                end = 0
                data = 'rwnd'.encode('utf-8')
            # 需要重传
            else:
                ack -= 1
                seq -= 1
                packet_count -= 1
                data = packet_buffer[0]

            del packet_buffer[0]
            # 暂存下要传输的包，用于重传机制
            packet_buffer.append(data)
            current_packet = seq

            s.sendto(packet_struct.pack(*(seq,ack,end,data)),server_addr)
        
        packet_count += 1

        # 发送成功，等待ack
        packeted_data,server_address = s.recvfrom(BUF_SIZE)
        unpacked_data = feedback_struct.unpack(packeted_data)
        rwnd = unpacked_data[1]
        ack = unpacked_data[0]

        # 判断是否需要重传
        if ack != current_packet:
            print('ack: ',ack,' current_packet: ',current_packet)
            retransmit_flag = True
        else:
            retransmit_flag = False

        # 判断rwnd是否已经满了
        if rwnd == 0:
            rwnd_zero_flag = True
        else:
            rwnd_zero_flag = False

        print('接受自',server_addr,'收到数据为：','rwnd = ', rwnd,' ack = ', ack)


    print('文件发送完成，一共发了'+str(packet_count),'个包')
    f.close()

def lget(s,server_addr,file_name):
    packet_count = 1
    # 第三次握手，确认后就开始接收
    data='ACK'.encode('utf-8')
    s.sendto(data,server_addr)
    f = open(file_name,"wb")

    # 接收窗口rwnd,rwnd = RcvBuffer - [LastByteRcvd - LastßyteRead] 
    rwnd = 50
    # 空列表用于暂时保存数据包
    List = []

    while True:
        packeted_data,addr = s.recvfrom(BUF_SIZE)
        unpacked_data = packet_struct.unpack(packeted_data)

        # 设置随机丢包，并通知服务器要求重发
        random_drop = random.randint(1,100)
        if random_drop <= 5:
            print('客户端已丢失第',unpacked_data[0],'个包,要求服务器重发')
            # 反馈上一个包的ack
            s.sendto(feedback_struct.pack(*(unpacked_data[1]-1,rwnd)), server_addr)
            continue

        packet_count+=1
        # 先将数据加入列表，后面再读取出来
        if rwnd > 0:
            # 服务端为确认rwnd的变化，会继续发送字节为1的包，这里我设置seq为-1代表服务端的确认
            # 此时直接跳过处理这个包，返回rwnd的大小
            if unpacked_data[0] == 0:
                s.sendto(feedback_struct.pack(*(unpacked_data[0],rwnd)), server_addr)
                continue

            # 要求序号要连续，否则将该包直接丢弃，等待下一个序号包的到来
            if unpacked_data[1] != packet_count-1:
                print('客户端接收第',unpacked_data[0],'个包的序号不正确,要求服务器重发')
                # 反馈上一个包的ack
                s.sendto(feedback_struct.pack(*(unpacked_data[1]-1,rwnd)), server_addr)
                continue

            # 序号一致，加进缓存
            List.append(unpacked_data)
            rwnd -= 1
            # 接收完毕，发送ACK反馈包
            s.sendto(feedback_struct.pack(*(unpacked_data[0],rwnd)), server_addr)
        else:
            s.sendto(feedback_struct.pack(*(unpacked_data[0],rwnd)), server_addr)  
        print('客户端已接收第',unpacked_data[0],'个包','rwnd为',rwnd)
        # 随机将数据包写入文件，即存在某一时刻不写入，继续接收
        random_write = random.randint(1,10)
        random_num = random.randint(1,100)
        # 40%机率写入文件,读入文件数也是随机数
        if random_write > 4:
            while len(List) > random_num:
                unpacked_data = List[0]
                seq = unpacked_data[0]
                ack = unpacked_data[1]
                end = unpacked_data[2]
                data = unpacked_data[3]
                del List[0]
                rwnd += 1
                if end != 1:
                    f.write(data)
                else:
                    break
        print('random_write: ',random_write,' random_num: ',random_num,' ', len(List),'end:',unpacked_data[2])
        # 接收完毕，但是要处理剩下在List中的数据包
        if unpacked_data[2] == 1:
            break

    # 处理剩下在List中的数据包
    while len(List) > 0:
        unpacked_data = List[0]
        end = unpacked_data[2]
        data = unpacked_data[3]
        del List[0]
        rwnd += 1
        if end != 1:
           f.write(data)
        else:
           break

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

    # 三方握手
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

    print('\n开始中断连接')
    # 中断连接，四次挥手
    data = 'Client requests disconnection'
    print(data)
    s.sendto(data.encode('utf-8'),server_addr)

    data,client_addr = s.recvfrom(BUF_SIZE)
    print(data.decode('utf-8'))

    data,client_addr = s.recvfrom(BUF_SIZE)
    print(data.decode('utf-8'))

    data = 'Client allows disconnection'
    s.sendto(data.encode('utf-8'),server_addr)
    print(data)

    print('The connection between client and server has been interrupted')
    s.close()

if __name__ == "__main__":
    main()