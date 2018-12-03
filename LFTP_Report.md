# LFTP Project Report

中山大学    数据科学与计算机学院     软件工程(计算机应用方向)    16340132     梁颖霖

---

### 一.项目要求

+  Please choose one of following programing languages: C, C++, Java, **Python**;
   +  **本项目采用的是python3.6**
+  LFTP should use a client-server service model;
   +  **本项目使用客户端-服务器的模式**
+  LFTP must include a client side program and a server side program; Client side program can not only send a large file to the server but also download a file from the server. 
   Sending file should use the following format：
   + LFTP lsend myserver mylargefile
      Getting file should use the following format
   + LFTP lget myserver mylargefile
      The parameter myserver can be a url address or an IP address. 
   + **本项目，客户端不仅可以向服务器上传大文件，也可以从服务器下载大文件**
+  LFTP should use UDP as the transport layer protocol. 
   +  **本项目利用UDP来作为传输层协议**
+  LFTP must realize 100% reliability as TCP;
   +  **本项目实现类似TCP的100%可靠性，处理了丢包，超时，数据包顺序不一致等问题**
+  LFTP must implement flow control function similar as TCP;
   +  **本项目实现了类似TCP的流控制，在接收方维护一个rwnd接收窗口**
+  LFTP must implement congestion control function similar as TCP;
   +  **本项目实现了类似TCP的阻塞控制，在发送方维护一个cwnd阻塞窗口**
+  LFTP server side must be able to support multiple clients at the same time;
   +  **本项目支持多个用户同时向服务器收发文件，使用了多线程的机制**
+  LFTP should  provide meaningful debug  information when  programs  are 
   executed.
   +  **本项目提供了有意义的debug消息来显示发送情况，包括丢包，阻塞等事件的处理**



### 二. 设计思路

基于UDP的传输过程如下图所示

