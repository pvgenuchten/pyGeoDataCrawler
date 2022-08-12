FROM osgeo/gdal:ubuntu-full-3.3.2

# ARGS
ARG TIMEZONE="Europe/Amsterdam"
ARG LOCALE="en_US.UTF-8"
#nano, sync for operations 
ARG ADD_DEB_PACKAGES="nano nmap rsync"
#for sld creation
ARG ADD_PIP_PACKAGES=""

ENV TZ=${TIMEZONE} \
	DEBIAN_FRONTEND="noninteractive" \
	DEB_BUILD_DEPS="tzdata build-essential apt-utils" \
	DEB_PACKAGES="locales python3-gdal ${ADD_DEB_PACKAGES}"

RUN \
	# Install dependencies
	apt-get update \
	&& apt-get --no-install-recommends install -y ${DEB_BUILD_DEPS} ${DEB_PACKAGES} \
	# Timezone
	&& cp /usr/share/zoneinfo/${TZ} /etc/localtime\
	&& dpkg-reconfigure tzdata \
	# Locale
	&& sed -i -e "s/# ${LOCALE} UTF-8/${LOCALE} UTF-8/" /etc/locale.gen \
	&& dpkg-reconfigure --frontend=noninteractive locales \
	&& update-locale LANG=${LOCALE} \
	&& echo "For ${TZ} date=$(date)" && echo "Locale=$(locale)" 

COPY . /pyGeoDataCrawler

RUN apt --no-install-recommends install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt --no-install-recommends install -y python3.9 python3-pip
RUN pip install poetry
WORKDIR /pyGeoDataCrawler 
RUN poetry install

RUN crawl-metadata --help

ENTRYPOINT ["tail", "-f", "/dev/null"]