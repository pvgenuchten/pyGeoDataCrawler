#FROM harbor.containers.wurnet.nl/isric/pycsw
#locally, build pcsw image first as docker build -t isric/pycsw .
#FROM isric/pycsw:latest
FROM geopython/pycsw

USER root

# ARGS
ARG TIMEZONE="Europe/Amsterdam"
ARG LOCALE="en_US.UTF-8"
#nano, sync for operations 
ARG ADD_DEB_PACKAGES="nano nmap rsync sqlite3 software-properties-common"
#for sld creation
ARG ADD_PIP_PACKAGES=""

ENV TZ=${TIMEZONE} \
	DEBIAN_FRONTEND="noninteractive" \
	DEB_BUILD_DEPS="tzdata build-essential apt-utils" \
	DEB_PACKAGES="locales python3-pip gdal-bin libgdal-dev python3-dev ${ADD_DEB_PACKAGES}"

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

RUN ogrinfo --version

RUN pip install GDAL==3.6.2
RUN pip install geodatacrawler==1.3.4

ENTRYPOINT ["tail", "-f", "/dev/null"]