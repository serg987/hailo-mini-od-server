FROM ubuntu:22.04

# python install part is taken from https://techkamar.medium.com/how-to-deploy-specific-version-of-python-using-docker-96d387c16779

WORKDIR /app

RUN mkdir /opt/python3.10

# To avoid .pyc files and save space
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# fix tzdata dialog https://grigorkh.medium.com/fix-tzdata-hangs-docker-image-build-cdb52cc3360d
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install all dependencies you need to compile Python3.10 and then a wheel for Hailo
RUN apt update
RUN apt install -y wget libffi-dev gcc build-essential curl tcl-dev tk-dev uuid-dev lzma-dev liblzma-dev libssl-dev libsqlite3-dev python3.10-dev dkms

# Download Python source code from official site and build it
RUN wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz
RUN tar -zxvf Python-3.10.0.tgz
RUN cd Python-3.10.0 && ./configure --prefix=/opt/python3.10 && make && make install

# Delete the python source code and temp files
RUN rm Python-3.10.0.tgz
RUN rm -r Python-3.10.0/

# Now link it so that $python works
RUN ln -s /opt/python3.10/bin/python3.10 /usr/bin/python

# update pip
RUN python -m pip install --upgrade pip

# copy some files to the image
RUN mkdir hailo_assets
COPY requirements.txt /app/
COPY hailo_assets/ /app/hailo_assets/

# compile HailoRT wheel
RUN python -m pip install ./hailo_assets/hailort-4.18.0-cp310-cp310-linux_x86_64.whl

RUN python -m pip install -r requirements.txt

# remove copied files to save some space
RUN rm -rf hailo_assets
