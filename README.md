# Cian Predicter
Parser for Cian.ru rental data.

```shell
docker build -t cian-parser .
```

```shell
docker run --rm -v "$(pwd)/data:/app/data" -v "$(pwd)/logs:/app/logs" cian-parser
```
