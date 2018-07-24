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
