import csv
import os
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

    for pkt in tqdm(packets, desc=f"Processing {os.path.basename(file_path)}"):
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

    # 返回统计信息字典
    return {
        "file_name": os.path.basename(file_path),
        "total_packets": total_packets,
        "total_flows": total_flows,
        "total_bidirectional_flows": total_bidirectional_flows,
        "avg_packet_length": avg_packet_length,
        "tcp_count": tcp_count,
        "tcp_ratio": f"{tcp_ratio:.2%}",
        "udp_count": udp_count,
        "udp_ratio": f"{udp_ratio:.2%}",
        "tcp_handshake_packets": tcp_handshake_count,
        "completed_tcp_handshakes": len(handshake_flows),
    }


def analyze_folder(folder_path, output_csv):
    # 遍历文件夹中的所有 PCAP 文件
    pcap_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".pcap")]

    # CSV 表头
    headers = [
        "file_name", "total_packets", "total_flows", "total_bidirectional_flows",
        "avg_packet_length", "tcp_count", "tcp_ratio", "udp_count", "udp_ratio",
        "tcp_handshake_packets", "completed_tcp_handshakes"
    ]

    with open(output_csv, mode="w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for file_path in pcap_files:
            stats = analyze_pcap(file_path)
            writer.writerow(stats)

    print(f"Analysis complete. Results saved to {output_csv}")


# 示例调用
folder_path = r"E:\dataset\pcap_files"  # 替换为你的 PCAP 文件夹路径
output_csv = r"D:\code\Traffic\build_datas\test\pcap_report.csv"  # 替换为保存的 CSV 文件路径
analyze_folder(folder_path, output_csv)
