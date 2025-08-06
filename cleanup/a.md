🎯 Final optimized build test...
#0 building with "default" instance using docker driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 733B done
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.10-slim-bullseye
#2 DONE 0.6s

#3 [internal] load .dockerignore
#3 transferring context: 1.04kB done
#3 DONE 0.0s

#4 [1/9] FROM docker.io/library/python:3.10-slim-bullseye@sha256:f1fb49e4d5501ac93d0ca519fb7ee6250842245aba8612926a46a0832a1ed089
#4 resolve docker.io/library/python:3.10-slim-bullseye@sha256:f1fb49e4d5501ac93d0ca519fb7ee6250842245aba8612926a46a0832a1ed089 0.0s done
#4 CACHED

#5 [internal] load build context
#5 transferring context: 59.96kB 0.0s done
#5 DONE 0.0s

#6 [2/9] COPY ./requirements.common.txt /tmp/
#6 DONE 0.0s

#7 [3/9] RUN pip install --no-cache-dir -r /tmp/requirements.common.txt
#7 1.350 Collecting psutil>=5.9.0
#7 1.448   Downloading psutil-7.0.0-cp36-abi3-manylinux_2_12_x86_64.manylinux2010_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl (277 kB)
#7 1.540      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 278.0/278.0 kB 3.0 MB/s eta 0:00:00
#7 1.988 Collecting pyzmq>=25.0.0
#7 2.021   Downloading pyzmq-27.0.1-cp310-cp310-manylinux_2_26_x86_64.manylinux_2_28_x86_64.whl (853 kB)
#7 2.095      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 853.8/853.8 kB 11.8 MB/s eta 0:00:00
#7 2.310 Collecting pydantic>=2.0.0
#7 2.341   Downloading pydantic-2.11.7-py3-none-any.whl (444 kB)
#7 2.379      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 444.8/444.8 kB 12.5 MB/s eta 0:00:00
#7 2.443 Collecting typing-extensions>=4.12.2
#7 2.474   Downloading typing_extensions-4.14.1-py3-none-any.whl (43 kB)
#7 2.478      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 43.9/43.9 kB 32.0 MB/s eta 0:00:00
#7 2.490 Collecting typing-inspection>=0.4.0
#7 2.523   Downloading typing_inspection-0.4.1-py3-none-any.whl (14 kB)
#7 3.796 Collecting pydantic-core==2.33.2
#7 3.842   Downloading pydantic_core-2.33.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.0 MB)
#7 3.997      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.0/2.0 MB 13.0 MB/s eta 0:00:00
#7 4.012 Collecting annotated-types>=0.6.0
#7 4.044   Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
#7 4.112 Installing collected packages: typing-extensions, pyzmq, psutil, annotated-types, typing-inspection, pydantic-core, pydantic
#7 4.525 Successfully installed annotated-types-0.7.0 psutil-7.0.0 pydantic-2.11.7 pydantic-core-2.33.2 pyzmq-27.0.1 typing-extensions-4.14.1 typing-inspection-0.4.1
#7 4.525 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv
#7 4.589 
#7 4.589 [notice] A new release of pip is available: 23.0.1 -> 25.2
#7 4.589 [notice] To update, run: pip install --upgrade pip
#7 DONE 4.8s

