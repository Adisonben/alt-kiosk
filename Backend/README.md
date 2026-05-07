### ALT kiosk application

# System requirement
- java 1.8.0_65
- libusb-0.1-4

# install java on pi5 arm 32 os
- [Download java sdk](https://www.oracle.com/java/technologies/javase/javase8-archive-downloads.html)
- `sudo tar -xvzf jdk-8u202-linux-arm64-vfp-hflt.tar.gz -C /usr/lib`
- `sudo update-alternatives --install /usr/bin/java java /usr/lib/jvm/jdk1.8.0_202/bin/java 1`
- `sudo update-alternatives --install /usr/bin/javac javac /usr/lib/jvm/jdk1.8.0_202/bin/javac 1`

# Install SecuGen sdk for pi5 arm32 os
- cd to 'FDx_SDK_PRO_LINUX_PI_armv7l_3_8_8/lib/pi'
- `sudo cp libpysgfplib.so.1.0.1.fdu05_rename libpysgfplib.so | sudo ldconfig` หรือ `sudo ln -sf libpysgfplib.so.1.0.1.fdu03_rename libpysgfplib.so`
- `sudo cd ../...make uninstall install`

# installation
1. ติดตั้ง dependency
    - `sudo apt install libcairo2-dev pkg-config python3-dev` dependency ของ KivyMD ต้องใช้ pycairo
    - `sudo apt install build-essential meson ninja-build cmake libusb-0.1-4 libusb-dev python3-picamera2` build tools ช่วยลดปัญหา package compile
2. สร้าง Virtual Environment (venv) `python3 -m venv venv --system-site-packages` และ activate
    - Linux / macOS / Raspberry Pi	`source venv/bin/activate`
    - Windows cmd `venv\Scripts\activate.bat`
    - freeze lib `pip freeze > requirements.txt`

3. ติดตั้ง lib อื่น ๆ :  `pip install -r requirements.txt`

Note:
Also you can install manually from sources. Just clone the project and run pip:
- `git clone https://github.com/kivymd/KivyMD.git --depth 1`
- `cd KivyMD`
- `pip install .`

4. สร้าง environment variable file `.env` สำหรับ storing secret key และ other configuration
    - `cp .env.example .env`
    - `nano .env`

# installation fingerprint library
1. `cd lib/pi`
2. `sudo cp libpysgfplib.so.1.0.1.fdu05_rename libpysgfplib.so`
3. `sudo make uninstall install`

Fix USB permission
<!-- USB permission fix for SecuGen fingerprint scanner -->
<!-- Create SecuGen group and add current user to it -->
- `sudo groupadd SecuGen`
- `sudo usermod -a -G SecuGen $USER`
<!-- Copy udev rules file to system directory -->
- `sudo nano /etc/udev/rules.d/99-piSecuGen.rules`
<!-- Reload udev rules and trigger device re-detection -->
-
```
    ATTRS{idVendor}=="1162", ATTRS{idProduct}=="0320", SYMLINK+="input/fdu03-%k", MODE="0660", GROUP="SecuGen"
    ATTRS{idVendor}=="1162", ATTRS{idProduct}=="0322", SYMLINK+="input/sdu03m-%k", MODE="0660", GROUP="SecuGen"
    ATTRS{idVendor}=="1162", ATTRS{idProduct}=="0330", SYMLINK+="input/fdu04-%k", MODE="0660", GROUP="SecuGen"
    ATTRS{idVendor}=="1162", ATTRS{idProduct}=="1000", SYMLINK+="input/sdu03p-%k", MODE="0660", GROUP="SecuGen"
    ATTRS{idVendor}=="1162", ATTRS{idProduct}=="2000", SYMLINK+="input/sdu04p-%k", MODE="0660", GROUP="SecuGen"
    ATTRS{idVendor}=="1162", ATTRS{idProduct}=="2200", SYMLINK+="input/sdu05-%k", MODE="0660", GROUP="SecuGen"
    KERNEL=="uinput", MODE="0660", GROUP="SecuGen"
```
4. `sudo reboot`
5. compile binary file 
    - `cd sgfplibtest`
    - `make -f Makefile.fingerprint` then got `finger_scan` in `../bin/pi/`
    - move `finger_scan` to root/bin by `sudo mv bin/pi/finger_scan {path_to_root}/bin/`

6. test binary file by go to root/bin and run `./finger_scan`

# other
- Check detection: `lsusb`
- use GPIO `pip install RPi.GPIO`

ถูกตัดออก (ไม่ได้ import อีกต่อไป)
Watchdog, DeviceManager, KioskController, SessionManager, UIEventAdapter, REST API, FingerprintService

$U/B,L/007,H/050,T/0234