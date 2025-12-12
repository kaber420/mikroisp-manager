# 2025-12-11 17:53:00 by RouterOS 7.20.5
# software id = JQF8-6YLM
#
# model = C52iG-5HaxD2HaxD
# serial number = HEB08YTD6SA
/interface bridge
add admin-mac=48:A9:8A:A0:04:D2 auto-mac=no comment=defconf name=bridge
/interface ethernet
set [ find default-name=ether1 ] comment=wan1
/interface wifi
set [ find default-name=wifi1 ] configuration.country="United States" .mode=\
    ap .ssid=wifi5G-kbr disabled=no security.authentication-types=\
    wpa2-psk,wpa3-psk .ft=yes .ft-over-ds=yes
set [ find default-name=wifi2 ] channel.skip-dfs-channels=10min-cac \
    configuration.country="United States" .mode=ap .ssid=kaber-wifi disabled=\
    no security.authentication-types=wpa2-psk,wpa3-psk .ft=yes .ft-over-ds=\
    yes
/interface vlan
add comment="managed by umonitor" interface=ether5 name=vlan250 vlan-id=250
/interface list
add comment=defconf name=WAN
add comment=defconf name=LAN
/interface wifi security
add authentication-types=wpa2-psk,wpa3-psk disabled=no name=kbrpass
/ip pool
add name=default-dhcp ranges=192.168.88.10-192.168.88.254
/ip dhcp-server
add address-pool=default-dhcp interface=bridge name=defconf
/queue simple
add comment="SUSPENDIDO - kaber test" max-limit=1k/1k name="kaber test" \
    target=192.168.88.55/32
add comment="Managed by \C2\B5Monitor: Residenciales [PARENT]" max-limit=\
    100M/120M name=Residenciales target=192.168.90.0/24
/user group
add name=api_full_access policy="local,ssh,ftp,read,write,policy,test,password\
    ,sniff,sensitive,api,romon,!telnet,!reboot,!winbox,!web,!rest-api"
/disk settings
set auto-media-interface=bridge auto-media-sharing=yes auto-smb-sharing=yes
/interface bridge port
add bridge=bridge comment=defconf interface=ether2
add bridge=bridge comment=defconf interface=ether3
add bridge=bridge comment=defconf interface=ether4
add bridge=bridge comment=defconf interface=ether5
add bridge=bridge comment=defconf interface=wifi1
add bridge=bridge comment=defconf interface=wifi2
/ip neighbor discovery-settings
set discover-interface-list=LAN
/interface list member
add comment=defconf interface=bridge list=LAN
add comment=defconf interface=ether1 list=WAN
/interface pppoe-server server
add authentication=mschap2 disabled=no interface=bridge service-name=\
    pppoe-server
/ip address
add address=192.168.88.1/24 comment=defconf interface=bridge network=\
    192.168.88.0
add address=192.168.89.1/24 comment="Managed by \C2\B5Monitor" interface=\
    bridge network=192.168.89.0
add address=192.168.66.1/24 interface=bridge network=192.168.66.0
/ip dhcp-client
add comment=defconf interface=ether1
/ip dhcp-server lease
add address=192.168.88.252 client-id=1:d8:c0:a6:31:b6:9 mac-address=\
    D8:C0:A6:31:B6:09 server=defconf use-src-mac=yes
/ip dhcp-server network
add address=192.168.88.0/24 comment=defconf dns-server=192.168.88.1 gateway=\
    192.168.88.1
/ip dns
set allow-remote-requests=yes
/ip dns static
add address=192.168.88.1 comment=defconf name=router.lan type=A
/ip firewall address-list
add address=192.168.88.40 comment=cliente2 list=clientes_activos
add address=192.168.88.252 comment=laptop list=clientes_activos
add address=192.168.88.42 comment="cliente 3" list=clientes_activos
/ip firewall filter
add action=accept chain=input comment=\
    "defconf: accept established,related,untracked" connection-state=\
    established,related,untracked
add action=drop chain=input comment="defconf: drop invalid" connection-state=\
    invalid
add action=accept chain=input comment="defconf: accept ICMP" protocol=icmp
add action=accept chain=input comment=\
    "defconf: accept to local loopback (for CAPsMAN)" dst-address=127.0.0.1
add action=drop chain=input comment="defconf: drop all not coming from LAN" \
    in-interface-list=!LAN
add action=accept chain=forward comment="defconf: accept in ipsec policy" \
    ipsec-policy=in,ipsec
add action=accept chain=forward comment="defconf: accept out ipsec policy" \
    ipsec-policy=out,ipsec
add action=fasttrack-connection chain=forward comment="defconf: fasttrack" \
    connection-state=established,related disabled=yes hw-offload=yes
