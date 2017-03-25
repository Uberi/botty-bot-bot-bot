# sudo apt-get install libbluetooth-dev && pip3 install pybluez

import bluetooth

#devices = bluetooth.discover_devices()

target_address = "20:16:02:30:88:12"

bluetooth_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
bluetooth_socket.connect((target_address, 1)) # note: PIN code is 1234
print("sending")
bluetooth_socket.send("Challange")
print("receiving")
response = bluetooth_socket.recv(1024)
print("received", response)
bluetooth_socket.close()