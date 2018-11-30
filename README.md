# LFTP
## 2018中山大学计算机网络项目：基于udp实现tcp功能进行大文件传输

+ LFTP	should	use	a	client-server	service	model;

+ LFTP	must	include	a	 client	 side	 program	and	a	 server	 side	 program;	
Client side	program	can	not	only	send	a	large	file	to	the	server	but	also	download	a	file from	the	server.	

  + Sending	file	should	use the	following	format：
			 LFTP	lsend	myserver	mylargefile
       
  + Getting	file	should	use	the	following	format
			 			 LFTP	lget myserver	mylargefile
             
  + The	parameter	myserver	can	be	a url	address	or	an	IP	address.	

+ LFTP	should	use	UDP	as	the	transport	layer	protocol.	

+	LFTP	must	realize	100%	reliability	as	TCP;

+ LFTP	must	implement	flow	control	function	similar as	TCP;

+ LFTP	must	implement	congestion control	function	similar	as	TCP;

+ LFTP	server	side	must	be	able	to	support	multiple	clients	at	the same	time;

+ LFTP	 should	 provide	 meaningful	 debug	 information	 when	 proggrams	 are	executed;
