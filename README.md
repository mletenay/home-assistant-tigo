# Tigo CCA (local network) monitoring for Home Assistant

Home assistant custom integration for local network monitoring of Tigo's Cloud Connect Advanced gateway and connected PV panel modules/optimizers like Tigo TS4-A-O.

## Preconditions

Out of the factory, the Tigo CCA does not allow local network access and any data have to be accessed via their cloud portal.

This limitation can be worked around by "rooting" the CCA device, exposing internal management web.

Beware ! Perform it at your own risk, hacking the device may void the waranty and improper use of the management web may damage/brick your devices.

Step by step instructions how to enable local network access to the CCA can be found here [Getting Data DIRECTLY from a Tigo TAP - is it possible ?](https://diysolarforum.com/threads/getting-data-directly-from-a-tigo-tap-is-it-possible.37414/page-2#post-1085251) or here [Details, Protokolle, Zugang auf Tigo CCA](https://www.photovoltaikforum.com/thread/149592-details-protokolle-zugang-auf-tigo-cca/?postID=3649832#post3649832).

In short:
Open web page `http://[cca ip address]/cgi-bin/shell` (Tigo/$olar), then login into it via ssh (root/gW$70#c). When in, remount the filesystem to be writable `mount -o remount,rw /` and expose the web console to local network by adding SNAT to its internal net via `echo "/usr/sbin/iptables -t nat -D INPUT -p tcp --dport 80 -j SNAT --to 10.11.1.1" >> /etc/rc.httpd`.
After reboot, the web console at `http://[cca ip address]/cgi-bin/mmdstatus` (Tigo/$olar) should be permanently accessible.

Just a remark, the procedure above exposes not only the administration console, but also a nice, user oriented web app at http://[cca ip address]/summary/

## Installation

Install this component using HACS by adding custom repository https://github.com/mletenay/home-assistant-tigo and searching for Tigo in the Integrations.

## Configuration

The component requires the hostname/IP (plus username/passwd when required) of the Tigo CCA web server.

## See also

https://github.com/rp-/tigo-exporter
