FROM python:3.11
LABEL org.opencontainers.image.source=https://github.com/hardbyte/netcheck
RUN pip install netcheck
CMD netcheck http -v