![27](https://github.com/dick20/LFTP/blob/master/image/27.png)



基于UDP来实现类似TCP的大文件传输

我的代码构建过程

1. 利用socket实现简单字符串传送
2. 对于文件进行处理，将1的代码改造成文件的传送
3. 对于文件进行分段，打包发送
4. 发送过程使用多线程
5. 服务器与客户端连接的建立与断开，三方握手，四次挥手
6. 处理命令行输入命令，与服务器进行交互
7. 添加ACK反馈包，建立判断重复ACK机制
8. 丢包事件的判断与处理
9. 接收方的序列号是否正确，要求重发
10. 接收方的流控制，构建接收窗口
11. 发送方的阻塞控制



### 三. 模块设计

#### 1.设置传送数据包的数据结构，以及反馈包的数据结构

这里的数据包与反馈包结构我采用的是struct结构体，其中一个数据包所带有文件数据为1024bytes，而头文件包括序列号，确认号，文件结束标志，为24bytes。

反馈包包括ack确认，rwnd接收窗口的大小

```python
# 传送一个包的结构，包含序列号，确认号，文件结束标志，数据包
packet_struct = struct.Struct('III1024s')

# 接收后返回的信息结构，包括ACK确认，rwnd
feedback_struct = struct.Struct('II')

BUF_SIZE = 1024+24
FILE_SIZE = 1024
```



#### 2.服务器部分：处理客户端传输的命令，并使用多线程来处理

服务器先建立一个主的线程来监听接收客户端到来的命令，将命令接收后传送到server_thread来处理，传递的参数包括客户端的命令参数以及客户端的地址。

```python
···
IP = '192.168.88.129'
SERVER_PORT = 7777
···

def main():
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    # 绑定端口:
    s.bind((IP, SERVER_PORT))

    while True:
        data,client_addr = s.recvfrom(BUF_SIZE)

        # 多线程处理
        my_thread = threading.Thread(target=server_thread,args=(client_addr,data))
        my_thread.start()
```



#### 3.服务器部分：多线程处理函数

该函数要为每一个客户端新建一个socket，并将命令解析得到客户端所需要的操作

```python
def server_thread(client_addr,string):
    # 处理传输过来的str，得到文件名，命令
    order = ''
    try:
        order = string.decode('utf-8').split(',')[0]
        file_name = string.decode('utf-8').split(',')[1]
    except Exception as e:
        return
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ···
```



除此以外，还需要像TCP建立连接一样来进行三方握手，确认连接才开始发送

客户端先申请连接

```python
	# 三方握手
    # 发送请求建立连接
    s.sendto(data,server_addr)
    # 接收连接允许
    print(data.decode('utf-8'))
    data,server_addr = s.recvfrom(BUF_SIZE)
    print('来自服务器', server_addr, '的数据是: ', data.decode('utf-8'))
```

服务器确认连接

```python
        # 文件存在，返回确认信号
        s.sendto('连接就绪'.encode('utf-8'),client_addr)
        data,client_addr = s.recvfrom(BUF_SIZE)
        print('来自',client_addr,'的数据是：',data.decode('utf-8'))
```

客户端再发送确认包，这时连接就建立完毕

```python
	# 第三次握手，确认后就开始接收
    data='ACK'.encode('utf-8')
    s.sendto(data,server_addr)
```



下面是四次挥手的过程：

当服务器执行完客户端的命令后，要像tcp一样来执行断开连接操作，断开连接后可以把socket释放掉，即调用close函数

服务器：

```python
print('\n开始中断连接')
    # 中断连接，四次挥手
    data,server_addr = s.recvfrom(BUF_SIZE)
    print(data.decode('utf-8'))

    data = 'Server allows disconnection'
    s.sendto(data.encode('utf-8'),client_addr)
    print(data)

    data = 'Server requests disconnection'
    s.sendto(data.encode('utf-8'),client_addr)
    print(data)

    data,server_addr = s.recvfrom(BUF_SIZE)
    print(data.decode('utf-8'))

    print('The connection between client and server has been interrupted')
    s.close()
```

客户端：

```python
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
```



说完建立连接与断开连接，回到多线程处理函数，对于lsend,lget函数的判断

当命令是lget时，要判断服务器是否存在该文件，如果不存在则直接返回信息后，关闭socket

若存在该文件直接进入lget函数来进行处理

当命令是lsend时，直接进入lsend函数来进行处理

```python
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
```



#### 4. lget，lsend函数逻辑

lget函数分别在客户端与服务器都各有一个，服务器负责发送功能，客户端负责接收功能。

lsend也类似，只是客户端与服务器的角色对调而已，这里只叙述其中一个函数。

##### a. 简单的分段发送功能

对于数据data，先判断它是否已经到达了文件尾，即data为空。

+ 若不为空则发送该data信息，并与ack，seq，end等信息一起打包发送到客户端的地址
+ 若为空则发送end=1的数据包，告诉客户端文件已经全部发送完毕

```python
if str(data) != "b''":
    end = 0
    s.sendto(packet_struct.pack(*(seq,ack,end,data)),client_addr)
else:
    end = 1
    packet_count+=1
    data = 'end'.encode('utf-8')
    s.sendto(packet_struct.pack(*(seq,ack,end,data)),client_addr)
    break
```



##### b. 发送后接收ACK反馈包

获取反馈包并unpack来得到接收方的ack，这个ack来确认客户端是否已经成功接收，是否需要重新发送或者序号是否正确等，rwnd则是用来用来处理流控制。

最后显示一些debug信息到控制台，可以查看文件传输的过程

```python
# 发送成功，等待ack
packeted_data,client_addr = s.recvfrom(BUF_SIZE)
unpacked_data = feedback_struct.unpack(packeted_data)
rwnd = unpacked_data[1]
ack = unpacked_data[0]
print('接受自',client_addr,'收到数据为：','rwnd = ', rwnd,
                    'ack = ', ack,'发送方的数据：cwnd = ', cwnd)
```



##### c. 发送方的流控制

发送方的流控制是要根据接收方返回的rwnd来处理的。

+ 若rwnd不为0，证明可以继续正常传输
+ 若rwnd为0，证明接收方已经不能处理这么多的数据包，应该停止发送，而是传送一个1字节的包去确认rwnd的变化

```python
	# 判断rwnd是否为0
    rwnd_zero_flag = False
    # 判断是否需要重传
    retransmit_flag = False
    # 下一个需要传的包的序号seq
    current_packet = 1
    # 接收窗口未满，正常发送
    if rwnd_zero_flag == False:
        ···
    # 接收窗口满了，发确认rwnd的包
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
        s.sendto(packet_struct.pack(*(seq,ack,end,data)),client_addr)
```



##### d. 接收方的流控制

接收方维护一个rwnd接收窗口，我初始化为50，List是用来缓存接收过来的数据，后面再进行处理，避免接收的延迟导致包的经常丢失。

+ 当发现rwnd大于0，则可以继续接收数据包，
+ 否则就发送rwnd已经满了的信息返回给服务器。

当接收到服务器的确认rwnd包，客户端会跳过处理这个包，而是告诉服务器rwnd的大小，让发送方继续进行发送操作

```python
	# 接收窗口rwnd,rwnd = RcvBuffer - [LastByteRcvd - LastßyteRead] 
    rwnd = 50
    # 空列表用于暂时保存数据包
    List = []
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
```

关于将缓存中数据写入文件，我采用的是一批批的写入，将缓存中的数据包一次性写入文件中。

```python
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
```

这样的随机写入，会出现在所有包接收完毕后，缓存中仍剩下部分数据未写入，所以在接收完毕后要对缓存的剩余做处理，直到最后一个包都写入文件中。

```python
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
```



##### e. 接收方的丢包处理

这里，我为了模拟丢包，所以在测试的时候设置了随机丢包事件，或者也可以设置一个定时器来，当超过一定的时间后，接收方就认为丢包，没有接收到下一个数据包。

这时，接收方的操作为发送上一个ACK包，重复的ACK包就是在告诉发送方接收不到新的数据包，要求重新发送。

```python
 		# 设置随机丢包，并通知服务器要求重发
        random_drop = random.randint(1,100)
        if random_drop <= 5:
            print('客户端已丢失第',unpacked_data[0],'个包,要求服务器重发')
            # 反馈上一个包的ack
            s.sendto(feedback_struct.pack(*(unpacked_data[1]-1,rwnd)), server_addr)
            continue
```



##### f.接收方的处理数据包的序号一致

packet_count是接收方期望收到的数据包序号，而传送过来的数据包序号不符合的时候，直接与丢包的处理一致，反馈上一个包的ack，通知发送方需要重新发送该数据包。

```python
# 要求序号要连续，否则将该包直接丢弃，等待下一个序号包的到来
if unpacked_data[1] != packet_count-1:
	print('客户端接收第',unpacked_data[0],'个包的序号不正确,要求服务器重发')
	# 反馈上一个包的ack
	s.sendto(feedback_struct.pack(*(unpacked_data[1]-1,rwnd)), server_addr)
	continue
```



##### g.发送方的丢包处理

设置一个flag来判断是否需要重传上一个数据包，而这个flag是根据收到重复的ACK包来决定的

```python
		# 判断是否需要重传
        if ack != current_packet:
            print('收到重复的ACK包: ack=',ack)
            retransmit_flag = True
        else:
            retransmit_flag = False
```

关于重传的机制，我预留了一个buffer，储存上一次发送的数据包，这样当需要重传的时候，我只需要从packet_buffer中拿出来进行传送就行。

```python
	# 判断是否需要重传
    retransmit_flag = False
    # 下一个需要传的包的序号seq
    current_packet = 1
    # 添加BUFFER暂时存储上一个发送过的包，当丢包发生时执行重传操作
    packet_buffer = ['hello']
```

根据retransmit_flag来判断重传，然后执行读文件还是读buffer。直到接收方成功接收到该数据包，否则会一直进入重传事件。

```python
	# 不需要重传
    if retransmit_flag == False:
		data = f.read(FILE_SIZE)
    # 需要重传
    else：
    	packet_count -= 1
        print('需要重传的包序号为 seq = ',seq,'出现丢包事件，将cwnd调整为 cwnd = ',threshold)
        data = packet_buffer[0]
     
    del packet_buffer[0]
    # 暂存下要传输的包，用于重传机制
    packet_buffer.append(data)
    current_packet = seq
    
```



##### h. 发送方的阻塞控制

关于阻塞控制部分，我仿照TCP的阻塞函数进行慢启动，快速恢复，线性增长，指数增长等操作。

初始化cwnd为1，阈值初始化为25，congestion_flag用于判断是否遇到阻塞

```python
	# 拥塞窗口cwnd,初始化为1，慢启动
    cwnd = 1
    # 空列表用于暂时保存数据包
    List = []
    # 拥塞窗口的阈值threshold,初始化为25
    threshold = 25
    # 判断是否遇到阻塞
    congestion_flag = False
    # 判断线性增长
    linear_flag = False
```

当遇到阻塞的时候，发送方应该先暂时停止传送，然后更改cwnd与threshold。cwnd为之前的阈值，然后开始线性增长。而阈值变化为当前遭遇阻塞的cwnd的一半

```python
		# 线路阻塞，停止发送，线程先休息0.01秒，稍后再继续发送
        if congestion_flag == True:
            print('传输线路遇到阻塞，将cwnd快速恢复至', cwnd)
            # cwnd等于之前的阈值，新阈值等于遭遇阻塞时cwnd的一半
            temp = cwnd
            cwnd = threshold
            threshold = int(temp/2)+1
            congestion_flag = True
            
            time.sleep(0.01)
            congestion_flag = False
            continue
```

当cwnd小于阈值，慢启动，指数增加。当cwnd大于等于阈值时候，线性增长

```python
# 阻塞控制
# cwnd小于阈值，慢启动，指数增加
if cwnd < threshold and linear_flag == False:
	cwnd *= 2
# 否则，线性增加
else:
	cwnd += 1
	linear_flag = True
```

##### 模块总结

以上的模块设计不仅适用于lget函数的客户端与服务器，而且也适用与lsend的服务器与客户端。唯一的不同只是发送方与接收方的角色对调，且地址需要更改，其余操作大致相同，这里就不再重复说明相同的代码设计。

根据上述

+ 分段发送
+ ACK反馈包接收确认
+ 丢包处理
+ 序列号正确处理
+ 流控制
+ 阻塞控制

这几部分的模块就可以在udp的传输协议下执行稳定正确的大文件传输。



#### 5. 处理客户端的命令行输入

处理客户端的输入，我使用了python的正则匹配，获取必要的操作，地址，文件名。将这些信息在后面发送到已经启动了的服务器中，来让服务器响应我的操作。

输入前提示输入规则，若输入错误，也应该提示响应的信息，这是更加友好的界面设计

```python
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
```



### 四.测试过程

客户端ip地址为172.18.32.199

![客户端ip](https://github.com/dick20/LFTP/blob/master/image/1.png)

服务器ip地址为192.168.88.129

![服务器ip地址](https://github.com/dick20/LFTP/blob/master/image/2.png)



#### 测试一：客户端向服务器发送一个test.pdf(5424kb)

服务器先启动服务：

![4](https://github.com/dick20/LFTP/blob/master/image/4.png)

客户端输入发送命令：

![3](https://github.com/dick20/LFTP/blob/master/image/3.png)



客户端发送完成截图：

![5](https://github.com/dick20/LFTP/blob/master/image/5.png)



**分析：文件发送完成，并统计大约发送了5455个包，大致符合文件的大小5424kb，其中包括一些重复的包重发，处理rwnd为0的事件，传输链路遇到阻塞等情况**

**发送完毕后，执行四次挥手来中断连接，此时客户端的命令就执行完毕。**



服务器端的完成情况：

![6](https://github.com/dick20/LFTP/blob/master/image/6.png)



**发送完毕后，可以在server.py的当前目录下找到传输过去的test.pdf，且文件内容正确，可正常打开，大小无误**



查看服务器端的debug信息：

![7](https://github.com/dick20/LFTP/blob/master/image/7.png)



**服务器与客户端发送一样，一共接收了5455个数据包。并且在传输完毕后执行四次挥手的断开连接操作。然后服务器完成该命令后，继续等待别的命令的到来。**



对于客户端的debug信息分析：阻塞事件

![8](https://github.com/dick20/LFTP/blob/master/image/8.png)

**在第5423个数据包发送的时候，遇到了线路阻塞，于是执行阻塞控制，将cwnd快速恢复到上次的阈值，然后再线性增长，符合阻塞控制的函数 **



对于客户端的debug信息分析：丢包事件

![9](https://github.com/dick20/LFTP/blob/master/image/9.png)

当发送方收到了重复的ACK包的时候，就会触发数据包重新发送的事件，直到下一个ACK为新值。



#### 测试二：客户端向服务器获取一个test1.mp4(57594kb)

该视频长度为3：14，大小约为57MB，能正常播放。

客户端命令：

![10](https://github.com/dick20/LFTP/blob/master/image/10.png)



执行结果：

![11](https://github.com/dick20/LFTP/blob/master/image/11.png)



**分析：文件接收成功，一共接收了57622个包。接收完成后，四次挥手中断连接**



![12](https://github.com/dick20/LFTP/blob/master/image/12.png)

**文件大小正确，且能正确播放**



服务器结果：

![13](https://github.com/dick20/LFTP/blob/master/image/13.png)



**客户端也是正常发送，一共发57622个数据包，数量正确。 **



#### 测试三：多个客户端向服务器获取test2.mp4，test3.mp4，上传test4.mp4 (57594kb)

这个测试是用于验证是否可以并发执行，服务器同时处理多个请求命令并正确运行。

服务端文件初始目录：

![14](https://github.com/dick20/LFTP/blob/master/image/14.png)



客户端文件初始目录：

![15](https://github.com/dick20/LFTP/blob/master/image/15.png)



打开三个命令行端口，分别输入命令来测试上传与获取：

![16](https://github.com/dick20/LFTP/blob/master/image/16.png)

![17](https://github.com/dick20/LFTP/blob/master/image/17.png)

![18](https://github.com/dick20/LFTP/blob/master/image/18.png)



测试结果：

![19](https://github.com/dick20/LFTP/blob/master/image/19.png)

![20](https://github.com/dick20/LFTP/blob/master/image/20.png)

![21](https://github.com/dick20/LFTP/blob/master/image/21.png)



并发执行成功，服务器支持多个客户端同时传输或获取文件。

执行后，文件目录截图：

![22](https://github.com/dick20/LFTP/blob/master/image/22.png)

![23](https://github.com/dick20/LFTP/blob/master/image/23.png)

**文件成功获取，客户端与服务器都可以正确打开文件，且文件大小一致**



#### 测试四：客户端向服务器发送超大文件jigsaw8.mp4 (约1.1GB)

本测试是最终测试，测试是否可以进行大文件的传输。

传输过程约用时 30min



客户端命令截图：

![24](https://github.com/dick20/LFTP/blob/master/image/24.png)



客户端执行结果：**一共发送1061920个数据包**

![25](https://github.com/dick20/LFTP/blob/master/image/25.png)



服务器执行结果：

![26](https://github.com/dick20/LFTP/blob/master/image/26.png)



### 五. 源代码

[github链接](https://github.com/dick20/LFTP)
