FROM python:3
ADD . /app
WORKDIR /app
RUN pip3 install -r requirements.txt
CMD ["python", "app.py"]
