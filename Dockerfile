FROM python:3.11
LABEL org.opencontainers.image.source=https://github.com/hardbyte/netcheck
COPY ./pyproject.toml poetry.lock* /opt/netcheck/
COPY netcheck /opt/netcheck
RUN pip install -e /opt/netcheck

CMD netcheck http -v
