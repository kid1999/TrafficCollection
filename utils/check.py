from collections import defaultdict

import scapy.all as scapy
from tqdm import tqdm


def analyze_pcap(file_path):
    packets = scapy.rdpcap(file_path)

    # 初始化统计数据
    total_packets = len(packets)
    total_length = sum(len(pkt) for pkt in packets)
    avg_packet_length = total_length / total_packets if total_packets > 0 else 0

    tcp_count = 0
    udp_count = 0
    tcp_handshake_count = 0  # TCP 握手包统计
    handshake_flows = set()  # 跟踪已完成三次握手的流
    flow_states = {}  # 跟踪每个流的状态：SYN -> SYN-ACK -> ACK
    flows = defaultdict(set)
    bidirectional_flows = set()

    for pkt in tqdm(packets):
        if scapy.IP in pkt:
            ip_src = pkt[scapy.IP].src
            ip_dst = pkt[scapy.IP].dst

            if scapy.TCP in pkt:
                tcp_count += 1
                sport, dport = pkt[scapy.TCP].sport, pkt[scapy.TCP].dport
                tcp_flags = pkt[scapy.TCP].flags

                flow = (ip_src, ip_dst, sport, dport)
                rev_flow = (ip_dst, ip_src, dport, sport)

                # 判断 TCP 握手状态
                if tcp_flags == 0x02:  # SYN
                    flow_states[flow] = "SYN"
                    tcp_handshake_count += 1
                elif tcp_flags == 0x12 and flow_states.get(rev_flow) == "SYN":  # SYN-ACK
                    flow_states[rev_flow] = "SYN-ACK"
                    tcp_handshake_count += 1
                elif tcp_flags == 0x10 and flow_states.get(flow) == "SYN-ACK":  # ACK（握手第三步）
                    tcp_handshake_count += 1
                    handshake_flows.add(flow)
                    del flow_states[flow]  # 移除已完成握手的流

            elif scapy.UDP in pkt:
                udp_count += 1
                sport, dport = pkt[scapy.UDP].sport, pkt[scapy.UDP].dport
            else:
                continue

            # 单向流和双向流统计
            flow = (ip_src, ip_dst, sport, dport)
            rev_flow = (ip_dst, ip_src, dport, sport)
            flows[flow].add(float(pkt.time))
            if rev_flow in flows:
                bidirectional_flows.add(frozenset([flow, rev_flow]))

    total_flows = len(flows)
    total_bidirectional_flows = len(bidirectional_flows)
    tcp_ratio = tcp_count / total_packets if total_packets > 0 else 0
    udp_ratio = udp_count / total_packets if total_packets > 0 else 0

    # 输出统计信息
    print(f"Total packets: {total_packets}")
    print(f"Total flows: {total_flows}")
    print(f"Total bidirectional flows: {total_bidirectional_flows}")
    print(f"Average packet length: {avg_packet_length:.2f} bytes")
    print(f"TCP packets: {tcp_count} ({tcp_ratio:.2%})")
    print(f"UDP packets: {udp_count} ({udp_ratio:.2%})")
    print(f"TCP handshake packets (SYN, SYN-ACK, ACK): {tcp_handshake_count}")
    print(f"Completed TCP handshakes: {len(handshake_flows)}")

# 示例调用
file_path = r"D:\code\Traffic\build_datas\test\pcap_files\baidu.com_20250110125021.pcap"  # 替换为你的 pcap 文件路径
analyze_pcap(file_path)