#8 [4/9] RUN apt-get update && apt-get install -y --no-install-recommends curl gcc build-essential     && rm -rf /var/lib/apt/lists/*
#8 0.462 Get:1 http://deb.debian.org/debian bullseye InRelease [116 kB]
#8 0.479 Get:2 http://deb.debian.org/debian-security bullseye-security InRelease [27.2 kB]
#8 0.482 Get:3 http://deb.debian.org/debian bullseye-updates InRelease [44.0 kB]
#8 0.561 Get:4 http://deb.debian.org/debian bullseye/main amd64 Packages [8066 kB]
#8 1.265 Get:5 http://deb.debian.org/debian-security bullseye-security/main amd64 Packages [389 kB]
#8 1.301 Get:6 http://deb.debian.org/debian bullseye-updates/main amd64 Packages [18.8 kB]
#8 1.908 Fetched 8661 kB in 1s (5921 kB/s)
#8 1.908 Reading package lists...
#8 2.194 Reading package lists...
#8 2.480 Building dependency tree...
#8 2.561 Reading state information...
#8 2.629 The following additional packages will be installed:
#8 2.629   binutils binutils-common binutils-x86-64-linux-gnu bzip2 cpp cpp-10 dpkg-dev
#8 2.629   g++ g++-10 gcc-10 libasan6 libatomic1 libbinutils libbrotli1 libc-dev-bin
#8 2.629   libc6-dev libcc1-0 libcrypt-dev libctf-nobfd0 libctf0 libcurl4 libdpkg-perl
#8 2.629   libgcc-10-dev libgdbm-compat4 libgomp1 libisl23 libitm1 libldap-2.4-2
#8 2.629   liblsan0 libmpc3 libmpfr6 libnghttp2-14 libnsl-dev libperl5.32 libpsl5
#8 2.629   libquadmath0 librtmp1 libsasl2-2 libsasl2-modules-db libssh2-1
#8 2.629   libstdc++-10-dev libtirpc-dev libtsan0 libubsan1 linux-libc-dev make patch
#8 2.629   perl perl-modules-5.32 xz-utils
#8 2.629 Suggested packages:
#8 2.629   binutils-doc bzip2-doc cpp-doc gcc-10-locales debian-keyring g++-multilib
#8 2.629   g++-10-multilib gcc-10-doc gcc-multilib manpages-dev autoconf automake
#8 2.629   libtool flex bison gdb gcc-doc gcc-10-multilib glibc-doc gnupg
#8 2.629   sensible-utils git bzr libstdc++-10-doc make-doc ed diffutils-doc perl-doc
#8 2.629   libterm-readline-gnu-perl | libterm-readline-perl-perl
#8 2.629   libtap-harness-archive-perl
#8 2.629 Recommended packages:
#8 2.629   fakeroot gnupg libalgorithm-merge-perl manpages manpages-dev libc-devtools
#8 2.629   libfile-fcntllock-perl liblocale-gettext-perl libldap-common publicsuffix
#8 2.629   libsasl2-modules
#8 2.758 The following NEW packages will be installed:
#8 2.758   binutils binutils-common binutils-x86-64-linux-gnu build-essential bzip2 cpp
#8 2.758   cpp-10 curl dpkg-dev g++ g++-10 gcc gcc-10 libasan6 libatomic1 libbinutils
#8 2.758   libbrotli1 libc-dev-bin libc6-dev libcc1-0 libcrypt-dev libctf-nobfd0
#8 2.758   libctf0 libcurl4 libdpkg-perl libgcc-10-dev libgdbm-compat4 libgomp1
#8 2.758   libisl23 libitm1 libldap-2.4-2 liblsan0 libmpc3 libmpfr6 libnghttp2-14
#8 2.758   libnsl-dev libperl5.32 libpsl5 libquadmath0 librtmp1 libsasl2-2
#8 2.758   libsasl2-modules-db libssh2-1 libstdc++-10-dev libtirpc-dev libtsan0
#8 2.759   libubsan1 linux-libc-dev make patch perl perl-modules-5.32 xz-utils
#8 2.783 0 upgraded, 53 newly installed, 0 to remove and 2 not upgraded.
#8 2.783 Need to get 71.0 MB of archives.
#8 2.783 After this operation, 279 MB of additional disk space will be used.
#8 2.783 Get:1 http://deb.debian.org/debian-security bullseye-security/main amd64 perl-modules-5.32 all 5.32.1-4+deb11u4 [2824 kB]
#8 3.038 Get:2 http://deb.debian.org/debian bullseye/main amd64 libgdbm-compat4 amd64 1.19-2 [44.7 kB]
#8 3.042 Get:3 http://deb.debian.org/debian-security bullseye-security/main amd64 libperl5.32 amd64 5.32.1-4+deb11u4 [4132 kB]
#8 3.407 Get:4 http://deb.debian.org/debian-security bullseye-security/main amd64 perl amd64 5.32.1-4+deb11u4 [293 kB]
#8 3.432 Get:5 http://deb.debian.org/debian bullseye/main amd64 bzip2 amd64 1.0.8-4 [49.3 kB]
#8 3.436 Get:6 http://deb.debian.org/debian bullseye/main amd64 xz-utils amd64 5.2.5-2.1~deb11u1 [220 kB]
#8 3.455 Get:7 http://deb.debian.org/debian bullseye/main amd64 binutils-common amd64 2.35.2-2 [2220 kB]
#8 3.644 Get:8 http://deb.debian.org/debian bullseye/main amd64 libbinutils amd64 2.35.2-2 [570 kB]
#8 3.691 Get:9 http://deb.debian.org/debian bullseye/main amd64 libctf-nobfd0 amd64 2.35.2-2 [110 kB]
#8 3.700 Get:10 http://deb.debian.org/debian bullseye/main amd64 libctf0 amd64 2.35.2-2 [53.2 kB]
#8 3.706 Get:11 http://deb.debian.org/debian bullseye/main amd64 binutils-x86-64-linux-gnu amd64 2.35.2-2 [1809 kB]
#8 3.858 Get:12 http://deb.debian.org/debian bullseye/main amd64 binutils amd64 2.35.2-2 [61.2 kB]
#8 3.864 Get:13 http://deb.debian.org/debian-security bullseye-security/main amd64 libc-dev-bin amd64 2.31-13+deb11u13 [277 kB]
#8 3.887 Get:14 http://deb.debian.org/debian-security bullseye-security/main amd64 linux-libc-dev amd64 5.10.237-1 [1820 kB]
#8 4.042 Get:15 http://deb.debian.org/debian bullseye/main amd64 libcrypt-dev amd64 1:4.4.18-4 [104 kB]
#8 4.051 Get:16 http://deb.debian.org/debian bullseye/main amd64 libtirpc-dev amd64 1.3.1-1+deb11u1 [191 kB]
#8 4.068 Get:17 http://deb.debian.org/debian bullseye/main amd64 libnsl-dev amd64 1.3.0-2 [66.4 kB]
#8 4.073 Get:18 http://deb.debian.org/debian-security bullseye-security/main amd64 libc6-dev amd64 2.31-13+deb11u13 [2362 kB]
#8 4.274 Get:19 http://deb.debian.org/debian bullseye/main amd64 libisl23 amd64 0.23-1 [676 kB]
#8 4.330 Get:20 http://deb.debian.org/debian bullseye/main amd64 libmpfr6 amd64 4.1.0-3 [2012 kB]
#8 4.502 Get:21 http://deb.debian.org/debian bullseye/main amd64 libmpc3 amd64 1.2.0-1 [45.0 kB]
#8 4.505 Get:22 http://deb.debian.org/debian bullseye/main amd64 cpp-10 amd64 10.2.1-6 [8528 kB]
#8 5.231 Get:23 http://deb.debian.org/debian bullseye/main amd64 cpp amd64 4:10.2.1-1 [19.7 kB]
#8 5.232 Get:24 http://deb.debian.org/debian bullseye/main amd64 libcc1-0 amd64 10.2.1-6 [47.0 kB]
#8 5.236 Get:25 http://deb.debian.org/debian bullseye/main amd64 libgomp1 amd64 10.2.1-6 [99.9 kB]
#8 5.249 Get:26 http://deb.debian.org/debian bullseye/main amd64 libitm1 amd64 10.2.1-6 [25.8 kB]
#8 5.279 Get:27 http://deb.debian.org/debian bullseye/main amd64 libatomic1 amd64 10.2.1-6 [9008 B]
#8 5.279 Get:28 http://deb.debian.org/debian bullseye/main amd64 libasan6 amd64 10.2.1-6 [2065 kB]
#8 5.423 Get:29 http://deb.debian.org/debian bullseye/main amd64 liblsan0 amd64 10.2.1-6 [828 kB]
#8 5.494 Get:30 http://deb.debian.org/debian bullseye/main amd64 libtsan0 amd64 10.2.1-6 [2000 kB]
#8 5.664 Get:31 http://deb.debian.org/debian bullseye/main amd64 libubsan1 amd64 10.2.1-6 [777 kB]
#8 5.730 Get:32 http://deb.debian.org/debian bullseye/main amd64 libquadmath0 amd64 10.2.1-6 [145 kB]
#8 5.744 Get:33 http://deb.debian.org/debian bullseye/main amd64 libgcc-10-dev amd64 10.2.1-6 [2328 kB]
#8 5.942 Get:34 http://deb.debian.org/debian bullseye/main amd64 gcc-10 amd64 10.2.1-6 [17.0 MB]
#8 7.560 Get:35 http://deb.debian.org/debian bullseye/main amd64 gcc amd64 4:10.2.1-1 [5192 B]
#8 7.560 Get:36 http://deb.debian.org/debian bullseye/main amd64 libstdc++-10-dev amd64 10.2.1-6 [1741 kB]
#8 7.659 Get:37 http://deb.debian.org/debian bullseye/main amd64 g++-10 amd64 10.2.1-6 [9380 kB]
#8 8.343 Get:38 http://deb.debian.org/debian bullseye/main amd64 g++ amd64 4:10.2.1-1 [1644 B]
#8 8.343 Get:39 http://deb.debian.org/debian bullseye/main amd64 make amd64 4.3-4.1 [396 kB]
#8 8.398 Get:40 http://deb.debian.org/debian bullseye/main amd64 libdpkg-perl all 1.20.13 [1552 kB]
#8 8.509 Get:41 http://deb.debian.org/debian bullseye/main amd64 patch amd64 2.7.6-7 [128 kB]
#8 8.520 Get:42 http://deb.debian.org/debian bullseye/main amd64 dpkg-dev all 1.20.13 [2314 kB]
#8 8.718 Get:43 http://deb.debian.org/debian bullseye/main amd64 build-essential amd64 12.9 [7704 B]
#8 8.718 Get:44 http://deb.debian.org/debian bullseye/main amd64 libbrotli1 amd64 1.0.9-2+b2 [279 kB]
#8 8.743 Get:45 http://deb.debian.org/debian bullseye/main amd64 libsasl2-modules-db amd64 2.1.27+dfsg-2.1+deb11u1 [69.1 kB]
#8 8.748 Get:46 http://deb.debian.org/debian bullseye/main amd64 libsasl2-2 amd64 2.1.27+dfsg-2.1+deb11u1 [106 kB]
#8 8.757 Get:47 http://deb.debian.org/debian bullseye/main amd64 libldap-2.4-2 amd64 2.4.57+dfsg-3+deb11u1 [232 kB]
#8 8.777 Get:48 http://deb.debian.org/debian-security bullseye-security/main amd64 libnghttp2-14 amd64 1.43.0-1+deb11u2 [77.0 kB]
#8 8.784 Get:49 http://deb.debian.org/debian bullseye/main amd64 libpsl5 amd64 0.21.0-1.2 [57.3 kB]
#8 8.790 Get:50 http://deb.debian.org/debian bullseye/main amd64 librtmp1 amd64 2.4+20151223.gitfa8646d.1-2+b2 [60.8 kB]
#8 8.793 Get:51 http://deb.debian.org/debian bullseye/main amd64 libssh2-1 amd64 1.9.0-2+deb11u1 [156 kB]
#8 8.807 Get:52 http://deb.debian.org/debian-security bullseye-security/main amd64 libcurl4 amd64 7.74.0-1.3+deb11u15 [347 kB]
#8 8.838 Get:53 http://deb.debian.org/debian-security bullseye-security/main amd64 curl amd64 7.74.0-1.3+deb11u15 [272 kB]
#8 8.932 debconf: delaying package configuration, since apt-utils is not installed
#8 8.954 Fetched 71.0 MB in 6s (11.6 MB/s)
#8 8.971 Selecting previously unselected package perl-modules-5.32.
#8 8.971 (Reading database ... 
(Reading database ... 5%
(Reading database ... 10%
(Reading database ... 15%
(Reading database ... 20%
(Reading database ... 25%
(Reading database ... 30%
(Reading database ... 35%
(Reading database ... 40%
(Reading database ... 45%
(Reading database ... 50%
(Reading database ... 55%
(Reading database ... 60%
(Reading database ... 65%
(Reading database ... 70%
(Reading database ... 75%
(Reading database ... 80%
(Reading database ... 85%
(Reading database ... 90%
(Reading database ... 95%
(Reading database ... 100%
(Reading database ... 7034 files and directories currently installed.)
#8 8.974 Preparing to unpack .../00-perl-modules-5.32_5.32.1-4+deb11u4_all.deb ...
#8 8.978 Unpacking perl-modules-5.32 (5.32.1-4+deb11u4) ...
#8 9.314 Selecting previously unselected package libgdbm-compat4:amd64.
#8 9.315 Preparing to unpack .../01-libgdbm-compat4_1.19-2_amd64.deb ...
#8 9.322 Unpacking libgdbm-compat4:amd64 (1.19-2) ...
#8 9.353 Selecting previously unselected package libperl5.32:amd64.
#8 9.354 Preparing to unpack .../02-libperl5.32_5.32.1-4+deb11u4_amd64.deb ...
#8 9.358 Unpacking libperl5.32:amd64 (5.32.1-4+deb11u4) ...
#8 9.727 Selecting previously unselected package perl.
#8 9.728 Preparing to unpack .../03-perl_5.32.1-4+deb11u4_amd64.deb ...
#8 9.736 Unpacking perl (5.32.1-4+deb11u4) ...
#8 9.779 Selecting previously unselected package bzip2.
#8 9.780 Preparing to unpack .../04-bzip2_1.0.8-4_amd64.deb ...
#8 9.783 Unpacking bzip2 (1.0.8-4) ...
#8 9.813 Selecting previously unselected package xz-utils.
#8 9.814 Preparing to unpack .../05-xz-utils_5.2.5-2.1~deb11u1_amd64.deb ...
#8 9.818 Unpacking xz-utils (5.2.5-2.1~deb11u1) ...
#8 9.850 Selecting previously unselected package binutils-common:amd64.
#8 9.851 Preparing to unpack .../06-binutils-common_2.35.2-2_amd64.deb ...
#8 9.855 Unpacking binutils-common:amd64 (2.35.2-2) ...
#8 10.04 Selecting previously unselected package libbinutils:amd64.
#8 10.04 Preparing to unpack .../07-libbinutils_2.35.2-2_amd64.deb ...
#8 10.04 Unpacking libbinutils:amd64 (2.35.2-2) ...
#8 10.11 Selecting previously unselected package libctf-nobfd0:amd64.
#8 10.11 Preparing to unpack .../08-libctf-nobfd0_2.35.2-2_amd64.deb ...
#8 10.11 Unpacking libctf-nobfd0:amd64 (2.35.2-2) ...
#8 10.15 Selecting previously unselected package libctf0:amd64.
#8 10.15 Preparing to unpack .../09-libctf0_2.35.2-2_amd64.deb ...
#8 10.15 Unpacking libctf0:amd64 (2.35.2-2) ...
#8 10.18 Selecting previously unselected package binutils-x86-64-linux-gnu.
#8 10.18 Preparing to unpack .../10-binutils-x86-64-linux-gnu_2.35.2-2_amd64.deb ...
#8 10.18 Unpacking binutils-x86-64-linux-gnu (2.35.2-2) ...
#8 10.33 Selecting previously unselected package binutils.
#8 10.34 Preparing to unpack .../11-binutils_2.35.2-2_amd64.deb ...
#8 10.34 Unpacking binutils (2.35.2-2) ...
#8 10.37 Selecting previously unselected package libc-dev-bin.
#8 10.37 Preparing to unpack .../12-libc-dev-bin_2.31-13+deb11u13_amd64.deb ...
#8 10.37 Unpacking libc-dev-bin (2.31-13+deb11u13) ...
#8 10.40 Selecting previously unselected package linux-libc-dev:amd64.
#8 10.40 Preparing to unpack .../13-linux-libc-dev_5.10.237-1_amd64.deb ...
#8 10.40 Unpacking linux-libc-dev:amd64 (5.10.237-1) ...
#8 10.55 Selecting previously unselected package libcrypt-dev:amd64.
#8 10.56 Preparing to unpack .../14-libcrypt-dev_1%3a4.4.18-4_amd64.deb ...
#8 10.56 Unpacking libcrypt-dev:amd64 (1:4.4.18-4) ...
#8 10.59 Selecting previously unselected package libtirpc-dev:amd64.
#8 10.59 Preparing to unpack .../15-libtirpc-dev_1.3.1-1+deb11u1_amd64.deb ...
#8 10.59 Unpacking libtirpc-dev:amd64 (1.3.1-1+deb11u1) ...
#8 10.63 Selecting previously unselected package libnsl-dev:amd64.
#8 10.63 Preparing to unpack .../16-libnsl-dev_1.3.0-2_amd64.deb ...
#8 10.63 Unpacking libnsl-dev:amd64 (1.3.0-2) ...
#8 10.66 Selecting previously unselected package libc6-dev:amd64.
#8 10.66 Preparing to unpack .../17-libc6-dev_2.31-13+deb11u13_amd64.deb ...
#8 10.66 Unpacking libc6-dev:amd64 (2.31-13+deb11u13) ...
#8 10.89 Selecting previously unselected package libisl23:amd64.
#8 10.89 Preparing to unpack .../18-libisl23_0.23-1_amd64.deb ...
#8 10.90 Unpacking libisl23:amd64 (0.23-1) ...
#8 10.97 Selecting previously unselected package libmpfr6:amd64.
#8 10.97 Preparing to unpack .../19-libmpfr6_4.1.0-3_amd64.deb ...
#8 10.97 Unpacking libmpfr6:amd64 (4.1.0-3) ...
#8 11.07 Selecting previously unselected package libmpc3:amd64.
#8 11.07 Preparing to unpack .../20-libmpc3_1.2.0-1_amd64.deb ...
#8 11.07 Unpacking libmpc3:amd64 (1.2.0-1) ...
#8 11.10 Selecting previously unselected package cpp-10.
#8 11.10 Preparing to unpack .../21-cpp-10_10.2.1-6_amd64.deb ...
#8 11.10 Unpacking cpp-10 (10.2.1-6) ...
#8 11.63 Selecting previously unselected package cpp.
#8 11.63 Preparing to unpack .../22-cpp_4%3a10.2.1-1_amd64.deb ...
#8 11.63 Unpacking cpp (4:10.2.1-1) ...
#8 11.69 Selecting previously unselected package libcc1-0:amd64.
#8 11.69 Preparing to unpack .../23-libcc1-0_10.2.1-6_amd64.deb ...
#8 11.69 Unpacking libcc1-0:amd64 (10.2.1-6) ...
#8 11.72 Selecting previously unselected package libgomp1:amd64.
#8 11.72 Preparing to unpack .../24-libgomp1_10.2.1-6_amd64.deb ...
#8 11.73 Unpacking libgomp1:amd64 (10.2.1-6) ...
#8 11.76 Selecting previously unselected package libitm1:amd64.
#8 11.76 Preparing to unpack .../25-libitm1_10.2.1-6_amd64.deb ...
#8 11.77 Unpacking libitm1:amd64 (10.2.1-6) ...
#8 11.80 Selecting previously unselected package libatomic1:amd64.
#8 11.80 Preparing to unpack .../26-libatomic1_10.2.1-6_amd64.deb ...
#8 11.80 Unpacking libatomic1:amd64 (10.2.1-6) ...
#8 11.83 Selecting previously unselected package libasan6:amd64.
#8 11.83 Preparing to unpack .../27-libasan6_10.2.1-6_amd64.deb ...
#8 11.84 Unpacking libasan6:amd64 (10.2.1-6) ...
#8 12.00 Selecting previously unselected package liblsan0:amd64.
#8 12.00 Preparing to unpack .../28-liblsan0_10.2.1-6_amd64.deb ...
#8 12.01 Unpacking liblsan0:amd64 (10.2.1-6) ...
#8 12.10 Selecting previously unselected package libtsan0:amd64.
#8 12.10 Preparing to unpack .../29-libtsan0_10.2.1-6_amd64.deb ...
#8 12.10 Unpacking libtsan0:amd64 (10.2.1-6) ...
#8 12.27 Selecting previously unselected package libubsan1:amd64.
#8 12.27 Preparing to unpack .../30-libubsan1_10.2.1-6_amd64.deb ...
#8 12.28 Unpacking libubsan1:amd64 (10.2.1-6) ...
#8 12.35 Selecting previously unselected package libquadmath0:amd64.
#8 12.36 Preparing to unpack .../31-libquadmath0_10.2.1-6_amd64.deb ...
#8 12.36 Unpacking libquadmath0:amd64 (10.2.1-6) ...
#8 12.39 Selecting previously unselected package libgcc-10-dev:amd64.
#8 12.39 Preparing to unpack .../32-libgcc-10-dev_10.2.1-6_amd64.deb ...
#8 12.40 Unpacking libgcc-10-dev:amd64 (10.2.1-6) ...
#8 12.57 Selecting previously unselected package gcc-10.
#8 12.57 Preparing to unpack .../33-gcc-10_10.2.1-6_amd64.deb ...
#8 12.57 Unpacking gcc-10 (10.2.1-6) ...
#8 13.60 Selecting previously unselected package gcc.
#8 13.60 Preparing to unpack .../34-gcc_4%3a10.2.1-1_amd64.deb ...
#8 13.61 Unpacking gcc (4:10.2.1-1) ...
#8 13.63 Selecting previously unselected package libstdc++-10-dev:amd64.
#8 13.63 Preparing to unpack .../35-libstdc++-10-dev_10.2.1-6_amd64.deb ...
#8 13.64 Unpacking libstdc++-10-dev:amd64 (10.2.1-6) ...
#8 13.84 Selecting previously unselected package g++-10.
#8 13.84 Preparing to unpack .../36-g++-10_10.2.1-6_amd64.deb ...
#8 13.84 Unpacking g++-10 (10.2.1-6) ...
#8 14.41 Selecting previously unselected package g++.
#8 14.42 Preparing to unpack .../37-g++_4%3a10.2.1-1_amd64.deb ...
#8 14.42 Unpacking g++ (4:10.2.1-1) ...
#8 14.44 Selecting previously unselected package make.
#8 14.44 Preparing to unpack .../38-make_4.3-4.1_amd64.deb ...
#8 14.45 Unpacking make (4.3-4.1) ...
#8 14.49 Selecting previously unselected package libdpkg-perl.
#8 14.50 Preparing to unpack .../39-libdpkg-perl_1.20.13_all.deb ...
#8 14.50 Unpacking libdpkg-perl (1.20.13) ...
#8 14.56 Selecting previously unselected package patch.
#8 14.56 Preparing to unpack .../40-patch_2.7.6-7_amd64.deb ...
#8 14.57 Unpacking patch (2.7.6-7) ...
#8 14.61 Selecting previously unselected package dpkg-dev.
#8 14.61 Preparing to unpack .../41-dpkg-dev_1.20.13_all.deb ...
#8 14.61 Unpacking dpkg-dev (1.20.13) ...
#8 14.70 Selecting previously unselected package build-essential.
#8 14.70 Preparing to unpack .../42-build-essential_12.9_amd64.deb ...
#8 14.71 Unpacking build-essential (12.9) ...
#8 14.74 Selecting previously unselected package libbrotli1:amd64.
#8 14.74 Preparing to unpack .../43-libbrotli1_1.0.9-2+b2_amd64.deb ...
#8 14.74 Unpacking libbrotli1:amd64 (1.0.9-2+b2) ...
#8 14.79 Selecting previously unselected package libsasl2-modules-db:amd64.
#8 14.79 Preparing to unpack .../44-libsasl2-modules-db_2.1.27+dfsg-2.1+deb11u1_amd64.deb ...
#8 14.79 Unpacking libsasl2-modules-db:amd64 (2.1.27+dfsg-2.1+deb11u1) ...
#8 14.82 Selecting previously unselected package libsasl2-2:amd64.
#8 14.82 Preparing to unpack .../45-libsasl2-2_2.1.27+dfsg-2.1+deb11u1_amd64.deb ...
#8 14.83 Unpacking libsasl2-2:amd64 (2.1.27+dfsg-2.1+deb11u1) ...
#8 14.86 Selecting previously unselected package libldap-2.4-2:amd64.
#8 14.86 Preparing to unpack .../46-libldap-2.4-2_2.4.57+dfsg-3+deb11u1_amd64.deb ...
#8 14.87 Unpacking libldap-2.4-2:amd64 (2.4.57+dfsg-3+deb11u1) ...
#8 14.91 Selecting previously unselected package libnghttp2-14:amd64.
#8 14.91 Preparing to unpack .../47-libnghttp2-14_1.43.0-1+deb11u2_amd64.deb ...
#8 14.91 Unpacking libnghttp2-14:amd64 (1.43.0-1+deb11u2) ...
#8 14.94 Selecting previously unselected package libpsl5:amd64.
#8 14.95 Preparing to unpack .../48-libpsl5_0.21.0-1.2_amd64.deb ...
#8 14.95 Unpacking libpsl5:amd64 (0.21.0-1.2) ...
#8 14.98 Selecting previously unselected package librtmp1:amd64.
#8 14.99 Preparing to unpack .../49-librtmp1_2.4+20151223.gitfa8646d.1-2+b2_amd64.deb ...
#8 14.99 Unpacking librtmp1:amd64 (2.4+20151223.gitfa8646d.1-2+b2) ...
#8 15.03 Selecting previously unselected package libssh2-1:amd64.
#8 15.03 Preparing to unpack .../50-libssh2-1_1.9.0-2+deb11u1_amd64.deb ...
#8 15.03 Unpacking libssh2-1:amd64 (1.9.0-2+deb11u1) ...
#8 15.08 Selecting previously unselected package libcurl4:amd64.
#8 15.08 Preparing to unpack .../51-libcurl4_7.74.0-1.3+deb11u15_amd64.deb ...
#8 15.08 Unpacking libcurl4:amd64 (7.74.0-1.3+deb11u15) ...
#8 15.13 Selecting previously unselected package curl.
#8 15.13 Preparing to unpack .../52-curl_7.74.0-1.3+deb11u15_amd64.deb ...
#8 15.13 Unpacking curl (7.74.0-1.3+deb11u15) ...
#8 15.18 Setting up libpsl5:amd64 (0.21.0-1.2) ...
#8 15.19 Setting up perl-modules-5.32 (5.32.1-4+deb11u4) ...
#8 15.20 Setting up libbrotli1:amd64 (1.0.9-2+b2) ...
#8 15.21 Setting up binutils-common:amd64 (2.35.2-2) ...
#8 15.22 Setting up libnghttp2-14:amd64 (1.43.0-1+deb11u2) ...
#8 15.23 Setting up linux-libc-dev:amd64 (5.10.237-1) ...
#8 15.24 Setting up libctf-nobfd0:amd64 (2.35.2-2) ...
#8 15.25 Setting up libgomp1:amd64 (10.2.1-6) ...
#8 15.26 Setting up bzip2 (1.0.8-4) ...
#8 15.27 Setting up libasan6:amd64 (10.2.1-6) ...
#8 15.28 Setting up libsasl2-modules-db:amd64 (2.1.27+dfsg-2.1+deb11u1) ...
#8 15.29 Setting up libtirpc-dev:amd64 (1.3.1-1+deb11u1) ...
#8 15.30 Setting up make (4.3-4.1) ...
#8 15.31 Setting up libmpfr6:amd64 (4.1.0-3) ...
#8 15.32 Setting up librtmp1:amd64 (2.4+20151223.gitfa8646d.1-2+b2) ...
#8 15.33 Setting up xz-utils (5.2.5-2.1~deb11u1) ...
#8 15.34 update-alternatives: using /usr/bin/xz to provide /usr/bin/lzma (lzma) in auto mode
#8 15.34 update-alternatives: warning: skip creation of /usr/share/man/man1/lzma.1.gz because associated file /usr/share/man/man1/xz.1.gz (of link group lzma) doesn't exist
#8 15.34 update-alternatives: warning: skip creation of /usr/share/man/man1/unlzma.1.gz because associated file /usr/share/man/man1/unxz.1.gz (of link group lzma) doesn't exist
#8 15.34 update-alternatives: warning: skip creation of /usr/share/man/man1/lzcat.1.gz because associated file /usr/share/man/man1/xzcat.1.gz (of link group lzma) doesn't exist
#8 15.34 update-alternatives: warning: skip creation of /usr/share/man/man1/lzmore.1.gz because associated file /usr/share/man/man1/xzmore.1.gz (of link group lzma) doesn't exist
#8 15.34 update-alternatives: warning: skip creation of /usr/share/man/man1/lzless.1.gz because associated file /usr/share/man/man1/xzless.1.gz (of link group lzma) doesn't exist
#8 15.34 update-alternatives: warning: skip creation of /usr/share/man/man1/lzdiff.1.gz because associated file /usr/share/man/man1/xzdiff.1.gz (of link group lzma) doesn't exist
#8 15.34 update-alternatives: warning: skip creation of /usr/share/man/man1/lzcmp.1.gz because associated file /usr/share/man/man1/xzcmp.1.gz (of link group lzma) doesn't exist
#8 15.34 update-alternatives: warning: skip creation of /usr/share/man/man1/lzgrep.1.gz because associated file /usr/share/man/man1/xzgrep.1.gz (of link group lzma) doesn't exist
#8 15.34 update-alternatives: warning: skip creation of /usr/share/man/man1/lzegrep.1.gz because associated file /usr/share/man/man1/xzegrep.1.gz (of link group lzma) doesn't exist
#8 15.34 update-alternatives: warning: skip creation of /usr/share/man/man1/lzfgrep.1.gz because associated file /usr/share/man/man1/xzfgrep.1.gz (of link group lzma) doesn't exist
#8 15.35 Setting up libquadmath0:amd64 (10.2.1-6) ...
#8 15.36 Setting up libmpc3:amd64 (1.2.0-1) ...
#8 15.36 Setting up libatomic1:amd64 (10.2.1-6) ...
#8 15.38 Setting up patch (2.7.6-7) ...
#8 15.38 Setting up libgdbm-compat4:amd64 (1.19-2) ...
#8 15.39 Setting up libperl5.32:amd64 (5.32.1-4+deb11u4) ...
#8 15.40 Setting up libsasl2-2:amd64 (2.1.27+dfsg-2.1+deb11u1) ...
#8 15.42 Setting up libubsan1:amd64 (10.2.1-6) ...
#8 15.43 Setting up libnsl-dev:amd64 (1.3.0-2) ...
#8 15.44 Setting up libcrypt-dev:amd64 (1:4.4.18-4) ...
#8 15.45 Setting up libssh2-1:amd64 (1.9.0-2+deb11u1) ...
#8 15.46 Setting up libbinutils:amd64 (2.35.2-2) ...
#8 15.47 Setting up libisl23:amd64 (0.23-1) ...
#8 15.48 Setting up libc-dev-bin (2.31-13+deb11u13) ...
#8 15.49 Setting up libcc1-0:amd64 (10.2.1-6) ...
#8 15.50 Setting up liblsan0:amd64 (10.2.1-6) ...
#8 15.51 Setting up cpp-10 (10.2.1-6) ...
#8 15.52 Setting up libitm1:amd64 (10.2.1-6) ...
#8 15.53 Setting up libtsan0:amd64 (10.2.1-6) ...
#8 15.54 Setting up libctf0:amd64 (2.35.2-2) ...
#8 15.56 Setting up libgcc-10-dev:amd64 (10.2.1-6) ...
#8 15.57 Setting up libldap-2.4-2:amd64 (2.4.57+dfsg-3+deb11u1) ...
#8 15.58 Setting up perl (5.32.1-4+deb11u4) ...
#8 15.59 Setting up libdpkg-perl (1.20.13) ...
#8 15.60 Setting up cpp (4:10.2.1-1) ...
#8 15.62 Setting up libcurl4:amd64 (7.74.0-1.3+deb11u15) ...
#8 15.63 Setting up libc6-dev:amd64 (2.31-13+deb11u13) ...
#8 15.64 Setting up curl (7.74.0-1.3+deb11u15) ...
#8 15.65 Setting up binutils-x86-64-linux-gnu (2.35.2-2) ...
#8 15.66 Setting up libstdc++-10-dev:amd64 (10.2.1-6) ...
#8 15.67 Setting up binutils (2.35.2-2) ...
#8 15.68 Setting up dpkg-dev (1.20.13) ...
#8 15.70 Setting up gcc-10 (10.2.1-6) ...
#8 15.71 Setting up g++-10 (10.2.1-6) ...
#8 15.72 Setting up gcc (4:10.2.1-1) ...
#8 15.74 Setting up g++ (4:10.2.1-1) ...
#8 15.76 update-alternatives: using /usr/bin/g++ to provide /usr/bin/c++ (c++) in auto mode
#8 15.76 Setting up build-essential (12.9) ...
#8 15.77 Processing triggers for libc-bin (2.31-13+deb11u13) ...
#8 DONE 16.0s

#9 [5/9] COPY requirements.txt /tmp/
#9 DONE 0.1s

#10 [6/9] RUN pip install --disable-pip-version-check --no-cache-dir -r /tmp/requirements.txt
#10 0.580 Collecting PyYAML>=6.0
#10 0.692   Downloading PyYAML-6.0.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (751 kB)
#10 0.848      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 751.2/751.2 kB 4.9 MB/s eta 0:00:00
#10 0.891 Collecting accelerate>=0.20.0
#10 0.925   Downloading accelerate-1.9.0-py3-none-any.whl (367 kB)
#10 0.958      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 367.1/367.1 kB 12.3 MB/s eta 0:00:00
#10 0.974 Collecting aiofiles>=23.0.0
#10 1.008   Downloading aiofiles-24.1.0-py3-none-any.whl (15 kB)
#10 1.028 Collecting asyncio-mqtt>=0.16.1
#10 1.062   Downloading asyncio_mqtt-0.16.2-py3-none-any.whl (17 kB)
#10 1.366 Collecting black>=23.7.0
#10 1.403   Downloading black-25.1.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.manylinux_2_28_x86_64.whl (1.8 MB)
#10 1.553      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.8/1.8 MB 11.9 MB/s eta 0:00:00
#10 1.581 Collecting click>=8.1.0
#10 1.616   Downloading click-8.2.1-py3-none-any.whl (102 kB)
#10 1.624      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 102.2/102.2 kB 16.4 MB/s eta 0:00:00
#10 1.662 Collecting datasets>=2.10.0
#10 1.700   Downloading datasets-4.0.0-py3-none-any.whl (494 kB)
#10 1.742      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 494.8/494.8 kB 12.3 MB/s eta 0:00:00
#10 1.822 Collecting fastapi>=0.100.0
#10 1.856   Downloading fastapi-0.116.1-py3-none-any.whl (95 kB)
#10 1.865      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 95.6/95.6 kB 13.0 MB/s eta 0:00:00
#10 2.102 Collecting flake8>=6.0.0
#10 2.136   Downloading flake8-7.3.0-py2.py3-none-any.whl (57 kB)
#10 2.142      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 57.9/57.9 kB 22.4 MB/s eta 0:00:00
#10 2.403 Collecting isort>=5.12.0
#10 2.437   Downloading isort-6.0.1-py3-none-any.whl (94 kB)
#10 2.445      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 94.2/94.2 kB 14.4 MB/s eta 0:00:00
#10 2.466 Collecting librosa>=0.10.0
#10 2.500   Downloading librosa-0.11.0-py3-none-any.whl (260 kB)
#10 2.523      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 260.7/260.7 kB 12.6 MB/s eta 0:00:00
#10 2.776 Collecting matplotlib>=3.7.0
#10 2.810   Downloading matplotlib-3.10.5-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (8.7 MB)
#10 3.556      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.7/8.7 MB 11.6 MB/s eta 0:00:00
#10 3.975 Collecting mypy>=1.5.0
#10 4.011   Downloading mypy-1.17.1-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (12.7 MB)
#10 5.102      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 12.7/12.7 MB 11.6 MB/s eta 0:00:00
#10 5.460 Collecting numpy>=1.24.0
#10 5.495   Downloading numpy-2.2.6-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (16.8 MB)
#10 6.943      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 16.8/16.8 MB 11.6 MB/s eta 0:00:00
#10 7.096 Collecting opencv-python>=4.8.0
#10 7.133   Downloading opencv_python-4.12.0.88-cp37-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (67.0 MB)
#10 12.34      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.0/67.0 MB 11.6 MB/s eta 0:00:00
#10 12.42 Collecting opentelemetry-api>=1.18.0
#10 12.45   Downloading opentelemetry_api-1.36.0-py3-none-any.whl (65 kB)
#10 12.46      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 65.6/65.6 kB 14.1 MB/s eta 0:00:00
#10 12.50 Collecting opentelemetry-sdk>=1.18.0
#10 12.54   Downloading opentelemetry_sdk-1.36.0-py3-none-any.whl (119 kB)
#10 12.55      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 120.0/120.0 kB 15.1 MB/s eta 0:00:00
#10 13.28 Collecting orjson>=3.8.0
#10 13.31   Downloading orjson-3.11.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (131 kB)
#10 13.32      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 131.1/131.1 kB 14.7 MB/s eta 0:00:00
#10 13.54 Collecting pandas>=2.0.0
#10 13.57   Downloading pandas-2.3.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (12.3 MB)
#10 14.64      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 12.3/12.3 MB 11.6 MB/s eta 0:00:00
#10 14.98 Collecting pillow>=10.0.0
#10 15.02   Downloading pillow-11.3.0-cp310-cp310-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (6.6 MB)
#10 15.59      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 6.6/6.6 MB 11.6 MB/s eta 0:00:00
#10 15.83 Collecting prometheus-client>=0.17.0
#10 15.87   Downloading prometheus_client-0.22.1-py3-none-any.whl (58 kB)
#10 15.87      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 58.7/58.7 kB 13.5 MB/s eta 0:00:00
#10 15.88 Requirement already satisfied: psutil>=5.9.0 in /usr/local/lib/python3.10/site-packages (from -r /tmp/requirements.txt (line 25)) (7.0.0)
#10 15.89 Collecting pyaudio>=0.2.11
#10 15.93   Downloading PyAudio-0.2.14.tar.gz (47 kB)
#10 15.93      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47.1/47.1 kB 36.7 MB/s eta 0:00:00
#10 15.95   Installing build dependencies: started
#10 17.69   Installing build dependencies: finished with status 'done'
#10 17.69   Getting requirements to build wheel: started
#10 17.85   Getting requirements to build wheel: finished with status 'done'
#10 17.85   Preparing metadata (pyproject.toml): started
#10 17.99   Preparing metadata (pyproject.toml): finished with status 'done'
#10 18.01 Collecting pybreaker>=1.0.0
#10 18.06   Downloading pybreaker-1.4.0-py3-none-any.whl (12 kB)
#10 18.29 Collecting pydantic==2.5.2
#10 18.33   Downloading pydantic-2.5.2-py3-none-any.whl (381 kB)
#10 18.36      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 381.9/381.9 kB 13.9 MB/s eta 0:00:00
#10 18.61 Collecting pytest-asyncio>=0.21.0
#10 18.66   Downloading pytest_asyncio-1.1.0-py3-none-any.whl (15 kB)
#10 18.76 Collecting pytest>=7.4.0
#10 18.81   Downloading pytest-8.4.1-py3-none-any.whl (365 kB)
#10 18.83      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 365.5/365.5 kB 21.0 MB/s eta 0:00:00
#10 18.85 Collecting python-dotenv>=1.0.0
#10 18.89   Downloading python_dotenv-1.1.1-py3-none-any.whl (20 kB)
#10 19.02 Collecting lz4>=4.0.0
#10 19.05   Downloading lz4-4.4.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (1.3 MB)
#10 19.17      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 10.7 MB/s eta 0:00:00
#10 19.66 Collecting pyzmq==27.0.0
#10 19.69   Downloading pyzmq-27.0.0-cp310-cp310-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (853 kB)
#10 19.77      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 853.8/853.8 kB 11.7 MB/s eta 0:00:00
#10 19.82 Collecting redis>=4.5.0
#10 19.86   Downloading redis-6.3.0-py3-none-any.whl (280 kB)
#10 19.88      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 280.0/280.0 kB 12.5 MB/s eta 0:00:00
#10 19.92 Collecting requests>=2.31.0
#10 19.98   Downloading requests-2.32.4-py3-none-any.whl (64 kB)
#10 19.98      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.8/64.8 kB 318.0 MB/s eta 0:00:00
#10 20.06 Collecting rich>=13.4.0
#10 20.09   Downloading rich-14.1.0-py3-none-any.whl (243 kB)
#10 20.11      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 243.4/243.4 kB 13.0 MB/s eta 0:00:00
#10 20.27 Collecting scikit-learn>=1.3.0
#10 20.31   Downloading scikit_learn-1.7.1-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (9.7 MB)
#10 21.14      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.7/9.7 MB 11.6 MB/s eta 0:00:00
#10 21.39 Collecting speechrecognition>=3.10.0
#10 21.43   Downloading speechrecognition-3.14.3-py3-none-any.whl (32.9 MB)
#10 24.26      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 32.9/32.9 MB 11.6 MB/s eta 0:00:00
#10 24.52 Collecting structlog>=23.1.0
#10 24.57   Downloading structlog-25.4.0-py3-none-any.whl (68 kB)
#10 24.57      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.7/68.7 kB 87.7 MB/s eta 0:00:00
#10 24.81 Collecting tenacity>=8.2.0
#10 24.84   Downloading tenacity-9.1.2-py3-none-any.whl (28 kB)
#10 25.21 Collecting tokenizers>=0.13.0
#10 25.25   Downloading tokenizers-0.21.4-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.1 MB)
#10 25.52      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.1/3.1 MB 11.6 MB/s eta 0:00:00
#10 25.61 Collecting torch>=2.0.0
#10 25.65   Downloading torch-2.8.0-cp310-cp310-manylinux_2_28_x86_64.whl (888.0 MB)
#10 101.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 888.0/888.0 MB 9.6 MB/s eta 0:00:00
#10 102.0 Collecting tqdm>=4.65.0
#10 102.0   Downloading tqdm-4.67.1-py3-none-any.whl (78 kB)
#10 102.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.5/78.5 kB 15.0 MB/s eta 0:00:00
#10 102.1 Collecting transformers>=4.30.0
#10 102.1   Downloading transformers-4.55.0-py3-none-any.whl (11.3 MB)
#10 103.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 11.3/11.3 MB 11.3 MB/s eta 0:00:00
#10 103.2 Collecting typer>=0.9.0
#10 103.2   Downloading typer-0.16.0-py3-none-any.whl (46 kB)
#10 103.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 46.3/46.3 kB 23.9 MB/s eta 0:00:00
#10 103.2 Collecting uvicorn>=0.23.0
#10 103.3   Downloading uvicorn-0.35.0-py3-none-any.whl (66 kB)
#10 103.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66.4/66.4 kB 21.9 MB/s eta 0:00:00
#10 103.7 Collecting websockets>=11.0.0
#10 103.7   Downloading websockets-15.0.1-cp310-cp310-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl (181 kB)
#10 103.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 181.6/181.6 kB 13.3 MB/s eta 0:00:00
#10 103.8 Collecting selenium>=4.21
#10 103.8   Downloading selenium-4.34.2-py3-none-any.whl (9.4 MB)
#10 104.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.4/9.4 MB 11.6 MB/s eta 0:00:00
#10 104.9 Collecting webdriver-manager>=4.0
#10 104.9   Downloading webdriver_manager-4.0.2-py2.py3-none-any.whl (27 kB)
#10 105.1 Collecting beautifulsoup4>=4.12
#10 105.2   Downloading beautifulsoup4-4.13.4-py3-none-any.whl (187 kB)
#10 105.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 187.3/187.3 kB 12.8 MB/s eta 0:00:00
#10 106.2 Collecting aiohttp>=3.9
#10 106.2   Downloading aiohttp-3.12.15-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (1.6 MB)
#10 106.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.6/1.6 MB 11.8 MB/s eta 0:00:00
#10 106.4 Collecting sentence-transformers>=2.5
#10 106.4   Downloading sentence_transformers-5.1.0-py3-none-any.whl (483 kB)
#10 106.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 483.4/483.4 kB 11.8 MB/s eta 0:00:00
#10 106.9 Collecting langchain>=0.1.4
#10 106.9   Downloading langchain-0.3.27-py3-none-any.whl (1.0 MB)
#10 107.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 12.0 MB/s eta 0:00:00
#10 107.0 Collecting networkx>=3.2
#10 107.1   Downloading networkx-3.4.2-py3-none-any.whl (1.7 MB)
#10 107.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.7/1.7 MB 11.7 MB/s eta 0:00:00
#10 107.6 Collecting scipy>=1.12
#10 107.6   Downloading scipy-1.15.3-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (37.7 MB)
#10 110.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 37.7/37.7 MB 11.6 MB/s eta 0:00:00
#10 111.0 Collecting plotly>=5.19
#10 111.0   Downloading plotly-6.2.0-py3-none-any.whl (9.6 MB)
#10 111.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.6/9.6 MB 11.5 MB/s eta 0:00:00
#10 111.9 Collecting streamlit>=1.32
#10 112.0   Downloading streamlit-1.48.0-py3-none-any.whl (9.9 MB)
#10 112.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.9/9.9 MB 11.5 MB/s eta 0:00:00
#10 113.1 Collecting bitsandbytes>=0.41.3
#10 113.1   Downloading bitsandbytes-0.46.1-py3-none-manylinux_2_24_x86_64.whl (72.9 MB)
#10 119.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 72.9/72.9 MB 11.6 MB/s eta 0:00:00
#10 119.9 Collecting peft>=0.7.1
#10 119.9   Downloading peft-0.17.0-py3-none-any.whl (503 kB)
#10 120.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 503.9/503.9 kB 12.2 MB/s eta 0:00:00
#10 120.0 Collecting playwright>=1.42
#10 120.1   Downloading playwright-1.54.0-py3-none-manylinux1_x86_64.whl (45.9 MB)
#10 124.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.9/45.9 MB 11.6 MB/s eta 0:00:00
#10 124.1 Collecting colorama>=0.4.6
#10 124.1   Downloading colorama-0.4.6-py2.py3-none-any.whl (25 kB)
#10 124.2 Collecting jsonschema>=4.0.0
#10 124.2   Downloading jsonschema-4.25.0-py3-none-any.whl (89 kB)
#10 124.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 89.2/89.2 kB 15.3 MB/s eta 0:00:00
#10 124.2 Collecting nltk>=3.8
#10 124.3   Downloading nltk-3.9.1-py3-none-any.whl (1.5 MB)
#10 124.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.5/1.5 MB 11.8 MB/s eta 0:00:00
#10 124.7 Collecting chromadb>=0.4.0
#10 124.7   Downloading chromadb-1.0.15-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (19.5 MB)
#10 125.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 19.5/19.5 MB 11.6 MB/s eta 0:00:00
#10 126.1 Collecting faiss-cpu>=1.7.4
#10 126.1   Downloading faiss_cpu-1.11.0.post1-cp310-cp310-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (31.3 MB)
#10 128.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 31.3/31.3 MB 11.5 MB/s eta 0:00:00
#10 128.9 Requirement already satisfied: typing-extensions>=4.6.1 in /usr/local/lib/python3.10/site-packages (from pydantic==2.5.2->-r /tmp/requirements.txt (line 28)) (4.14.1)
#10 130.3 Collecting pydantic-core==2.14.5
#10 130.3   Downloading pydantic_core-2.14.5-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.1 MB)
#10 130.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.1/2.1 MB 11.7 MB/s eta 0:00:00
#10 130.5 Requirement already satisfied: annotated-types>=0.4.0 in /usr/local/lib/python3.10/site-packages (from pydantic==2.5.2->-r /tmp/requirements.txt (line 28)) (0.7.0)
#10 130.6 Collecting packaging>=20.0
#10 130.6   Downloading packaging-25.0-py3-none-any.whl (66 kB)
#10 130.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66.5/66.5 kB 26.8 MB/s eta 0:00:00
#10 130.8 Collecting safetensors>=0.4.3
#10 130.9   Downloading safetensors-0.6.1-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (485 kB)
#10 130.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 485.9/485.9 kB 12.4 MB/s eta 0:00:00
#10 131.0 Collecting huggingface_hub>=0.21.0
#10 131.0   Downloading huggingface_hub-0.34.3-py3-none-any.whl (558 kB)
#10 131.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 558.8/558.8 kB 12.1 MB/s eta 0:00:00
#10 131.3 Collecting paho-mqtt>=1.6.0
#10 131.3   Downloading paho_mqtt-2.1.0-py3-none-any.whl (67 kB)
#10 131.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.2/67.2 kB 21.7 MB/s eta 0:00:00
#10 131.4 Collecting pathspec>=0.9.0
#10 131.4   Downloading pathspec-0.12.1-py3-none-any.whl (31 kB)
#10 131.7 Collecting tomli>=1.1.0
#10 131.7   Downloading tomli-2.2.1-py3-none-any.whl (14 kB)
#10 131.7 Collecting platformdirs>=2
#10 131.8   Downloading platformdirs-4.3.8-py3-none-any.whl (18 kB)
#10 132.0 Collecting mypy-extensions>=0.4.3
#10 132.0   Downloading mypy_extensions-1.1.0-py3-none-any.whl (5.0 kB)
#10 132.1 Collecting multiprocess<0.70.17
#10 132.2   Downloading multiprocess-0.70.16-py310-none-any.whl (134 kB)
#10 132.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 134.8/134.8 kB 14.5 MB/s eta 0:00:00
#10 132.4 Collecting pyarrow>=15.0.0
#10 132.4   Downloading pyarrow-21.0.0-cp310-cp310-manylinux_2_28_x86_64.whl (42.7 MB)
#10 136.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 42.7/42.7 MB 11.6 MB/s eta 0:00:00
#10 136.3 Collecting xxhash
#10 136.3   Downloading xxhash-3.5.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (194 kB)
#10 136.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 194.1/194.1 kB 12.4 MB/s eta 0:00:00
#10 136.3 Collecting filelock
#10 136.4   Downloading filelock-3.18.0-py3-none-any.whl (16 kB)
#10 136.4 Collecting fsspec[http]<=2025.3.0,>=2023.1.0
#10 136.5   Downloading fsspec-2025.3.0-py3-none-any.whl (193 kB)
#10 136.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 193.6/193.6 kB 11.5 MB/s eta 0:00:00
#10 136.5 Collecting dill<0.3.9,>=0.3.0
#10 136.5   Downloading dill-0.3.8-py3-none-any.whl (116 kB)
#10 136.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 116.3/116.3 kB 15.1 MB/s eta 0:00:00
#10 136.6 Collecting starlette<0.48.0,>=0.40.0
#10 136.7   Downloading starlette-0.47.2-py3-none-any.whl (72 kB)
#10 136.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.0/73.0 kB 18.9 MB/s eta 0:00:00
#10 136.9 Collecting pycodestyle<2.15.0,>=2.14.0
#10 136.9   Downloading pycodestyle-2.14.0-py2.py3-none-any.whl (31 kB)
#10 137.2 Collecting mccabe<0.8.0,>=0.7.0
#10 137.2   Downloading mccabe-0.7.0-py2.py3-none-any.whl (7.3 kB)
#10 137.4 Collecting pyflakes<3.5.0,>=3.4.0
#10 137.5   Downloading pyflakes-3.4.0-py2.py3-none-any.whl (63 kB)
#10 137.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 63.6/63.6 kB 18.4 MB/s eta 0:00:00
#10 137.7 Collecting numba>=0.51.0
#10 137.7   Downloading numba-0.61.2-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (3.8 MB)
#10 138.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.8/3.8 MB 11.7 MB/s eta 0:00:00
#10 138.1 Collecting decorator>=4.3.0
#10 138.1   Downloading decorator-5.2.1-py3-none-any.whl (9.2 kB)
#10 138.1 Collecting soundfile>=0.12.1
#10 138.2   Downloading soundfile-0.13.1-py2.py3-none-manylinux_2_28_x86_64.whl (1.3 MB)
#10 138.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 11.6 MB/s eta 0:00:00
#10 138.4 Collecting msgpack>=1.0
#10 138.4   Downloading msgpack-1.1.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (408 kB)
#10 138.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 408.6/408.6 kB 12.0 MB/s eta 0:00:00
#10 138.5 Collecting lazy_loader>=0.1
#10 138.5   Downloading lazy_loader-0.4-py3-none-any.whl (12 kB)
#10 138.7 Collecting soxr>=0.3.2
#10 138.7   Downloading soxr-0.5.0.post1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (252 kB)
#10 138.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 252.8/252.8 kB 13.4 MB/s eta 0:00:00
#10 138.7 Collecting joblib>=1.0
#10 138.8   Downloading joblib-1.5.1-py3-none-any.whl (307 kB)
#10 138.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 307.7/307.7 kB 21.8 MB/s eta 0:00:00
#10 138.8 Collecting audioread>=2.1.9
#10 138.9   Downloading audioread-3.0.1-py3-none-any.whl (23 kB)
#10 138.9 Collecting pooch>=1.1
#10 139.0   Downloading pooch-1.8.2-py3-none-any.whl (64 kB)
#10 139.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.6/64.6 kB 245.5 MB/s eta 0:00:00
#10 139.4 Collecting fonttools>=4.22.0
#10 139.4   Downloading fonttools-4.59.0-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (4.8 MB)
#10 139.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.8/4.8 MB 11.7 MB/s eta 0:00:00
#10 139.8 Collecting cycler>=0.10
#10 139.9   Downloading cycler-0.12.1-py3-none-any.whl (8.3 kB)
#10 139.9 Collecting python-dateutil>=2.7
#10 139.9   Downloading python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
#10 139.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 229.9/229.9 kB 12.4 MB/s eta 0:00:00
#10 140.1 Collecting contourpy>=1.0.1
#10 140.1   Downloading contourpy-1.3.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (325 kB)
#10 140.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 325.0/325.0 kB 12.7 MB/s eta 0:00:00
#10 140.2 Collecting kiwisolver>=1.3.1
#10 140.3   Downloading kiwisolver-1.4.8-cp310-cp310-manylinux_2_12_x86_64.manylinux2010_x86_64.whl (1.6 MB)
#10 140.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.6/1.6 MB 11.8 MB/s eta 0:00:00
#10 140.5 Collecting pyparsing>=2.3.1
#10 140.5   Downloading pyparsing-3.2.3-py3-none-any.whl (111 kB)
#10 140.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 111.1/111.1 kB 8.4 MB/s eta 0:00:00
#10 140.6 Collecting importlib-metadata<8.8.0,>=6.0
#10 140.6   Downloading importlib_metadata-8.7.0-py3-none-any.whl (27 kB)
#10 140.7 Collecting opentelemetry-semantic-conventions==0.57b0
#10 140.7   Downloading opentelemetry_semantic_conventions-0.57b0-py3-none-any.whl (201 kB)
#10 140.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 201.6/201.6 kB 13.2 MB/s eta 0:00:00
#10 140.9 Collecting pytz>=2020.1
#10 140.9   Downloading pytz-2025.2-py2.py3-none-any.whl (509 kB)
#10 141.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 509.2/509.2 kB 19.2 MB/s eta 0:00:00
#10 141.0 Collecting tzdata>=2022.7
#10 141.0   Downloading tzdata-2025.2-py2.py3-none-any.whl (347 kB)
#10 141.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 347.8/347.8 kB 12.5 MB/s eta 0:00:00
#10 141.4 Collecting backports-asyncio-runner<2,>=1.1
#10 141.4   Downloading backports_asyncio_runner-1.2.0-py3-none-any.whl (12 kB)
#10 141.4 Collecting pygments>=2.7.2
#10 141.5   Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
#10 141.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 11.9 MB/s eta 0:00:00
#10 141.6 Collecting exceptiongroup>=1
#10 141.7   Downloading exceptiongroup-1.3.0-py3-none-any.whl (16 kB)
#10 141.7 Collecting iniconfig>=1
#10 141.7   Downloading iniconfig-2.1.0-py3-none-any.whl (6.0 kB)
#10 141.7 Collecting pluggy<2,>=1.5
#10 141.8   Downloading pluggy-1.6.0-py3-none-any.whl (20 kB)
#10 141.8 Collecting async-timeout>=4.0.3
#10 141.8   Downloading async_timeout-5.0.1-py3-none-any.whl (6.2 kB)
#10 142.0 Collecting charset_normalizer<4,>=2
#10 142.0   Downloading charset_normalizer-3.4.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (149 kB)
#10 142.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 149.5/149.5 kB 11.6 MB/s eta 0:00:00
#10 142.1 Collecting idna<4,>=2.5
#10 142.1   Downloading idna-3.10-py3-none-any.whl (70 kB)
#10 142.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 70.4/70.4 kB 20.9 MB/s eta 0:00:00
#10 142.1 Collecting certifi>=2017.4.17
#10 142.2   Downloading certifi-2025.8.3-py3-none-any.whl (161 kB)
#10 142.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 161.2/161.2 kB 100.2 MB/s eta 0:00:00
#10 142.3 Collecting urllib3<3,>=1.21.1
#10 142.3   Downloading urllib3-2.5.0-py3-none-any.whl (129 kB)
#10 142.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 129.8/129.8 kB 11.7 MB/s eta 0:00:00
#10 142.4 Collecting markdown-it-py>=2.2.0
#10 142.4   Downloading markdown_it_py-3.0.0-py3-none-any.whl (87 kB)
#10 142.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 87.5/87.5 kB 309.0 MB/s eta 0:00:00
#10 142.5 Collecting threadpoolctl>=3.1.0
#10 142.5   Downloading threadpoolctl-3.6.0-py3-none-any.whl (18 kB)
#10 142.6 Collecting jinja2
#10 142.7   Downloading jinja2-3.1.6-py3-none-any.whl (134 kB)
#10 142.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 134.9/134.9 kB 101.0 MB/s eta 0:00:00
#10 142.9 Collecting nvidia-cuda-nvrtc-cu12==12.8.93
#10 143.0   Downloading nvidia_cuda_nvrtc_cu12-12.8.93-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl (88.0 MB)
#10 150.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 88.0/88.0 MB 11.6 MB/s eta 0:00:00
#10 150.8 Collecting nvidia-cuda-cupti-cu12==12.8.90
#10 150.9   Downloading nvidia_cuda_cupti_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (10.2 MB)
#10 151.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.2/10.2 MB 11.6 MB/s eta 0:00:00
#10 152.0 Collecting nvidia-nvjitlink-cu12==12.8.93
#10 152.0   Downloading nvidia_nvjitlink_cu12-12.8.93-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl (39.3 MB)
#10 155.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 39.3/39.3 MB 11.5 MB/s eta 0:00:00
#10 155.6 Collecting nvidia-cuda-runtime-cu12==12.8.90
#10 155.6   Downloading nvidia_cuda_runtime_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (954 kB)
#10 155.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 954.8/954.8 kB 11.5 MB/s eta 0:00:00
#10 155.9 Collecting nvidia-cusparse-cu12==12.5.8.93
#10 155.9   Downloading nvidia_cusparse_cu12-12.5.8.93-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (288.2 MB)
#10 180.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 288.2/288.2 MB 11.6 MB/s eta 0:00:00
#10 180.9 Collecting triton==3.4.0
#10 180.9   Downloading triton-3.4.0-cp310-cp310-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (155.4 MB)
#10 193.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 155.4/155.4 MB 11.6 MB/s eta 0:00:00
#10 194.0 Collecting nvidia-nvtx-cu12==12.8.90
#10 194.0   Downloading nvidia_nvtx_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (89 kB)
#10 194.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 90.0/90.0 kB 16.2 MB/s eta 0:00:00
#10 194.3 Collecting nvidia-cudnn-cu12==9.10.2.21
#10 194.3   Downloading nvidia_cudnn_cu12-9.10.2.21-py3-none-manylinux_2_27_x86_64.whl (706.8 MB)
#10 254.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 706.8/706.8 MB 11.6 MB/s eta 0:00:00
#10 254.9 Collecting nvidia-cufft-cu12==11.3.3.83
#10 254.9   Downloading nvidia_cufft_cu12-11.3.3.83-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (193.1 MB)
#10 271.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 193.1/193.1 MB 11.6 MB/s eta 0:00:00
#10 272.3 Collecting nvidia-cusolver-cu12==11.7.3.90
#10 272.3   Downloading nvidia_cusolver_cu12-11.7.3.90-py3-none-manylinux_2_27_x86_64.whl (267.5 MB)
#10 295.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 267.5/267.5 MB 11.6 MB/s eta 0:00:00
#10 295.5 Collecting nvidia-cufile-cu12==1.13.1.3
#10 295.6   Downloading nvidia_cufile_cu12-1.13.1.3-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (1.2 MB)
#10 295.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 11.6 MB/s eta 0:00:00
#10 295.9 Collecting nvidia-cublas-cu12==12.8.4.1
#10 295.9   Downloading nvidia_cublas_cu12-12.8.4.1-py3-none-manylinux_2_27_x86_64.whl (594.3 MB)
#10 346.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 594.3/594.3 MB 11.6 MB/s eta 0:00:00
#10 346.6 Collecting nvidia-cusparselt-cu12==0.7.1
#10 346.6   Downloading nvidia_cusparselt_cu12-0.7.1-py3-none-manylinux2014_x86_64.whl (287.2 MB)
#10 370.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 287.2/287.2 MB 12.1 MB/s eta 0:00:00
#10 371.3 Collecting nvidia-curand-cu12==10.3.9.90
#10 371.3   Downloading nvidia_curand_cu12-10.3.9.90-py3-none-manylinux_2_27_x86_64.whl (63.6 MB)
#10 376.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 63.6/63.6 MB 11.4 MB/s eta 0:00:00
#10 376.9 Collecting sympy>=1.13.3
#10 377.0   Downloading sympy-1.14.0-py3-none-any.whl (6.3 MB)
#10 377.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 6.3/6.3 MB 11.4 MB/s eta 0:00:00
#10 377.5 Collecting fsspec
#10 377.6   Downloading fsspec-2025.7.0-py3-none-any.whl (199 kB)
#10 377.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 199.6/199.6 kB 12.3 MB/s eta 0:00:00
#10 377.8 Collecting nvidia-nccl-cu12==2.27.3
#10 377.9   Downloading nvidia_nccl_cu12-2.27.3-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (322.4 MB)
#10 405.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 322.4/322.4 MB 14.4 MB/s eta 0:00:00
#10 406.2 Requirement already satisfied: setuptools>=40.8.0 in /usr/local/lib/python3.10/site-packages (from triton==3.4.0->torch>=2.0.0->-r /tmp/requirements.txt (line 44)) (65.5.1)
#10 407.4 Collecting regex!=2019.12.17
#10 407.4   Downloading regex-2025.7.34-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (789 kB)
#10 407.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 789.8/789.8 kB 11.7 MB/s eta 0:00:00
#10 407.5 Collecting shellingham>=1.3.0
#10 407.6   Downloading shellingham-1.5.4-py2.py3-none-any.whl (9.8 kB)
#10 407.6 Collecting h11>=0.8
#10 407.6   Downloading h11-0.16.0-py3-none-any.whl (37 kB)
#10 407.7 Collecting trio~=0.30.0
#10 407.7   Downloading trio-0.30.0-py3-none-any.whl (499 kB)
#10 407.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 499.2/499.2 kB 11.8 MB/s eta 0:00:00
#10 407.8 Collecting websocket-client~=1.8.0
#10 407.8   Downloading websocket_client-1.8.0-py3-none-any.whl (58 kB)
#10 407.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 58.8/58.8 kB 20.3 MB/s eta 0:00:00
#10 407.9 Collecting trio-websocket~=0.12.2
#10 407.9   Downloading trio_websocket-0.12.2-py3-none-any.whl (21 kB)
#10 407.9 Collecting soupsieve>1.2
#10 408.0   Downloading soupsieve-2.7-py3-none-any.whl (36 kB)
#10 408.1 Collecting frozenlist>=1.1.1
#10 408.2   Downloading frozenlist-1.7.0-cp310-cp310-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl (222 kB)
#10 408.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 222.9/222.9 kB 76.1 MB/s eta 0:00:00
#10 408.2 Collecting aiosignal>=1.4.0
#10 408.2   Downloading aiosignal-1.4.0-py3-none-any.whl (7.5 kB)
#10 408.2 Collecting attrs>=17.3.0
#10 408.3   Downloading attrs-25.3.0-py3-none-any.whl (63 kB)
#10 408.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 63.8/63.8 kB 24.0 MB/s eta 0:00:00
#10 408.8 Collecting yarl<2.0,>=1.17.0
#10 408.8   Downloading yarl-1.20.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (326 kB)
#10 408.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 326.1/326.1 kB 12.7 MB/s eta 0:00:00
#10 409.3 Collecting multidict<7.0,>=4.5
#10 409.3   Downloading multidict-6.6.3-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (241 kB)
#10 409.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 241.6/241.6 kB 13.0 MB/s eta 0:00:00
#10 409.4 Collecting aiohappyeyeballs>=2.5.0
#10 409.4   Downloading aiohappyeyeballs-2.6.1-py3-none-any.whl (15 kB)
#10 409.5 Collecting propcache>=0.2.0
#10 409.6   Downloading propcache-0.3.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (198 kB)
#10 409.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 198.3/198.3 kB 13.3 MB/s eta 0:00:00
#10 410.2 Collecting SQLAlchemy<3,>=1.4
#10 410.2   Downloading sqlalchemy-2.0.42-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.2 MB)
#10 410.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.2/3.2 MB 11.7 MB/s eta 0:00:00
#10 410.6 Collecting langchain>=0.1.4
#10 410.6   Downloading langchain-0.3.26-py3-none-any.whl (1.0 MB)
#10 410.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.6 MB/s eta 0:00:00
#10 410.7   Downloading langchain-0.3.25-py3-none-any.whl (1.0 MB)
#10 410.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.8 MB/s eta 0:00:00
#10 410.9 Collecting langchain-core<1.0.0,>=0.3.58
#10 411.0   Downloading langchain_core-0.3.72-py3-none-any.whl (442 kB)
#10 411.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 442.8/442.8 kB 24.4 MB/s eta 0:00:00
#10 411.0 Collecting langchain>=0.1.4
#10 411.1   Downloading langchain-0.3.24-py3-none-any.whl (1.0 MB)
#10 411.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.9 MB/s eta 0:00:00
#10 411.2   Downloading langchain-0.3.23-py3-none-any.whl (1.0 MB)
#10 411.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.8 MB/s eta 0:00:00
#10 411.4   Downloading langchain-0.3.22-py3-none-any.whl (1.0 MB)
#10 411.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.7 MB/s eta 0:00:00
#10 411.5   Downloading langchain-0.3.21-py3-none-any.whl (1.0 MB)
#10 411.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.5 MB/s eta 0:00:00
#10 411.7   Downloading langchain-0.3.20-py3-none-any.whl (1.0 MB)
#10 411.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.7 MB/s eta 0:00:00
#10 411.8   Downloading langchain-0.3.19-py3-none-any.whl (1.0 MB)
#10 411.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.8 MB/s eta 0:00:00
#10 412.0   Downloading langchain-0.3.18-py3-none-any.whl (1.0 MB)
#10 412.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.7 MB/s eta 0:00:00
#10 412.1   Downloading langchain-0.3.17-py3-none-any.whl (1.0 MB)
#10 412.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.8 MB/s eta 0:00:00
#10 412.3   Downloading langchain-0.3.16-py3-none-any.whl (1.0 MB)
#10 412.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.8 MB/s eta 0:00:00
#10 412.4   Downloading langchain-0.3.15-py3-none-any.whl (1.0 MB)
#10 412.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.8 MB/s eta 0:00:00
#10 412.6   Downloading langchain-0.3.14-py3-none-any.whl (1.0 MB)
#10 412.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.7 MB/s eta 0:00:00
#10 412.7   Downloading langchain-0.3.13-py3-none-any.whl (1.0 MB)
#10 412.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.6 MB/s eta 0:00:00
#10 412.9   Downloading langchain-0.3.12-py3-none-any.whl (1.0 MB)
#10 413.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.8 MB/s eta 0:00:00
#10 413.0   Downloading langchain-0.3.11-py3-none-any.whl (1.0 MB)
#10 413.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 9.4 MB/s eta 0:00:00
#10 413.2   Downloading langchain-0.3.10-py3-none-any.whl (1.0 MB)
#10 413.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.7 MB/s eta 0:00:00
#10 413.3   Downloading langchain-0.3.9-py3-none-any.whl (1.0 MB)
#10 413.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.8 MB/s eta 0:00:00
#10 413.5   Downloading langchain-0.3.8-py3-none-any.whl (1.0 MB)
#10 413.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 12.2 MB/s eta 0:00:00
#10 413.6   Downloading langchain-0.3.7-py3-none-any.whl (1.0 MB)
#10 413.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.7 MB/s eta 0:00:00
#10 414.1   Downloading langchain-0.3.6-py3-none-any.whl (1.0 MB)
#10 414.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.9 MB/s eta 0:00:00
#10 414.2   Downloading langchain-0.3.5-py3-none-any.whl (1.0 MB)
#10 414.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.8 MB/s eta 0:00:00
#10 414.3   Downloading langchain-0.3.4-py3-none-any.whl (1.0 MB)
#10 414.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.6 MB/s eta 0:00:00
#10 414.5   Downloading langchain-0.3.3-py3-none-any.whl (1.0 MB)
#10 414.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.7 MB/s eta 0:00:00
#10 414.6   Downloading langchain-0.3.2-py3-none-any.whl (1.0 MB)
#10 414.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.6 MB/s eta 0:00:00
#10 414.8   Downloading langchain-0.3.1-py3-none-any.whl (1.0 MB)
#10 414.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.7 MB/s eta 0:00:00
#10 414.9   Downloading langchain-0.3.0-py3-none-any.whl (1.0 MB)
#10 415.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.2 MB/s eta 0:00:00
#10 415.1   Downloading langchain-0.2.17-py3-none-any.whl (1.0 MB)
#10 415.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.7 MB/s eta 0:00:00
#10 415.2   Downloading langchain-0.2.16-py3-none-any.whl (1.0 MB)
#10 415.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.8 MB/s eta 0:00:00
#10 415.4   Downloading langchain-0.2.15-py3-none-any.whl (1.0 MB)
#10 415.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.8 MB/s eta 0:00:00
#10 415.5 Collecting langchain-core<0.3.0,>=0.2.35
#10 415.5   Downloading langchain_core-0.2.43-py3-none-any.whl (397 kB)
#10 415.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 397.1/397.1 kB 12.6 MB/s eta 0:00:00
#10 415.6 Collecting langchain>=0.1.4
#10 415.6   Downloading langchain-0.2.14-py3-none-any.whl (997 kB)
#10 415.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 997.8/997.8 kB 11.8 MB/s eta 0:00:00
#10 415.7   Downloading langchain-0.2.13-py3-none-any.whl (997 kB)
#10 415.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 997.8/997.8 kB 11.6 MB/s eta 0:00:00
#10 415.9   Downloading langchain-0.2.12-py3-none-any.whl (990 kB)
#10 416.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 990.6/990.6 kB 11.6 MB/s eta 0:00:00
#10 416.3   Downloading langchain-0.2.11-py3-none-any.whl (990 kB)
#10 416.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 990.3/990.3 kB 11.8 MB/s eta 0:00:00
#10 416.4   Downloading langchain-0.2.10-py3-none-any.whl (990 kB)
#10 416.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 990.0/990.0 kB 12.2 MB/s eta 0:00:00
#10 416.6   Downloading langchain-0.2.9-py3-none-any.whl (987 kB)
#10 416.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 987.7/987.7 kB 11.7 MB/s eta 0:00:00
#10 416.7   Downloading langchain-0.2.8-py3-none-any.whl (987 kB)
#10 416.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 987.6/987.6 kB 11.7 MB/s eta 0:00:00
#10 417.1   Downloading langchain-0.2.7-py3-none-any.whl (983 kB)
#10 417.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 983.6/983.6 kB 11.8 MB/s eta 0:00:00
#10 417.3   Downloading langchain-0.2.6-py3-none-any.whl (975 kB)
#10 417.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 975.5/975.5 kB 11.6 MB/s eta 0:00:00
#10 417.4   Downloading langchain-0.2.5-py3-none-any.whl (974 kB)
#10 417.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 974.6/974.6 kB 11.6 MB/s eta 0:00:00
#10 417.5   Downloading langchain-0.2.4-py3-none-any.whl (974 kB)
#10 417.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 974.2/974.2 kB 11.9 MB/s eta 0:00:00
#10 417.7   Downloading langchain-0.2.3-py3-none-any.whl (974 kB)
#10 417.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 974.0/974.0 kB 11.7 MB/s eta 0:00:00
#10 417.8 Collecting langchain-text-splitters<0.3.0,>=0.2.0
#10 417.8   Downloading langchain_text_splitters-0.2.4-py3-none-any.whl (25 kB)
#10 417.8 Collecting async-timeout>=4.0.3
#10 417.9   Downloading async_timeout-4.0.3-py3-none-any.whl (5.7 kB)
#10 418.0 Collecting langsmith<0.2.0,>=0.1.17
#10 418.1   Downloading langsmith-0.1.147-py3-none-any.whl (311 kB)
#10 418.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 311.8/311.8 kB 12.8 MB/s eta 0:00:00
#10 418.1 Collecting langchain>=0.1.4
#10 418.1   Downloading langchain-0.2.2-py3-none-any.whl (973 kB)
#10 418.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 973.6/973.6 kB 11.7 MB/s eta 0:00:00
#10 418.3   Downloading langchain-0.2.1-py3-none-any.whl (973 kB)
#10 418.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 973.5/973.5 kB 11.8 MB/s eta 0:00:00
#10 418.5   Downloading langchain-0.2.0-py3-none-any.whl (973 kB)
#10 418.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 973.7/973.7 kB 11.9 MB/s eta 0:00:00
#10 418.9 Collecting dataclasses-json<0.7,>=0.5.7
#10 419.0   Downloading dataclasses_json-0.6.7-py3-none-any.whl (28 kB)
#10 419.0 Collecting langchain>=0.1.4
#10 419.0   Downloading langchain-0.1.20-py3-none-any.whl (1.0 MB)
#10 419.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.7 MB/s eta 0:00:00
#10 419.2 Collecting langchain-community<0.1,>=0.0.38
#10 419.3   Downloading langchain_community-0.0.38-py3-none-any.whl (2.0 MB)
#10 419.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.0/2.0 MB 11.6 MB/s eta 0:00:00
#10 419.5 Collecting langchain>=0.1.4
#10 419.5   Downloading langchain-0.1.19-py3-none-any.whl (1.0 MB)
#10 419.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 11.6 MB/s eta 0:00:00
#10 419.7   Downloading langchain-0.1.17-py3-none-any.whl (867 kB)
#10 419.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 867.6/867.6 kB 11.7 MB/s eta 0:00:00
#10 419.9 Collecting jsonpatch<2.0,>=1.33
#10 419.9   Downloading jsonpatch-1.33-py2.py3-none-any.whl (12 kB)
#10 419.9 Collecting langchain-core<0.2.0,>=0.1.48
#10 420.0   Downloading langchain_core-0.1.53-py3-none-any.whl (303 kB)
#10 420.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 303.1/303.1 kB 12.8 MB/s eta 0:00:00
#10 420.0 Collecting langchain>=0.1.4
#10 420.0   Downloading langchain-0.1.16-py3-none-any.whl (817 kB)
#10 419.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 817.7/817.7 kB 11.9 MB/s eta 0:00:00
#10 420.0 Collecting langchain-text-splitters<0.1,>=0.0.1
#10 420.1   Downloading langchain_text_splitters-0.0.2-py3-none-any.whl (23 kB)
#10 420.1 Collecting langchain>=0.1.4
#10 420.1   Downloading langchain-0.1.15-py3-none-any.whl (814 kB)
#10 419.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 814.5/814.5 kB 11.5 MB/s eta 0:00:00
#10 419.9   Downloading langchain-0.1.14-py3-none-any.whl (812 kB)
#10 420.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 812.8/812.8 kB 11.7 MB/s eta 0:00:00
#10 420.1   Downloading langchain-0.1.13-py3-none-any.whl (810 kB)
#10 420.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 810.5/810.5 kB 11.7 MB/s eta 0:00:00
#10 420.3   Downloading langchain-0.1.12-py3-none-any.whl (809 kB)
#10 420.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 809.1/809.1 kB 11.7 MB/s eta 0:00:00
#10 420.5   Downloading langchain-0.1.11-py3-none-any.whl (807 kB)
#10 420.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 807.5/807.5 kB 11.9 MB/s eta 0:00:00
#10 420.7   Downloading langchain-0.1.10-py3-none-any.whl (806 kB)
#10 420.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 806.2/806.2 kB 11.7 MB/s eta 0:00:00
#10 420.9   Downloading langchain-0.1.9-py3-none-any.whl (816 kB)
#10 421.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 817.0/817.0 kB 11.7 MB/s eta 0:00:00
#10 421.4   Downloading langchain-0.1.8-py3-none-any.whl (816 kB)
#10 421.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 816.1/816.1 kB 12.0 MB/s eta 0:00:00
#10 421.8   Downloading langchain-0.1.7-py3-none-any.whl (815 kB)
#10 421.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 815.9/815.9 kB 11.9 MB/s eta 0:00:00
#10 422.0 Collecting langsmith<0.1,>=0.0.83
#10 422.0   Downloading langsmith-0.0.92-py3-none-any.whl (56 kB)
#10 422.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 56.5/56.5 kB 14.1 MB/s eta 0:00:00
#10 422.0 Collecting langchain>=0.1.4
#10 422.1   Downloading langchain-0.1.6-py3-none-any.whl (811 kB)
#10 422.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 811.8/811.8 kB 12.0 MB/s eta 0:00:00
#10 422.3   Downloading langchain-0.1.5-py3-none-any.whl (806 kB)
#10 422.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 806.7/806.7 kB 8.2 MB/s eta 0:00:00
#10 422.5   Downloading langchain-0.1.4-py3-none-any.whl (803 kB)
#10 422.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 803.6/803.6 kB 12.0 MB/s eta 0:00:00
#10 422.7 INFO: pip is looking at multiple versions of sentence-transformers to determine which version is compatible with other requirements. This could take a while.
#10 422.7 Collecting sentence-transformers>=2.5
#10 422.7   Downloading sentence_transformers-5.0.0-py3-none-any.whl (470 kB)
#10 422.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 470.2/470.2 kB 11.9 MB/s eta 0:00:00
#10 422.9 INFO: pip is looking at multiple versions of aiohttp to determine which version is compatible with other requirements. This could take a while.
#10 422.9 Collecting aiohttp>=3.9
#10 422.9   Downloading aiohttp-3.12.14-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (1.6 MB)
#10 423.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.6/1.6 MB 11.8 MB/s eta 0:00:00
#10 423.1 INFO: pip is looking at multiple versions of beautifulsoup4 to determine which version is compatible with other requirements. This could take a while.
#10 423.1 Collecting beautifulsoup4>=4.12
#10 423.2   Downloading beautifulsoup4-4.13.3-py3-none-any.whl (186 kB)
#10 423.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 186.0/186.0 kB 12.5 MB/s eta 0:00:00
#10 423.3 INFO: pip is looking at multiple versions of webdriver-manager to determine which version is compatible with other requirements. This could take a while.
#10 423.3 Collecting webdriver-manager>=4.0
#10 423.3   Downloading webdriver_manager-4.0.1-py2.py3-none-any.whl (27 kB)
#10 423.4 INFO: pip is looking at multiple versions of selenium to determine which version is compatible with other requirements. This could take a while.
#10 423.4 Collecting selenium>=4.21
#10 423.5   Downloading selenium-4.34.1-py3-none-any.whl (9.4 MB)
#10 424.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.4/9.4 MB 11.6 MB/s eta 0:00:00
#10 424.4 INFO: pip is looking at multiple versions of websockets to determine which version is compatible with other requirements. This could take a while.
#10 424.4 Collecting websockets>=11.0.0
#10 424.4   Downloading websockets-15.0-cp310-cp310-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl (180 kB)
#10 424.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 180.9/180.9 kB 13.0 MB/s eta 0:00:00
#10 424.5 INFO: pip is looking at multiple versions of uvicorn to determine which version is compatible with other requirements. This could take a while.
#10 424.5 Collecting uvicorn>=0.23.0
#10 424.5   Downloading uvicorn-0.34.3-py3-none-any.whl (62 kB)
#10 424.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 62.4/62.4 kB 21.3 MB/s eta 0:00:00
#10 424.6 INFO: pip is looking at multiple versions of typer to determine which version is compatible with other requirements. This could take a while.
#10 424.6 Collecting typer>=0.9.0
#10 424.7   Downloading typer-0.15.4-py3-none-any.whl (45 kB)
#10 424.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.3/45.3 kB 17.0 MB/s eta 0:00:00
#10 424.8 INFO: pip is looking at multiple versions of transformers to determine which version is compatible with other requirements. This could take a while.
#10 424.8 Collecting transformers>=4.30.0
#10 424.8   Downloading transformers-4.54.1-py3-none-any.whl (11.2 MB)
#10 425.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 11.2/11.2 MB 11.6 MB/s eta 0:00:00
#10 426.3   Downloading transformers-4.54.0-py3-none-any.whl (11.2 MB)
#10 427.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 11.2/11.2 MB 11.6 MB/s eta 0:00:00
#10 427.9   Downloading transformers-4.53.3-py3-none-any.whl (10.8 MB)
#10 428.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.8/10.8 MB 12.4 MB/s eta 0:00:00
#10 429.3   Downloading transformers-4.53.2-py3-none-any.whl (10.8 MB)
#10 430.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.8/10.8 MB 11.5 MB/s eta 0:00:00
#10 430.8   Downloading transformers-4.53.1-py3-none-any.whl (10.8 MB)
#10 431.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.8/10.8 MB 11.5 MB/s eta 0:00:00
#10 432.3   Downloading transformers-4.53.0-py3-none-any.whl (10.8 MB)
#10 433.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.8/10.8 MB 11.8 MB/s eta 0:00:00
#10 433.7   Downloading transformers-4.52.4-py3-none-any.whl (10.5 MB)
#10 434.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.5/10.5 MB 11.5 MB/s eta 0:00:00
#10 435.1 INFO: pip is looking at multiple versions of transformers to determine which version is compatible with other requirements. This could take a while.
#10 435.1   Downloading transformers-4.52.3-py3-none-any.whl (10.5 MB)
#10 436.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.5/10.5 MB 11.5 MB/s eta 0:00:00
#10 436.6   Downloading transformers-4.52.2-py3-none-any.whl (10.5 MB)
#10 437.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.5/10.5 MB 11.6 MB/s eta 0:00:00
#10 438.2   Downloading transformers-4.52.1-py3-none-any.whl (10.5 MB)
#10 439.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.5/10.5 MB 11.6 MB/s eta 0:00:00
#10 439.9   Downloading transformers-4.51.3-py3-none-any.whl (10.4 MB)
#10 440.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.4/10.4 MB 11.6 MB/s eta 0:00:00
#10 441.3   Downloading transformers-4.51.2-py3-none-any.whl (10.4 MB)
#10 442.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.4/10.4 MB 11.6 MB/s eta 0:00:00
#10 442.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 442.7   Downloading transformers-4.51.1-py3-none-any.whl (10.4 MB)
#10 443.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.4/10.4 MB 12.3 MB/s eta 0:00:00
#10 444.1   Downloading transformers-4.51.0-py3-none-any.whl (10.4 MB)
#10 445.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.4/10.4 MB 11.6 MB/s eta 0:00:00
#10 445.5   Downloading transformers-4.50.3-py3-none-any.whl (10.2 MB)
#10 446.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.2/10.2 MB 11.6 MB/s eta 0:00:00
#10 446.9   Downloading transformers-4.50.2-py3-none-any.whl (10.2 MB)
#10 447.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.2/10.2 MB 11.5 MB/s eta 0:00:00
#10 448.3   Downloading transformers-4.50.1-py3-none-any.whl (10.2 MB)
#10 449.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.2/10.2 MB 11.6 MB/s eta 0:00:00
#10 449.3   Downloading transformers-4.50.0-py3-none-any.whl (10.2 MB)
#10 449.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.2/10.2 MB 11.6 MB/s eta 0:00:00
#10 450.2   Downloading transformers-4.49.0-py3-none-any.whl (10.0 MB)
#10 451.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.0/10.0 MB 11.6 MB/s eta 0:00:00
#10 451.6   Downloading transformers-4.48.3-py3-none-any.whl (9.7 MB)
#10 452.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.7/9.7 MB 11.6 MB/s eta 0:00:00
#10 452.9   Downloading transformers-4.48.2-py3-none-any.whl (9.7 MB)
#10 453.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.7/9.7 MB 11.5 MB/s eta 0:00:00
#10 454.3   Downloading transformers-4.48.1-py3-none-any.whl (9.7 MB)
#10 455.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.7/9.7 MB 11.4 MB/s eta 0:00:00
#10 455.6   Downloading transformers-4.48.0-py3-none-any.whl (9.7 MB)
#10 456.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.7/9.7 MB 11.4 MB/s eta 0:00:00
#10 457.3   Downloading transformers-4.47.1-py3-none-any.whl (10.1 MB)
#10 458.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.1/10.1 MB 11.6 MB/s eta 0:00:00
#10 458.7   Downloading transformers-4.47.0-py3-none-any.whl (10.1 MB)
#10 459.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.1/10.1 MB 11.4 MB/s eta 0:00:00
#10 460.0   Downloading transformers-4.46.3-py3-none-any.whl (10.0 MB)
#10 460.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.0/10.0 MB 11.6 MB/s eta 0:00:00
#10 461.5 Collecting tokenizers>=0.13.0
#10 461.6   Downloading tokenizers-0.20.3-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.0 MB)
#10 461.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.0/3.0 MB 11.6 MB/s eta 0:00:00
#10 461.9 Collecting transformers>=4.30.0
#10 462.0   Downloading transformers-4.46.2-py3-none-any.whl (10.0 MB)
#10 462.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.0/10.0 MB 11.6 MB/s eta 0:00:00
#10 463.3   Downloading transformers-4.46.1-py3-none-any.whl (10.0 MB)
#10 464.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.0/10.0 MB 11.5 MB/s eta 0:00:00
#10 464.7   Downloading transformers-4.45.2-py3-none-any.whl (9.9 MB)
#10 465.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.9/9.9 MB 10.7 MB/s eta 0:00:00
#10 466.1   Downloading transformers-4.45.1-py3-none-any.whl (9.9 MB)
#10 467.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.9/9.9 MB 11.6 MB/s eta 0:00:00
#10 467.5   Downloading transformers-4.45.0-py3-none-any.whl (9.9 MB)
#10 468.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.9/9.9 MB 11.5 MB/s eta 0:00:00
#10 468.8   Downloading transformers-4.44.2-py3-none-any.whl (9.5 MB)
#10 469.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.5/9.5 MB 11.5 MB/s eta 0:00:00
#10 470.0 Collecting tokenizers>=0.13.0
#10 470.0   Downloading tokenizers-0.19.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.6 MB)
#10 470.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.6/3.6 MB 11.6 MB/s eta 0:00:00
#10 470.5 Collecting transformers>=4.30.0
#10 470.5   Downloading transformers-4.44.1-py3-none-any.whl (9.5 MB)
#10 471.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.5/9.5 MB 11.3 MB/s eta 0:00:00
#10 471.8   Downloading transformers-4.44.0-py3-none-any.whl (9.5 MB)
#10 472.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.5/9.5 MB 11.4 MB/s eta 0:00:00
#10 473.5   Downloading transformers-4.43.4-py3-none-any.whl (9.4 MB)
#10 474.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.4/9.4 MB 11.3 MB/s eta 0:00:00
#10 474.8   Downloading transformers-4.43.3-py3-none-any.whl (9.4 MB)
#10 475.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.4/9.4 MB 11.6 MB/s eta 0:00:00
#10 476.1   Downloading transformers-4.43.2-py3-none-any.whl (9.4 MB)
#10 476.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.4/9.4 MB 11.6 MB/s eta 0:00:00
#10 477.3   Downloading transformers-4.43.1-py3-none-any.whl (9.4 MB)
#10 478.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.4/9.4 MB 9.2 MB/s eta 0:00:00
#10 478.6   Downloading transformers-4.43.0-py3-none-any.whl (9.4 MB)
#10 479.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.4/9.4 MB 8.6 MB/s eta 0:00:00
#10 479.7   Downloading transformers-4.42.4-py3-none-any.whl (9.3 MB)
#10 480.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.3/9.3 MB 11.0 MB/s eta 0:00:00
#10 481.0   Downloading transformers-4.42.3-py3-none-any.whl (9.3 MB)
#10 481.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.3/9.3 MB 11.3 MB/s eta 0:00:00
#10 482.1   Downloading transformers-4.42.2-py3-none-any.whl (9.3 MB)
#10 483.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.3/9.3 MB 9.9 MB/s eta 0:00:00
#10 483.6   Downloading transformers-4.42.1-py3-none-any.whl (9.3 MB)
#10 484.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.3/9.3 MB 7.8 MB/s eta 0:00:00
#10 485.4   Downloading transformers-4.42.0-py3-none-any.whl (9.3 MB)
#10 486.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.3/9.3 MB 11.6 MB/s eta 0:00:00
#10 486.6   Downloading transformers-4.41.2-py3-none-any.whl (9.1 MB)
#10 487.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.1/9.1 MB 11.6 MB/s eta 0:00:00
#10 487.8   Downloading transformers-4.41.1-py3-none-any.whl (9.1 MB)
#10 488.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.1/9.1 MB 11.4 MB/s eta 0:00:00
#10 489.1   Downloading transformers-4.41.0-py3-none-any.whl (9.1 MB)
#10 489.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.1/9.1 MB 11.7 MB/s eta 0:00:00
#10 490.8   Downloading transformers-4.40.2-py3-none-any.whl (9.0 MB)
#10 491.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.0/9.0 MB 11.6 MB/s eta 0:00:00
#10 492.1   Downloading transformers-4.40.1-py3-none-any.whl (9.0 MB)
#10 493.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.0/9.0 MB 4.8 MB/s eta 0:00:00
#10 494.4   Downloading transformers-4.40.0-py3-none-any.whl (9.0 MB)
#10 495.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.0/9.0 MB 11.3 MB/s eta 0:00:00
#10 495.7   Downloading transformers-4.39.3-py3-none-any.whl (8.8 MB)
#10 496.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.8/8.8 MB 9.6 MB/s eta 0:00:00
#10 497.0 Collecting tokenizers>=0.13.0
#10 497.0   Downloading tokenizers-0.15.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.6 MB)
#10 497.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.6/3.6 MB 11.6 MB/s eta 0:00:00
#10 497.5 Collecting transformers>=4.30.0
#10 497.5   Downloading transformers-4.39.2-py3-none-any.whl (8.8 MB)
#10 498.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.8/8.8 MB 11.5 MB/s eta 0:00:00
#10 498.8   Downloading transformers-4.39.1-py3-none-any.whl (8.8 MB)
#10 500.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.8/8.8 MB 6.7 MB/s eta 0:00:00
#10 500.6   Downloading transformers-4.39.0-py3-none-any.whl (8.8 MB)
#10 501.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.8/8.8 MB 11.6 MB/s eta 0:00:00
#10 501.9   Downloading transformers-4.38.2-py3-none-any.whl (8.5 MB)
#10 502.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.5/8.5 MB 11.6 MB/s eta 0:00:00
#10 503.1   Downloading transformers-4.38.1-py3-none-any.whl (8.5 MB)
#10 503.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.5/8.5 MB 11.6 MB/s eta 0:00:00
#10 504.4   Downloading transformers-4.38.0-py3-none-any.whl (8.5 MB)
#10 505.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.5/8.5 MB 11.6 MB/s eta 0:00:00
#10 505.6   Downloading transformers-4.37.2-py3-none-any.whl (8.4 MB)
#10 506.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.4/8.4 MB 11.6 MB/s eta 0:00:00
#10 506.9   Downloading transformers-4.37.1-py3-none-any.whl (8.4 MB)
#10 507.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.4/8.4 MB 11.9 MB/s eta 0:00:00
#10 507.9   Downloading transformers-4.37.0-py3-none-any.whl (8.4 MB)
#10 508.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.4/8.4 MB 11.6 MB/s eta 0:00:00
#10 508.7   Downloading transformers-4.36.2-py3-none-any.whl (8.2 MB)
#10 509.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.2/8.2 MB 11.6 MB/s eta 0:00:00
#10 509.9   Downloading transformers-4.36.1-py3-none-any.whl (8.3 MB)
#10 510.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.3/8.3 MB 11.6 MB/s eta 0:00:00
#10 511.2   Downloading transformers-4.36.0-py3-none-any.whl (8.2 MB)
#10 511.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.2/8.2 MB 11.6 MB/s eta 0:00:00
#10 512.4   Downloading transformers-4.35.2-py3-none-any.whl (7.9 MB)
#10 513.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.9/7.9 MB 11.6 MB/s eta 0:00:00
#10 513.6   Downloading transformers-4.35.1-py3-none-any.whl (7.9 MB)
#10 514.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.9/7.9 MB 11.6 MB/s eta 0:00:00
#10 514.6 Collecting tokenizers>=0.13.0
#10 514.6   Downloading tokenizers-0.14.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.8 MB)
#10 514.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.8/3.8 MB 11.6 MB/s eta 0:00:00
#10 515.1 Collecting transformers>=4.30.0
#10 515.1   Downloading transformers-4.35.0-py3-none-any.whl (7.9 MB)
#10 515.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.9/7.9 MB 11.6 MB/s eta 0:00:00
#10 516.3   Downloading transformers-4.34.1-py3-none-any.whl (7.7 MB)
#10 517.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.7/7.7 MB 11.5 MB/s eta 0:00:00
#10 517.5   Downloading transformers-4.34.0-py3-none-any.whl (7.7 MB)
#10 518.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.7/7.7 MB 11.5 MB/s eta 0:00:00
#10 518.7   Downloading transformers-4.33.3-py3-none-any.whl (7.6 MB)
#10 519.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.6/7.6 MB 9.3 MB/s eta 0:00:00
#10 520.2 Collecting tokenizers>=0.13.0
#10 520.3   Downloading tokenizers-0.13.3-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (7.8 MB)
#10 521.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.8/7.8 MB 11.5 MB/s eta 0:00:00
#10 521.1 Collecting transformers>=4.30.0
#10 521.2   Downloading transformers-4.33.2-py3-none-any.whl (7.6 MB)
#10 521.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.6/7.6 MB 11.5 MB/s eta 0:00:00
#10 522.4   Downloading transformers-4.33.1-py3-none-any.whl (7.6 MB)
#10 523.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.6/7.6 MB 11.5 MB/s eta 0:00:00
#10 523.6   Downloading transformers-4.33.0-py3-none-any.whl (7.6 MB)
#10 524.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.6/7.6 MB 11.5 MB/s eta 0:00:00
#10 524.8   Downloading transformers-4.32.1-py3-none-any.whl (7.5 MB)
#10 525.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.5/7.5 MB 11.6 MB/s eta 0:00:00
#10 525.9   Downloading transformers-4.32.0-py3-none-any.whl (7.5 MB)
#10 526.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.5/7.5 MB 11.6 MB/s eta 0:00:00
#10 527.0   Downloading transformers-4.31.0-py3-none-any.whl (7.4 MB)
#10 527.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.4/7.4 MB 11.6 MB/s eta 0:00:00
#10 528.2   Downloading transformers-4.30.2-py3-none-any.whl (7.2 MB)
#10 528.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.2/7.2 MB 11.6 MB/s eta 0:00:00
#10 529.3   Downloading transformers-4.30.1-py3-none-any.whl (7.2 MB)
#10 530.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.2/7.2 MB 10.6 MB/s eta 0:00:00
#10 530.5   Downloading transformers-4.30.0-py3-none-any.whl (7.2 MB)
#10 531.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.2/7.2 MB 11.6 MB/s eta 0:00:00
#10 531.6 INFO: pip is looking at multiple versions of tqdm to determine which version is compatible with other requirements. This could take a while.
#10 531.6 Collecting tqdm>=4.65.0
#10 531.6   Downloading tqdm-4.67.0-py3-none-any.whl (78 kB)
#10 531.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.6/78.6 kB 18.6 MB/s eta 0:00:00
#10 532.5   Downloading tqdm-4.66.6-py3-none-any.whl (78 kB)
#10 532.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.3/78.3 kB 13.5 MB/s eta 0:00:00
#10 542.2 INFO: pip is looking at multiple versions of triton to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-nvtx-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-nvjitlink-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-nccl-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-cusparselt-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-cusparse-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-cusolver-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-curand-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-cufile-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-cufft-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-cudnn-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-cuda-runtime-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-cuda-nvrtc-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-cuda-cupti-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of nvidia-cublas-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 542.2 INFO: pip is looking at multiple versions of torch to determine which version is compatible with other requirements. This could take a while.
#10 542.2 Collecting torch>=2.0.0
#10 542.2   Downloading torch-2.7.1-cp310-cp310-manylinux_2_28_x86_64.whl (821.2 MB)
#10 612.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 821.2/821.2 MB 11.5 MB/s eta 0:00:00
#10 613.1 Collecting nvidia-cuda-nvrtc-cu12==12.6.77
#10 613.1   Downloading nvidia_cuda_nvrtc_cu12-12.6.77-py3-none-manylinux2014_x86_64.whl (23.7 MB)
#10 615.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 23.7/23.7 MB 11.5 MB/s eta 0:00:00
#10 615.2 Collecting nvidia-cublas-cu12==12.6.4.1
#10 615.3   Downloading nvidia_cublas_cu12-12.6.4.1-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (393.1 MB)
#10 648.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 393.1/393.1 MB 11.6 MB/s eta 0:00:00
#10 648.9 Collecting nvidia-nvtx-cu12==12.6.77
#10 649.0   Downloading nvidia_nvtx_cu12-12.6.77-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (89 kB)
#10 649.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 89.3/89.3 kB 60.0 MB/s eta 0:00:00
#10 649.0 Collecting nvidia-cusparselt-cu12==0.6.3
#10 649.0   Downloading nvidia_cusparselt_cu12-0.6.3-py3-none-manylinux2014_x86_64.whl (156.8 MB)
#10 662.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 156.8/156.8 MB 11.4 MB/s eta 0:00:00
#10 662.1 Collecting nvidia-cuda-runtime-cu12==12.6.77
#10 662.1   Downloading nvidia_cuda_runtime_cu12-12.6.77-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (897 kB)
#10 662.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 897.7/897.7 kB 11.9 MB/s eta 0:00:00
#10 662.2 Collecting nvidia-nvjitlink-cu12==12.6.85
#10 662.2   Downloading nvidia_nvjitlink_cu12-12.6.85-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl (19.7 MB)
#10 664.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 19.7/19.7 MB 11.6 MB/s eta 0:00:00
#10 664.0 Collecting nvidia-nccl-cu12==2.26.2
#10 664.0   Downloading nvidia_nccl_cu12-2.26.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (201.3 MB)
#10 681.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 201.3/201.3 MB 11.5 MB/s eta 0:00:00
#10 681.6 Collecting nvidia-cuda-cupti-cu12==12.6.80
#10 681.7   Downloading nvidia_cuda_cupti_cu12-12.6.80-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (8.9 MB)
#10 682.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.9/8.9 MB 11.6 MB/s eta 0:00:00
#10 682.4 Collecting triton==3.3.1
#10 682.5   Downloading triton-3.3.1-cp310-cp310-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (155.6 MB)
#10 695.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 155.6/155.6 MB 11.4 MB/s eta 0:00:00
#10 695.4 Collecting nvidia-cusolver-cu12==11.7.1.2
#10 695.4   Downloading nvidia_cusolver_cu12-11.7.1.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (158.2 MB)
#10 709.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 158.2/158.2 MB 11.2 MB/s eta 0:00:00
#10 709.3 Collecting nvidia-cufft-cu12==11.3.0.4
#10 709.4   Downloading nvidia_cufft_cu12-11.3.0.4-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (200.2 MB)
#10 725.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 200.2/200.2 MB 11.5 MB/s eta 0:00:00
#10 726.1 Collecting nvidia-curand-cu12==10.3.7.77
#10 726.1   Downloading nvidia_curand_cu12-10.3.7.77-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (56.3 MB)
#10 731.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 56.3/56.3 MB 11.5 MB/s eta 0:00:00
#10 731.1 Collecting nvidia-cusparse-cu12==12.5.4.2
#10 731.1   Downloading nvidia_cusparse_cu12-12.5.4.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (216.6 MB)
#10 749.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 216.6/216.6 MB 11.6 MB/s eta 0:00:00
#10 749.3 Collecting nvidia-cufile-cu12==1.11.1.6
#10 749.4   Downloading nvidia_cufile_cu12-1.11.1.6-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (1.1 MB)
#10 749.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 11.7 MB/s eta 0:00:00
#10 749.5 Collecting nvidia-cudnn-cu12==9.5.1.17
#10 749.5   Downloading nvidia_cudnn_cu12-9.5.1.17-py3-none-manylinux_2_28_x86_64.whl (571.0 MB)
#10 799.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 571.0/571.0 MB 10.5 MB/s eta 0:00:00
#10 800.6 Collecting torch>=2.0.0
#10 800.6   Downloading torch-2.7.0-cp310-cp310-manylinux_2_28_x86_64.whl (865.2 MB)
#10 874.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 865.2/865.2 MB 11.4 MB/s eta 0:00:00
#10 884.9 INFO: pip is looking at multiple versions of tokenizers to determine which version is compatible with other requirements. This could take a while.
#10 884.9 Collecting tokenizers>=0.13.0
#10 884.9   Downloading tokenizers-0.21.2-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.1 MB)
#10 885.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.1/3.1 MB 11.6 MB/s eta 0:00:00
#10 886.4   Downloading tokenizers-0.21.1-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.0 MB)
#10 886.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.0/3.0 MB 11.6 MB/s eta 0:00:00
#10 896.1 INFO: pip is looking at multiple versions of tenacity to determine which version is compatible with other requirements. This could take a while.
#10 896.1 Collecting tenacity>=8.2.0
#10 896.1   Downloading tenacity-9.0.0-py3-none-any.whl (28 kB)
#10 897.4   Downloading tenacity-8.5.0-py3-none-any.whl (28 kB)
#10 907.6 INFO: pip is looking at multiple versions of structlog to determine which version is compatible with other requirements. This could take a while.
#10 907.6 Collecting structlog>=23.1.0
#10 907.7   Downloading structlog-25.3.0-py3-none-any.whl (68 kB)
#10 907.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.2/68.2 kB 13.8 MB/s eta 0:00:00
#10 909.2   Downloading structlog-25.2.0-py3-none-any.whl (68 kB)
#10 909.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.4/68.4 kB 19.9 MB/s eta 0:00:00
#10 919.5 INFO: pip is looking at multiple versions of speechrecognition to determine which version is compatible with other requirements. This could take a while.
#10 919.5 Collecting speechrecognition>=3.10.0
#10 919.6   Downloading speechrecognition-3.14.2-py3-none-any.whl (32.9 MB)
#10 922.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 32.9/32.9 MB 12.0 MB/s eta 0:00:00
#10 923.8   Downloading SpeechRecognition-3.14.1-py3-none-any.whl (32.9 MB)
#10 926.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 32.9/32.9 MB 11.8 MB/s eta 0:00:00
#10 936.8 INFO: pip is looking at multiple versions of scikit-learn to determine which version is compatible with other requirements. This could take a while.
#10 936.8 Collecting scikit-learn>=1.3.0
#10 936.9   Downloading scikit_learn-1.7.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (12.9 MB)
#10 938.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 12.9/12.9 MB 11.6 MB/s eta 0:00:00
#10 938.3 INFO: pip is looking at multiple versions of sentence-transformers to determine which version is compatible with other requirements. This could take a while.
#10 938.5 INFO: pip is looking at multiple versions of aiohttp to determine which version is compatible with other requirements. This could take a while.
#10 938.5 INFO: pip is looking at multiple versions of beautifulsoup4 to determine which version is compatible with other requirements. This could take a while.
#10 938.6 INFO: pip is looking at multiple versions of webdriver-manager to determine which version is compatible with other requirements. This could take a while.
#10 938.7 INFO: pip is looking at multiple versions of selenium to determine which version is compatible with other requirements. This could take a while.
#10 938.8 INFO: pip is looking at multiple versions of websockets to determine which version is compatible with other requirements. This could take a while.
#10 938.9 INFO: pip is looking at multiple versions of uvicorn to determine which version is compatible with other requirements. This could take a while.
#10 939.0 INFO: pip is looking at multiple versions of typer to determine which version is compatible with other requirements. This could take a while.
#10 939.1 INFO: pip is looking at multiple versions of tqdm to determine which version is compatible with other requirements. This could take a while.
#10 949.3   Downloading scikit_learn-1.6.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (13.5 MB)
#10 950.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 13.5/13.5 MB 11.8 MB/s eta 0:00:00
#10 951.7 INFO: pip is looking at multiple versions of triton to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-nvtx-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-nvjitlink-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-nccl-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-cusparselt-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-cusparse-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-cusolver-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-curand-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-cufile-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-cufft-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-cudnn-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-cuda-runtime-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-cuda-nvrtc-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-cuda-cupti-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of nvidia-cublas-cu12 to determine which version is compatible with other requirements. This could take a while.
#10 951.7 INFO: pip is looking at multiple versions of torch to determine which version is compatible with other requirements. This could take a while.
#10 962.7   Downloading scikit_learn-1.6.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (13.5 MB)
#10 963.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 13.5/13.5 MB 11.3 MB/s eta 0:00:00
#10 965.1 INFO: pip is looking at multiple versions of tokenizers to determine which version is compatible with other requirements. This could take a while.
#10 975.5   Downloading scikit_learn-1.5.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (13.3 MB)
#10 976.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 13.3/13.3 MB 11.6 MB/s eta 0:00:00
#10 977.3 INFO: pip is looking at multiple versions of tenacity to determine which version is compatible with other requirements. This could take a while.
#10 987.5   Downloading scikit_learn-1.5.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (13.4 MB)
#10 988.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 13.4/13.4 MB 11.6 MB/s eta 0:00:00
#10 990.5 INFO: pip is looking at multiple versions of structlog to determine which version is compatible with other requirements. This could take a while.
#10 1000.5   Downloading scikit_learn-1.5.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (13.3 MB)
#10 1001.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 13.3/13.3 MB 13.9 MB/s eta 0:00:00
#10 1002.0 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1002.1 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1002.2 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1002.3 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1002.3 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1002.4 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1002.5 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1002.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1002.7 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1003.1 INFO: pip is looking at multiple versions of speechrecognition to determine which version is compatible with other requirements. This could take a while.
#10 1012.4   Downloading scikit_learn-1.4.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (12.1 MB)
#10 1013.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 12.1/12.1 MB 11.6 MB/s eta 0:00:00
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1014.6 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1025.1 INFO: pip is looking at multiple versions of scikit-learn to determine which version is compatible with other requirements. This could take a while.
#10 1025.2   Downloading scikit_learn-1.4.1.post1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (12.1 MB)
#10 1026.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 12.1/12.1 MB 11.6 MB/s eta 0:00:00
#10 1026.3   Downloading scikit_learn-1.4.0-1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (12.1 MB)
#10 1027.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 12.1/12.1 MB 11.5 MB/s eta 0:00:00
#10 1027.4   Downloading scikit_learn-1.3.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (10.8 MB)
#10 1028.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.8/10.8 MB 11.5 MB/s eta 0:00:00
#10 1028.5   Downloading scikit_learn-1.3.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (10.8 MB)
#10 1029.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.8/10.8 MB 11.2 MB/s eta 0:00:00
#10 1029.5   Downloading scikit_learn-1.3.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (10.8 MB)
#10 1030.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.8/10.8 MB 11.5 MB/s eta 0:00:00
#10 1031.7 INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
#10 1041.5 INFO: pip is looking at multiple versions of rich to determine which version is compatible with other requirements. This could take a while.
#10 1041.5 Collecting rich>=13.4.0
#10 1041.5   Downloading rich-14.0.0-py3-none-any.whl (243 kB)
#10 1041.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 243.2/243.2 kB 27.2 MB/s eta 0:00:00