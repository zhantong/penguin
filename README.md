# Penguin

## 调试运行

```bash
flask run
```

## 下载安装javascript依赖

```bash
flask download_js_packages
```

## 初始化数据库

```bash
flask deploy
```

## 导入Typecho数据

### 导出Typecho数据为统一中间表示

```bash
python migrations/typecho/Dump.py
```

得到`dump.json`，此时将Typecho的`usr`文件夹复制到`dump.json`同一目录下。

### 导入中间表示数据

```bash
flask restore --file-path /path/to/json
```

## 本地SSL调试

### 生成证书

新建`openssl.conf`文件：

```ini
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no
[req_distinguished_name]
C = US
ST = VA
L = SomeCity
O = MyCompany
OU = MyDivision
CN = localhost
[v3_req]
keyUsage = critical, digitalSignature, keyAgreement
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = localhost
IP.2 = 127.0.0.1
```

命令行运行：

```shell
openssl req -x509 -nodes -days 730 -newkey rsa:2048 -keyout cert.key -out cert.pem -config /path/to/openssl.conf -sha256
```

这时会生成两个文件`cert.key`和`cert.pem`。

### `flask`添加SSL参数

在原`flask run`命令基础上增加参数，即：

```shell
flask run --cert cert.pem --key cert.key
```

### 信任证书

1. Chrome访问`https://127.0.0.1:5000/`
2. 点击地址栏前的红色删除线的锁
3. 点击“证书”
4. 在弹出的对话框中按住“证书图标”并拖至桌面
5. 双击出现在桌面的`localhost.cer`文件
6. 在弹出的“钥匙串”中添加此证书
7. 证书右键点击“显示简介”
8. 展开“信任”选项卡，将“使用此证书时”设置为“始终信任”

## 完成

重新访问`https://127.0.0.1:5000/`即无证书警告，此时地址栏前有绿色的锁。
