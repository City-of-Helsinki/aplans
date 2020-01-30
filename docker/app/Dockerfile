FROM ubuntu:19.10

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV STATIC_ROOT /srv/static
ENV MEDIA_ROOT /srv/media

RUN mkdir /code
RUN mkdir -p /srv/media

# Install PostgreSQL 11
RUN apt-get update
RUN apt-get install -y gnupg wget lsb-release software-properties-common
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1 apt-key add -
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -sc)-pgdg main" > /etc/apt/sources.list.d/postgres.list
RUN apt-get update
RUN apt-get install -y python3.8 python3-pip libpython3.8-dev \
	postgresql-client-common postgresql-client libpq-dev \
	gettext git-core \
	zlib1g-dev libjpeg8-dev libtiff-dev libopenjp2-7-dev libwebp-dev \
	voikko-fi libhfstospell10
RUN wget http://ftp.fi.debian.org/debian/pool/main/libv/libvoikko/libvoikko1_4.3-1_amd64.deb && \
    dpkg -i libvoikko1_4.3-1_amd64.deb

RUN ln -fs /usr/bin/python3.8 /usr/bin/python3
RUN ln -fs /usr/bin/python3 /usr/bin/python
RUN ln -fs /usr/bin/pip3 /usr/bin/pip
RUN pip install --upgrade pip
COPY requirements.txt requirements-prod.txt /code/
RUN pip install -r /code/requirements-prod.txt -r /code/requirements.txt

COPY . /code/
WORKDIR /code
RUN ./manage.py collectstatic --no-input
RUN ./manage.py compilemessages
COPY ./docker/app/docker-entrypoint.sh /
COPY ./docker/app/wait-for-it.sh /

CMD ["/bin/bash", "/docker-entrypoint.sh"]
