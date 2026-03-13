FROM ghcr.io/osgeo/gdal:ubuntu-small-3.12.2

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV VENV=/opt/venv
ENV PATH="$VENV/bin:$PATH"
ENV pgdc_schema_path=/opt/venv/lib/python3.12/site-packages/geodatacrawler/schemas

# Install Python and minimal build dependencies
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    python3 \
    git \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# create virtualenv
RUN python3 -m venv $VENV

# upgrade tooling
# RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python GDAL bindings matching system GDAL
RUN GDAL_VERSION=$(gdal-config --version | cut -d. -f1-2) \
 && pip install --no-cache-dir "GDAL==${GDAL_VERSION}.*"

# Install pycsw
RUN pip install --no-cache-dir "SQLAlchemy<2.0.0"
RUN pip install --no-cache-dir git+https://github.com/geopython/pycsw.git@master
RUN pip install --no-cache-dir geodatacrawler==1.3.12

# Default command
CMD ["crawl-metadata", "--help"]
