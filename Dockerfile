FROM fedora:32

RUN yum -y update; \
    yum install -y python3-aiohttp; \
    yum install -y python3-pytest; \
	yum install -y python3-pytest-aiohttp

WORKDIR /var/www/html

COPY . /var/www/html
	 
RUN chmod +x /var/www/html/app.py; \
    chmod +x /var/www/html/nshandler.py; \
	chmod +x /var/www/html/nstester.py

RUN ln -sf /usr/share/zoneinfo/Asia/Yekaterinburg /etc/localtime

ENTRYPOINT ["python3", "/var/www/html/app.py"]

EXPOSE 8080