add action=accept chain=forward comment=\
    "defconf: accept established,related, untracked" connection-state=\
    established,related,untracked
add action=drop chain=forward comment="defconf: drop invalid" \
    connection-state=invalid
add action=drop chain=forward comment=\
    "defconf: drop all from WAN not DSTNATed" connection-nat-state=!dstnat \
    connection-state=new in-interface-list=WAN
/ip firewall nat
add action=masquerade chain=srcnat comment="defconf: masquerade" \
    ipsec-policy=out,none out-interface-list=WAN
/ip service
set telnet disabled=yes
set www disabled=yes
set api-ssl certificate=api_ssl_cert
/ipv6 firewall address-list
add address=::/128 comment="defconf: unspecified address" list=bad_ipv6
add address=::1/128 comment="defconf: lo" list=bad_ipv6
add address=fec0::/10 comment="defconf: site-local" list=bad_ipv6
add address=::ffff:0.0.0.0/96 comment="defconf: ipv4-mapped" list=bad_ipv6
add address=::/96 comment="defconf: ipv4 compat" list=bad_ipv6
add address=100::/64 comment="defconf: discard only " list=bad_ipv6
add address=2001:db8::/32 comment="defconf: documentation" list=bad_ipv6
add address=2001:10::/28 comment="defconf: ORCHID" list=bad_ipv6
add address=3ffe::/16 comment="defconf: 6bone" list=bad_ipv6
/ipv6 firewall filter
add action=accept chain=input comment=\
    "defconf: accept established,related,untracked" connection-state=\
    established,related,untracked
add action=drop chain=input comment="defconf: drop invalid" connection-state=\
    invalid
add action=accept chain=input comment="defconf: accept ICMPv6" protocol=\
    icmpv6
add action=accept chain=input comment="defconf: accept UDP traceroute" \
    dst-port=33434-33534 protocol=udp
add action=accept chain=input comment=\
    "defconf: accept DHCPv6-Client prefix delegation." dst-port=546 protocol=\
    udp src-address=fe80::/10
add action=accept chain=input comment="defconf: accept IKE" dst-port=500,4500 \
    protocol=udp
add action=accept chain=input comment="defconf: accept ipsec AH" protocol=\
    ipsec-ah
add action=accept chain=input comment="defconf: accept ipsec ESP" protocol=\
    ipsec-esp
add action=accept chain=input comment=\
    "defconf: accept all that matches ipsec policy" ipsec-policy=in,ipsec
add action=drop chain=input comment=\
    "defconf: drop everything else not coming from LAN" in-interface-list=\
    !LAN
add action=fasttrack-connection chain=forward comment="defconf: fasttrack6" \
    connection-state=established,related
add action=accept chain=forward comment=\
    "defconf: accept established,related,untracked" connection-state=\
    established,related,untracked
add action=drop chain=forward comment="defconf: drop invalid" \
    connection-state=invalid
add action=drop chain=forward comment=\
    "defconf: drop packets with bad src ipv6" src-address-list=bad_ipv6
add action=drop chain=forward comment=\
    "defconf: drop packets with bad dst ipv6" dst-address-list=bad_ipv6
add action=drop chain=forward comment="defconf: rfc4890 drop hop-limit=1" \
    hop-limit=equal:1 protocol=icmpv6
add action=accept chain=forward comment="defconf: accept ICMPv6" protocol=\
    icmpv6
add action=accept chain=forward comment="defconf: accept HIP" protocol=139
add action=accept chain=forward comment="defconf: accept IKE" dst-port=\
    500,4500 protocol=udp
add action=accept chain=forward comment="defconf: accept ipsec AH" protocol=\
    ipsec-ah
add action=accept chain=forward comment="defconf: accept ipsec ESP" protocol=\
    ipsec-esp
add action=accept chain=forward comment=\
    "defconf: accept all that matches ipsec policy" ipsec-policy=in,ipsec
add action=drop chain=forward comment=\
    "defconf: drop everything else not coming from LAN" in-interface-list=\
    !LAN
/ppp secret
add comment="Client-ID: 1" name=fco.ivan.romero.guzman profile=\
    default-encryption service=pppoe
add comment="Client-ID: 2" name=jose profile=default-encryption service=pppoe
add comment="Client-ID: 2" name=ffgbfgbf profile=default-encryption service=\
    pppoe
/system clock
set time-zone-name=America/Hermosillo
/system identity
set name=kbr-hapax2
/tool mac-server
set allowed-interface-list=LAN
/tool mac-server mac-winbox
set allowed-interface-list=LAN
/tool romon
set enabled=yes
