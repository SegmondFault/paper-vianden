FROM mariadb:10.11

ENV MYSQL_ROOT_PASSWORD=S3cretDB!2024
ENV MYSQL_DATABASE=acme_corp
ENV MYSQL_USER=app_user
ENV MYSQL_PASSWORD=S3cretDB!2024

COPY sql/init.sql /docker-entrypoint-initdb.d/

EXPOSE 3306
