# Centos8安装Python3.12.2

1.下载Python3.12.2Linux版安装包

```shell
#安装包地址
https://www.python.org/ftp/python/

#使用wget下载安装包
wget https://www.python.org/ftp/python/3.13.2/Python-3.13.2.tgz
```

2.准备编译环境

```shell
yum install -y gcc zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel xz-devel libffi-devel
```

3.编译安装

```shell

./configure --prefix=/usr/local/bin/python3 --enable-optimizations
```

