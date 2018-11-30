import socket
import struct
import threading
import os
import sys
import random

# 传送一个包的结构，包含序列号，确认号，文件结束标志，数据包
packet_struct = struct.Struct('III1024s')

# 接收后返回的信息结构，包括ACK确认，rwnd
feedback_struct = struct.Struct('II')

BUF_SIZE = 1024+24
FILE_SIZE = 1024
IP = '127.0.0.1'
SERVER_PORT = 7777
# 用于流控制
WINDOW_SIZE = 50


print('Bind UDP on 7777...')

# 服务器接收函数
def lget(s,client_addr,file_name):
    print('服务器正在发送',file_name,'到客户端',client_addr)
    # 暂时固定文件目录
    f = open(file_name,"rb")
    packet_count = 1
    rwnd_zero_flag = False

    while True:
        seq = packet_count
        ack = packet_count
        # 阻塞窗口未满，正常发送
        if rwnd_zero_flag == False:
            data = f.read(FILE_SIZE)
            if str(data) != "b''":
                end = 0
                s.sendto(packet_struct.pack(*(seq,ack,end,data)),client_addr)
                # print sys.getsizeof(packet_struct.pack(*(seq,ack,end,data)))
                # print(data)
            else:
                end = 1
                packet_count+=1
                data = 'end'.encode('utf-8')
                s.sendto(packet_struct.pack(*(seq,ack,end,data)),client_addr)
                break
        # 阻塞窗口满了，发确认rwnd的包
        else:
            seq = 0
            end = 0
            data = 'rwnd'.encode('utf-8')
            s.sendto(packet_struct.pack(*(seq,ack,end,data)),client_addr)

        # 发送成功，等待ack
        packeted_data,client_addr = s.recvfrom(BUF_SIZE)
        unpacked_data = feedback_struct.unpack(packeted_data)
        rwnd = unpacked_data[1]
        ack = unpacked_data[0]
        # 判断rwnd是否已经满了
        if rwnd == 0:
            rwnd_zero_flag = True
        else:
            rwnd_zero_flag = False
        
        print('接受自',client_addr,'收到数据为：','rwnd = ', rwnd,' ack = ', ack)
        packet_count += 1

    print('文件发送完成，一共发了'+str(packet_count),'个包')
    f.close()

# 服务器发送函数
def lsend(s,client_addr,file_name):
    print('服务器正在接收',file_name,'从客户端',client_addr)
    # 暂时固定文件目录
    f = open(file_name,"wb")
    packet_count = 1

    # 接收窗口rwnd,rwnd = RcvBuffer - [LastByteRcvd - LastßyteRead ] 
    rwnd = 50
    # 空列表用于暂时保存数据包
    List = []

    while True:
        data,client_addr = s.recvfrom(BUF_SIZE)
        unpacked_data = packet_struct.unpack(data)

        packet_count += 1
        if rwnd > 0:
            # 服务端为确认rwnd的变化，会继续发送字节为1的包，这里我设置seq为-1代表服务端的确认
            # 此时直接跳过处理这个包，返回rwnd的大小
            if unpacked_data[0] == 0:
                s.sendto(feedback_struct.pack(*(unpacked_data[0],rwnd)), client_addr)
                continue
            List.append(unpacked_data)
            rwnd -= 1
            # 接收完毕，发送ACK反馈包
            s.sendto(feedback_struct.pack(*(unpacked_data[0],rwnd)), client_addr)
        else:
            s.sendto(feedback_struct.pack(*(unpacked_data[0],rwnd)), client_addr)  
        print('服务器已接收第',unpacked_data[0],'个包','rwnd为',rwnd)
        
        # 随机将数据包写入文件，即存在某一时刻不写入，继续接收
        random_write = random.randint(1,10)
        random_num = random.randint(1,100)
        # 40%机率写入文件,读入文件数也是随机数
        if random_write > 6:
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
        print(len(List),'end:',unpacked_data[2])
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