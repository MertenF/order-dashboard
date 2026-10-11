import time
from time import sleep
from socket import socket, AF_INET, SOCK_DGRAM, IPPROTO_UDP, IPPROTO_IP, IP_MULTICAST_TTL, IP_MULTICAST_IF, inet_aton

def main():
    mcast_grp = '224.0.0.1'
    mcast_port = 17899
    ttl = 2
    msg = bytes.fromhex('46ca5a6c')
    # 77beee5e

    sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
    #sock.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, ttl)
    sock.setsockopt(IPPROTO_IP, IP_MULTICAST_IF, inet_aton('192.168.0.200'))

    while True:
        sock.sendto(msg, (mcast_grp, mcast_port))
        print(f'multicast {msg} sent')
        time.sleep(0.1)


if __name__ == '__main__':
    main()

    print('done')