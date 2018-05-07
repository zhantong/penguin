# Penguin

## 调试运行

```bash
flask run
```

## 初始化数据库

```bash
flask deploy
```

## 导入Typecho数据

```bash
flask migrate --application-name typecho --db-url "mysql+pymysql://root:password@localhost/typecho?charset=utf8" --upload-parent-directory-path /path/to/typecho
```
