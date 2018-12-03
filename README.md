# LFTP
## 2018中山大学计算机网络项目：基于udp实现tcp功能进行大文件传输

### 一.项目要求

+ Please choose one of following programing languages: C, C++, Java, **Python**;
  + **本项目采用的是python3.6**
+ LFTP should use a client-server service model;
  + **本项目使用客户端-服务器的模式**
+ LFTP must include a client side program and a server side program; Client side program can not only send a large file to the server but also download a file from the server. 
  Sending file should use the following format：
  + LFTP lsend myserver mylargefile
    Getting file should use the following format
  + LFTP lget myserver mylargefile
    The parameter myserver can be a url address or an IP address. 
  + **本项目，客户端不仅可以向服务器上传大文件，也可以从服务器下载大文件**
+ LFTP should use UDP as the transport layer protocol. 
  + **本项目利用UDP来作为传输层协议**
+ LFTP must realize 100% reliability as TCP;
  + **本项目实现类似TCP的100%可靠性，处理了丢包，超时，数据包顺序不一致等问题**
+ LFTP must implement flow control function similar as TCP;
  + **本项目实现了类似TCP的流控制，在接收方维护一个rwnd接收窗口**
+ LFTP must implement congestion control function similar as TCP;
  + **本项目实现了类似TCP的阻塞控制，在发送方维护一个cwnd阻塞窗口**
+ LFTP server side must be able to support multiple clients at the same time;
  + **本项目支持多个用户同时向服务器收发文件，使用了多线程的机制**
+ LFTP should  provide meaningful debug  information when  programs  are 
  executed.
  + **本项目提供了有意义的debug消息来显示发送情况，包括丢包，阻塞等事件的处理**

