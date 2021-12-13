FROM python:3

# Ensure that the python output is sent straight to terminal
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /npdb
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . /npdb

ENTRYPOINT ["/bin/sh", "-c" , "python manage.py makemigrations cdb_rest && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
CMD ["/bin/bash"]
