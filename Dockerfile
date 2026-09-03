FROM python:3.12

ENV PYTHONUNBUFFERED=1


WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install gunicorn

COPY . .
RUN chmod +x startup.sh

CMD ["/app/startup.sh"]
